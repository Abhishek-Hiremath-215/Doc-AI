# add_project.py

from sqlalchemy.orm import Session
from database import SessionLocal
from models import Project, User
import uuid

# Replace this with a real user ID from your users table
user_id = uuid.UUID("2391c78e-8e5a-4d4e-a7f0-7fac026ae1ec")

def add_project():
    db: Session = SessionLocal()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        print("User not found!")
        return

    project = Project(
        name="Demo Project",
        creator_id=user.id,
        creator_email=user.email  # ✅ now saved in DB
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    print(f"✅ Project created: {project.name} by {project.creator_email}")

if __name__ == "__main__":
    add_project()
