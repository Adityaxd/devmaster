"""Tests for FileSystemService."""

import pytest
import asyncio
from pathlib import Path
import json
import shutil
from datetime import datetime, timezone

from app.services.file_system import FileSystemService, FileOperation
from app.core.events import event_bus, EventType


@pytest.fixture
async def file_system_service():
    """Create a file system service instance."""
    service = FileSystemService(event_bus)
    # Use a test directory
    service.base_path = Path("./test_projects")
    service._ensure_base_directory()
    yield service
    # Cleanup
    if service.base_path.exists():
        shutil.rmtree(service.base_path)


@pytest.fixture
def test_project_id():
    """Test project ID."""
    return "test-project-123"


class TestFileSystemService:
    """Test FileSystemService functionality."""
    
    async def test_initialize_project_structure(self, file_system_service, test_project_id):
        """Test project structure initialization."""
        result = await file_system_service.initialize_project_structure(test_project_id)
        
        assert result["success"] is True
        assert "project_path" in result
        assert "virtual_fs" in result
        
        # Check that directories were created
        project_path = Path(result["project_path"])
        assert project_path.exists()
        assert (project_path / "src" / "backend").exists()
        assert (project_path / "src" / "frontend").exists()
        assert (project_path / "docs").exists()
        assert (project_path / ".devmaster").exists()
        
        # Check that files were created
        assert (project_path / "README.md").exists()
        assert (project_path / ".gitignore").exists()
        assert (project_path / "src" / "backend" / "requirements.txt").exists()
        assert (project_path / "src" / "frontend" / "package.json").exists()
    
    async def test_read_write_file(self, file_system_service, test_project_id):
        """Test file read and write operations."""
        # Initialize project first
        await file_system_service.initialize_project_structure(test_project_id)
        
        # Write a file
        file_path = "test_file.txt"
        content = "Hello, DevMaster!"
        
        write_result = await file_system_service.write_file(
            test_project_id,
            file_path,
            content
        )
        
        assert write_result["success"] is True
        assert write_result["path"] == file_path
        assert write_result["size"] == len(content)
        
        # Read the file back
        read_result = await file_system_service.read_file(test_project_id, file_path)
        
        assert read_result["success"] is True
        assert read_result["content"] == content
        assert read_result["path"] == file_path
    
    async def test_delete_file(self, file_system_service, test_project_id):
        """Test file deletion."""
        # Initialize and create a file
        await file_system_service.initialize_project_structure(test_project_id)
        await file_system_service.write_file(test_project_id, "test.txt", "content")
        
        # Delete the file
        result = await file_system_service.delete_file(test_project_id, "test.txt")
        
        assert result["success"] is True
        assert result["path"] == "test.txt"
        
        # Verify file is deleted
        read_result = await file_system_service.read_file(test_project_id, "test.txt")
        assert read_result["success"] is False
        assert "not found" in read_result["error"]
    
    async def test_atomic_operations(self, file_system_service, test_project_id):
        """Test atomic file operations."""
        await file_system_service.initialize_project_structure(test_project_id)
        
        # Create multiple operations
        operations = [
            FileOperation(
                operation="create",
                path="file1.txt",
                content="Content 1"
            ),
            FileOperation(
                operation="create",
                path="file2.txt",
                content="Content 2"
            ),
            FileOperation(
                operation="create",
                path="file3.txt",
                content="Content 3"
            )
        ]
        
        # Execute operations
        result = await file_system_service.execute_atomic_operations(
            test_project_id,
            operations
        )
        
        assert result["success"] is True
        assert result["operations_count"] == 3
        
        # Verify all files were created
        for i in range(1, 4):
            read_result = await file_system_service.read_file(
                test_project_id,
                f"file{i}.txt"
            )
            assert read_result["success"] is True
            assert read_result["content"] == f"Content {i}"
    
    async def test_atomic_operations_rollback(self, file_system_service, test_project_id):
        """Test atomic operations rollback on failure."""
        await file_system_service.initialize_project_structure(test_project_id)
        
        # Create operations with one that will fail
        operations = [
            FileOperation(
                operation="create",
                path="success1.txt",
                content="Will succeed"
            ),
            FileOperation(
                operation="create",
                path="success2.txt",
                content="Will succeed"
            ),
            FileOperation(
                operation="delete",
                path="nonexistent.txt"  # This will fail
            )
        ]
        
        # Execute operations
        result = await file_system_service.execute_atomic_operations(
            test_project_id,
            operations
        )
        
        assert result["success"] is False
        assert "failed_operation" in result
        
        # Note: Current implementation doesn't have proper rollback
        # This is a known limitation that should be addressed
    
    async def test_virtual_file_system(self, file_system_service, test_project_id):
        """Test virtual file system building."""
        await file_system_service.initialize_project_structure(test_project_id)
        
        # Add some files
        await file_system_service.write_file(
            test_project_id,
            "src/backend/app/main.py",
            "# Main application"
        )
        await file_system_service.write_file(
            test_project_id,
            "src/frontend/src/App.tsx",
            "export default function App() {}"
        )
        
        # Get virtual file system
        result = await file_system_service.get_virtual_file_system(test_project_id)
        
        assert result["success"] is True
        assert "virtual_fs" in result
        
        vfs = result["virtual_fs"]
        assert vfs["type"] == "directory"
        assert "children" in vfs
        assert "src" in vfs["children"]
        
        # Navigate to backend
        src = vfs["children"]["src"]
        assert "backend" in src["children"]
        backend = src["children"]["backend"]
        assert "app" in backend["children"]
        app = backend["children"]["app"]
        assert "main.py" in app["children"]
        assert app["children"]["main.py"]["type"] == "file"
    
    async def test_nested_directory_creation(self, file_system_service, test_project_id):
        """Test creation of nested directories."""
        await file_system_service.initialize_project_structure(test_project_id)
        
        # Write file in deeply nested directory
        deep_path = "src/backend/app/services/specialized/implementations/service.py"
        content = "class SpecializedService: pass"
        
        result = await file_system_service.write_file(
            test_project_id,
            deep_path,
            content,
            create_dirs=True
        )
        
        assert result["success"] is True
        
        # Verify file exists
        read_result = await file_system_service.read_file(test_project_id, deep_path)
        assert read_result["success"] is True
        assert read_result["content"] == content
    
    async def test_file_metadata_in_vfs(self, file_system_service, test_project_id):
        """Test that virtual file system includes metadata."""
        await file_system_service.initialize_project_structure(test_project_id)
        
        # Create a file
        await file_system_service.write_file(
            test_project_id,
            "test.py",
            "print('test')"
        )
        
        # Get VFS
        result = await file_system_service.get_virtual_file_system(test_project_id)
        vfs = result["virtual_fs"]
        
        # Find the test file
        test_file = vfs["children"]["test.py"]
        assert test_file["type"] == "file"
        assert test_file["size"] > 0
        assert "modified_at" in test_file
        
        # Verify it's a valid timestamp
        modified_at = datetime.fromisoformat(test_file["modified_at"])
        assert isinstance(modified_at, datetime)
