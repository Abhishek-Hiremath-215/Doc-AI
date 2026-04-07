import datetime
import uuid
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Boolean, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from database import Base
from core.role_enum import MessageType, UserRole

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    users = relationship(
        "User", back_populates="organization", lazy="selectin", cascade="all, delete-orphan"
    )
    projects = relationship(
        "Project", back_populates="organization", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Organization {self.name}>"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(
        SQLAlchemyEnum(UserRole, name="userrole"),
        nullable=False,
        default=UserRole.user
    )
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    projects = relationship("Project", back_populates="creator", cascade="all, delete-orphan", lazy="selectin")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    
    # Project permissions - permissions granted TO this user
    granted_permissions = relationship(
        "ProjectPermission", 
        foreign_keys="ProjectPermission.user_id", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # Project permissions - permissions this user GRANTED to others
    permissions_granted = relationship(
        "ProjectPermission", 
        foreign_keys="ProjectPermission.granted_by_user_id",  # CHANGED FROM granted_by
        back_populates="granted_by_user"  # CHANGED FROM granter
    )

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    folder_path = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    creator = relationship("User", back_populates="projects")
    organization = relationship("Organization", back_populates="projects")
    # ✅ REMOVED: chat_sessions relationship - Sessions are now flexible!
    
    # Project permissions
    permissions = relationship(
        "ProjectPermission", 
        back_populates="project", 
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Project {self.name}>"

class ProjectPermission(Base):
    __tablename__ = "project_permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    granted_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # CHANGED TO nullable=True
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="permissions")
    user = relationship("User", foreign_keys=[user_id], back_populates="granted_permissions")
    granted_by_user = relationship("User", foreign_keys=[granted_by_user_id], back_populates="permissions_granted")
    
    # Ensure unique project-user combinations
    __table_args__ = (
        UniqueConstraint('project_id', 'user_id', name='unique_project_user_permission'),
    )
    
    def __repr__(self):
        return f"<ProjectPermission project_id={self.project_id} user_id={self.user_id}>"

# ✅ FLEXIBLE CHAT SYSTEM MODELS
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, default="New Chat")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # ✅ REMOVED: project_id - Sessions are now flexible!
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    # ✅ REMOVED: project relationship - Sessions are flexible!
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", lazy="selectin")
    
    def __repr__(self):
        return f"<ChatSession {self.title} - User: {self.user_id}>"

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_type = Column(SQLAlchemyEnum(MessageType, name="messagetype"), nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column("metadata", Text, nullable=True)  # JSON string for sources, context, project_id, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User")
    
    def __repr__(self):
        return f"<ChatMessage {self.message_type} - Session: {self.session_id}>"
