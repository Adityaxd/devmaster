"""
Project Management API Routes

Handles all project-related operations including:
- Project CRUD operations
- File management
- Code artifact storage
- Project statistics
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.services import ProjectService, FileSystemService, ProjectFileManager
from app.services.websocket_manager import websocket_manager
from app.core.events import event_bus, EventType
from app.models.project import ProjectType, ProjectStatus
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

# Initialize services
fs_service = FileSystemService(event_bus)
file_manager = ProjectFileManager(fs_service, event_bus)
project_service = ProjectService(event_bus, fs_service, file_manager)


# Request/Response models
class ProjectCreateRequest(BaseModel):
    """Request model for creating a project."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    project_type: ProjectType
    technology_stack: Optional[Dict[str, str]] = None


class ProjectUpdateRequest(BaseModel):
    """Request model for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    technology_stack: Optional[Dict[str, str]] = None
    settings: Optional[Dict[str, Any]] = None


class FileOperationRequest(BaseModel):
    """Request model for file operations."""
    path: str
    content: Optional[str] = None
    operation: str = Field(..., pattern="^(create|update|delete|move)$")
    destination: Optional[str] = None


class GeneratedArtifactsRequest(BaseModel):
    """Request model for saving generated artifacts."""
    artifacts: Dict[str, Any]
    agent_name: str


# API Endpoints
@router.post("/", summary="Create a new project")
async def create_project(
    request: ProjectCreateRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new development project."""
    # TODO: Get actual user ID from authentication
    # For now, using a dummy user ID
    dummy_user_id = UUID("00000000-0000-0000-0000-000000000001")
    
    result = await project_service.create_project(
        name=request.name,
        description=request.description,
        project_type=request.project_type,
        owner_id=dummy_user_id,
        technology_stack=request.technology_stack,
        db=db
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result["project"]


@router.get("/", summary="List user projects")
async def list_projects(
    status: Optional[ProjectStatus] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """List all projects for the authenticated user."""
    # TODO: Get actual user ID from authentication
    dummy_user_id = UUID("00000000-0000-0000-0000-000000000001")
    
    result = await project_service.list_user_projects(
        owner_id=dummy_user_id,
        status=status,
        db=db
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result["projects"]


@router.get("/{project_id}", summary="Get project details")
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_async_db)
):
    """Get detailed information about a project."""
    result = await project_service.get_project(project_id, db)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result["project"]


@router.patch("/{project_id}", summary="Update project")
async def update_project(
    project_id: UUID,
    request: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Update project information."""
    updates = request.model_dump(exclude_unset=True)
    
    result = await project_service.update_project_state(
        project_id=project_id,
        updates=updates,
        db=db
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {"message": result["message"], "project_id": str(project_id)}


@router.post("/{project_id}/archive", summary="Archive project")
async def archive_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_async_db)
):
    """Archive a project and create a backup snapshot."""
    result = await project_service.archive_project(project_id, db)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {"message": "Project archived successfully", "project_id": str(project_id)}


# File Management Endpoints
@router.get("/{project_id}/files", summary="Get project files")
async def get_project_files(
    project_id: UUID,
    organized: bool = False
):
    """Get project file structure."""
    result = await project_service.get_project_files(project_id, organized)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/{project_id}/files/{file_path:path}", summary="Read file content")
async def read_file(
    project_id: UUID,
    file_path: str
):
    """Read content of a specific file."""
    result = await fs_service.read_file(str(project_id), file_path)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return {
        "path": result["path"],
        "content": result["content"],
        "size": result["size"]
    }


@router.post("/{project_id}/files", summary="Perform file operation")
async def file_operation(
    project_id: UUID,
    request: FileOperationRequest
):
    """Perform a file operation (create, update, delete, move)."""
    if request.operation in ["create", "update"]:
        if request.content is None:
            raise HTTPException(status_code=400, detail="Content required for create/update")
        
        result = await fs_service.write_file(
            str(project_id),
            request.path,
            request.content
        )
    
    elif request.operation == "delete":
        result = await fs_service.delete_file(str(project_id), request.path)
    
    elif request.operation == "move":
        if request.destination is None:
            raise HTTPException(status_code=400, detail="Destination required for move")
        
        # Implement as read + write + delete
        read_result = await fs_service.read_file(str(project_id), request.path)
        if not read_result["success"]:
            result = read_result
        else:
            write_result = await fs_service.write_file(
                str(project_id),
                request.destination,
                read_result["content"]
            )
            if not write_result["success"]:
                result = write_result
            else:
                result = await fs_service.delete_file(str(project_id), request.path)
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown operation: {request.operation}")
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {"message": f"File {request.operation} successful", "result": result}


@router.post("/{project_id}/artifacts", summary="Save generated artifacts")
async def save_artifacts(
    project_id: UUID,
    request: GeneratedArtifactsRequest
):
    """Save code artifacts generated by an agent."""
    result = await project_service.save_generated_artifacts(
        project_id=project_id,
        artifacts=request.artifacts,
        agent_name=request.agent_name
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {"message": "Artifacts saved successfully", "result": result}


@router.get("/{project_id}/stats", summary="Get project statistics")
async def get_project_stats(
    project_id: UUID
):
    """Get statistics about project files."""
    result = await file_manager.get_file_stats(str(project_id))
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result["stats"]


@router.post("/{project_id}/snapshot", summary="Create project snapshot")
async def create_snapshot(
    project_id: UUID
):
    """Create a backup snapshot of the project."""
    result = await file_manager.create_backup_snapshot(str(project_id))
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {
        "message": "Snapshot created successfully",
        "snapshot_id": result["snapshot_id"],
        "created_at": result["created_at"]
    }


# WebSocket endpoint for real-time updates
@router.websocket("/{project_id}/ws")
async def project_websocket(
    websocket: WebSocket,
    project_id: UUID
):
    """WebSocket endpoint for real-time project updates."""
    await websocket_manager.handle_connection(websocket, str(project_id))
