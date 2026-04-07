import sys
import os

# Add the parent directory to Python path to import your modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import User, Organization
from core.role_enum import UserRole

def assign_users():
    db = SessionLocal()
    
    try:
        # Get organizations
        draa = db.query(Organization).filter(Organization.name == "DRAA").first()
        new = db.query(Organization).filter(Organization.name == "NEW").first()
        new2 = db.query(Organization).filter(Organization.name == "NEW2").first()
        
        if not all([draa, new, new2]):
            print("❌ One or more organizations not found!")
            return
        
        print(f"🏢 Found organizations:")
        print(f"   DRAA: {draa.id}")
        print(f"   NEW: {new.id}")
        print(f"   NEW2: {new2.id}")
        
        # Define specific user assignments
        assignments = {
            "akash@gmail.com": (draa.id, UserRole.orgadmin),  # Make akash orgadmin of DRAA
            "admin@example.com": (new.id, UserRole.superadmin),  # Keep admin as superadmin in NEW
            # Add more specific assignments as needed
        }
        
        # Apply specific assignments
        for email, (org_id, role) in assignments.items():
            user = db.query(User).filter(User.email == email).first()
            if user:
                user.organization_id = org_id
                user.role = role
                print(f"✅ Assigned {email} to organization with role {role}")
            else:
                print(f"⚠️  User {email} not found")
        
        # Assign remaining unassigned users to NEW2 organization
        unassigned_users = db.query(User).filter(User.organization_id.is_(None)).all()
        for user in unassigned_users:
            user.organization_id = new2.id
            print(f"✅ Assigned {user.email} to NEW2 organization (default)")
        
        db.commit()
        print("🎉 All users assigned to organizations!")
        
        # Verify assignments
        print("\n📋 Final user-organization assignments:")
        all_users = db.query(User).all()
        for user in all_users:
            org_name = "No Organization"
            if user.organization_id:
                org = db.query(Organization).filter(Organization.id == user.organization_id).first()
                if org:
                    org_name = org.name
            print(f"   {user.email} ({user.role}) → {org_name}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    assign_users()
