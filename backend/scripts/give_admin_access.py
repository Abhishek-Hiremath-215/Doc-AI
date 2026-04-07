import sys
import os

# Add parent directory (backend/) to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from graph_manager import GraphManager

# Configure your Neo4j connection
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

# Your Admin UUID
ADMIN_ID = "b116509b-836f-411e-a0a1-2fc57e30a490"

def main():
    gm = GraphManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    # ✅ Give Admin access to all existing projects
    gm.give_admin_access_to_all_projects(ADMIN_ID)

    # ✅ Give Admin access to all existing users
    gm.give_admin_access_to_all_users(ADMIN_ID)

    gm.close()
    print("✅ Admin now has access to all existing projects and users.")

if __name__ == "__main__":
    main()
