from fastapi import APIRouter, Form, HTTPException, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql import or_
from uuid import UUID

from pydantic import BaseModel
from typing import List, Optional
import os, logging

from core.auth import require_superadmin
from schemas import ProjectAssign, ProjectOut, ProjectPermissionGrant, ProjectPermissionList, UserOut, UserSummary
from models import Project, User, ProjectPermission
from dependencies import get_current_active_user, get_current_user, get_db, require_roles
from core.config import graph_manager, UPLOAD_DIR
from core.role_enum import UserRole

router = APIRouter()
logger = logging.getLogger("uvicorn")

# ===========================
# New Pydantic Models for Request Bodies
# ===========================
class GrantAccessPayload(BaseModel):
    user_id: UUID

class AssignProjectPayload(BaseModel):
    user_id: UUID

# ===========================
# List Projects with Permission-Based Access
# ===========================


@router.get("/", response_model=List[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List projects based on user's role and permissions"""
    print(f"🔍 DEBUG - User Details:")
    print(f"  Email: {current_user.email}")
    print(f"  ID: {current_user.id}")
    print(f"  Role: {current_user.role}")
    print(f"  Organization ID: {current_user.organization_id}")
    
    # Base query with relationships loaded
    query = db.query(Project).options(
        selectinload(Project.creator),
        selectinload(Project.organization),
        selectinload(Project.permissions)
    )
    
    if current_user.role == UserRole.superadmin:
        print("🔧 Superadmin access - showing all projects")
        projects = query.all()
        
    elif current_user.role == UserRole.orgadmin:
        print(f"👑 Organization admin - showing all org projects in {current_user.organization_id}")
        projects = query.filter(
            Project.organization_id == current_user.organization_id
        ).all()
        
    elif current_user.organization_id:
        print(f"🏢 Regular user in organization {current_user.organization_id}")
        
        # Users with organizations see: owned + org projects + granted projects
        permission_subquery = db.query(ProjectPermission.project_id).filter(
            ProjectPermission.user_id == current_user.id
        ).subquery()
        
        projects = query.filter(
            or_(
                Project.creator_id == current_user.id,              # Own projects
                Project.organization_id == current_user.organization_id,  # Org projects  
                Project.id.in_(permission_subquery)               # Granted projects
            )
        ).all()
        
    else:
        # ✅ CRITICAL FIX: Non-org users see owned + granted projects
        print("👤 Non-org user - showing owned projects + granted access projects")
        permission_subquery = db.query(ProjectPermission.project_id).filter(
            ProjectPermission.user_id == current_user.id
        ).subquery()
        
        projects = query.filter(
            or_(
                Project.creator_id == current_user.id,    # Own projects
                Project.id.in_(permission_subquery)       # Granted projects
            )
        ).all()
    
    print(f"📊 Found {len(projects)} accessible projects")
    
    # ✅ ENHANCED: Build proper response with organization names
    response_projects = []
    for project in projects:
        # Extract organization name from the loaded relationship
        organization_name = None
        if hasattr(project, 'organization') and project.organization:
            organization_name = project.organization.name
            print(f"  📁 Project '{project.name}' -> Org: '{organization_name}'")
        else:
            print(f"  📁 Project '{project.name}' -> No organization")
        
        # Extract creator email
        creator_email = "Unknown"
        if hasattr(project, 'creator') and project.creator:
            creator_email = project.creator.email
        
        # Build response object with all fields
        project_data = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "creator_id": project.creator_id,
            "organization_id": project.organization_id,
            "organization_name": organization_name,  # ✅ ADD ORGANIZATION NAME
            "folder_path": project.folder_path,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "creator_email": creator_email,
            "permission_count": len(project.permissions) if project.permissions else 0,
            "user_has_access": True
        }
        
        response_projects.append(ProjectOut(**project_data))
    
    print(f"✅ Returning {len(response_projects)} projects with organization names")
    return response_projects

# ===========================
# Create Project (Updated - Private by Default)
# ===========================
@router.post("/create", response_model=ProjectOut)
def create_project(
    project_name: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a project - PRIVATE BY DEFAULT (only creator and superadmins have access)"""
    project_name_clean = project_name.strip()
    description_clean = description.strip()
    
    if not project_name_clean:
        raise HTTPException(status_code=400, detail="Project name is required.")
    
    # Check for duplicate project names within organization
    existing_project = db.query(Project).filter(
        Project.name == project_name_clean,
        Project.organization_id == current_user.organization_id
    ).first()
    if existing_project:
        raise HTTPException(status_code=400, detail="Project name already exists in your organization.")
    
    try:
        # 1. Create project in PostgreSQL
        new_project = Project(
            name=project_name_clean,
            description=description_clean,
            creator_id=current_user.id,
            organization_id=current_user.organization_id,
            folder_path=""
        )
        
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        # 2. Create project folder
        folder_name = f"{new_project.id}_{project_name_clean.replace(' ', '_')}"
        project_path = os.path.join(UPLOAD_DIR, folder_name)
        os.makedirs(project_path, exist_ok=True)
        
        new_project.folder_path = project_path
        db.commit()
        
        # 3. Neo4j operations
        try:
            from core.config import graph_manager
            
            # Create project node in Neo4j
            graph_manager.create_project_node(
                project_id=new_project.id,
                project_name=new_project.name,
                description=new_project.description,
                owner_id=str(new_project.creator_id)
            )
            
            # Add organization relationship
            if new_project.organization_id:
                graph_manager._safe_run("""
                    MATCH (p:Project {project_id: $project_id})
                    SET p.organization_id = $org_id
                """, project_id=new_project.id, org_id=str(new_project.organization_id))
            
            # Only superadmins get automatic access
            graph_manager._safe_run("""
                MATCH (super:User {role: 'superadmin'})
                MATCH (p:Project {project_id: $project_id})
                MERGE (super)-[:HAS_ACCESS]->(p)
            """, project_id=new_project.id)
            
            # Project creator gets owner relationship
            graph_manager._safe_run("""
                MATCH (creator:User {id: $creator_id})
                MATCH (p:Project {project_id: $project_id})
                MERGE (creator)-[:OWNS]->(p)
            """, creator_id=str(new_project.creator_id), project_id=new_project.id)
            
            print(f"✅ Project '{new_project.name}' created as PRIVATE (creator + superadmin access only)")
            
        except Exception as neo4j_error:
            logger.error(f"❌ Neo4j sync failed for project {new_project.name}: {neo4j_error}")
        
        # Add creator info to response
        new_project.creator_email = current_user.email
        new_project.permission_count = 0
        new_project.user_has_access = True
        
        return new_project
        
    except Exception as e:
        db.rollback()
        print(f"❌ Project creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create project")

# ===========================
# ✅ FIXED: Grant Project Access (Permissions Only - No Ownership Change)
# ===========================
@router.post("/{project_id}/grant-access")
def grant_project_access(
    project_id: int,
    payload: GrantAccessPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Grant project access to a user without changing ownership"""
    
    print(f"🔐 Grant access request - Project: {project_id}, User: {payload.user_id}")
    
    # Get project
    project = db.query(Project).options(selectinload(Project.creator)).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Authorization check
    if current_user.role == UserRole.superadmin:
        print("✅ SuperAdmin access granted")
    elif current_user.role == UserRole.orgadmin:
        if project.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Can only manage projects in your organization")
        print("✅ OrgAdmin access granted")
    elif project.creator_id == current_user.id:
        print("✅ Project creator access granted")
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions to grant access")
    
    # Get target user
    target_user = db.query(User).filter(User.id == payload.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    # Check if user is in same organization (unless superadmin)
    if (current_user.role != UserRole.superadmin and 
        project.organization_id and 
        target_user.organization_id != project.organization_id):
        raise HTTPException(status_code=400, detail="User must be in the same organization as the project")
    
    # Prevent granting access to project creator
    if target_user.id == project.creator_id:
        raise HTTPException(status_code=400, detail="Cannot grant access to project creator (they already own it)")
    
    # Check if permission already exists
    existing = db.query(ProjectPermission).filter(
        ProjectPermission.project_id == project_id,
        ProjectPermission.user_id == payload.user_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="User already has access to this project")
    
    # CREATE PERMISSION (NOT OWNERSHIP TRANSFER)
    new_permission = ProjectPermission(
        project_id=project_id,
        user_id=payload.user_id,
        granted_by_user_id=current_user.id
    )
    
    db.add(new_permission)
    db.commit()
    db.refresh(new_permission)
    
    # Update Neo4j
    try:
        graph_manager._safe_run("""
            MATCH (user:User {id: $user_id})
            MATCH (project:Project {project_id: $project_id})
            MERGE (user)-[:HAS_ACCESS]->(project)
        """, user_id=str(payload.user_id), project_id=project_id)
        print("✅ Neo4j relationship created")
    except Exception as e:
        logger.warning(f"Failed to update Neo4j for permission grant: {e}")
    
    print(f"✅ Access granted to {target_user.email} for project {project.name}")
    return {"message": f"Access granted to {target_user.email}"}

# ===========================
# ✅ CRITICAL FIX: Assign Project (Transfer Ownership) - CREATE PERMISSION RECORD
# ===========================
@router.post("/{project_id}/assign")
def assign_project_to_user(
    project_id: int,
    payload: AssignProjectPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign project to another user (transfer ownership) - SuperAdmin only"""
    
    print(f"🔄 Project assignment request - Project: {project_id}, New Owner: {payload.user_id}")
    
    # ONLY SUPERADMIN CAN TRANSFER OWNERSHIP
    if current_user.role != UserRole.superadmin:
        raise HTTPException(status_code=403, detail="Only superadmin can transfer project ownership")
    
    # Get project
    project = db.query(Project).options(selectinload(Project.creator)).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get target user
    target_user = db.query(User).filter(User.id == payload.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    # Prevent assigning to current owner
    if target_user.id == project.creator_id:
        raise HTTPException(status_code=400, detail="User already owns this project")
    
    try:
        # Store old values for logging
        old_creator = project.creator_id
        old_org = project.organization_id
        
        # ✅ CRITICAL FIX: Don't clear permissions, keep them for tracking
        # Clear existing permissions for this project 
        db.query(ProjectPermission).filter(ProjectPermission.project_id == project_id).delete()
        
        # ✅ TRANSFER OWNERSHIP (CHANGE CREATOR)
        project.creator_id = target_user.id
        project.organization_id = target_user.organization_id
        
        db.commit()
        db.refresh(project)
        
        # ✅ CRITICAL FIX: Create a permission record for the assignment tracking
        assignment_permission = ProjectPermission(
            project_id=project_id,
            user_id=target_user.id,
            granted_by=current_user.id
        )
        db.add(assignment_permission)
        db.commit()
        db.refresh(assignment_permission)
        
        print(f"✅ Assignment permission record created for {target_user.email}")
        
        # Update Neo4j ownership
        try:
            # Remove old ownership
            graph_manager._safe_run("""
                MATCH (old_owner:User {id: $old_creator})-[r:OWNS]->(project:Project {project_id: $project_id})
                DELETE r
            """, old_creator=str(old_creator), project_id=project_id)
            
            # Create new ownership
            graph_manager._safe_run("""
                MATCH (new_owner:User {id: $new_creator})
                MATCH (project:Project {project_id: $project_id})
                MERGE (new_owner)-[:OWNS]->(project)
                SET project.organization_id = $new_org_id
            """, new_creator=str(target_user.id), project_id=project_id, new_org_id=str(target_user.organization_id))
            
            print("✅ Neo4j ownership updated")
        except Exception as e:
            logger.warning(f"Failed to update Neo4j for project assignment: {e}")
        
        print(f"✅ Project {project.name} transferred from {old_creator} to {target_user.email}")
        
        return {
            "message": f"Project ownership transferred to {target_user.email}",
            "project": {
                "id": project.id,
                "name": project.name,
                "new_owner": target_user.email,
                "new_organization": target_user.organization.name if target_user.organization else None
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Assignment failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign project")

# ===========================
# Revoke Project Access
# ===========================
@router.delete("/{project_id}/revoke-access/{user_id}")
def revoke_project_access(
    project_id: int,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke project access from a user"""
    
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Authorization check
    if current_user.role == UserRole.superadmin:
        pass
    elif current_user.role == UserRole.orgadmin:
        if project.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Can only manage projects in your organization")
    elif project.creator_id == current_user.id:
        pass
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions to revoke access")
    
    # Prevent revoking creator's access
    if project.creator_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot revoke access from project creator")
    
    # Find and delete permission
    permission = db.query(ProjectPermission).filter(
        ProjectPermission.project_id == project_id,
        ProjectPermission.user_id == user_id
    ).first()
    
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    user_email = db.query(User).filter(User.id == user_id).first().email
    
    db.delete(permission)
    db.commit()
    
    # Update Neo4j
    try:
        graph_manager._safe_run("""
            MATCH (user:User {id: $user_id})-[r:HAS_ACCESS]->(project:Project {project_id: $project_id})
            DELETE r
        """, user_id=str(user_id), project_id=project_id)
    except Exception as e:
        logger.warning(f"Failed to update Neo4j for permission revoke: {e}")
    
    return {"message": f"Access revoked from {user_email}"}

# ===========================
# Get Project Permissions
# ===========================
@router.get("/{project_id}/permissions")
def get_project_permissions(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of users who have access to a project"""
    
    # Get project
    project = db.query(Project).options(selectinload(Project.creator)).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Authorization check
    if current_user.role == UserRole.superadmin:
        pass
    elif current_user.role == UserRole.orgadmin:
        if project.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Can only view projects in your organization")
    elif project.creator_id == current_user.id:
        pass
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions to view project permissions")
    
    # ✅ CRITICAL: Get fresh permissions from database
    permissions = db.query(ProjectPermission).options(
        selectinload(ProjectPermission.user),
        selectinload(ProjectPermission.granted_by_user)
    ).filter(ProjectPermission.project_id == project_id).all()
    
    print(f"🔍 Found {len(permissions)} permissions for project {project_id}")
    
    return {
        "project_id": project_id,
        "project_name": project.name,
        "creator": {
            "id": str(project.creator_id),
            "email": project.creator.email if project.creator else "Unknown"
        },
        "permissions": [
            {
                "permission_id": str(p.id),
                "user_id": str(p.user_id),
                "user_email": p.user.email,
                "granted_by": p.granted_by_user.email if p.granted_by_user else "System",
                "granted_at": p.granted_at
            }
            for p in permissions
        ]
    }

# ===========================
# Get Organization Users for Permission Grant
# ===========================
@router.get("/{project_id}/available-users", response_model=List[UserSummary])
def get_available_users_for_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get users in the same organization who can be granted access to the project"""
    
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Authorization check
    if current_user.role == UserRole.superadmin:
        # SuperAdmin can assign to any user in system
        users_with_access = db.query(ProjectPermission.user_id).filter(
            ProjectPermission.project_id == project_id
        ).subquery()
        
        available_users = db.query(User).filter(
            User.is_active == True,
            User.id != project.creator_id,
            ~User.id.in_(users_with_access)
        ).all()
        
        return available_users
    elif current_user.role == UserRole.orgadmin:
        if project.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Can only manage projects in your organization")
    elif project.creator_id == current_user.id:
        pass
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    if not project.organization_id:
        return []
    
    # Get users who already have access
    users_with_access = db.query(ProjectPermission.user_id).filter(
        ProjectPermission.project_id == project_id
    ).subquery()
    
    # Get available users (in same org, active, not creator, not already have access)
    available_users = db.query(User).filter(
        User.organization_id == project.organization_id,
        User.is_active == True,
        User.id != project.creator_id,
        ~User.id.in_(users_with_access)
    ).all()
    
    return available_users

# ===========================
# Get ALL users for SuperAdmin assignment
# ===========================
@router.get("/{project_id}/all-users", response_model=List[UserOut])
def get_all_users_for_assignment(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all users in the system for SuperAdmin project assignment"""
    
    # Authorization - only superadmin can assign any project to any user
    if current_user.role != UserRole.superadmin:
        raise HTTPException(status_code=403, detail="Only superadmin can assign projects")
    
    # Get the project first
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get ALL users except the project creator
    users = db.query(User).filter(
        User.id != project.creator_id,
        User.is_active == True
    ).all()
    
    print(f"🔍 Found {len(users)} users available for assignment")
    return users

# ===========================
# ✅ CRITICAL FIX: Get assigned users for a project
# ===========================
@router.get("/{project_id}/assigned-users")
def get_assigned_users(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all users assigned to a project"""
    
    if current_user.role != UserRole.superadmin:
        raise HTTPException(status_code=403, detail="Only superadmin can view assignments")
    
    # Get project with creator info
    project = db.query(Project).options(selectinload(Project.creator)).filter(
        Project.id == project_id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # ✅ CRITICAL FIX: Get fresh permissions from database with proper session
    db.expire_all()  # Force refresh of all objects
    permissions = db.query(ProjectPermission).options(
        selectinload(ProjectPermission.user),
        selectinload(ProjectPermission.granted_by_user)
    ).filter(ProjectPermission.project_id == project_id).all()
    
    assigned_users = []
    for permission in permissions:
        assigned_users.append({
            "user_id": str(permission.user_id),
            "user_email": permission.user.email,
            "user_role": permission.user.role.value,
            "assigned_at": permission.granted_at.isoformat(),
            "assigned_by": permission.granted_by_user.email if permission.granted_by_user else "System"
        })
    
    print(f"✅ Found {len(assigned_users)} assigned users for project {project_id}")
    
    return {
        "project_id": project_id,
        "project_name": project.name,
        "project_owner": project.creator.email if project.creator else "Unknown",
        "assigned_users": assigned_users
    }

# ===========================
# Revoke project assignment
# ===========================
@router.delete("/{project_id}/revoke-assignment/{user_id}")
def revoke_project_assignment(
    project_id: int,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke project assignment from user"""
    
    if current_user.role != UserRole.superadmin:
        raise HTTPException(status_code=403, detail="Only superadmin can revoke assignments")
    
    # Remove permission record
    permission = db.query(ProjectPermission).filter(
        ProjectPermission.project_id == project_id,
        ProjectPermission.user_id == user_id
    ).first()
    
    if permission:
        user_email = permission.user.email
        db.delete(permission)
        db.commit()
        
        # Update Neo4j
        try:
            graph_manager._safe_run("""
                MATCH (user:User {id: $user_id})-[r:HAS_ACCESS]->(project:Project {project_id: $project_id})
                DELETE r
            """, user_id=str(user_id), project_id=project_id)
        except Exception as e:
            logger.warning(f"Failed to update Neo4j for assignment revoke: {e}")
            
        return {"message": f"Assignment revoked from {user_email}"}
    else:
        raise HTTPException(status_code=404, detail="Assignment not found")

# ===========================
# Updated Get Project Files with Permission Check
# ===========================
@router.get("/{project_id}/files", summary="List files in a project by ID")
def get_project_files(
    project_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get files in a project with permission-based access control"""
    print(f"📁 Getting files for project {project_id} by user: {current_user.email}")
    
    # Get project from database
    project_db = db.query(Project).options(
        selectinload(Project.creator),
        selectinload(Project.organization)
    ).filter(Project.id == project_id).first()
    
    if not project_db:
        raise HTTPException(status_code=404, detail="Project not found in database.")

    # ✅ CRITICAL FIX: Enhanced permission-based access control
    has_access = False
    
    if current_user.role == UserRole.superadmin:
        has_access = True
        print("✅ Superadmin access")
    elif project_db.creator_id == current_user.id:
        has_access = True
        print("✅ Creator access")
    else:
        # ✅ FIXED: Check explicit permission for ALL users (not just org users)
        permission = db.query(ProjectPermission).filter(
            ProjectPermission.project_id == project_id,
            ProjectPermission.user_id == current_user.id
        ).first()
        
        if permission:
            has_access = True
            print("✅ Explicit permission access")
        # Organization access as fallback
        elif current_user.organization_id and project_db.organization_id == current_user.organization_id:
            has_access = True
            print("✅ Organization access")
    
    if not has_access:
        print(f"❌ Access denied for user {current_user.email} to project {project_id}")
        raise HTTPException(status_code=403, detail="Access denied. You don't have permission to view this project.")

    # Find project folder
    try:
        folder = next((f for f in os.listdir(UPLOAD_DIR) if f.startswith(f"{project_id}_")), None)
        if not folder:
            print(f"❌ Project folder not found for project {project_id}")
            raise HTTPException(status_code=404, detail="Project folder not found.")

        folder_path = os.path.join(UPLOAD_DIR, folder)
        print(f"📂 Found project folder: {folder_path}")

        # List files in the project folder
        files = []
        for f in os.listdir(folder_path):
            file_path = os.path.join(folder_path, f)
            if os.path.isfile(file_path) and not f.endswith("metadata.json"):
                try:
                    file_size_kb = round(os.path.getsize(file_path) / 1024, 1)
                    file_extension = os.path.splitext(f)[1][1:]  # Remove the dot
                    
                    files.append({
                        "name": f,
                        "size_kb": file_size_kb,
                        "type": file_extension or "unknown"
                    })
                except OSError as e:
                    logger.warning(f"Could not read file {f}: {e}")
                    continue

        print(f"📋 Found {len(files)} files in project {project_id}")
        return {"files": files, "project_name": project_db.name}
        
    except FileNotFoundError:
        logger.error(f"Upload directory not found: {UPLOAD_DIR}")
        raise HTTPException(status_code=500, detail="Upload directory not accessible.")
    except PermissionError:
        logger.error(f"Permission denied accessing directory: {UPLOAD_DIR}")
        raise HTTPException(status_code=500, detail="Permission denied accessing files.")
    except Exception as e:
        logger.error(f"[List Project Files] Error reading files: {e}")
        raise HTTPException(status_code=500, detail="Failed to list files.")

from fastapi import Query
@router.get("/{project_id}/files/{filename:path}", summary="Serve a specific file from a project")
def serve_project_file(
    project_id: int = Path(..., gt=0),
    filename: str = Path(...),
    token: Optional[str] = Query(None, description="Auth token for URL-based access"),
    db: Session = Depends(get_db),
):
    """Serve a specific file from a project with permission-based access control"""
    print(f"📄 Serving file {filename} from project {project_id}")
    
    current_user = None
    
    # Try to get user from token first if provided
    if token:
        try:
            print(f"🔑 Token provided: {token[:20]}...")
            
            # Use your existing JWT setup
            from core.config import SECRET_KEY, ALGORITHM
            from jose import JWTError, jwt
            from uuid import UUID
            
            # Decode the token
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            print(f"🔓 Token payload: {payload}")
            
            # Get user ID from payload
            user_id_str = payload.get("sub")
            if not user_id_str:
                print("❌ No 'sub' field in token payload")
                raise HTTPException(status_code=401, detail="Invalid token format")
            
            # Convert to UUID
            user_id = UUID(user_id_str)
            
            # Get user from database
            current_user = db.query(User).filter(User.id == user_id).first()
            if not current_user or not current_user.is_active:
                print(f"❌ User not found or inactive with ID: {user_id}")
                raise HTTPException(status_code=401, detail="User not found or inactive")
            
            print(f"✅ Token authentication successful for user: {current_user.email}")
            
        except (JWTError, ValueError) as e:
            print(f"❌ JWT decode error: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        except Exception as e:
            print(f"❌ Token validation failed: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Token validation error: {str(e)}")
    
    # If no token provided, require authentication
    if not current_user:
        print("❌ No authentication provided")
        raise HTTPException(status_code=401, detail="Authentication required")
    
    print(f"👤 Current user: {current_user.email} (role: {current_user.role})")
    
    # Decode the filename in case it's URL encoded
    from urllib.parse import unquote
    filename = unquote(filename)
    
    # Get project from database
    project_db = db.query(Project).options(
        selectinload(Project.creator),
        selectinload(Project.organization)
    ).filter(Project.id == project_id).first()
    
    if not project_db:
        raise HTTPException(status_code=404, detail="Project not found in database.")

    # Permission-based access control
    has_access = False
    
    if current_user.role == UserRole.superadmin:
        has_access = True
        print("✅ Superadmin access")
    elif project_db.creator_id == current_user.id:
        has_access = True
        print("✅ Creator access")
    else:
        # Check explicit permission
        permission = db.query(ProjectPermission).filter(
            ProjectPermission.project_id == project_id,
            ProjectPermission.user_id == current_user.id
        ).first()
        
        if permission:
            has_access = True
            print("✅ Explicit permission access")
        elif current_user.organization_id and project_db.organization_id == current_user.organization_id:
            has_access = True
            print("✅ Organization access")
    
    if not has_access:
        print(f"❌ Access denied for user {current_user.email} to project {project_id}")
        raise HTTPException(status_code=403, detail="Access denied.")

    # Find project folder and serve file
    try:
        import os
        import mimetypes
        from fastapi.responses import FileResponse
        
        folder = next((f for f in os.listdir(UPLOAD_DIR) if f.startswith(f"{project_id}_")), None)
        if not folder:
            print(f"❌ Project folder not found for project {project_id}")
            raise HTTPException(status_code=404, detail="Project folder not found.")

        folder_path = os.path.join(UPLOAD_DIR, folder)
        file_path = os.path.join(folder_path, filename)
        
        # Debug logging
        print(f"📂 Folder: {folder}")
        print(f"📂 Folder path: {folder_path}")
        print(f"📄 File path: {file_path}")
        print(f"📊 File exists: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"📏 File size: {file_size} bytes")
            print(f"🔓 File readable: {os.access(file_path, os.R_OK)}")
        
        # Security check
        if not os.path.commonpath([folder_path, file_path]) == folder_path:
            print(f"❌ Security check failed")
            raise HTTPException(status_code=403, detail="Invalid file path.")
        
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            print(f"❌ File not found: {file_path}")
            raise HTTPException(status_code=404, detail="File not found.")
        
        if not os.access(file_path, os.R_OK):
            print(f"❌ File not readable")
            raise HTTPException(status_code=403, detail="File not readable.")
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            print(f"❌ File is empty")
            raise HTTPException(status_code=404, detail="File is empty.")

        print(f"✅ Serving file: {file_path} ({file_size} bytes)")
        
        # MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'
        
        print(f"🎭 MIME type: {mime_type}")
        print(f"🔧 About to return FileResponse...")
        
        abs_file_path = os.path.abspath(file_path)
        print(f"📍 Absolute path: {abs_file_path}")
        
        return FileResponse(
            path=abs_file_path,
            filename=filename,
            media_type=mime_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f"inline; filename*=UTF-8''{filename}'"
            }
        )
        
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        logger.error(f"[Serve Project File] Error serving file: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve file.")





# ===========================
# Get Projects Assigned to Current User
# ===========================
@router.get("/assigned")
def assigned_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get projects accessible to current user"""
    if current_user.role == UserRole.superadmin:
        # Superadmin sees all projects
        projects = db.query(Project).all()
    elif current_user.organization_id:
        # Only projects they created or have explicit permission to
        subquery = db.query(ProjectPermission.project_id).filter(
            ProjectPermission.user_id == current_user.id
        ).subquery()
        
        projects = db.query(Project).filter(
            or_(
                Project.creator_id == current_user.id,
                Project.id.in_(subquery)
            )
        ).filter(Project.organization_id == current_user.organization_id).all()
    else:
        # Non-org users see only own projects
        projects = db.query(Project).filter(Project.creator_id == current_user.id).all()
    
    return {
        "assigned_projects": [
            {"project_id": p.id, "project_name": p.name, "description": p.description or ""}
            for p in projects
        ]
    }

# ===========================
# Get All Projects (Admin Only)
# ===========================
@router.get("/all")
def all_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superadmin)
):
    """Get all projects (superadmin only)"""
    projects = db.query(Project).all()
    return {
        "all_projects": [
            {"project_id": p.id, "project_name": p.name, "description": p.description or ""}
            for p in projects
        ]
    }

# ===========================
# Update Project Description (Admin Only)
# ===========================
@router.post("/update_description", summary="Update project description (admin only)")
def update_description(
    project_name: str = Form(...),
    description: str = Form(...),
    current_admin: User = Depends(lambda: require_roles(UserRole.superadmin, UserRole.orgadmin))
):
    try:
        project = graph_manager.get_project_by_name(project_name.strip())
        if not project:
            raise HTTPException(status_code=404, detail="Project not found.")

        if not description.strip():
            raise HTTPException(status_code=400, detail="Description required.")

        success = graph_manager.update_project_description(project["project_id"], description.strip())
        if not success:
            raise HTTPException(status_code=500, detail="Update failed.")

        return {
            "message": f"✅ Description updated.",
            "project_name": project_name.strip(),
            "updated_description": description.strip(),
        }
    except Exception as e:
        logger.error(f"[Update Description] Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update description.")



