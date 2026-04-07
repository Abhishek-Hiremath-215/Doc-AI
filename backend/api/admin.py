import logging
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.role_enum import UserRole
from models import User, Project
from dependencies import get_db, require_roles
from core.config import graph_manager
from schemas import ProjectOut

logger = logging.getLogger("uvicorn")
router = APIRouter(tags=["Admin"])

# ===========================
# 📦 Pydantic Models
# ===========================
class UserOut(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    created_at: str
    assigned_projects: List[str]


class UsersResponse(BaseModel):
    users: List[UserOut]
    total: int
    page: int
    limit: int


class AssignProjectRequest(BaseModel):
    project_name: str


# ===========================
# 🔹 Helper Functions
# ===========================
def format_project(proj: dict):
    return {
        "id": str(proj.get("project_id")),
        "name": proj.get("project_name", ""),
        "description": proj.get("description", "")
    }


def get_user_by_id(db: Session, user_id: UUID, current_admin: User):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_admin.role == UserRole.orgadmin and user.organization_id != current_admin.organization_id:
        raise HTTPException(status_code=403, detail="Cannot access users outside your organization")
    return user


def get_project_by_name(db: Session, project_name: str, current_admin: User):
    query = db.query(Project).filter(Project.name == project_name)
    if current_admin.role == UserRole.orgadmin:
        query = query.filter(Project.organization_id == current_admin.organization_id)
    project = query.first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found in DB")
    return project


# ===========================
# 🚀 Users Endpoints
# ===========================
@router.get("/users", response_model=UsersResponse)
def get_all_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.superadmin, UserRole.orgadmin)),
):
    query = db.query(User)
    if current_user.role == UserRole.orgadmin:
        query = query.filter(User.organization_id == current_user.organization_id)

    total_users = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    user_list = []
    for user in users:
        try:
            assigned_projects = graph_manager.get_projects_assigned_to_user(str(user.id))
            assigned_projects = sorted({p.strip() for p in assigned_projects if p and p.strip()})
        except Exception as e:
            logger.error(f"[Admin] Error fetching projects for user {user.id}: {e}")
            assigned_projects = []

        user_list.append(UserOut(
            id=str(user.id),
            email=user.email or "",
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            assigned_projects=assigned_projects
        ))

    return UsersResponse(users=user_list, total=total_users, page=page, limit=limit)


@router.put("/users/{user_id}/toggle")
def toggle_user_active(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.superadmin, UserRole.orgadmin)),
):
    user = get_user_by_id(db, user_id, current_user)
    user.is_active = not user.is_active
    db.commit()
    return {"message": f"User {user.email} active status set to {user.is_active}"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.superadmin, UserRole.orgadmin)),
):
    user = get_user_by_id(db, user_id, current_user)
    db.delete(user)
    db.commit()
    return {"message": f"User {user.email} deleted successfully"}


# ===========================
# 🚀 Projects Endpoints
# ===========================
# ✅ New route for frontend: /admin/projects
@router.get("/projects", response_model=List[str])
def list_all_projects_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.superadmin, UserRole.orgadmin)),
):
    """
    Returns a list of all project names.
    Superadmins see all projects.
    Orgadmins see only projects in their organization.
    """
    try:
        query = db.query(Project)
        if current_user.role == UserRole.orgadmin:
            query = query.filter(Project.organization_id == current_user.organization_id)
        projects = query.all()
        return [p.name for p in projects]
    except Exception as e:
        logger.error(f"[Admin] Failed to fetch projects: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch projects")


@router.get("/projects/all")
def get_all_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.superadmin, UserRole.orgadmin)),
):
    try:
        query = db.query(Project)
        if current_user.role == UserRole.orgadmin:
            query = query.filter(Project.organization_id == current_user.organization_id)
        projects = query.all()
        return {"projects": [p.name for p in projects]}
    except Exception as e:
        logger.error(f"[Admin] Error fetching all projects: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch projects")


@router.get("/user/{user_id}/projects", response_model=List[ProjectOut])
def get_projects_by_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.superadmin, UserRole.orgadmin)),
):
    user = get_user_by_id(db, user_id, current_user)
    projects = db.query(Project).filter(Project.creator_id == user_id).all()
    return projects


@router.post("/users/{user_id}/assign_project")
def assign_project_to_user(
    user_id: UUID,
    payload: AssignProjectRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.superadmin, UserRole.orgadmin)),
):
    user = get_user_by_id(db, user_id, current_admin)
    project_name_clean = payload.project_name.strip()
    if not project_name_clean:
        raise HTTPException(status_code=400, detail="Invalid project name")

    db_project = get_project_by_name(db, project_name_clean, current_admin)
    db_project.creator_id = user.id
    db.commit()

    success = graph_manager.assign_project_to_user(str(user.id), db_project.id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to assign project in graph")

    return {"message": f"✅ Project '{project_name_clean}' assigned to user '{user.email}'."}


@router.post("/users/{user_id}/unassign_project")
def unassign_project_from_user(
    user_id: UUID,
    payload: AssignProjectRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.superadmin, UserRole.orgadmin)),
):
    user = get_user_by_id(db, user_id, current_admin)
    project_name_clean = payload.project_name.strip()
    if not project_name_clean:
        raise HTTPException(status_code=400, detail="Invalid project name")

    db_project = get_project_by_name(db, project_name_clean, current_admin)

    success = graph_manager.unassign_project_from_user(str(user.id), db_project.id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to unassign project in graph")

    return {"message": f"✅ Project '{project_name_clean}' unassigned from user '{user.email}'."}


# ===========================
# 🚀 Users with Projects
# ===========================
@router.get("/users_with_created_projects")
def get_users_with_created_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.superadmin, UserRole.orgadmin)),
):
    try:
        query = db.query(User)
        if current_admin.role == UserRole.orgadmin:
            query = query.filter(User.organization_id == current_admin.organization_id)

        total_users = query.count()
        users = query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

        users_with_projects = []
        for user in users:
            try:
                all_projects = graph_manager.get_projects_for_user(str(user.id))
            except Exception as e:
                logger.error(f"[Admin] Error fetching projects for user {user.id}: {e}")
                all_projects = []

            created_projects = []
            assigned_projects = []
            for p in all_projects:
                owner_id = p.get("owner_id")
                if owner_id == str(user.id):
                    created_projects.append(p)
                else:
                    assigned_projects.append(p)

            users_with_projects.append({
                "id": str(user.id),
                "email": user.email or "",
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "assigned_projects": [format_project(p) for p in assigned_projects],
                "created_projects": [format_project(p) for p in created_projects],
            })

        return {"users": users_with_projects, "total": total_users, "page": page, "limit": limit}
    except Exception as e:
        logger.error(f"[Admin] Error in get_users_with_created_projects: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ===========================
# 🚀 Test endpoint
# ===========================
@router.get("/test")
def admin_test(current_admin: User = Depends(require_roles(UserRole.superadmin, UserRole.orgadmin))):
    return {"message": f"Hello Admin {current_admin.email}"}
