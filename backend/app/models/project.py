"""Project model for managing development projects."""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from .base import Base, TimestampMixin


class ProjectStatus(str, enum.Enum):
    """Status of a project."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ProjectType(str, enum.Enum):
    """Type of project being developed."""
    FULLSTACK_WEB = "fullstack_web"
    API_ONLY = "api_only"
    FRONTEND_ONLY = "frontend_only"
    CLI_TOOL = "cli_tool"
    LIBRARY = "library"
    MICROSERVICE = "microservice"


class Project(Base, TimestampMixin):
    """
    Project model for the DevMaster platform.
    
    Represents a development project with all its metadata,
    configuration, and relationship to executions.
    """
    __tablename__ = "projects"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Basic info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(
        Enum(ProjectStatus),
        default=ProjectStatus.ACTIVE,
        nullable=False
    )
    project_type = Column(Enum(ProjectType))
    
    # Ownership
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Configuration
    technology_stack = Column(JSON, default=dict)  # {"backend": "FastAPI", "frontend": "React", etc.}
    settings = Column(JSON, default=dict)  # Project-specific settings
    
    # File system
    file_structure = Column(JSON, default=dict)  # Virtual file system representation
    repository_url = Column(String(500))  # Git repository URL if connected
    
    # Deployment
    deployment_config = Column(JSON, default=dict)
    is_deployed = Column(Boolean, default=False)
    deployment_url = Column(String(500))
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    executions = relationship("Execution", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"
