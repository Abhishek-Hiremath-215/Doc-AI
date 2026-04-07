

# """
# Universal Retrieval Agent - Semantic search for ANY question type
# PRODUCTION-READY with optimized thresholds and content key compatibility
# """
# import logging
# from typing import List, Dict, Any
# from core.config import qdrant_client, embedding, collection_name, graph_manager
# from qdrant_client.http import models as rest

# logger = logging.getLogger("uvicorn")

# class RetrievalAgent:
#     """
#     Universal retrieval system:
#     - Works for ANY question type (WHO/WHAT/WHEN/WHERE/HOW)
#     - Semantic search (not just keyword matching)
#     - Multi-tier fallback strategy
#     - Context-aware chunk merging
#     - Adaptive score thresholds
#     - Content key compatibility (ensures both "text" and "content" keys)
#     """

#     # Score thresholds for different retrieval tiers
#     PRIMARY_THRESHOLD = 0.5    # High confidence matches
#     SECONDARY_THRESHOLD = 0.3  # Good matches
#     FALLBACK_THRESHOLD = 0.15  # Broader matches

#     async def process(self, state: dict) -> dict:
#         """Main retrieval orchestrator"""
#         query = state["query"]
#         project_id = state.get("project_id")
#         selected_files = state.get("selected_files", [])
#         requires_documents = state.get("requires_documents", False)
#         requires_graph = state.get("requires_graph", False)

#         documents = []
#         graph_data = None

#         logger.info(f"🔍 RETRIEVAL AGENT STARTED")
#         logger.info(f"   - Query: {query[:100]}")
#         logger.info(f"   - Project ID: {project_id}")
#         logger.info(f"   - Selected files: {selected_files}")

#         # Document retrieval with adaptive thresholds
#         if requires_documents and project_id:
#             try:
#                 documents = await self._universal_search(
#                     query=query,
#                     project_id=project_id,
#                     selected_files=selected_files
#                 )

#                 # Merge adjacent chunks for complete context
#                 documents = self._merge_adjacent_chunks(documents)
#                 logger.info(f"✅ Retrieved {len(documents)} documents")

#             except Exception as e:
#                 logger.error(f"❌ Retrieval error: {e}")
#                 import traceback
#                 logger.error(traceback.format_exc())
#                 state["error"] = f"Retrieval failed: {str(e)}"

#         # Graph data retrieval
#         if requires_graph and project_id:
#             try:
#                 user_id = state.get("user_id")
#                 project_data = graph_manager.get_project_by_id(project_id)
#                 assigned_users = []
#                 try:
#                     assigned_users = graph_manager.get_projects_assigned_to_user(user_id)
#                 except Exception as e:
#                     logger.warning(f"   - Could not get assigned users: {e}")

#                 graph_data = {
#                     "project": project_data,
#                     "assigned_users": assigned_users,
#                 }
#                 logger.info(f"✅ Retrieved graph data")

#             except Exception as e:
#                 logger.error(f"❌ Graph retrieval error: {e}")

#         logger.info(f"🏁 RETRIEVAL COMPLETE")

#         return {
#             **state,
#             "documents": documents,
#             "graph_data": graph_data
#         }

#     async def universal_search(
#         self, 
#         query: str, 
#         project_id: int, 
#         selected_files: List[str]
#     ) -> List[Dict[str, Any]]:
#         """
#         Universal semantic search with DYNAMIC HIERARCHICAL FILTERING.
#         Uses LLM to extract filters from query - works for ANY domain/file.
#         """
#         project_id_str = str(project_id)
        
#         # Base filter
#         must_conditions = [
#             rest.FieldCondition(key="project_id", match=rest.MatchValue(value=project_id_str))
#         ]
        
#         # File filter
#         if selected_files and len(selected_files) > 0:
#             logger.info(f"   - File filter: {selected_files}")
#             must_conditions.append(
#                 rest.FieldCondition(key="file_name", match=rest.MatchAny(any=selected_files))
#             )
        
#         # ✅ GENERIC: Let LLM extract filters dynamically
#         hierarchy_filters = await self._extract_filters_with_llm(query, project_id_str)
        
#         if hierarchy_filters:
#             logger.info(f"   - Dynamic filters extracted: {hierarchy_filters}")
            
#             # Apply ALL extracted filters generically
#             for field_name, field_value in hierarchy_filters.items():
#                 if field_value:  # Only add non-empty filters
#                     must_conditions.append(
#                         rest.FieldCondition(
#                             key=field_name,
#                             match=rest.MatchValue(value=field_value)
#                         )
#                     )
        
#         search_filter = rest.Filter(must=must_conditions)
        
#         # Generate query vector
#         query_vector = embedding.embed_query(query)
#         logger.info(f"   Semantic search for: {query[:100]}")
        
