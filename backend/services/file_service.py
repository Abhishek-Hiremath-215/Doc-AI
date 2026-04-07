# services/file_service.py
from sqlalchemy.orm import Session
from typing import List
import os
import logging

from models import Project, User
from graph_manager import GraphManager
from core.role_enum import UserRole

logger = logging.getLogger("uvicorn")

class FileService:
    def __init__(self, db: Session):
        self.db = db
        self.graph_manager = GraphManager()
    
    def create_file_nodes(self, filenames: List[str], project: Project, file_summaries: dict = None) -> None:
        """Create file nodes in Neo4j with automatic relationships"""
        try:
            for filename in filenames:
                summary = file_summaries.get(filename, "File uploaded to project") if file_summaries else "File uploaded to project"
                
                # ✅ Create file node in Neo4j
                self.graph_manager.create_file_node(
                    file_name=filename,
                    project_name=project.name,
                    summary=summary
                )
                
                # ✅ Link file to project
                self.graph_manager.create_file_project_relationship(
                    file_name=filename,
                    project_name=project.name
                )
                
                # ✅ Create automatic file access relationships
                self._create_file_relationships(filename, project)
            
            logger.info(f"✅ Created {len(filenames)} file nodes with automatic relationships")
            
        except Exception as e:
            logger.error(f"❌ File node creation failed: {e}")
            raise e
        finally:
            self.graph_manager.close()
    
    def _create_file_relationships(self, filename: str, project: Project) -> None:
        """Create automatic file access relationships"""
        # Super admins get access to all files
        self.graph_manager._safe_run("""
            MATCH (super:User {role: 'superadmin'})
            MATCH (f:File {name: $filename})
            MERGE (super)-[:HAS_ACCESS]->(f)
        """, filename=filename)
        
        # Org users get access to files in their org projects
        if project.organization_id:
            self.graph_manager._safe_run("""
                MATCH (f:File {name: $filename})-[:BELONGS_TO]->(p:Project)
                MATCH (orguser:User)
                WHERE orguser.organization_id = $org_id
                MERGE (orguser)-[:HAS_ACCESS]->(f)
            """, filename=filename, org_id=str(project.organization_id))
