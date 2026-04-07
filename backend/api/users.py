from fastapi import APIRouter, Depends, HTTPException, logger, status
from sqlalchemy.orm import Session, selectinload
from passlib.context import CryptContext
from typing import List, Optional
from uuid import UUID

from core.role_enum import UserRole
from models import User, Organization
from schemas import UserCreate, UserLogin, UserOut, Token
from core.auth import get_db, create_access_token, get_current_user, get_current_user_optional

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

@router.post("/register", response_model=UserOut)
def register_user(
    user_in: UserCreate, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    # Check if user already exists
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered.")
    
    # ✅ Automatic organization assignment logic
    organization_id = None
    
    if current_user:
        if current_user.role == UserRole.orgadmin:
            # ✅ Orgadmin can only create users in their own organization
            if not current_user.organization_id:
                raise HTTPException(
                    status_code=400, 
                    detail="Organization admin must belong to an organization to create users"
                )
            organization_id = current_user.organization_id
            print(f"🏢 Orgadmin {current_user.email} creating user in organization: {organization_id}")
            
        elif current_user.role == UserRole.superadmin:
            # ✅ Superadmin can specify organization or leave unassigned
            organization_id = user_in.organization_id
            print(f"🔧 Superadmin creating user with organization: {organization_id}")
    else:
        # ✅ Public registration - no organization assignment
        print("🌐 Public registration - user will be unassigned")
    
    try:
        # 1. Create user in PostgreSQL
        new_user = User(
            email=user_in.email,
            password_hash=hash_password(user_in.password),
            role=user_in.role,
            organization_id=organization_id
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # ✅ 2. Automatically sync to Neo4j
        try:
            from core.config import graph_manager
            
            # Create user node
            graph_manager.create_user_node(
                user_id=str(new_user.id),
                name=new_user.email.split('@')[0],
                email=new_user.email,
                role=new_user.role.value if hasattr(new_user.role, 'value') else str(new_user.role),
                is_active=new_user.is_active,
                created_at=new_user.created_at.isoformat() if new_user.created_at else None
            )
            
            # Add organization relationship
            if new_user.organization_id:
                graph_manager._safe_run("""
                    MATCH (u:User {id: $user_id})
                    SET u.organization_id = $org_id
                """, user_id=str(new_user.id), org_id=str(new_user.organization_id))
            
            # ✅ 3. Create automatic role-based relationships
            if new_user.role == UserRole.superadmin:
                # Super admin gets access to all existing entities
                graph_manager._safe_run("""
                    MATCH (super:User {id: $user_id})
                    MATCH (target) WHERE target:User OR target:Project OR target:File OR target:Organization
                    MERGE (super)-[:HAS_ACCESS]->(target)
                """, user_id=str(new_user.id))
                
            elif new_user.role == UserRole.orgadmin and new_user.organization_id:
                # Org admin gets access to org entities
                graph_manager._safe_run("""
                    MATCH (orgadmin:User {id: $user_id})
                    MATCH (entity) 
                    WHERE entity.organization_id = $org_id AND (entity:User OR entity:Project OR entity:File)
                    MERGE (orgadmin)-[:HAS_ACCESS]->(entity)
                    
                    WITH orgadmin
                    MATCH (org:Organization {id: $org_id})
                    MERGE (orgadmin)-[:MANAGES]->(org)
                """, user_id=str(new_user.id), org_id=str(new_user.organization_id))
                
            # Org users get access to their org's projects and files
            elif new_user.organization_id:
                graph_manager._safe_run("""
                    MATCH (orguser:User {id: $user_id})
                    MATCH (project:Project {organization_id: $org_id})
                    MERGE (orguser)-[:HAS_ACCESS]->(project)
                    
                    WITH orguser
                    MATCH (file:File)-[:BELONGS_TO]->(project:Project {organization_id: $org_id})
                    MERGE (orguser)-[:HAS_ACCESS]->(file)
                """, user_id=str(new_user.id), org_id=str(new_user.organization_id))
            
            # ✅ Super admins always get access to all new users
            graph_manager._safe_run("""
                MATCH (super:User {role: 'superadmin'})
                MATCH (newuser:User {id: $user_id})
                MERGE (super)-[:HAS_ACCESS]->(newuser)
            """, user_id=str(new_user.id))
            
            print(f"✅ User {new_user.email} synced to Neo4j with relationships")
            
        except Exception as neo4j_error:
            logger.error(f"❌ Neo4j sync failed for user {new_user.email}: {neo4j_error}")
            # Don't rollback PostgreSQL - user still created successfully
        
        # ✅ Return user with relationships loaded
        user_with_org = (
            db.query(User)
            .options(selectinload(User.organization), selectinload(User.projects))
            .filter(User.id == new_user.id)
            .first()
        )
        
        print(f"✅ Created user {new_user.email} in organization: {organization_id}")
        return user_with_org
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ User creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@router.post("/login", response_model=Token)
def login_user(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # ✅ FIXED: Use correct relationship name 'projects'
    user_with_org = (
        db.query(User)
        .options(
            selectinload(User.organization),
            selectinload(User.projects)  # ✅ FIXED: Use 'projects' not 'created_projects'
        )
        .filter(User.id == current_user.id)
        .first()
    )
    
    print(f"🔍 /me endpoint - User: {user_with_org.email}")
    print(f"🔍 /me endpoint - Org ID: {user_with_org.organization_id}")
    print(f"🔍 /me endpoint - Organization: {user_with_org.organization}")
    print(f"🔍 /me endpoint - Role: {user_with_org.role}")
    
    return user_with_org

@router.get("/", response_model=List[UserOut])
def list_users(
    organization_filter: Optional[str] = None,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """List users based on current user's role and organization"""
    print(f"🔍 /users endpoint called by: {current_user.email} (role: {current_user.role})")
    
    # ✅ FIXED: Use correct relationship name
    query = db.query(User).options(
        selectinload(User.organization),
        selectinload(User.projects)  # ✅ FIXED: Use 'projects'
    )
    
    # ✅ Role-based filtering
    if current_user.role == UserRole.orgadmin:
        # Orgadmin can only see users in their organization
        if not current_user.organization_id:
            raise HTTPException(status_code=400, detail="Organization admin must belong to an organization")
        query = query.filter(User.organization_id == current_user.organization_id)
        print(f"🏢 Orgadmin filter: showing users from organization {current_user.organization_id}")
        
    elif current_user.role == UserRole.superadmin:
        # Superadmin can see all users and apply organization filter
        if organization_filter and organization_filter != "all":
            if organization_filter == "Unassigned":
                query = query.filter(User.organization_id.is_(None))
            else:
                org = db.query(Organization).filter(Organization.name == organization_filter).first()
                if org:
                    query = query.filter(User.organization_id == org.id)
        print(f"🔧 Superadmin filter: {organization_filter or 'all users'}")
    else:
        # Regular users can't access this endpoint
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    users = query.all()
    
    print(f"🔍 /users endpoint - Loaded {len(users)} users")
    for user in users[:3]:
        org_name = user.organization.name if user.organization else "No Organization"
        print(f"  👤 {user.email} -> Org: {org_name}")
    
    return users

@router.get("/with-projects", response_model=List[UserOut])
def fetch_users_with_projects(
    page: int = 1,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch users with their projects and organizations"""
    print(f"🔍 /users/with-projects called by: {current_user.email} (role: {current_user.role})")
    
    if current_user.role not in [UserRole.superadmin, UserRole.orgadmin]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    offset = (page - 1) * limit
    query = (
        db.query(User)
        .options(
            selectinload(User.organization),
            selectinload(User.projects)  # ✅ FIXED: Use 'projects'
        )
        .offset(offset)
        .limit(limit)
    )
    
    # ✅ Apply role-based filtering
    if current_user.role == UserRole.orgadmin:
        if not current_user.organization_id:
            raise HTTPException(status_code=400, detail="Organization admin must belong to an organization")
        query = query.filter(User.organization_id == current_user.organization_id)
    
    users = query.all()
    
    print(f"🔍 /users/with-projects - Loaded {len(users)} users")
    for user in users[:3]:
        print(f"  User: {user.email}, Org: {user.organization.name if user.organization else 'None'}")
    
    return users

@router.get("/organization", response_model=List[UserOut])
def list_organization_users(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """List users in the current user's organization"""
    print(f"🔍 /users/organization called by: {current_user.email}")
    print(f"🏢 User's organization_id: {current_user.organization_id}")
    print(f"🔑 User's role: {current_user.role}")
    
    if not current_user.organization_id:
        print("❌ User has no organization_id - rejecting request")
        raise HTTPException(status_code=400, detail="User is not part of any organization")
    
    if current_user.role not in [UserRole.orgadmin, UserRole.superadmin]:
        print(f"❌ User role '{current_user.role}' not authorized")
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    print(f"🔍 Querying for users with organization_id: {current_user.organization_id}")
    
    # ✅ FIXED: Use correct relationship name
    users = (
        db.query(User)
        .options(
            selectinload(User.organization),
            selectinload(User.projects)  # ✅ FIXED: Use 'projects'
        )
        .filter(User.organization_id == current_user.organization_id)
        .all()
    )
    
    print(f"👥 Found {len(users)} users in organization")
    
    # Debug: Log each found user with organization info
    for i, user in enumerate(users, 1):
        org_name = user.organization.name if user.organization else 'No Organization'
        print(f"   User {i}: {user.email} (role: {user.role}, org: {org_name}, active: {user.is_active})")
    
    return users

@router.put("/{user_id}/activate", response_model=UserOut)
def toggle_user_activation(
    user_id: UUID, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.superadmin, UserRole.orgadmin]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # ✅ FIXED: Use correct relationship name
    user = (
        db.query(User)
        .options(
            selectinload(User.organization),
            selectinload(User.projects)  # ✅ FIXED: Use 'projects'
        )
        .filter(User.id == user_id)
        .first()
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # ✅ Orgadmin can only manage users in their organization
    if current_user.role == UserRole.orgadmin:
        if not current_user.organization_id:
            raise HTTPException(status_code=400, detail="Organization admin must belong to an organization")
        if user.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Can only manage users in your organization")
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    return user

@router.delete("/{user_id}")
def delete_user(
    user_id: UUID, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.superadmin, UserRole.orgadmin]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # ✅ Orgadmin can only delete users in their organization
    if current_user.role == UserRole.orgadmin:
        if not current_user.organization_id:
            raise HTTPException(status_code=400, detail="Organization admin must belong to an organization")
        if user.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Can only delete users in your organization")
    
    # ✅ Prevent deleting superadmin users
    if user.role == UserRole.superadmin and current_user.role != UserRole.superadmin:
        raise HTTPException(status_code=403, detail="Cannot delete superadmin users")
    
    db.delete(user)
    db.commit()
    return {"detail": "User deleted successfully"}


# Add to your existing api/users.py
from services import UserService
from dependencies import get_user_service

@router.post("/register", response_model=UserOut)
def register_user(
    user_in: UserCreate, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    user_service: UserService = Depends(get_user_service)  # ✅ Add service dependency
):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered.")
    
    # ✅ Use service layer for automatic Neo4j sync
    new_user = user_service.create_user(user_in.dict(), current_user)
    
    # Return user with relationships
    user_with_org = (
        db.query(User)
        .options(selectinload(User.organization), selectinload(User.projects))
        .filter(User.id == new_user.id)
        .first()
    )
    
    return user_with_org
