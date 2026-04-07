


import logging
from datetime import datetime
from neo4j import GraphDatabase

from models import User

logger = logging.getLogger("uvicorn")

class GraphManager:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="12345678"):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                logger.info(f"[Neo4j] ✅ Connected: {result.single()}")
        except Exception as e:
            logger.error(f"[Neo4j] ❌ Connection failed: {e}")
            raise e

    def close(self):
        self.driver.close()

    def _safe_run(self, query, **params):
        try:
            with self.driver.session() as session:
                def run_tx(tx):
                    result = tx.run(query, **params)
                    # Consume result fully to avoid "result consumed" errors
                    _ = list(result)
                    return True
                return session.write_transaction(run_tx)
        except Exception as e:
            logger.error(f"[Neo4j] ❌ Query failed: {e}\nQuery: {query}\nParams: {params}")
            return False

    def get_next_project_id(self):
        with self.driver.session() as session:
            result = session.run("""
                MERGE (counter:ProjectCounter {id: 'project_id_counter'})
                ON CREATE SET counter.value = 1
                ON MATCH SET counter.value = counter.value + 1
                RETURN counter.value AS next_id
            """)
            record = result.single()
            return record["next_id"] if record else None

    def create_user_node(self, user_id: str, name: str, email: str, role: str,
                         is_active: bool = True, created_at: str = None):
        created_at = created_at or datetime.utcnow().isoformat()
        logger.info(f"Creating/updating user node: {user_id}")

        return self._safe_run("""
            MERGE (u:User {id: $user_id})
            SET u.name = $name,
                u.email = $email,
                u.role = $role,
                u.is_active = $is_active,
                u.created_at = datetime($created_at)
        """, user_id=str(user_id), name=name.strip(), email=email.strip(),
            role=role.strip(), is_active=bool(is_active), created_at=created_at)

 
    def assign_project_to_user(self, user_id, project_id):
        logger.info(f"Assigning project {project_id} to user {user_id}")
        return self._safe_run("""
            MATCH (u:User {id: $user_id})
            MATCH (p:Project {project_id: toString($project_id)})
            MERGE (u)-[:ASSIGNED_TO]->(p)
        """, user_id=str(user_id), project_id=str(project_id))

    def get_project_by_name(self, project_name):
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (p:Project {project_name: $project_name})
                    RETURN p.project_id AS project_id, p.project_name AS project_name, p.description AS description
                """, project_name=project_name.strip())
                record = result.single()
                return dict(record) if record else None
        except Exception as e:
            logger.error(f"[Neo4j] ❌ get_project_by_name failed: {e}")
            return None

    # Other getters like get_project_by_id, update_project_description, unassign_project_from_user etc. 
    # keep same logic with `toString()` and robust error handling.

    def get_projects_assigned_to_user(self, user_id):
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (u:User {id: $user_id})-[:ASSIGNED_TO]->(p:Project)
                    RETURN p.project_id AS project_id, p.project_name AS project_name, p.description AS description
                """, user_id=str(user_id))
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"[Neo4j] ❌ get_projects_assigned_to_user failed: {e}")
            return []

    def sync_users_to_neo4j(self, db):
        users = db.query(User).all()
        with self.driver.session() as session:
            for user in users:
                try:
                    session.write_transaction(lambda tx: tx.run("""
                        MERGE (u:User {id: $user_id})
                        SET u.email = $email,
                            u.role = $role,
                            u.is_active = $is_active,
                            u.created_at = datetime($created_at)
                    """,
                    user_id=str(user.id),
                    email=user.email,
                    role=user.role.value if hasattr(user.role, 'value') else str(user.role),
                    is_active=user.is_active,
                    created_at=user.created_at.isoformat()
                    ))
                except Exception as e:
                    logger.error(f"[Neo4j] ❌ Failed syncing user {user.id}: {e}")
        logger.info("[Neo4j] ✅ Synced all users to Neo4j")




    def get_projects_for_user(self, user_id):
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (u:User {id: $user_id})
                    OPTIONAL MATCH (u)-[:ASSIGNED_TO]->(p1:Project)
                    OPTIONAL MATCH (p2:Project {owner_id: $user_id})
                    WITH COLLECT(DISTINCT p1) + COLLECT(DISTINCT p2) AS projects
                    UNWIND projects AS project
                    RETURN DISTINCT project.project_id AS project_id,
                                    project.project_name AS project_name,
                                    project.description AS description,
                                    project.owner_id AS owner_id
                """, user_id=str(user_id))
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"[Neo4j] get_projects_for_user failed: {e}")
            return []


    def get_projects_owned_by_user(self, user_id):
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (p:Project {owner_id: $user_id})
                    RETURN p.project_id AS project_id, p.project_name AS project_name, p.description AS description
                """, user_id=str(user_id))
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"[Neo4j] ❌ get_projects_owned_by_user failed: {e}")
            return []
        
    def is_user_owner_of_project(self, user_id: str, project_id: str) -> bool:
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (p:Project {project_id: toString($project_id), owner_id: $user_id})
                    RETURN p
                """, project_id=str(project_id), user_id=str(user_id))
                return result.single() is not None
        except Exception as e:
            logger.error(f"[Neo4j] ❌ is_user_owner_of_project failed: {e}")
            return False

    def is_project_assigned_to_user(self, user_id: str, project_id: str) -> bool:
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (u:User {id: $user_id})-[:ASSIGNED_TO]->(p:Project {project_id: toString($project_id)})
                    RETURN p
                """, user_id=str(user_id), project_id=str(project_id))
                return result.single() is not None
        except Exception as e:
            logger.error(f"[Neo4j] ❌ is_project_assigned_to_user failed: {e}")
            return False
    

        # ✅ Give Admin access to all projects
    def give_admin_access_to_all_projects(self, admin_id: str):
        with self.driver.session() as session:
            session.run("""
                MATCH (a:User {id: $admin_id, role: 'admin'}), (p:Project)
                MERGE (a)-[:HAS_ACCESS_TO]->(p)
            """, admin_id=admin_id)

    # ✅ Give Admin access to all users
    def give_admin_access_to_all_users(self, admin_id: str):
        with self.driver.session() as session:
            session.run("""
                MATCH (a:User {id: $admin_id, role: 'admin'}), (u:User)
                MERGE (a)-[:HAS_ACCESS_TO]->(u)
            """, admin_id=admin_id)


    def create_project_node(self, project_id: int, project_name: str, description: str, owner_id: str):
        logger.info(f"Creating/updating project node: {project_name} (ID: {project_id})")
        return self._safe_run("""
            MERGE (u:User {id: $owner_id})
            MERGE (p:Project {project_id: $project_id})
            ON CREATE SET 
                p.project_name = $project_name,
                p.description = $description,
                p.owner_id = $owner_id,
                p.created_at = datetime()
            MERGE (u)-[:OWNS]->(p)
        """, project_id=int(project_id), project_name=project_name.strip(),
        description=description.strip(), owner_id=owner_id)


    def get_project_by_id(self, project_id: int):
        """
        Fetch a project node from Neo4j by its project_id.
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Project {project_id: $project_id})
                RETURN p { .project_id, .project_name, .description } AS project
                """,
                project_id=str(project_id)  # <-- convert to string
            ).single()
            if result:
                return result["project"]
            return None
        
    def create_file_node(self, file_name: str, project_name: str, summary: str):
        """
        Create a file node in Neo4j and attach metadata.
        """
        with self.driver.session() as session:
            session.run(
                """
                MERGE (f:File {name: $file_name})
                ON CREATE SET 
                    f.project_name = $project_name,
                    f.summary = $summary,
                    f.created_at = datetime()
                """,
                file_name=file_name,
                project_name=project_name,
                summary=summary
            )
        return True
    
    def create_file_project_relationship(self, file_name: str, project_name: str):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (f:File {name: $file_name})
                MATCH (p:Project {project_name: $project_name})
                MERGE (f)-[:BELONGS_TO]->(p)
                """,
                file_name=file_name,
                project_name=project_name
            )
        return True
    

    def get_all_projects(self):
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (p:Project)
                    RETURN p.project_id AS project_id, p.project_name AS project_name, p.description AS description
                """)
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"[Neo4j] ❌ get_all_projects failed: {e}")
            return []


    # Add these methods to your existing GraphManager class

    def create_organization_node(self, org_id: str, name: str, description: str):
        """Create organization node in Neo4j"""
        logger.info(f"Creating organization node: {name}")
        return self._safe_run("""
            MERGE (org:Organization {id: $org_id})
            SET org.name = $name,
                org.description = $description,
                org.created_at = datetime()
        """, org_id=str(org_id), name=name.strip(), description=description.strip())

    def create_org_admin_relationship(self, org_id: str, admin_id: str):
        """Create relationship between organization and its admin"""
        logger.info(f"Creating org-admin relationship: {admin_id} manages {org_id}")
        return self._safe_run("""
            MATCH (org:Organization {id: $org_id})
            MATCH (admin:User {id: $admin_id})
            MERGE (admin)-[:MANAGES]->(org)
            MERGE (org)-[:HAS_ADMIN]->(admin)
            SET admin.organization_id = $org_id
        """, org_id=str(org_id), admin_id=str(admin_id))


