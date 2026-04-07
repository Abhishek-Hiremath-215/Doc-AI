from sqlalchemy.orm import Session
from models import User, Project
from database import SessionLocal
import uuid
from graph_manager import get_projects_from_neo4j

def sync_projects_to_postgres():
    neo4j_projects = get_projects_from_neo4j()
    db: Session = SessionLocal()

    for project_data in neo4j_projects:
        user = db.query(User).filter_by(email=project_data["email"]).first()
        if user:
            existing_project = db.query(Project).filter_by(name=project_data["name"], creator_id=user.id).first()
            if not existing_project:
                project = Project(
                    id=uuid.uuid4(),
                    name=project_data["name"],
                    creator_id=user.id,
                    creator_email=user.email  # new column
                )
                db.add(project)
                print(f"✅ Added: {project.name} for {user.email}")
        else:
            print(f"⚠️ Skipping project '{project_data['name']}' — user not found: {project_data['email']}")

    db.commit()
    db.close()
