"""
Integration test for the entire DevMaster system.
Tests the full flow from API to agents to database.
"""
import pytest
import httpx
from typing import Dict, Any


# Test server URL
BASE_URL = "http://localhost:8003"


class TestDevMasterIntegration:
    """Integration tests for DevMaster."""
    
    @pytest.fixture
    def client(self):
        """Create an HTTP client for testing."""
        with httpx.Client(base_url=BASE_URL) as client:
            yield client
    
    def test_server_is_running(self, client):
        """Test that the server is running and accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger-ui" in response.text.lower()
    
    def test_echo_orchestration(self, client):
        """Test the echo orchestration endpoint."""
        # Send a test message
        response = client.post(
            "/api/v1/orchestration/test/echo",
            json={"message": "Integration test message"}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "project_id" in data
        assert data["status"] == "completed"
        assert len(data["messages"]) > 0
        
        # Check that the echo message is in the response
        echo_messages = [
            msg for msg in data["messages"] 
            if "Echo: Integration test message" in msg["content"]
        ]
        assert len(echo_messages) == 1
    
    def test_sequential_orchestration(self, client):
        """Test sequential agent execution."""
        response = client.post(
            "/api/v1/orchestration/test/sequence",
            json={"message": "Test sequential execution"}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "project_id" in data
        assert data["status"] == "completed"
        
        # Check execution path
        execution_path = data.get("execution_path", [])
        expected_path = ["TestAgent1", "TestAgent2", "TestAgent3", "EchoAgent"]
        assert execution_path == expected_path
    
    def test_task_types_listing(self, client):
        """Test listing available task types."""
        response = client.get("/api/v1/orchestration/task-types")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "task_types" in data
        assert len(data["task_types"]) > 0
        
        # Check that FULLSTACK_DEVELOPMENT is present
        task_types = [t["value"] for t in data["task_types"]]
        assert "FULLSTACK_DEVELOPMENT" in task_types
    
    def test_project_creation(self, client):
        """Test creating a new project."""
        response = client.post(
            "/api/v1/projects/",
            json={
                "name": "Integration Test Project",
                "description": "Testing the full stack",
                "project_type": "fullstack"
            }
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert data["name"] == "Integration Test Project"
        assert data["status"] == "active"
        
        # Store project ID for cleanup
        project_id = data["id"]
        
        # Test getting the project
        get_response = client.get(f"/api/v1/projects/{project_id}")
        assert get_response.status_code == 200
        
        # Cleanup - archive the project
        cleanup_response = client.post(f"/api/v1/projects/{project_id}/archive")
        assert cleanup_response.status_code == 200
    
    def test_file_operations(self, client):
        """Test file system operations on a project."""
        # Create a project first
        project_response = client.post(
            "/api/v1/projects/",
            json={
                "name": "File Test Project",
                "description": "Testing file operations",
                "project_type": "fullstack"
            }
        )
        
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]
        
        # Create a file
        file_response = client.post(
            f"/api/v1/projects/{project_id}/files",
            json={
                "path": "test.py",
                "content": "print('Hello from integration test')"
            }
        )
        
        assert file_response.status_code == 200
        
        # List files
        list_response = client.get(f"/api/v1/projects/{project_id}/files")
        assert list_response.status_code == 200
        
        files = list_response.json()
        assert any(f["path"] == "test.py" for f in files["files"])
        
        # Cleanup
        cleanup_response = client.post(f"/api/v1/projects/{project_id}/archive")
        assert cleanup_response.status_code == 200


if __name__ == "__main__":
    # Run a quick smoke test
    print("Running DevMaster Integration Tests...")
    
    with httpx.Client(base_url=BASE_URL) as client:
        try:
            # Test server is running
            response = client.get("/docs")
            print(f"✓ Server is running on {BASE_URL}")
            
            # Test echo endpoint
            echo_response = client.post(
                "/api/v1/orchestration/test/echo",
                json={"message": "Quick test"}
            )
            if echo_response.status_code == 200:
                print("✓ Echo orchestration working")
            else:
                print(f"✗ Echo orchestration failed: {echo_response.status_code}")
            
            # Test task types
            types_response = client.get("/api/v1/orchestration/task-types")
            if types_response.status_code == 200:
                task_count = len(types_response.json()["task_types"])
                print(f"✓ Task types endpoint working ({task_count} types)")
            else:
                print(f"✗ Task types failed: {types_response.status_code}")
                
        except Exception as e:
            print(f"✗ Error connecting to server: {e}")
            print(f"  Make sure the server is running on {BASE_URL}")
