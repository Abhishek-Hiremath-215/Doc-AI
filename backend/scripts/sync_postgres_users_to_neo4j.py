import sys
import os

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import User, Project
from graph_manager import GraphManager


def sync_users_to_neo4j():
    """Sync users from PostgreSQL to Neo4j without color attributes"""
    db = SessionLocal()
    graph_manager = GraphManager()

    try:
        users = db.query(User).all()
        print(f"[INFO] Found {len(users)} users in PostgreSQL.")

        synced_count = 0
        failed_count = 0

        for user in users:
            try:
                role_str = user.role.value if hasattr(user.role, 'value') else str(user.role)

                # ✅ Create user node WITHOUT color attribute
                created = graph_manager.create_user_node(
                    user_id=str(user.id),
                    name=user.email.split('@')[0],
                    email=user.email,
                    role=role_str,
                    is_active=user.is_active,
                    created_at=user.created_at.isoformat() if user.created_at else None
                )
                
                # ✅ Add organization_id property (no color)
                graph_manager._safe_run("""
                    MATCH (u:User {id: $user_id})
                    SET u.organization_id = $org_id
                """, user_id=str(user.id), 
                org_id=str(user.organization_id) if user.organization_id else None)
                
                if created:
                    print(f"[SYNCED] ✅ User {user.email} (ID: {user.id}) - {role_str}")
                    synced_count += 1
                else:
                    print(f"[EXISTS] 📝 User {user.email} already exists")
                    synced_count += 1
                    
            except Exception as e:
                print(f"[FAILED] ❌ User {user.email}: {e}")
                failed_count += 1

        print(f"\n[SUMMARY] Users sync completed:")
        print(f"  ✅ Synced: {synced_count}")
        print(f"  ❌ Failed: {failed_count}")
        print(f"  📊 Total: {len(users)}")

    except Exception as e:
        print(f"[ERROR] Critical error during users sync: {e}")
    finally:
        db.close()
        graph_manager.close()


def sync_projects_to_neo4j():
    """Sync projects from PostgreSQL to Neo4j without color attributes"""
    db = SessionLocal()
    graph_manager = GraphManager()

    try:
        projects = db.query(Project).all()
        print(f"[INFO] Found {len(projects)} projects in PostgreSQL.")

        synced_count = 0
        failed_count = 0

        for project in projects:
            try:
                # ✅ Create project node WITHOUT color attribute
                created = graph_manager.create_project_node(
                    project_id=project.id,
                    project_name=project.name,
                    description=project.description or "No description available",
                    owner_id=str(project.creator_id) if project.creator_id else "unknown"
                )
                
                # ✅ Add organization_id property (no color)
                graph_manager._safe_run("""
                    MATCH (p:Project {project_id: $project_id})
                    SET p.organization_id = $org_id
                """, project_id=project.id, 
                org_id=str(project.organization_id) if project.organization_id else None)
                
                if created:
                    print(f"[SYNCED] ✅ Project '{project.name}' (ID: {project.id})")
                    synced_count += 1
                else:
                    print(f"[EXISTS] 📝 Project '{project.name}' already exists")
                    synced_count += 1

            except Exception as e:
                print(f"[FAILED] ❌ Project '{project.name}': {e}")
                failed_count += 1

        print(f"\n[SUMMARY] Projects sync completed:")
        print(f"  ✅ Synced: {synced_count}")
        print(f"  ❌ Failed: {failed_count}")
        print(f"  📊 Total: {len(projects)}")

    except Exception as e:
        print(f"[ERROR] Critical error during projects sync: {e}")
    finally:
        db.close()
        graph_manager.close()


def link_existing_files():
    """Link existing files from uploaded_files directory to Neo4j"""
    graph_manager = GraphManager()
    
    try:
        print("\n[FILES] Linking existing uploaded files to Neo4j...")
        
        with graph_manager.driver.session() as session:
            # ✅ Find existing file nodes (created by your upload process)
            result = session.run("MATCH (f:File) RETURN count(f) as file_count")
            record = result.single()
            file_count = record["file_count"] if record else 0
            print(f"📊 Found {file_count} existing files in Neo4j")
            
            if file_count > 0:
                # Show sample files
                result = session.run("""
                    MATCH (f:File) 
                    OPTIONAL MATCH (f)-[:BELONGS_TO]->(p:Project)
                    RETURN f.name as filename, p.project_name as project_name 
                    LIMIT 5
                """)
                
                print("📋 Sample uploaded files:")
                for record in result:
                    filename = record.get("filename", "N/A")
                    project = record.get("project_name", "Not linked")
                    print(f"  - {filename} → {project}")
            else:
                print("ℹ️  No files found. Files will be created when you upload through the API.")
                
        print("✅ File linking verification completed")
        
    except Exception as e:
        print(f"[ERROR] Failed to link files: {e}")
    finally:
        graph_manager.close()


