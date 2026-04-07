from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from core.role_enum import UserRole, MessageType

# ------------------------
# Organization Schemas
# ------------------------
class OrganizationBase(BaseModel):
    name: str
    description: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    """Schema for creating a new organization with its org admin."""
    admin_email: EmailStr
    admin_password: str
    
    @field_validator('admin_password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Admin password must be at least 6 characters long')
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Organization name cannot be empty')
        return v.strip()

class OrganizationOut(OrganizationBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class OrgAdminResponse(BaseModel):
    """Response schema for org admin user."""
    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    organization_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class OrganizationDetail(BaseModel):
    """Response when creating org + org admin"""
    organization: OrganizationOut
    org_admin: OrgAdminResponse

# ------------------------
# Project Permission Schemas
# ------------------------
class ProjectPermissionGrant(BaseModel):
    """Schema for granting project access to a user"""
    user_id: UUID

class ProjectPermissionOut(BaseModel):
    """Schema for project permission details"""
    id: UUID
    user_id: UUID
    user_email: str
    granted_by: UUID
    granted_by_email: str
    granted_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ProjectPermissionList(BaseModel):
    """Schema for listing project permissions"""
    project_id: int
    project_name: str
    creator: dict
    permissions: List[dict]

class UserProjectAccess(BaseModel):
    """Schema for user's project access summary"""
    user_id: UUID
    user_email: str
    has_access: bool
    access_type: str  # "creator", "granted", "org_admin", "superadmin"
    granted_at: Optional[datetime] = None

# ------------------------
# Project Schemas
# ------------------------
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectOut(ProjectBase):
    id: int
    creator_id: UUID
    organization_id: Optional[UUID] = None
    organization_name: Optional[str] = None
    folder_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    creator_email: Optional[str] = None
    permission_count: Optional[int] = None
    user_has_access: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)

class ProjectAssign(BaseModel):
    """Schema for assigning projects to users"""
    user_id: UUID
    model_config = ConfigDict(from_attributes=True)

# ------------------------
# User Schemas
# ------------------------
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.user
    organization_id: Optional[UUID] = None

class UserLogin(UserBase):
    password: str

class UserOut(UserBase):
    id: UUID
    role: UserRole
    is_active: bool
    organization_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    organization: Optional[OrganizationOut] = None
    projects: List[ProjectOut] = []
    model_config = ConfigDict(from_attributes=True)

class UserSummary(BaseModel):
    """Simple user info for permission displays"""
    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

# ------------------------
# Token Schemas
# ------------------------
class Token(BaseModel):
    access_token: str
    token_type: str

# ------------------------
# Generic Request
# ------------------------
class URLRequest(BaseModel):
    url: str

# ------------------------
# FLEXIBLE CHAT SCHEMAS
# ------------------------
class ChatSessionBase(BaseModel):
    title: Optional[str] = "New Chat"
    # ✅ REMOVED: project_id - Sessions are flexible!

class ChatSessionCreate(ChatSessionBase):
    """Schema for creating a flexible chat session - NO project lock"""
    pass
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is not None and len(v.strip()) == 0:
            return "New Chat"  # Replace empty strings with default
        return v

class ChatSessionUpdate(BaseModel):
    """Schema for updating chat session (mainly title)"""
    title: Optional[str] = None
    is_active: Optional[bool] = None
    
    @field_validator('title')
    @classmethod
    def validate_title_update(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Title cannot be empty')
        return v

class ChatMessageBase(BaseModel):
    content: str
    message_type: MessageType
    message_metadata: Optional[str] = None

class ChatMessageCreate(BaseModel):
    """Schema for creating a new chat message"""
    content: str
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()

class ChatMessageOut(ChatMessageBase):
    """Schema for chat message output"""
    id: UUID
    session_id: UUID
    user_id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ChatSessionOut(BaseModel):
    """Schema for flexible chat session output - NO project_id"""
    id: UUID
    user_id: UUID
    title: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: Optional[int] = 0
    last_message_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class ChatSessionDetail(ChatSessionOut):
    """Schema for chat session with messages"""
    messages: List[ChatMessageOut] = []
    project_name: Optional[str] = None  # ✅ Always None for flexible sessions
    
    model_config = ConfigDict(from_attributes=True)

class ChatQueryRequest(BaseModel):
    """Schema for asking questions with DYNAMIC project selection"""
    query: str
    use_context: bool = True
    selected_files: List[str] = []
    project_id: Optional[int] = None  # ✅ NEW: Dynamic project per question
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()

# In your schemas.py
class ChatQueryResponse(BaseModel):
    answer: str
    sources: List[dict] = []
    session_id: UUID
    message_id: UUID
    user_message_id: UUID
    context_used: bool = False
    enhanced_query: Optional[str] = None
    # ✅ ADD CHART FIELDS
    chartBase64: Optional[str] = None
    chartUrl: Optional[str] = None
    has_chart: bool = False

class ChatContextSummary(BaseModel):
    """Schema for conversation context summary"""
    session_id: UUID
    total_messages: int
    context_messages_used: int
    relevant_documents: List[str] = []
    conversation_themes: List[str] = []
