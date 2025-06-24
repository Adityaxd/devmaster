"""
Tests for File System Service
"""

import pytest
import asyncio
from pathlib import Path
import json
import shutil
from unittest.mock import Mock

from app.services.file_system import FileSystemService, FileOperation
from app.core.events import EventBus, EventType


@pytest.fixture
async def event_bus():
    """Create a mock event bus."""
    bus = Mock(spec=EventBus)
    bus.emit = Mock(return_value=asyncio.Future())
    bus.emit.return_value.set_result(None)
    return bus


@pytest.fixture
async def file_system_service(event_bus, tmp_path):
    """Create a file system service for testing."""
    # Override the base path to use temp directory
    service = FileSystemService(event_bus)
    service.base_path = tmp_path
    return service


@pytest.fixture
async def test_project_id():
    """Generate a test project ID."""
    return "test-project-123"


class TestFileSystemService:
    """Test cases for FileSystemService."""
    
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
        
        # Check that initial files were created
        assert (project_path / "README.md").exists()
        assert (project_path / ".gitignore").exists()
        assert (project_path / "src" / "backend" / "requirements.txt").exists()
        assert (project_path / "src" / "frontend" / "package.json").exists()
    
    async def test_read_file(self, file_system_service, test_project_id):
        """Test reading a file."""
        # Initialize project first
        await file_system_service.initialize_project_structure(test_project_id)
        
        # Read an existing file
        result = await file_system_service.read_file(test_project_id, "README.md")
        
        assert result["success"] is True
        assert "content" in result
        assert test_project_id in result["content"]
    
    async def test_read_nonexistent_file(self, file_system_service, test_project_id):
        """Test reading a non-existent file."""
        result = await file_system_service.read_file(test_project_id, "nonexistent.txt")
        
        assert result["success"] is False
        assert "error" in result
    
    async def test_write_file(self, file_system_service, test_project_id):
        """Test writing a file."""
        # Initialize project first
        await file_system_service.initialize_project_structure(test_project_id)
        
        # Write a new file
        content = "Test content\nLine 2"
        result = await file_system_service.write_file(
            test_project_id,
            "test_file.txt",
            content
        )
        
        assert result["success"] is True
        assert result["size"] == len(content)
        
        # Verify file was written
        read_result = await file_system_service.read_file(test_project_id, "test_file.txt")
        assert read_result["success"] is True
        assert read_result["content"] == content
    
    async def test_delete_file(self, file_system_service, test_project_id):
        """Test deleting a file."""
        # Initialize project and create a file
        await file_system_service.initialize_project_structure(test_project_id)
        await file_system_service.write_file(test_project_id, "to_delete.txt", "Delete me")
        
        # Delete the file
        result = await file_system_service.delete_file(test_project_id, "to_delete.txt")
        
        assert result["success"] is True
        
        # Verify file was deleted
        read_result = await file_system_service.read_file(test_project_id, "to_delete.txt")
        assert read_result["success"] is False
    
    async def test_atomic_operations(self, file_system_service, test_project_id):
        """Test atomic file operations."""
        # Initialize project
        await file_system_service.initialize_project_structure(test_project_id)
        
        # Define operations
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
                path="subdir/file3.txt",
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
        for op in operations:
            read_result = await file_system_service.read_file(test_project_id, op.path)
            assert read_result["success"] is True
            assert read_result["content"] == op.content
    
    async def test_atomic_operations_rollback(self, file_system_service, test_project_id):
        """Test that atomic operations rollback on failure."""
        # Initialize project
        await file_system_service.initialize_project_structure(test_project_id)
        
        # Define operations with one that will fail
        operations = [
            FileOperation(
                operation="create",
                path="file1.txt",
                content="Content 1"
            ),
            FileOperation(
                operation="invalid_op",  # This will fail
                path="file2.txt",
                content="Content 2"
            )
        ]
        
        # Execute operations
        result = await file_system_service.execute_atomic_operations(
            test_project_id,
            operations
        )
        
        assert result["success"] is False
        assert "error" in result
    
    async def test_get_virtual_file_system(self, file_system_service, test_project_id):
        """Test getting virtual file system representation."""
        # Initialize project and add some files
        await file_system_service.initialize_project_structure(test_project_id)
        await file_system_service.write_file(test_project_id, "src/test.py", "print('test')")
        
        # Get virtual file system
        result = await file_system_service.get_virtual_file_system(test_project_id)
        
        assert result["success"] is True
        assert "virtual_fs" in result
        
        vfs = result["virtual_fs"]
        assert vfs["type"] == "directory"
        assert "children" in vfs
        assert "src" in vfs["children"]
        
        # Check that test.py is in the structure
        src_node = vfs["children"]["src"]
        assert "test.py" in src_node["children"]
        assert src_node["children"]["test.py"]["type"] == "file"
    
    async def test_move_operation(self, file_system_service, test_project_id):
        """Test moving a file using atomic operations."""
        # Initialize project and create a file
        await file_system_service.initialize_project_structure(test_project_id)
        await file_system_service.write_file(test_project_id, "old_path.txt", "Move me")
        
        # Move the file
        operations = [
            FileOperation(
                operation="move",
                path="old_path.txt",
                destination="new_path.txt"
            )
        ]
        
        result = await file_system_service.execute_atomic_operations(
            test_project_id,
            operations
        )
        
        assert result["success"] is True
        
        # Verify file was moved
        old_result = await file_system_service.read_file(test_project_id, "old_path.txt")
        assert old_result["success"] is False
        
        new_result = await file_system_service.read_file(test_project_id, "new_path.txt")
        assert new_result["success"] is True
        assert new_result["content"] == "Move me"
