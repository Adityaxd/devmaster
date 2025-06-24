"""
Project File Manager

Higher-level file management operations for projects.
Handles code generation artifacts and file organization.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import logging
from datetime import datetime, timezone

from app.services.file_system.file_system_service import FileSystemService, FileOperation
from app.core.events import EventBus, EventType

logger = logging.getLogger(__name__)


class ProjectFileManager:
    """
    Manages project files at a higher level.
    
    Handles:
    - Code artifact storage
    - File organization by type
    - Template application
    - Bulk operations
    """
    
    def __init__(self, file_system_service: FileSystemService, event_bus: EventBus):
        self.fs_service = file_system_service
        self.event_bus = event_bus
    
    async def save_generated_code(
        self,
        project_id: str,
        artifacts: Dict[str, Any],
        agent_name: str
    ) -> Dict[str, Any]:
        """
        Save generated code artifacts from an agent.
        
        Args:
            project_id: The project ID
            artifacts: Dictionary of file paths to content
            agent_name: Name of the agent that generated the code
        """
        operations = []
        
        try:
            # Convert artifacts to file operations
            for file_path, content in artifacts.items():
                # Ensure proper path format
                if isinstance(content, dict):
                    # Handle structured artifacts
                    if "content" in content:
                        actual_content = content["content"]
                    else:
                        actual_content = json.dumps(content, indent=2)
                else:
                    actual_content = str(content)
                
                operations.append(FileOperation(
                    operation="create",
                    path=file_path,
                    content=actual_content,
                    metadata={
                        "agent": agent_name,
                        "generated_at": datetime.now(timezone.utc).isoformat()
                    }
                ))
            
            # Execute operations atomically
            result = await self.fs_service.execute_atomic_operations(
                project_id,
                operations
            )
            
            if result["success"]:
                # Emit event
                await self.event_bus.emit(
                    EventType.CODE_GENERATED,
                    {
                        "project_id": project_id,
                        "agent": agent_name,
                        "files_count": len(operations),
                        "files": list(artifacts.keys())
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error saving generated code: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def organize_by_type(self, project_id: str) -> Dict[str, Any]:
        """
        Organize project files by type (models, services, routers, etc.).
        
        Returns a structured view of the project.
        """
        try:
            vfs_result = await self.fs_service.get_virtual_file_system(project_id)
            
            if not vfs_result["success"]:
                return vfs_result
            
            vfs = vfs_result["virtual_fs"]
            
            # Categorize files
            organized = {
                "backend": {
                    "models": [],
                    "services": [],
                    "routers": [],
                    "schemas": [],
                    "tests": [],
                    "other": []
                },
                "frontend": {
                    "components": [],
                    "pages": [],
                    "services": [],
                    "styles": [],
                    "tests": [],
                    "other": []
                },
                "config": [],
                "docs": [],
                "scripts": []
            }
            
            # Traverse the virtual file system
            await self._categorize_files(vfs, organized, "")
            
            return {
                "success": True,
                "organized": organized,
                "stats": {
                    "total_files": sum(
                        len(files) for category in organized.values()
                        for files in (category.values() if isinstance(category, dict) else [category])
                        if isinstance(files, list)
                    )
                }
            }
            
        except Exception as e:
            logger.error(f"Error organizing files: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _categorize_files(
        self, 
        node: Dict[str, Any], 
        organized: Dict[str, Any],
        current_path: str
    ):
        """Recursively categorize files in the virtual file system."""
        if node["type"] == "file":
            file_info = {
                "name": node["name"],
                "path": current_path + "/" + node["name"] if current_path else node["name"],
                "size": node["size"]
            }
            
            # Categorize based on path and extension
            if "backend" in current_path:
                if "models" in current_path:
                    organized["backend"]["models"].append(file_info)
                elif "services" in current_path:
                    organized["backend"]["services"].append(file_info)
                elif "routers" in current_path:
                    organized["backend"]["routers"].append(file_info)
                elif "schemas" in current_path:
                    organized["backend"]["schemas"].append(file_info)
                elif "tests" in current_path:
                    organized["backend"]["tests"].append(file_info)
                else:
                    organized["backend"]["other"].append(file_info)
            elif "frontend" in current_path:
                if "components" in current_path:
                    organized["frontend"]["components"].append(file_info)
                elif "pages" in current_path:
                    organized["frontend"]["pages"].append(file_info)
                elif "services" in current_path:
                    organized["frontend"]["services"].append(file_info)
                elif node["name"].endswith((".css", ".scss", ".sass")):
                    organized["frontend"]["styles"].append(file_info)
                elif "tests" in current_path or node["name"].endswith((".test.ts", ".test.tsx", ".spec.ts")):
                    organized["frontend"]["tests"].append(file_info)
                else:
                    organized["frontend"]["other"].append(file_info)
            elif "docs" in current_path or node["name"].endswith((".md", ".rst", ".txt")):
                organized["docs"].append(file_info)
            elif "scripts" in current_path or node["name"].endswith((".sh", ".py")):
                organized["scripts"].append(file_info)
            elif node["name"] in ["package.json", "tsconfig.json", "vite.config.ts", ".env", "docker-compose.yml"]:
                organized["config"].append(file_info)
        
        elif node["type"] == "directory" and "children" in node:
            # Recursively process children
            new_path = current_path + "/" + node["name"] if current_path else node["name"]
            for child in node["children"].values():
                await self._categorize_files(child, organized, new_path)
    
    async def apply_template(
        self,
        project_id: str,
        template_name: str,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply a project template with variable substitution.
        
        Args:
            project_id: The project ID
            template_name: Name of the template to apply
            variables: Variables to substitute in the template
        """
        # TODO: Implement template system
        # For now, return a placeholder
        return {
            "success": True,
            "message": f"Template '{template_name}' would be applied with variables",
            "variables": variables
        }
    
    async def create_backup_snapshot(self, project_id: str) -> Dict[str, Any]:
        """Create a backup snapshot of the current project state."""
        try:
            # Get current file system state
            vfs_result = await self.fs_service.get_virtual_file_system(project_id)
            
            if not vfs_result["success"]:
                return vfs_result
            
            # Save snapshot metadata
            snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            snapshot_path = f".devmaster/snapshots/{snapshot_id}/metadata.json"
            
            snapshot_data = {
                "snapshot_id": snapshot_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "project_id": project_id,
                "file_system": vfs_result["virtual_fs"]
            }
            
            await self.fs_service.write_file(
                project_id,
                snapshot_path,
                json.dumps(snapshot_data, indent=2)
            )
            
            # Emit event
            await self.event_bus.emit(
                EventType.PROJECT_SNAPSHOT_CREATED,
                {
                    "project_id": project_id,
                    "snapshot_id": snapshot_id
                }
            )
            
            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "created_at": snapshot_data["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Error creating snapshot: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_file_stats(self, project_id: str) -> Dict[str, Any]:
        """Get statistics about project files."""
        try:
            organized_result = await self.organize_by_type(project_id)
            
            if not organized_result["success"]:
                return organized_result
            
            organized = organized_result["organized"]
            
            # Calculate stats
            stats = {
                "backend": {
                    "models_count": len(organized["backend"]["models"]),
                    "services_count": len(organized["backend"]["services"]),
                    "routers_count": len(organized["backend"]["routers"]),
                    "tests_count": len(organized["backend"]["tests"])
                },
                "frontend": {
                    "components_count": len(organized["frontend"]["components"]),
                    "pages_count": len(organized["frontend"]["pages"]),
                    "services_count": len(organized["frontend"]["services"]),
                    "tests_count": len(organized["frontend"]["tests"])
                },
                "total_files": organized_result["stats"]["total_files"],
                "documentation_files": len(organized["docs"]),
                "config_files": len(organized["config"])
            }
            
            return {
                "success": True,
                "stats": stats
            }
            
        except Exception as e:
            logger.error(f"Error getting file stats: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
