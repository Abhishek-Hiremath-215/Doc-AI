from graph_manager import GraphManager
from database import SessionLocal  # or your SQLAlchemy session factory
from models import User

graph_manager = GraphManager()

def sync_users_to_neo4j():
    db = SessionLocal()
    users = db.query(User).all()

    for user in users:
        # derive "name" from email (part before @)
        derived_name = user.email.split("@")[0] if user.email else None

        success = graph_manager._safe_run(
            """
            MERGE (u:User {id: toString($id)})
            ON CREATE SET 
                u.email = $email,
                u.role = $role,
                u.is_active = $is_active,
                u.name = $name,
                u.created_at = datetime($created_at)
            ON MATCH SET
                u.email = $email,
                u.role = $role,
                u.is_active = $is_active,
                u.name = $name,
                u.created_at = datetime($created_at)
            """,
            id=str(user.id),
            email=user.email,
            role=user.role.value if hasattr(user.role, "value") else user.role,
            is_active=user.is_active,
            name=derived_name,
            created_at=user.created_at.isoformat()
        )
        if not success:
            print(f"❌ Failed to sync user {user.email}")
        else:
            print(f"✅ Synced user {user.email}")

    db.close()
    graph_manager.close()

if __name__ == "__main__":
    sync_users_to_neo4j()
