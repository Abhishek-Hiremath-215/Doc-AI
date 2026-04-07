from database import engine, Base
from models import Organization, User, Project

# This will create all tables
print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created successfully")