#         # Tier 1: High confidence
#         search_results = qdrant_client.search(
#             collection_name=collection_name,
#             query_vector=query_vector,
#             query_filter=search_filter,
#             limit=20,
#             score_threshold=self.PRIMARY_THRESHOLD
#         )
        
#         logger.info(f"   - Tier 1 (threshold {self.PRIMARY_THRESHOLD}): {len(search_results)} matches")
        
#         # Fallback tiers
#         if len(search_results) < 3:
#             logger.info(f"   - Falling back to Tier 2 (threshold {self.SECONDARY_THRESHOLD})")
#             search_results = qdrant_client.search(
#                 collection_name=collection_name,
#                 query_vector=query_vector,
#                 query_filter=search_filter,
#                 limit=20,
#                 score_threshold=self.SECONDARY_THRESHOLD
#             )
#             logger.info(f"   - Tier 2: {len(search_results)} matches")
        
#         if len(search_results) < 3:
#             logger.info(f"   - Falling back to Tier 3 (threshold {self.FALLBACK_THRESHOLD})")
#             search_results = qdrant_client.search(
#                 collection_name=collection_name,
#                 query_vector=query_vector,
#                 query_filter=search_filter,
#                 limit=20,
#                 score_threshold=self.FALLBACK_THRESHOLD
#             )
#             logger.info(f"   - Tier 3: {len(search_results)} matches")
        
#         if not search_results:
#             logger.warning(f"   ⚠️ No results found across all tiers")
        
#         # Build documents (existing logic)
#         documents = []
#         for i, hit in enumerate(search_results):
#             logger.info(f"   - Result {i+1}: {hit.payload.get('file_name')} (score: {hit.score:.3f})")
            
#             text_content = hit.payload.get("text", "")
            
#             doc = {
#                 "text": text_content,
#                 "content": text_content,
#                 "file_name": hit.payload.get("file_name", "Unknown"),
#                 "score": hit.score,
#                 "data_type": hit.payload.get("data_type", "text_document"),
#                 "metadata": {
#                     "project_id": hit.payload.get("project_id"),
#                     "chunk_index": hit.payload.get("chunk_index"),
#                     "page": hit.payload.get("page", "N/A"),
#                     "sheet_name": hit.payload.get("sheet_name", "N/A"),
#                     "row_range": hit.payload.get("row_range", "N/A"),
#                     "row": hit.payload.get("row", "N/A"),
#                     "source": hit.payload.get("source", "Unknown")
#                 }
#             }
            
#             if "rows_data" in hit.payload:
#                 doc["rows_data"] = hit.payload["rows_data"]
#             if "column_names" in hit.payload:
#                 doc["column_names"] = hit.payload["column_names"]
#             if "row_count" in hit.payload:
#                 doc["row_count"] = hit.payload["row_count"]
#             doc["column_count"] = hit.payload.get("column_count", 0)
            
#             documents.append(doc)
        
#         return documents


#     async def _extract_filters_with_llm(self, query: str, project_id: str) -> dict:
#         """
#         GENERIC filter extraction using LLM.
#         Discovers available fields from data and extracts values from query.
#         Works for ANY domain - healthcare, sales, finance, etc.
#         """
#         try:
#             # Step 1: Get sample document to discover available metadata fields
#             sample_doc = qdrant_client.scroll(
#                 collection_name=collection_name,
#                 scroll_filter=rest.Filter(
#                     must=[rest.FieldCondition(key="project_id", match=rest.MatchValue(value=project_id))]
#                 ),
#                 limit=1,
#                 with_payload=True
#             )
            
#             if not sample_doc or not sample_doc[0]:
#                 logger.warning("   No sample document found - skipping filter extraction")
#                 return {}
            
#             # Extract available metadata fields
#             sample_payload = sample_doc[0][0].payload
#             available_fields = {}
            
#             # Look for common hierarchy/metadata fields
#             metadata_keys = ["region", "country", "treatment_line", "regimen", 
#                             "category", "department", "product", "location",
#                             "hierarchy_level_1", "hierarchy_level_2", "hierarchy_level_3"]
            
#             for key in metadata_keys:
#                 if key in sample_payload:
#                     example_value = sample_payload.get(key, "")
#                     if example_value and str(example_value).strip() and str(example_value) != "None":
#                         available_fields[key] = example_value
            
#             if not available_fields:
#                 logger.info("   No filterable metadata fields found")
#                 return {}
            
#             logger.info(f"   Available filter fields: {list(available_fields.keys())}")
            
#             # Step 2: Ask LLM to extract filter values from query
#             from core.config import settings
#             from langchain_openai import ChatOpenAI
#             from langchain_ollama import ChatOllama
#             from langchain_core.messages import SystemMessage, HumanMessage
#             import json
            
