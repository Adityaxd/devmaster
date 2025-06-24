"""
Project Management Service

Core service for managing project lifecycle, state, and operations.
"""

from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timezone
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import Project, ProjectStatus, ProjectType
from app.services.file_system import FileSystemService, ProjectFileManager
from app.core.events import EventBus, EventType
from app.database import get_async_db

logger = logging.getLogger(__name__)


class ProjectService:
    """
    Service for managing projects.
    
    Handles:
    - Project creation and configuration
    - Project state management
    - File system integration
    - Project lifecycle operations
    """
    
    def __init__(
        self, 
        event_bus: EventBus,
        file_system_service: FileSystemService,
        project_file_manager: ProjectFileManager
    ):
        self.event_bus = event_bus
        self.fs_service = file_system_service
        self.file_manager = project_file_manager
    
    async def create_project(
        self,
        name: str,
        description: str,
        project_type: ProjectType,
        owner_id: UUID,
        technology_stack: Optional[Dict[str, str]] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Create a new project.
        
        This includes:
        - Database record creation
        - File system initialization
        - Initial configuration
        """
        should_close_db = False
        if db is None:
            db = await get_async_db().__anext__()
            should_close_db = True
        
        try:
            # Create project record
            project = Project(
                name=name,
                description=description,
                project_type=project_type,
                owner_id=owner_id,
                technology_stack=technology_stack or self._get_default_stack(project_type),
                settings={
                    "auto_save": True,
                    "validation_level": "strict",
                    "deployment_target": None
                }
            )
            
            db.add(project)
            await db.commit()
            await db.refresh(project)
            
            # Initialize file system
            fs_result = await self.fs_service.initialize_project_structure(
                str(project.id)
            )
            
            if not fs_result["success"]:
                # Rollback on file system error
                await db.delete(project)
                await db.commit()
                return {
                    "success": False,
                    "error": f"Failed to initialize file system: {fs_result['error']}"
                }
            
            # Update project with file structure
            project.file_structure = fs_result["virtual_fs"]
            await db.commit()
            
            # Emit event
            await self.event_bus.emit(
                EventType.PROJECT_CREATED,
                {
                    "project_id": str(project.id),
                    "name": project.name,
                    "type": project.project_type.value,
                    "owner_id": str(project.owner_id)
                }
            )
            
            return {
                "success": True,
                "project": {
                    "id": str(project.id),
                    "name": project.name,
                    "description": project.description,
                    "type": project.project_type.value,
                    "status": project.status.value,
                    "created_at": project.created_at.isoformat(),
                    "file_system_path": fs_result["project_path"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            await db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if should_close_db:
                await db.close()
    
    async def get_project(
        self,
        project_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Get project details."""
        should_close_db = False
        if db is None:
            db = await get_async_db().__anext__()
            should_close_db = True
        
        try:
            result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            
            if not project:
                return {
                    "success": False,
                    "error": "Project not found"
                }
            
            # Get current file system state
            vfs_result = await self.fs_service.get_virtual_file_system(
                str(project.id)
            )
            
            return {
                "success": True,
                "project": {
                    "id": str(project.id),
                    "name": project.name,
                    "description": project.description,
                    "type": project.project_type.value,
                    "status": project.status.value,
                    "technology_stack": project.technology_stack,
                    "settings": project.settings,
                    "created_at": project.created_at.isoformat(),
                    "updated_at": project.updated_at.isoformat(),
                    "is_deployed": project.is_deployed,
                    "deployment_url": project.deployment_url,
                    "file_structure": vfs_result.get("virtual_fs") if vfs_result["success"] else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting project: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if should_close_db:
                await db.close()
    
    async def update_project_state(
        self,
        project_id: UUID,
        updates: Dict[str, Any],
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Update project state and metadata."""
        should_close_db = False
        if db is None:
            db = await get_async_db().__anext__()
            should_close_db = True
        
        try:
            result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            
            if not project:
                return {
                    "success": False,
                    "error": "Project not found"
                }
            
            # Update allowed fields
            allowed_fields = [
                "name", "description", "status", "technology_stack",
                "settings", "deployment_config", "is_deployed",
                "deployment_url", "repository_url"
            ]
            
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(project, field, value)
            
            await db.commit()
            
            # Emit event
            await self.event_bus.emit(
                EventType.PROJECT_UPDATED,
                {
                    "project_id": str(project.id),
                    "updates": updates
                }
            )
            
            return {
                "success": True,
                "message": "Project updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating project: {str(e)}")
            await db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if should_close_db:
                await db.close()
    
    async def save_generated_artifacts(
        self,
        project_id: UUID,
        artifacts: Dict[str, Any],
        agent_name: str
    ) -> Dict[str, Any]:
        """Save generated code artifacts to project."""
        # Use file manager to save artifacts
        result = await self.file_manager.save_generated_code(
            str(project_id),
            artifacts,
            agent_name
        )
        
        if result["success"]:
            # Update project metadata
            await self.update_project_state(
                project_id,
                {
                    "updated_at": datetime.now(timezone.utc)
                }
            )
        
        return result
    
    async def get_project_files(
        self,
        project_id: UUID,
        organized: bool = False
    ) -> Dict[str, Any]:
        """Get project files, optionally organized by type."""
        if organized:
            return await self.file_manager.organize_by_type(str(project_id))
        else:
            return await self.fs_service.get_virtual_file_system(str(project_id))
    
    async def archive_project(
        self,
        project_id: UUID,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Archive a project."""
        # Create backup snapshot
        snapshot_result = await self.file_manager.create_backup_snapshot(
            str(project_id)
        )
        
        if not snapshot_result["success"]:
            return snapshot_result
        
        # Update project status
        return await self.update_project_state(
            project_id,
            {
                "status": ProjectStatus.ARCHIVED,
                "settings": {
                    "archived_at": datetime.now(timezone.utc).isoformat(),
                    "snapshot_id": snapshot_result["snapshot_id"]
                }
            },
            db
        )
    
    async def list_user_projects(
        self,
        owner_id: UUID,
        status: Optional[ProjectStatus] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """List all projects for a user."""
        should_close_db = False
        if db is None:
            db = await get_async_db().__anext__()
            should_close_db = True
        
        try:
            query = select(Project).where(Project.owner_id == owner_id)
            
            if status:
                query = query.where(Project.status == status)
            
            result = await db.execute(query.order_by(Project.created_at.desc()))
            projects = result.scalars().all()
            
            return {
                "success": True,
                "projects": [
                    {
                        "id": str(p.id),
                        "name": p.name,
                        "description": p.description,
                        "type": p.project_type.value,
                        "status": p.status.value,
                        "created_at": p.created_at.isoformat(),
                        "updated_at": p.updated_at.isoformat(),
                        "is_deployed": p.is_deployed
                    }
                    for p in projects
                ]
            }
            
        except Exception as e:
            logger.error(f"Error listing projects: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if should_close_db:
                await db.close()
    
    def _get_default_stack(self, project_type: ProjectType) -> Dict[str, str]:
        """Get default technology stack for project type."""
        stacks = {
            ProjectType.FULLSTACK_WEB: {
                "backend": "FastAPI",
                "frontend": "React + TypeScript",
                "database": "PostgreSQL",
                "styling": "Tailwind CSS",
                "deployment": "Docker"
            },
            ProjectType.API_ONLY: {
                "backend": "FastAPI",
                "database": "PostgreSQL",
                "documentation": "OpenAPI",
                "deployment": "Docker"
            },
            ProjectType.FRONTEND_ONLY: {
                "frontend": "React + TypeScript",
                "styling": "Tailwind CSS",
                "build": "Vite",
                "deployment": "Vercel"
            },
            ProjectType.CLI_TOOL: {
                "language": "Python",
                "framework": "Click",
                "packaging": "Poetry",
                "deployment": "PyPI"
            },
            ProjectType.LIBRARY: {
                "language": "Python",
                "packaging": "Poetry",
                "testing": "pytest",
                "deployment": "PyPI"
            },
            ProjectType.MICROSERVICE: {
                "backend": "FastAPI",
                "database": "PostgreSQL",
                "messaging": "Redis",
                "deployment": "Kubernetes"
            }
        }
        
        return stacks.get(project_type, {})
