from qdrant_client import QdrantClient, models

client = QdrantClient(host="localhost", port=6333)

client.delete(
    collection_name="project_files",
    points_selector=models.FilterSelector(
        filter=models.Filter(must=[])
    )
)

print("project_files is now empty.")