#             # Initialize LLM
#             if settings.LLM_PROVIDER.lower() == "openai":
#                 llm = ChatOpenAI(
#                     model=settings.OPENAI_MODEL,
#                     api_key=settings.OPENAI_API_KEY,
#                     temperature=0.0
#                 )
#             else:
#                 llm = ChatOllama(
#                     model=settings.LLM_MODEL,
#                     base_url=settings.LLM_BASE_URL,
#                     temperature=0.0
#                 )
            
#             # Create field descriptions for LLM
#             field_descriptions = "\n".join([
#                 f"- {field}: (example: '{value}')" 
#                 for field, value in list(available_fields.items())[:5]
#             ])
            
#             extraction_prompt = f"""You are a metadata extraction assistant. Extract filter values from the user's query.

#     Available metadata fields in this dataset:
#     {field_descriptions}

#     User Query: "{query}"

#     Extract any mentioned values that match these fields. Return ONLY a JSON object.

#     Rules:
#     1. Only extract fields that are explicitly mentioned in the query
#     2. Use exact capitalization when possible (e.g., "Afghanistan" not "afghanistan")
#     3. Return empty object {{}} if no filters detected
#     4. Field names must EXACTLY match the available fields listed above

#     Example 1:
#     Query: "What is the cost in Afghanistan for 1st Line?"
#     Output: {{"country": "Afghanistan", "treatment_line": "1st Line"}}

#     Example 2:
#     Query: "Show me sales data"
#     Output: {{}}

#     Your JSON response:"""

#             messages = [
#                 SystemMessage(content="You extract metadata filters from queries. Output valid JSON only."),
#                 HumanMessage(content=extraction_prompt)
#             ]
            
#             response = await llm.ainvoke(messages)
#             response_text = response.content.strip()
            
#             # Clean response (remove markdown code blocks if present)
#             import re
#             response_text = re.sub(r'```json\s*|\s*```', '', response_text).strip()
            
#             # Parse JSON
#             filters = json.loads(response_text)
            
#             # Validate: only return fields that actually exist in metadata
#             valid_filters = {
#                 k: v for k, v in filters.items() 
#                 if k in available_fields.keys() and v and str(v).strip()
#             }
            
#             logger.info(f"   Extracted filters: {valid_filters}")
#             return valid_filters
            
#         except Exception as e:
#             logger.warning(f"   Filter extraction failed: {e} - proceeding without filters")
#             return {}

#     def _merge_adjacent_chunks(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#         """
#         Merge chunks from same file for complete context
#         Helps reconstruct full answers from split chunks

#         ✅ Ensures merged documents also have both "content" and "text" keys
#         """
#         if not documents:
#             return documents

#         # Group by file
#         file_groups = {}
#         for doc in documents:
#             file_name = doc["file_name"]
#             if file_name not in file_groups:
#                 file_groups[file_name] = []
#             file_groups[file_name].append(doc)

#         merged = []
#         for file_name, file_docs in file_groups.items():
#             if len(file_docs) == 1:
#                 # Single chunk - no merging needed
#                 # Ensure both keys exist
#                 if "content" not in file_docs[0] and "text" in file_docs[0]:
#                     file_docs[0]["content"] = file_docs[0]["text"]
#                 elif "text" not in file_docs[0] and "content" in file_docs[0]:
#                     file_docs[0]["text"] = file_docs[0]["content"]
#                 merged.extend(file_docs)
#             else:
#                 # Multiple chunks - merge top 3 by score
#                 file_docs.sort(key=lambda x: x["score"], reverse=True)
#                 top_docs = file_docs[:3]

#                 # Concatenate content using "content" key (already set in _universal_search)
#                 merged_content = "\n\n--- Document Section ---\n\n".join(
#                     [d.get("content", d.get("text", "")) for d in top_docs]
#                 )

#                 # ✅ FIX: Set BOTH keys in merged document
#                 merged_doc = {
#                     "text": merged_content,        # ← For consistency with Qdrant format
#                     "content": merged_content,     # ← For response agent compatibility
#                     "file_name": file_name,
#                     "score": max(d["score"] for d in top_docs),  # Use highest score
#                     "data_type": top_docs[0]["data_type"],
#                     "metadata": {
#                         **top_docs[0]["metadata"],
#                         "merged_chunks": len(top_docs)
#                     }
#                 }

#                 # Merge Excel/CSV row data if present
#                 if top_docs[0].get("rows_data"):
#                     all_rows = []
#                     for d in top_docs:
#                         if d.get("rows_data"):
#                             all_rows.extend(d["rows_data"])
#                     merged_doc["rows_data"] = all_rows

#                 if top_docs[0].get("column_names"):
#                     merged_doc["column_names"] = top_docs[0]["column_names"]

#                 if top_docs[0].get("row_count"):
#                     merged_doc["row_count"] = sum(d.get("row_count", 0) for d in top_docs)
#                     merged_doc["column_count"] = top_docs[0].get("column_count", 0)

