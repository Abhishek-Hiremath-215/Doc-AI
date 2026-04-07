from qdrant_client import QdrantClient
import qdrant_client.http.models as rest

client = QdrantClient(url='http://localhost:6333')

print("🔧 Fixing Qdrant collection...")
print()

# Check current state
info = client.get_collection('project_files')
print(f"Current vector size: {info.config.params.vectors.size}")
print(f"Current points: {info.points_count}")
print()

# Delete old collection
print("🗑️ Deleting old collection...")
client.delete_collection('project_files')
print("✅ Deleted!")
print()

# Create new collection with correct size
print("📦 Creating new collection with size=1536...")
client.create_collection(
    collection_name='project_files',
    vectors_config=rest.VectorParams(size=1536, distance=rest.Distance.COSINE)
)
print("✅ Collection created!")
print()

# Verify
info = client.get_collection('project_files')
print(f"New vector size: {info.config.params.vectors.size}")
print(f"New points: {info.points_count}")
print()

print("=" * 60)
print("🎉 SUCCESS! Collection fixed!")
print()
print("⚠️ IMPORTANT: Now you must RE-UPLOAD all files:")
print("   1. Go to project 13 in your UI")
print("   2. Delete 4.xlsx")
print("   3. Upload 4.xlsx again")
print()
print("After re-upload, test: 'What does gghed mean?'")
print("=" * 60)
