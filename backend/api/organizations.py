import logging
from uuid import UUID, uuid4
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Organization, User, UserRole
from schemas import OrganizationCreate, OrganizationDetail, OrganizationOut, OrgAdminResponse, UserOut
from core.auth import get_password_hash
from core.config import graph_manager  # ✅ Add this import
from dependencies import require_roles

logger = logging.getLogger("uvicorn")
router = APIRouter(tags=["Organizations"])

# -----------------------------
# Create Organization + Org Admin with Neo4j Integration
# -----------------------------
@router.post("/", response_model=OrganizationDetail)
def create_organization(
    org: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.superadmin))
):
    # Check if organization name already exists
    if db.query(Organization).filter(Organization.name == org.name).first():
        raise HTTPException(status_code=400, detail="Organization with this name already exists")
    
    # Check if admin email already exists
    if db.query(User).filter(User.email == org.admin_email).first():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    try:
        # 1. Create organization in PostgreSQL
        org_id = uuid4()
        new_org = Organization(
            id=org_id, 
            name=org.name, 
            description=org.description
        )
        db.add(new_org)
        db.flush()  # Make organization available in session
        
        # 2. Create org admin user in PostgreSQL
        hashed_pw = get_password_hash(org.admin_password)
        new_org_admin = User(
            id=uuid4(),
            email=org.admin_email,
            password_hash=hashed_pw,
            role=UserRole.orgadmin,
            organization_id=org_id,
            is_active=True
        )
        db.add(new_org_admin)
        
        # 3. Commit both to PostgreSQL
        db.commit()
        db.refresh(new_org)
        db.refresh(new_org_admin)

        # ✅ 4. Automatically sync to Neo4j
        try:
            # Create organization node in Neo4j
            graph_manager.create_organization_node(
                org_id=str(new_org.id),
                name=new_org.name,
                description=new_org.description or ""
            )
            logger.info(f"✅ Created organization node in Neo4j: {new_org.name}")
            
            # Create admin user node in Neo4j
            graph_manager.create_user_node(
                user_id=str(new_org_admin.id),
                name=new_org_admin.email.split('@')[0],
                email=new_org_admin.email,
                role=new_org_admin.role.value,
                is_active=new_org_admin.is_active,
                created_at=new_org_admin.created_at.isoformat()
            )
            logger.info(f"✅ Created admin user node in Neo4j: {new_org_admin.email}")
            
            # Create organization-admin relationship
            graph_manager.create_org_admin_relationship(
                org_id=str(new_org.id),
                admin_id=str(new_org_admin.id)
            )
            logger.info(f"✅ Created org-admin relationship in Neo4j")
            
            # ✅ Create automatic access relationships for super admins
            graph_manager._safe_run("""
                MATCH (super:User {role: 'superadmin'})
                MATCH (org:Organization {id: $org_id})
                MERGE (super)-[:HAS_ACCESS]->(org)
                
                WITH super
                MATCH (admin:User {id: $admin_id})
                MERGE (super)-[:HAS_ACCESS]->(admin)
            """, org_id=str(new_org.id), admin_id=str(new_org_admin.id))
            logger.info(f"✅ Created super admin access relationships")
            
        except Exception as neo4j_error:
            logger.error(f"❌ Neo4j sync failed (PostgreSQL data preserved): {neo4j_error}")
            # Don't rollback PostgreSQL - organization still created successfully

        logger.info(f"✅ Organization '{org.name}' created with admin '{org.admin_email}' and Neo4j sync")

        return OrganizationDetail(
            organization=OrganizationOut.from_orm(new_org),
            org_admin=OrgAdminResponse.from_orm(new_org_admin)
        )
        
    except Exception as e:
        logger.error(f"❌ Organization creation failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create organization: {str(e)}")

# -----------------------------
# Get all organizations (unchanged)
# -----------------------------
@router.get("/", response_model=List[OrganizationOut])
def get_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.superadmin, UserRole.orgadmin))
):
    try:
        if current_user.role == UserRole.superadmin:
            organizations = db.query(Organization).all()
        else:
            organizations = db.query(Organization).filter(Organization.id == current_user.organization_id).all()
        
        logger.info(f"[Organizations] Retrieved {len(organizations)} organizations for user {current_user.email}")
        return organizations
    except Exception as e:
        logger.error(f"[Organizations] Failed to fetch organizations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch organizations")

# -----------------------------
# Get users in an organization (unchanged)
# -----------------------------
@router.get("/{org_id}/users", response_model=List[UserOut])
def get_organization_users(
    org_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.superadmin, UserRole.orgadmin))
):
    # Authorization check
    if current_user.role == UserRole.orgadmin and current_user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Cannot view users outside your organization")

    try:
        users = db.query(User).filter(User.organization_id == org_id).all()
        logger.info(f"[Organizations] Retrieved {len(users)} users for organization {org_id}")
        return users
    except Exception as e:
        logger.error(f"[Organizations] Failed to fetch users for org {org_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch users")