#                 merged.append(merged_doc)
#                 logger.info(f"   📎 Merged {len(top_docs)} chunks from {file_name} (combined score: {merged_doc['score']:.3f})")

#         return merged

# # Export for workflow integration
# retrieval_agent = RetrievalAgent()

"""
Universal Retrieval Agent - Production-Ready
Optimized for row-based Excel data with zero full-table scans
✅ Works with BOTH "year: 2008" AND "year: 2008.0" formats
✅ Generic matching for ANY dataset structure
"""
import logging
import re
from typing import List, Dict, Any, Optional
from core.config import qdrant_client, embedding, collection_name, graph_manager
from qdrant_client.http import models as rest


logger = logging.getLogger("uvicorn")


class RetrievalAgent:
    """
    Production retrieval system:
    - ZERO full-table scans (uses Qdrant filters)
    - Dynamic location discovery (no hardcoded lists)
    - Configurable thresholds per project
    - LLM optimization with regex pre-pass
    - Standardized output schema
    - ✅ Handles both integer and float year formats
    """

    def __init__(self):
        # Configurable thresholds (can be set per project)
        self.thresholds = {
            "primary": 0.3,
            "secondary": 0.2,
            "fallback": 0.1,
            "codebook": 0.4
        }

    async def process(self, state: dict) -> dict:
        """Main retrieval orchestrator"""
        query = state["query"]
        project_id = state.get("project_id")
        selected_files = state.get("selected_files", [])
        requires_documents = state.get("requires_documents", False)
        requires_graph = state.get("requires_graph", False)

        documents = []
        graph_data = None

        logger.info(f"🔍 RETRIEVAL AGENT STARTED")
        logger.info(f"   - Query: {query[:100]}")
        logger.info(f"   - Project ID: {project_id}")
        logger.info(f"   - Selected files: {selected_files}")

        # Document retrieval
        if requires_documents and project_id:
            try:
                documents = await self._intelligent_search(
                    query=query,
                    project_id=project_id,
                    selected_files=selected_files
                )

                logger.info(f"✅ Retrieved {len(documents)} documents")

            except Exception as e:
                logger.error(f"❌ Retrieval error: {e}")
                import traceback
                logger.error(traceback.format_exc())
                state["error"] = f"Retrieval failed: {str(e)}"

        # Graph data retrieval
        if requires_graph and project_id:
            try:
                user_id = state.get("user_id")
                project_data = graph_manager.get_project_by_id(project_id)
                assigned_users = []
                try:
                    assigned_users = graph_manager.get_projects_assigned_to_user(user_id)
                except Exception as e:
                    logger.warning(f"   - Could not get assigned users: {e}")

                graph_data = {
                    "project": project_data,
                    "assigned_users": assigned_users,
                }
                logger.info(f"✅ Retrieved graph data")

            except Exception as e:
                logger.error(f"❌ Graph retrieval error: {e}")

        logger.info(f"🏁 RETRIEVAL COMPLETE")

        return {
            **state,
            "documents": documents,
            "graph_data": graph_data
        }

    async def _intelligent_search(
        self,
        query: str,
        project_id: int,
        selected_files: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Intelligent search strategy with zero full-table scans
        """
        project_id_str = str(project_id)
        
        # STRATEGY 1: Direct lookup with Qdrant filters (O(1) operation)
        logger.info(f"   🎯 Attempting direct lookup with Qdrant filters...")
        direct_results = await self._direct_row_lookup_optimized(query, project_id_str, selected_files)
        
        if direct_results:
            logger.info(f"   ✅ Direct lookup succeeded: {len(direct_results)} exact matches")
            return direct_results
        
        # STRATEGY 2: Semantic search fallback
        logger.info(f"   🔍 Direct lookup failed, using semantic search...")
        return await self._semantic_search(query, project_id_str, selected_files)

    def _extract_year_flexible(self, query: str) -> Optional[str]:
        """
        ✅ Flexible year detection
        Handles: 2004, FY 2004, 2004-05, Year:2004, etc.
        """
        patterns = [
            r'\b(19\d{2}|20\d{2})\b',           # Standard: 2004
            r'FY\s*(\d{4})',                     # FY 2004
            r'year[:\s]+(\d{4})',                # Year: 2004
            r'(\d{4})[–-]\d{2,4}',              # 2004-05 or 2004–2005
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    async def _check_metadata_field_exists(self, field: str, project_id_str: str) -> bool:
        """
        Check if a field exists in metadata (avoids full scan)
        """
        try:
            sample = qdrant_client.scroll(
                collection_name=collection_name,
                scroll_filter=rest.Filter(
                    must=[rest.FieldCondition(key="project_id", match=rest.MatchValue(value=project_id_str))]
                ),
                limit=1,
                with_payload=True
            )
            
            if sample and sample[0]:
                return field in sample[0][0].payload
            
            return False
        except:
            return False

    async def _direct_row_lookup_optimized(
        self,
        query: str,
        project_id_str: str,
        selected_files: List[str]
    ) -> List[Dict[str, Any]]:
        """
        ✅ OPTIMIZED: Uses Qdrant filters (NO full-table scan)
        ✅ Dynamic location discovery from actual data
        ✅ Case-insensitive matching
        ✅ Flexible year detection (handles both "2008" and "2008.0")
        """
        year = self._extract_year_flexible(query)
        
        if not year:
            logger.info(f"   ⚠️ No year detected in query")
            return []
        
        must_conditions = [
            rest.FieldCondition(key="project_id", match=rest.MatchValue(value=project_id_str)),
            rest.FieldCondition(key="data_type", match=rest.MatchValue(value="excel_csv_row"))
        ]
        
        if selected_files:
            must_conditions.append(
                rest.FieldCondition(key="file_name", match=rest.MatchAny(any=selected_files))
            )
        
        year_in_metadata = await self._check_metadata_field_exists("year", project_id_str)
        
        if year_in_metadata:
            # ✅ Try both string and numeric year formats
            for year_format in [year, str(int(year)), f"{year}.0"]:
                must_conditions_with_year = must_conditions + [
                    rest.FieldCondition(key="year", match=rest.MatchValue(value=year_format))
                ]
                
                logger.info(f"   🚀 Trying metadata filter for year={year_format}")
                
                filtered_rows = qdrant_client.scroll(
                    collection_name=collection_name,
                    scroll_filter=rest.Filter(must=must_conditions_with_year),
                    limit=100,
                    with_payload=True
                )
                
                if filtered_rows and filtered_rows[0]:
                    logger.info(f"   📊 Found {len(filtered_rows[0])} rows for year={year_format}")
                    return await self._find_location_match(filtered_rows[0], query, year)
            
            logger.info(f"   ⚠️ No rows found for year {year} in any format")
            return []
        
        else:
            # ✅ FALLBACK: Parse text with flexible year pattern
            logger.info(f"   ⚠️ Year not in metadata, parsing text (limited scan)")
            
            all_rows = qdrant_client.scroll(
                collection_name=collection_name,
                scroll_filter=rest.Filter(must=must_conditions),
                limit=1000,
                with_payload=True
            )
            
            if not all_rows or not all_rows[0]:
                return []
            
            # ✅ FIX: Flexible year pattern (handles both "2008" and "2008.0")
            year_filtered = []
            year_pattern = rf'year:\s*{year}(?:\.0)?(?:\s|$|\n)'
            
            for point in all_rows[0]:
                text = point.payload.get("text", "")
                if re.search(year_pattern, text, re.IGNORECASE):
                    year_filtered.append(point)
            
            logger.info(f"   📊 Found {len(year_filtered)} rows matching year {year}")
            
            if not year_filtered:
                return []
            
            return await self._find_location_match(year_filtered, query, year)

    async def _find_location_match(
        self,
        points: List,
        query: str,
        year: str
    ) -> List[Dict[str, Any]]:
        """
        ✅ BULLETPROOF: Matches location with fuzzy logic
        """
        query_lower = query.lower()
        
        # Extract location from query explicitly
        location_from_query = None
        
        # Try to extract location name from query patterns
        location_patterns = [
            r'for\s+([a-z\s]+?)\s+in\s+\d{4}',  # "for Algeria in 2007"
            r'in\s+([a-z\s]+?)\s+in\s+\d{4}',   # "in Algeria in 2007"
            r'for\s+([a-z\s]+?)\s+\d{4}',       # "for Algeria 2007"
            r'\b([a-z]{4,})\s+\d{4}',           # "Algeria 2007"
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, query_lower)
            if match:
                location_from_query = match.group(1).strip()
                logger.info(f"   🎯 Extracted location from query: '{location_from_query}'")
                break
        
        # Extract keywords
        stopwords = {'what', 'is', 'the', 'for', 'in', 'of', 'and', 'or', 'a', 'an', 'to', 'from', 'with', 'by', 'as'}
        query_words = [
            w.lower() for w in re.findall(r'\b\w{3,}\b', query) 
            if w.lower() not in stopwords and not w.isdigit()
        ]
        
        logger.info(f"   🔍 Searching {len(points)} rows...")
        logger.info(f"   🎯 Query keywords: {query_words}")
        if location_from_query:
            logger.info(f"   🎯 Target location: '{location_from_query}'")
        
        scored_rows = []
        
        for idx, point in enumerate(points):
            text = point.payload.get("text", "")
            text_lower = text.lower()
            
            # Verify year
            year_pattern = rf'year:\s*{year}(?:\.0)?(?:\s|$|\n)'
            if not re.search(year_pattern, text, re.IGNORECASE):
                continue
            
            score = 0
            identifier_value = None
            identifier_field = None
            
            # ✅ STRATEGY 1: Check location field
            location_match = re.search(r'location:\s*([^\n]+)', text, re.IGNORECASE)
            if location_match:
                location_value = location_match.group(1).strip()
                location_lower = location_value.lower()
                
                # Method 1: Exact match with extracted location
                if location_from_query and location_from_query.lower() == location_lower:
                    score = 100
                    identifier_value = location_value
                    identifier_field = "location"
                    logger.info(f"      ✅ Row {idx}: EXACT location match '{location_value}' (+100)")
                
                # Method 2: Location appears in query
                elif location_lower in query_lower or any(location_lower in qw for qw in query_words):
                    score = 100
                    identifier_value = location_value
                    identifier_field = "location"
                    logger.info(f"      ✅ Row {idx}: Location '{location_value}' in query (+100)")
                
                # Method 3: Partial word match
                else:
                    location_words = [w.lower() for w in re.findall(r'\b\w{3,}\b', location_value)]
                    matches = sum(1 for qw in query_words if any(qw == lw or qw in lw or lw in qw for lw in location_words))
                    if matches > 0:
                        score = matches * 30
                        identifier_value = location_value
                        identifier_field = "location"
                        logger.info(f"      ⚠️ Row {idx}: {matches} partial matches in '{location_value}' (+{matches*30})")
                    else:
                        # No match - log for debugging
                        logger.info(f"      ❌ Row {idx}: NO MATCH for location '{location_value}' (query had '{location_from_query}')")
            
            # ✅ STRATEGY 2: Fallback to other fields
            if score == 0:
                for pattern in [r'country:\s*([^\n]+)', r'name:\s*([^\n]+)']:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        if value.lower() in query_lower or (location_from_query and value.lower() == location_from_query.lower()):
                            score = 80
                            identifier_value = value
                            identifier_field = pattern.split(':')[0]
                            logger.info(f"      ⚠️ Row {idx}: Fallback match on {identifier_field}='{value}' (+80)")
                            break
            
            # ✅ STRATEGY 3: General keywords
            if score == 0:
                keyword_matches = sum(1 for qw in query_words if qw in text_lower)
                if keyword_matches > 0:
                    score = keyword_matches * 5
                    # Extract any identifier
                    for pattern in [r'location:\s*([^\n]+)', r'country:\s*([^\n]+)', r'code:\s*([^\s\n]+)']:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            identifier_value = match.group(1).strip()
                            identifier_field = pattern.split(':')[0]
                            break
            
            # ✅ STRATEGY 4: Field code boost
            field_codes = re.findall(r'\b([a-z]+_[a-z_]+):', text_lower)
            query_codes = re.findall(r'\b([a-z]+_[a-z_]+)\b', query_lower)
            code_matches = sum(1 for qc in query_codes if qc in field_codes)
            if code_matches > 0:
                score += code_matches * 10
            
            if score > 0 and identifier_value:
                scored_rows.append({
                    'point': point,
                    'score': score,
                    'identifier': identifier_value,
                    'identifier_field': identifier_field,
                    'row_id': point.payload.get('excel_row_id', idx)
                })
        
        # Sort and return
        if scored_rows:
            scored_rows.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"   📊 Top 5 matches:")
            for i, row in enumerate(scored_rows[:5]):
                logger.info(f"      {i+1}. {row['identifier_field']}='{row['identifier']}' (score: {row['score']}, row: {row['row_id']})")
            
            best_match = scored_rows[0]
            
            # Only return if score is high enough
            if best_match['score'] >= 50:
                doc = self._build_standard_document(
                    best_match['point'],
                    best_match['identifier'],
                    year,
                    1.0
                )
                
                logger.info(f"   ✅ FINAL: {best_match['identifier_field']}='{best_match['identifier']}', year={year} (score: {best_match['score']})")
                return [doc]
            else:
                logger.warning(f"   ⚠️ Best match score too low: {best_match['score']} < 50")
        
        logger.warning(f"   ❌ No good matches found for '{location_from_query}' in year {year}")
        return []

    async def _semantic_search(
        self,
        query: str,
        project_id_str: str,
        selected_files: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Semantic search with codebook resolution
        """
        # Regex pre-pass before LLM
        cheap_filters = self._extract_filters_regex(query)
        
        # Only call LLM if regex didn't find obvious filters
        if not cheap_filters:
            logger.info(f"   🤖 Regex pre-pass found nothing, trying LLM...")
            cheap_filters = await self._extract_filters_with_llm(query, project_id_str)
        else:
            logger.info(f"   ⚡ Regex pre-pass extracted: {cheap_filters}")
        
        # Resolve columns from codebook
        resolved_columns = await self._resolve_columns_from_codebook(query, project_id_str)
        
        # Enhance query
        enhanced_query = query
        if resolved_columns:
            enhanced_query = f"{query} {' '.join(resolved_columns)}"
            logger.info(f"   🔍 Enhanced query with columns: {resolved_columns}")
        
        # Build filter
        must_conditions = [
            rest.FieldCondition(key="project_id", match=rest.MatchValue(value=project_id_str))
        ]
        
        must_not_conditions = [
            rest.FieldCondition(key="sheet_name", match=rest.MatchValue(value="Codebook"))
        ]
        
        if selected_files:
            must_conditions.append(
                rest.FieldCondition(key="file_name", match=rest.MatchAny(any=selected_files))
            )
        
        # Apply extracted filters
        for field_name, field_value in cheap_filters.items():
            if field_value:
                must_conditions.append(
                    rest.FieldCondition(key=field_name, match=rest.MatchValue(value=field_value))
                )
        
        search_filter = rest.Filter(must=must_conditions, must_not=must_not_conditions)
        
        # Multi-tier search
        query_vector = embedding.embed_query(enhanced_query)
        
        search_results = []
        for tier, threshold in [
            ("Primary", self.thresholds["primary"]),
            ("Secondary", self.thresholds["secondary"]),
            ("Fallback", self.thresholds["fallback"])
        ]:
            search_results = qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=20,
                score_threshold=threshold
            )
            
            logger.info(f"   - {tier} tier (threshold {threshold}): {len(search_results)} matches")
            
            if len(search_results) >= 3:
                break
        
        # Standardized output
        documents = []
        for i, hit in enumerate(search_results):
            doc = self._build_standard_document(
                hit,
                hit.payload.get("location"),
                hit.payload.get("year"),
                hit.score
            )
            documents.append(doc)
            logger.info(f"   - Result {i+1}: {doc['file_name']} (score: {doc['score']:.3f})")
        
        return documents

    def _extract_filters_regex(self, query: str) -> dict:
        """
        Cheap regex pre-pass (no LLM needed for obvious cases)
        """
        filters = {}
        
        # Extract year
        year = self._extract_year_flexible(query)
        if year:
            filters["year"] = year
        
        # Extract region codes (AFR, EUR, etc.)
        region_match = re.search(r'\b(AFR|AMR|EMR|EUR|SEAR|WPR)\b', query, re.IGNORECASE)
        if region_match:
            filters["region"] = region_match.group(1).upper()
        
        # Extract income levels
        income_patterns = {
            r'\blow[- ]income\b': "Low-income",
            r'\blower[- ]middle\b': "Lower-middle",
            r'\bupper[- ]middle\b': "Upper-middle",
            r'\bhigh[- ]income\b': "High-income"
        }
        
        for pattern, value in income_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                filters["income"] = value
                break
        
        return filters

    async def _resolve_columns_from_codebook(
        self,
        query: str,
        project_id_str: str
    ) -> List[str]:
        """
        Normalized codebook parsing
        Prioritizes exact shortcode matches
        """
        logger.info(f"📖 Checking codebook...")
        
        shortcodes = []
        
        try:
            # STEP 1: Check for shortcode patterns in query
            potential_codes = re.findall(r'\b([a-z]+_[a-z_]+)\b', query.lower())
            
            if potential_codes:
                logger.info(f"   🎯 Found potential shortcodes: {potential_codes}")
                
                codebook_filter = rest.Filter(
                    must=[
                        rest.FieldCondition(key="project_id", match=rest.MatchValue(value=project_id_str)),
                        rest.FieldCondition(key="sheet_name", match=rest.MatchValue(value="Codebook"))
                    ]
                )
                
                all_codebook = qdrant_client.scroll(
                    collection_name=collection_name,
                    scroll_filter=codebook_filter,
                    limit=500,
                    with_payload=True
                )
                
                if all_codebook and all_codebook[0]:
                    valid_codes = set()
                    for point in all_codebook[0]:
                        text = point.payload.get("text", "")
                        
                        # Flexible parsing
                        for line in text.split('\n'):
                            line_lower = line.lower().strip()
                            if line_lower.startswith('variable code'):
                                code_match = re.search(r'variable\s+code\s*[:=]\s*([^\s]+)', line_lower)
                                if code_match:
                                    code = code_match.group(1).strip()
                                    if code and code != '-':
                                        valid_codes.add(code)
                    
                    for code in potential_codes:
                        if code in valid_codes:
                            shortcodes.append(code)
                            logger.info(f"   ✅ Validated: {code}")
            
            # STEP 2: Semantic search fallback
            if not shortcodes:
                logger.info(f"   🔍 Trying semantic search...")
                
                codebook_filter = rest.Filter(
                    must=[
                        rest.FieldCondition(key="project_id", match=rest.MatchValue(value=project_id_str)),
                        rest.FieldCondition(key="sheet_name", match=rest.MatchValue(value="Codebook"))
                    ]
                )
                
                query_vector = embedding.embed_query(query)
                codebook_results = qdrant_client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    query_filter=codebook_filter,
                    limit=3,
                    score_threshold=self.thresholds["codebook"]
                )
                
                for hit in codebook_results:
                    text = hit.payload.get("text", "")
                    for line in text.split('\n'):
                        line_lower = line.lower().strip()
                        if line_lower.startswith('variable code'):
                            code_match = re.search(r'variable\s+code\s*[:=]\s*([^\s]+)', line_lower)
                            if code_match:
                                code = code_match.group(1).strip()
                                if code and code != '-' and code not in shortcodes:
                                    shortcodes.append(code)
                                    logger.info(f"   ✅ Semantic: {code} (score: {hit.score:.3f})")
                                break
            
            return shortcodes[:3]
            
        except Exception as e:
            logger.warning(f"   ⚠️ Codebook lookup failed: {e}")
            return []

    async def _extract_filters_with_llm(self, query: str, project_id: str) -> dict:
        """
        LLM-based filter extraction (only called if regex fails)
        """
        try:
            sample_doc = qdrant_client.scroll(
                collection_name=collection_name,
                scroll_filter=rest.Filter(
                    must=[rest.FieldCondition(key="project_id", match=rest.MatchValue(value=project_id))]
                ),
                limit=1,
                with_payload=True
            )
            
            if not sample_doc or not sample_doc[0]:
                return {}
            
            sample_payload = sample_doc[0][0].payload
            available_fields = {}
            
            metadata_keys = ["region", "country", "treatment_line", "regimen", 
                            "category", "department", "product", "location"]
            
            for key in metadata_keys:
                if key in sample_payload:
                    example_value = sample_payload.get(key, "")
                    if example_value and str(example_value).strip() and str(example_value) != "None":
                        available_fields[key] = example_value
            
            if not available_fields:
                return {}
            
            from core.config import settings
            from langchain_openai import ChatOpenAI
            from langchain_ollama import ChatOllama
            from langchain_core.messages import SystemMessage, HumanMessage
            import json
            
            if settings.LLM_PROVIDER.lower() == "openai":
                llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL,
                    api_key=settings.OPENAI_API_KEY,
                    temperature=0.0
                )
            else:
                llm = ChatOllama(
                    model=settings.LLM_MODEL,
                    base_url=settings.LLM_BASE_URL,
                    temperature=0.0
                )
            
            field_descriptions = "\n".join([
                f"- {field}: (example: '{value}')" 
                for field, value in list(available_fields.items())[:5]
            ])
            
            extraction_prompt = f"""Extract filter values from query. Return ONLY valid JSON.

Available fields:
{field_descriptions}

Query: "{query}"

Rules:
1. Only extract explicitly mentioned fields
2. Exact capitalization
3. Return {{}} if no filters

Your JSON:"""

            messages = [
                SystemMessage(content="Extract metadata filters. Output valid JSON only."),
                HumanMessage(content=extraction_prompt)
            ]
            
            response = await llm.ainvoke(messages)
            response_text = re.sub(r'```json\s*|\s*```', '', response.content.strip()).strip()
            
            filters = json.loads(response_text)
            
            valid_filters = {
                k: v for k, v in filters.items() 
                if k in available_fields.keys() and v and str(v).strip()
            }
            
            return valid_filters
            
        except Exception as e:
            logger.warning(f"   Filter extraction failed: {e}")
            return {}

    def _build_standard_document(
        self,
        point,
        location: Optional[str],
        year: Optional[str],
        score: float
    ) -> Dict[str, Any]:
        """
        Standardized document schema
        """
        payload = point.payload if hasattr(point, 'payload') else point
        text_content = payload.get("text", "")
        
        doc = {
            "text": text_content,
            "content": text_content,
            "file_name": payload.get("file_name", "Unknown"),
            "score": score,
            "data_type": payload.get("data_type", "excel_csv_row"),
            "metadata": {
                "project_id": payload.get("project_id"),
                "sheet_name": payload.get("sheet_name", "N/A"),
                "excel_row_id": payload.get("excel_row_id", "N/A"),
                "source": payload.get("source", "Unknown"),
                "location": location,
                "year": year,
                "chunk_index": payload.get("chunk_index"),
                "page": payload.get("page", "N/A"),
                "row_range": payload.get("row_range", "N/A"),
                "hierarchy_depth": payload.get("hierarchy_depth", "N/A")
            },
            "rows_data": payload.get("rows_data"),
            "column_names": payload.get("column_names"),
            "row_count": payload.get("row_count"),
            "column_count": payload.get("column_count", 0)
        }
        
        return doc

    def set_thresholds(self, **kwargs):
        """
        Configurable thresholds per project
        
        Usage:
        agent.set_thresholds(primary=0.4, secondary=0.25)
        """
        self.thresholds.update(kwargs)
        logger.info(f"   🎛️ Updated thresholds: {self.thresholds}")


# Export
retrieval_agent = RetrievalAgent()
