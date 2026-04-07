# seed_admin.py
from models import User, UserRole
from database import SessionLocal
from passlib.hash import bcrypt

db = SessionLocal()

# Hash the password
hashed_password = bcrypt.hash("admin123")

# Create super admin
super_admin_user = User(
    email="admin@example.com",
    password_hash=hashed_password,
    role=UserRole.superadmin  # match your DB enum exactly
)

db.add(super_admin_user)
db.commit()
db.close()

print("✅ Super admin created successfully.")
