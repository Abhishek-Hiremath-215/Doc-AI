import argparse
import json
import re

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from langchain_community.vectorstores import Qdrant as LangchainQdrant
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM

from graph_manager import GraphManager

# Initialize components
embedding = HuggingFaceEmbeddings(model_name="BAAI/bge-large-en-v1.5")
qdrant_client = QdrantClient(url="http://localhost:6333")
collection_name = "project_files"
graph_manager = GraphManager(password="12345678")
llm = OllamaLLM(model="llama3")

def process_project(project_name):
    print(f"[INFO] 🚀 Processing project: {project_name}")

    qdrant = LangchainQdrant(
        client=qdrant_client,
        collection_name=collection_name,
        embeddings=embedding,
    )

    # Fetch relevant chunks
    qdrant_filter = rest.Filter(must=[
        rest.FieldCondition(key="metadata.project_name", match=rest.MatchValue(value=project_name))
    ])

    docs = qdrant.similarity_search(query="*", k=1000, filter=qdrant_filter)
    print(f"[INFO] ✅ Retrieved {len(docs)} chunks for project '{project_name}'")

    for idx, doc in enumerate(docs):
        content = doc.page_content[:3000]
        file_name = doc.metadata.get("source", "unknown")
        
        prompt = (
            "Extract entities in STRICT JSON format with these keys only:\n"
            "{\n"
            "  \"persons\": [{\"name\": \"name\", \"email\": \"email\", \"phone\": \"phone\"}],\n"
            "  \"organizations\": [{\"name\": \"name\"}]\n"
            "}\n\n"
            "ONLY return valid JSON, no explanations.\n\n"
            f"Content:\n{content}"
        )

        try:
            extracted = llm.invoke(prompt)
            json_match = re.search(r"\{.*\}", extracted, re.DOTALL)
            json_str = json_match.group(0) if json_match else "{}"
            entity_data = json.loads(json_str.replace("'", "\""))

            persons = [p.get("name") for p in entity_data.get("persons", []) if p.get("name")]
            orgs = [o.get("name") for o in entity_data.get("organizations", []) if o.get("name")]

            for person_name in persons:
                graph_manager.create_person_node(person_name)
                graph_manager.create_person_project_relationship(person_name, project_name)
                print(f"[INFO] ✅ Linked Person '{person_name}' to Project '{project_name}'")

            for org_name in orgs:
                graph_manager.create_organization_node(org_name)
                graph_manager.create_file_organization_relationship(file_name, org_name)
                print(f"[INFO] ✅ Linked Organization '{org_name}' to File '{file_name}'")

                for person_name in persons:
                    graph_manager.create_person_organization_relationship(person_name, org_name)
                    print(f"[INFO] ✅ Linked Person '{person_name}' WORKED_AT '{org_name}'")

        except Exception as e:
            print(f"[ERROR] ❌ Extraction failed for chunk {idx} in '{file_name}': {e}")

    print(f"[INFO] 🎉 Finished building graph for project '{project_name}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deferred ingestion: Build Neo4j graph from Qdrant vectors.")
    parser.add_argument("--project", type=str, required=True, help="Project name to process")
    args = parser.parse_args()

    try:
        process_project(args.project)
    finally:
        graph_manager.close()
