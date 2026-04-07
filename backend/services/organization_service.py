# services/organization_service.py
from sqlalchemy.orm import Session
from typing import Dict, Any
from uuid import uuid4
import logging

from models import Organization, User
from graph_manager import GraphManager
from core.auth import get_password_hash
from core.role_enum import UserRole

logger = logging.getLogger("uvicorn")

class OrganizationService:
    def __init__(self, db: Session):
        self.db = db
        self.graph_manager = GraphManager()
    
    def create_organization(self, org_data: Dict[str, Any]) -> tuple[Organization, User]:
        """Create organization with org admin in both PostgreSQL and Neo4j"""
        try:
            # Create organization
            org_id = uuid4()
            new_org = Organization(
                id=org_id,
                name=org_data["name"],
                description=org_data.get("description", "")
            )
            self.db.add(new_org)
            self.db.flush()
            
            # Create org admin user
            new_org_admin = User(
                id=uuid4(),
                email=org_data["admin_email"],
                password_hash=get_password_hash(org_data["admin_password"]),
                role=UserRole.orgadmin,
                organization_id=org_id,
                is_active=True
            )
            self.db.add(new_org_admin)
            self.db.commit()
            self.db.refresh(new_org)
            self.db.refresh(new_org_admin)
            
            # ✅ Automatically create nodes in Neo4j
            self._create_neo4j_organization_node(new_org)
            self._create_neo4j_org_admin_node(new_org_admin)
            
            # ✅ Create organization-admin relationship
            self._create_organization_relationships(new_org, new_org_admin)
            
            logger.info(f"✅ Organization '{new_org.name}' created with admin '{new_org_admin.email}'")
            return new_org, new_org_admin
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Organization creation failed: {e}")
            raise e
        finally:
            self.graph_manager.close()
    
    def _create_neo4j_organization_node(self, org: Organization) -> None:
        """Create organization node in Neo4j"""
        self.graph_manager._safe_run("""
            CREATE (org:Organization {
                id: $org_id,
                name: $name,
                description: $description,
                created_at: datetime()
            })
        """, org_id=str(org.id), name=org.name, description=org.description)
    
    def _create_neo4j_org_admin_node(self, user: User) -> None:
        """Create org admin user node in Neo4j"""
        self.graph_manager.create_user_node(
            user_id=str(user.id),
            name=user.email.split('@')[0],
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
        
        self.graph_manager._safe_run("""
            MATCH (u:User {id: $user_id})
            SET u.organization_id = $org_id
        """, user_id=str(user.id), org_id=str(user.organization_id))
    
    def _create_organization_relationships(self, org: Organization, admin: User) -> None:
        """Create organization-admin relationships"""
        self.graph_manager._safe_run("""
            MATCH (org:Organization {id: $org_id})
            MATCH (admin:User {id: $admin_id})
            MERGE (admin)-[:MANAGES]->(org)
            MERGE (org)-[:HAS_ADMIN]->(admin)
        """, org_id=str(org.id), admin_id=str(admin.id))
