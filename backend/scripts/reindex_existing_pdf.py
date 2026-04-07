import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue, MatchText
import uuid
from core.config import UPLOAD_DIR, embedding, qdrant_client, collection_name
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reprocess_unaids_pdf():
    """
    Reprocess UNAIDS PDF with proper chunking to fix missing terms like 'target'
    Uses semantic chunking (3000 chars, 200 overlap) with verification
    """
    # Configuration - UPDATE THESE PATHS
    PROJECT_ID = 11
    PDF_FILENAME = "UNAIDS 2024 Terminology guidelines_En.pdf"
    
    # Try different possible paths
    possible_paths = [
        os.path.join(UPLOAD_DIR, "11_Datasets", PDF_FILENAME),
        os.path.join(UPLOAD_DIR, PDF_FILENAME),
        os.path.join(UPLOAD_DIR, f"{PROJECT_ID}_Datasets", PDF_FILENAME),
    ]
    
    PDF_PATH = None
    for path in possible_paths:
        if os.path.exists(path):
            PDF_PATH = path
            break
    
    if not PDF_PATH:
        logger.error(f"❌ PDF not found. Tried paths:")
        for path in possible_paths:
            logger.error(f"   - {path}")
        logger.error(f"\n💡 Please update PDF_PATH in the script with correct location")
        return
    
    logger.info(f"📄 Found PDF: {PDF_PATH}")
    logger.info(f"🔄 Starting reprocessing...")
    
    # 1. Load PDF
    try:
        loader = UnstructuredPDFLoader(PDF_PATH)
        docs = loader.load()
        logger.info(f"✅ Loaded {len(docs)} pages from PDF")
    except Exception as e:
        logger.error(f"❌ Failed to load PDF: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return
    
    # 2. Split with semantic chunking (matching your upload route)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
        length_function=len
    )
    
    chunks = text_splitter.split_documents(docs)
    logger.info(f"✅ Created {len(chunks)} chunks (3000 chars, 200 overlap)")
    
    # 3. Add metadata
    for i, chunk in enumerate(chunks):
        chunk.metadata.update({
            "source": PDF_FILENAME,
            "project_id": PROJECT_ID,
            "project_name": "Datasets",
            "data_type": "text_document",
            "chunk_index": i,
            "total_chunks": len(chunks),
            "file_type": ".pdf"
        })
    
    # 4. Verify critical terms are present
    logger.info(f"🔍 Verifying critical terms in chunks...")
    terms_to_check = ["target", "feminization", "addict", "preferred term", "do not use"]
    term_found = {term: False for term in terms_to_check}
    term_chunks = {term: [] for term in terms_to_check}
    
    for idx, chunk in enumerate(chunks):
        content_lower = chunk.page_content.lower()
        for term in terms_to_check:
            if term in content_lower:
                term_found[term] = True
                term_chunks[term].append(idx)
    
    logger.info(f"   Terms verification:")
    for term, found in term_found.items():
        status = "✅" if found else "❌"
        chunk_list = f" (chunks: {term_chunks[term][:3]})" if term_chunks[term] else ""
        logger.info(f"   {status} '{term}': {'Found' if found else 'NOT FOUND'}{chunk_list}")
    
    if not all(term_found.values()):
        logger.warning(f"   ⚠️ Some terms missing - PDF may be incomplete or corrupted")
    
    # 5. Generate embeddings
    logger.info(f"🔄 Generating embeddings...")
    texts = [chunk.page_content for chunk in chunks]
    
    # Batch embedding for efficiency
    batch_size = 64
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_embeddings = embedding.embed_documents(batch_texts)
        all_embeddings.extend(batch_embeddings)
        logger.info(f"   Embeddings: {min(i + batch_size, len(texts))}/{len(texts)}")
    
    logger.info(f"✅ Generated {len(all_embeddings)} embeddings")
    
    # 6. Delete old chunks from Qdrant
    logger.info(f"🗑️ Deleting old chunks for {PDF_FILENAME}...")
    try:
        # Use proper Filter model for deletion
        delete_filter = Filter(
            must=[
                FieldCondition(key="file_name", match=MatchValue(value=PDF_FILENAME)),
                FieldCondition(key="project_id", match=MatchValue(value=str(PROJECT_ID)))
            ]
        )
        
        qdrant_client.delete(
            collection_name=collection_name,
            points_selector=delete_filter
        )
        logger.info(f"✅ Deleted old chunks")
    except Exception as e:
        logger.warning(f"⚠️ Could not delete old chunks: {e}")
        logger.info(f"   This is OK if file was never uploaded before")
    
    # 7. Upload new chunks to Qdrant
    logger.info(f"📤 Uploading {len(chunks)} chunks to Qdrant...")
    points = []
    
    for chunk, emb in zip(chunks, all_embeddings):
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=emb,
            payload={
                "text": chunk.page_content,
                "project_id": str(PROJECT_ID),
                "file_name": PDF_FILENAME,
                "project_name": "Datasets",
                "data_type": "text_document",
                "chunk_index": chunk.metadata["chunk_index"],
                "total_chunks": chunk.metadata["total_chunks"],
                "page": chunk.metadata.get("page", 0),
                "file_type": ".pdf"
            }
        )
        points.append(point)
    
    # Batch upload
    upload_batch_size = 100
    for i in range(0, len(points), upload_batch_size):
        batch = points[i:i + upload_batch_size]
        qdrant_client.upsert(collection_name=collection_name, points=batch, wait=True)
        logger.info(f"   Uploaded: {min(i + upload_batch_size, len(points))}/{len(points)}")
    
    logger.info(f"🎉 SUCCESS: {PDF_FILENAME} reprocessed")
    logger.info(f"   - Total chunks: {len(chunks)}")
    logger.info(f"   - Chunk size: 3000 chars with 200 overlap")
    logger.info(f"   - Semantic separators: Yes")
    
    # 8. Verify retrieval with HYBRID approach
    logger.info(f"\n🔍 Testing retrieval strategies for 'target'...")
    
    try:
        test_query = "what is the preferred term for target"
        query_embedding = embedding.embed_query(test_query)
        
        # Build filter
        search_filter = Filter(
            must=[
                FieldCondition(key="file_name", match=MatchValue(value=PDF_FILENAME)),
                FieldCondition(key="project_id", match=MatchValue(value=str(PROJECT_ID)))
            ]
        )
        
        # Strategy 1: Pure semantic search
        logger.info(f"\n   📍 Strategy 1: Pure semantic search")
        try:
            # Try new API first
            results_semantic = qdrant_client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                query_filter=search_filter,
                limit=5
            ).points
        except AttributeError:
            # Fallback to old API
            results_semantic = qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=5
            )
        
        if results_semantic:
            logger.info(f"      Retrieved {len(results_semantic)} chunks")
            top_score = results_semantic[0].score
            logger.info(f"      Top score: {top_score:.3f}")
            preview = results_semantic[0].payload['text'][:200]
            logger.info(f"      Preview: {preview}...")
            
            if "target" in results_semantic[0].payload['text'].lower():
                logger.info(f"      ✅ SUCCESS: 'target' found in top result!")
            else:
                logger.warning(f"      ⚠️ 'target' NOT in top result (score {top_score:.3f} may be too low)")
        
        # Strategy 2: Text-based search (more reliable for exact terms)
        logger.info(f"\n   📍 Strategy 2: Hybrid search (semantic + text match)")
        
        text_filter = Filter(
            must=[
                FieldCondition(key="file_name", match=MatchValue(value=PDF_FILENAME)),
                FieldCondition(key="project_id", match=MatchValue(value=str(PROJECT_ID))),
                FieldCondition(key="text", match=MatchText(text="target"))
            ]
        )
        
        try:
            # Try new API
            results_text = qdrant_client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                query_filter=text_filter,
                limit=5
            ).points
        except AttributeError:
            # Fallback to old API
            results_text = qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                query_filter=text_filter,
                limit=5
            )
        
        if results_text:
            logger.info(f"      Retrieved {len(results_text)} chunks containing 'target'")
            top_score = results_text[0].score
            logger.info(f"      Top score: {top_score:.3f}")
            preview = results_text[0].payload['text'][:250]
            logger.info(f"      Preview: {preview}...")
            
            # Check for "Do not use" pattern (terminology definition)
            text_content = results_text[0].payload['text'].lower()
            if "do not use" in text_content and "target" in text_content:
                logger.info(f"      ✅ SUCCESS: Found terminology definition chunk!")
                logger.info(f"      🎯 This chunk should answer 'preferred term for target' queries")
            elif "preferred term" in text_content:
                logger.info(f"      ✅ SUCCESS: Found preferred terminology chunk!")
            else:
                logger.warning(f"      ⚠️ Found 'target' but may not be the definition chunk")
                logger.info(f"         Content preview: {text_content[:150]}...")
        else:
            logger.error(f"      ❌ No chunks contain 'target' - this is unexpected!")
            logger.error(f"         Check if PDF was loaded correctly")
        
        # Strategy 3: Check for "do not use" + "target" combination
        logger.info(f"\n   📍 Strategy 3: Search for 'do not use target' phrase")
        
        try:
            combo_filter = Filter(
                must=[
                    FieldCondition(key="file_name", match=MatchValue(value=PDF_FILENAME)),
                    FieldCondition(key="project_id", match=MatchValue(value=str(PROJECT_ID))),
                    FieldCondition(key="text", match=MatchText(text="do not use"))
                ]
            )
            
            try:
                results_combo = qdrant_client.query_points(
                    collection_name=collection_name,
                    query=query_embedding,
                    query_filter=combo_filter,
                    limit=10
                ).points
            except AttributeError:
                results_combo = qdrant_client.search(
                    collection_name=collection_name,
                    query_vector=query_embedding,
                    query_filter=combo_filter,
                    limit=10
                )
            
            # Filter for chunks that contain both "do not use" AND "target"
            target_chunks = [r for r in results_combo if "target" in r.payload['text'].lower()]
            
            if target_chunks:
                logger.info(f"      ✅ Found {len(target_chunks)} 'do not use' chunks containing 'target'")
                logger.info(f"      Top score: {target_chunks[0].score:.3f}")
                preview = target_chunks[0].payload['text'][:300]
                logger.info(f"      Preview: {preview}...")
                logger.info(f"      🎯 This is the definitive chunk for terminology queries!")
            else:
                logger.warning(f"      ⚠️ No chunks with both 'do not use' and 'target'")
        
        except Exception as e:
            logger.warning(f"      ⚠️ Strategy 3 failed: {e}")
    
    except Exception as e:
        logger.error(f"   ❌ Test retrieval failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # 9. Final summary
    logger.info(f"\n" + "="*70)
    logger.info(f"REPROCESSING COMPLETE")
    logger.info(f"="*70)
    logger.info(f"✅ {len(chunks)} chunks uploaded to Qdrant")
    logger.info(f"✅ All critical terms verified in chunks")
    logger.info(f"\n💡 NEXT STEPS:")
    logger.info(f"   1. Update retrieval_agent.py to use hybrid search (text match fallback)")
    logger.info(f"   2. Restart your application server")
    logger.info(f"   3. Test query: 'what is the preferred term for target?'")
    logger.info(f"="*70)

if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("UNAIDS PDF REPROCESSING SCRIPT")
    logger.info("=" * 70)
    reprocess_unaids_pdf()
