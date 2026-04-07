# services/user_service.py
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging

from models import User, Organization
from graph_manager import GraphManager
from core.role_enum import UserRole
from core.auth import get_password_hash

logger = logging.getLogger("uvicorn")

class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.graph_manager = GraphManager()
    
    def create_user(self, user_data: Dict[str, Any], current_user: Optional[User] = None) -> User:
        """Create user in both PostgreSQL and Neo4j with automatic relationships"""
        try:
            # Determine organization assignment
            organization_id = self._determine_organization_id(user_data, current_user)
            
            # Create user in PostgreSQL
            new_user = User(
                email=user_data["email"],
                password_hash=get_password_hash(user_data["password"]),
                role=user_data.get("role", UserRole.user),
                organization_id=organization_id,
                is_active=True
            )
            
            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)
            
            # ✅ Automatically create user node in Neo4j
            self._create_neo4j_user_node(new_user)
            
            # ✅ Create automatic role-based relationships
            self._create_user_relationships(new_user)
            
            logger.info(f"✅ User {new_user.email} created with automatic Neo4j sync")
            return new_user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ User creation failed: {e}")
            raise e
        finally:
            self.graph_manager.close()
    
    def _determine_organization_id(self, user_data: Dict[str, Any], current_user: Optional[User]) -> Optional[str]:
        """Determine organization assignment based on current user's role"""
        if current_user:
            if current_user.role == UserRole.orgadmin:
                if not current_user.organization_id:
                    raise ValueError("Organization admin must belong to an organization to create users")
                return current_user.organization_id
            elif current_user.role == UserRole.superadmin:
                return user_data.get("organization_id")
        return user_data.get("organization_id")
    
    def _create_neo4j_user_node(self, user: User) -> None:
        """Create user node in Neo4j"""
        self.graph_manager.create_user_node(
            user_id=str(user.id),
            name=user.email.split('@')[0],
            email=user.email,
            role=user.role.value if hasattr(user.role, 'value') else str(user.role),
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else None
        )
        
        # Add organization relationship
        if user.organization_id:
            self.graph_manager._safe_run("""
                MATCH (u:User {id: $user_id})
                SET u.organization_id = $org_id
            """, user_id=str(user.id), org_id=str(user.organization_id))
    
    def _create_user_relationships(self, user: User) -> None:
        """Create automatic role-based relationships"""
        if user.role == UserRole.superadmin:
            # Super admin gets access to all existing entities
            self.graph_manager._safe_run("""
                MATCH (super:User {id: $user_id})
                MATCH (target) WHERE target:User OR target:Project OR target:File
                MERGE (super)-[:HAS_ACCESS]->(target)
            """, user_id=str(user.id))
            
        elif user.role == UserRole.orgadmin and user.organization_id:
            # Org admin gets access to org entities
            self.graph_manager._safe_run("""
                MATCH (orgadmin:User {id: $user_id})
                MATCH (entity) 
                WHERE entity.organization_id = $org_id AND (entity:User OR entity:Project OR entity:File)
                MERGE (orgadmin)-[:HAS_ACCESS]->(entity)
            """, user_id=str(user.id), org_id=str(user.organization_id))
            
        # Org users get access to their org's projects and files
        if user.organization_id:
            self.graph_manager._safe_run("""
                MATCH (orguser:User {id: $user_id})
                MATCH (project:Project {organization_id: $org_id})
                MERGE (orguser)-[:HAS_ACCESS]->(project)
                
                WITH orguser
                MATCH (file:File)-[:BELONGS_TO]->(project:Project {organization_id: $org_id})
                MERGE (orguser)-[:HAS_ACCESS]->(file)
            """, user_id=str(user.id), org_id=str(user.organization_id))