def create_role_based_relationships():
    """Create hierarchical relationships based on roles and organization"""
    graph_manager = GraphManager()
    
    try:
        print("\n[RELATIONSHIPS] Creating role-based access relationships...")
        
        with graph_manager.driver.session() as session:
            # ✅ Super Admin has access to ALL unassigned users, org admins, projects, files
            session.run("""
                MATCH (super:User {role: 'superadmin'})
                MATCH (target:User) WHERE target.role IN ['user', 'orgadmin'] OR target.organization_id IS NULL
                MERGE (super)-[:HAS_ACCESS]->(target)
            """)
            
            session.run("""
                MATCH (super:User {role: 'superadmin'})
                MATCH (project:Project)
                MERGE (super)-[:HAS_ACCESS]->(project)
            """)
            
            session.run("""
                MATCH (super:User {role: 'superadmin'})
                MATCH (file:File)
                MERGE (super)-[:HAS_ACCESS]->(file)
            """)
            print("✅ Super admin relationships created")
            
            # ✅ Org Admin has access to users in their organization
            session.run("""
                MATCH (orgadmin:User {role: 'orgadmin'})
                MATCH (orguser:User) 
                WHERE orguser.organization_id = orgadmin.organization_id 
                AND orguser.role = 'user'
                MERGE (orgadmin)-[:MANAGES]->(orguser)
            """)
            
            # ✅ Org Admin has access to projects in their organization
            session.run("""
                MATCH (orgadmin:User {role: 'orgadmin'})
                MATCH (project:Project) 
                WHERE project.organization_id = orgadmin.organization_id
                MERGE (orgadmin)-[:HAS_ACCESS]->(project)
            """)
            
            # ✅ Org Admin has access to files in their organization projects
            session.run("""
                MATCH (orgadmin:User {role: 'orgadmin'})
                MATCH (file:File)-[:BELONGS_TO]->(project:Project)
                WHERE project.organization_id = orgadmin.organization_id
                MERGE (orgadmin)-[:HAS_ACCESS]->(file)
            """)
            print("✅ Org admin relationships created")
            
            # ✅ All users in org have access to org projects and files
            session.run("""
                MATCH (orguser:User) 
                WHERE orguser.organization_id IS NOT NULL
                MATCH (project:Project)
                WHERE project.organization_id = orguser.organization_id
                MERGE (orguser)-[:HAS_ACCESS]->(project)
            """)
            
            session.run("""
                MATCH (orguser:User) 
                WHERE orguser.organization_id IS NOT NULL
                MATCH (file:File)-[:BELONGS_TO]->(project:Project)
                WHERE project.organization_id = orguser.organization_id
                MERGE (orguser)-[:HAS_ACCESS]->(file)
            """)
            print("✅ Organization user relationships created")
            
        print("[RELATIONSHIPS] ✅ All role-based relationships created successfully!")
        
    except Exception as e:
        print(f"[ERROR] Failed to create relationships: {e}")
    finally:
        graph_manager.close()


def verify_graph():
    """Verify the graph structure without colors"""
    graph_manager = GraphManager()
    
    try:
        print("\n[VERIFICATION] Checking graph structure...")
        
        with graph_manager.driver.session() as session:
            # Count nodes by type and role
            result = session.run("""
                MATCH (n:User)
                RETURN n.role as role, count(n) as count
                ORDER BY role
            """)
            
            print("📊 User counts by role:")
            for record in result:
                if record["role"]:
                    print(f"  {record['role']:12} : {record['count']}")
            
            # Count projects and files
            result = session.run("MATCH (p:Project) RETURN count(p) as count")
            project_count = result.single()["count"] if result.single() else 0
            print(f"📊 Projects: {project_count}")
            
            result = session.run("MATCH (f:File) RETURN count(f) as count")
            file_count = result.single()["count"] if result.single() else 0
            print(f"📊 Files: {file_count}")
            
            # Count relationships by type
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(r) as count
                ORDER BY rel_type
            """)
            
            print("\n📊 Relationship counts:")
            for record in result:
                print(f"  {record['rel_type']:15} : {record['count']}")
            
            # Show super admin connections
            result = session.run("""
                MATCH (super:User {role: 'superadmin'})-[r]->(target)
                RETURN labels(target)[0] as target_type, count(r) as connections
                ORDER BY target_type
            """)
            
            print("\n📊 Super admin connections:")
            for record in result:
                print(f"  → {record['target_type']:8} : {record['connections']} connections")
        
    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
    finally:
        graph_manager.close()


def sync_all_with_relationships():
    """Complete sync with hierarchical relationships (no colors, no dummy files)"""
    print("🚀 Starting PostgreSQL to Neo4j sync with role-based relationships...\n")
    
    print("=" * 60)
    print("STEP 1: Syncing Users (role-based)")
    print("=" * 60)
    sync_users_to_neo4j()
    
    print("\n" + "=" * 60)
    print("STEP 2: Syncing Projects")
    print("=" * 60)
    sync_projects_to_neo4j()
    
    print("\n" + "=" * 60)
    print("STEP 3: Linking Existing Files")
    print("=" * 60)
    link_existing_files()
    
    print("\n" + "=" * 60)
    print("STEP 4: Creating Role-based Relationships")
    print("=" * 60)
    create_role_based_relationships()
    
    print("\n" + "=" * 60)
    print("STEP 5: Verification")
    print("=" * 60)
    verify_graph()
    
    print("\n✅ Complete hierarchical graph sync finished!")
    print("\n🏗️  Graph Structure (without color attributes):")
    print("  👑 Super Admin → Access to ALL users, projects, files")
    print("  👔 Org Admin → Manages org users, access to org projects/files") 
    print("  👥 Org Users → Access to org projects and files")
    print("  👤 Users → Individual access based on assignments")
    print("  📁 Projects → Linked to organizations")
    print("  📄 Files → From uploaded_files directory, linked to projects")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync PostgreSQL data to Neo4j with role-based relationships")
    parser.add_argument("--users", action="store_true", help="Sync users only")
    parser.add_argument("--projects", action="store_true", help="Sync projects only")
    parser.add_argument("--relationships", action="store_true", help="Create relationships only")
    parser.add_argument("--files", action="store_true", help="Link existing files only")
    parser.add_argument("--verify", action="store_true", help="Verify graph only")
    
    args = parser.parse_args()
    
    if args.users:
        sync_users_to_neo4j()
    elif args.projects:
        sync_projects_to_neo4j()
    elif args.relationships:
        create_role_based_relationships()
    elif args.files:
        link_existing_files()
    elif args.verify:
        verify_graph()
    else:
        # Default: sync all with relationships
        sync_all_with_relationships()
