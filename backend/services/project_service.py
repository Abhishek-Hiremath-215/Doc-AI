# services/project_service.py
from sqlalchemy.orm import Session
from typing import Dict, Any
import os
import logging

from models import Project, User
from graph_manager import GraphManager
from core.config import UPLOAD_DIR
from core.role_enum import UserRole

logger = logging.getLogger("uvicorn")

class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.graph_manager = GraphManager()
    
    def create_project(self, project_data: Dict[str, Any], creator: User) -> Project:
        """Create project in both PostgreSQL and Neo4j with automatic relationships"""
        try:
            # Create project in PostgreSQL
            new_project = Project(
                name=project_data["name"],
                description=project_data.get("description", ""),
                creator_id=creator.id,
                organization_id=creator.organization_id,  # Auto-assign to creator's org
                folder_path=""
            )
            
            self.db.add(new_project)
            self.db.commit()
            self.db.refresh(new_project)
            
            # Create project folder
            self._create_project_folder(new_project)
            
            # ✅ Automatically create project node in Neo4j
            self._create_neo4j_project_node(new_project, creator)
            
            # ✅ Create automatic access relationships
            self._create_project_relationships(new_project)
            
            logger.info(f"✅ Project '{new_project.name}' created with automatic Neo4j sync")
            return new_project
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Project creation failed: {e}")
            raise e
        finally:
            self.graph_manager.close()
    
    def _create_project_folder(self, project: Project) -> None:
        """Create project folder in filesystem"""
        folder_name = f"{project.id}_{project.name.replace(' ', '_')}"
        project_path = os.path.join(UPLOAD_DIR, folder_name)
        os.makedirs(project_path, exist_ok=True)
        
        project.folder_path = project_path
        self.db.commit()
    
    def _create_neo4j_project_node(self, project: Project, creator: User) -> None:
        """Create project node in Neo4j"""
        self.graph_manager.create_project_node(
            project_id=project.id,
            project_name=project.name,
            description=project.description,
            owner_id=str(project.creator_id)
        )
        
        # Add organization relationship
        if project.organization_id:
            self.graph_manager._safe_run("""
                MATCH (p:Project {project_id: $project_id})
                SET p.organization_id = $org_id
            """, project_id=project.id, org_id=str(project.organization_id))
    
    def _create_project_relationships(self, project: Project) -> None:
        """Create automatic access relationships for project"""
        # Super admins get access to all projects
        self.graph_manager._safe_run("""
            MATCH (super:User {role: 'superadmin'})
            MATCH (p:Project {project_id: $project_id})
            MERGE (super)-[:HAS_ACCESS]->(p)
        """, project_id=project.id)
        
        # Org admins and org users get access to org projects
        if project.organization_id:
            self.graph_manager._safe_run("""
                MATCH (orguser:User)
                WHERE orguser.organization_id = $org_id
                MATCH (p:Project {project_id: $project_id})
                MERGE (orguser)-[:HAS_ACCESS]->(p)
            """, org_id=str(project.organization_id), project_id=project.id)
