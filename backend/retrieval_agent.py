"""Retrieval agent - Universal hybrid search with intelligent query understanding"""
import logging
import re
from typing import List, Tuple, Dict, Any
from core.config import qdrant_client, embedding, collection_name, graph_manager
from qdrant_client.http import models as rest

logger = logging.getLogger("uvicorn")

class RetrievalAgent:
    """
    Production-grade retrieval system:
    - Universal keyword extraction (case-insensitive, any question format)
    - Multi-tier search with index page filtering
    - Smart definition detection
    - Context-aware chunk merging
    """
    
    STOP_WORDS = {
        'what', 'is', 'the', 'to', 'be', 'used', 'for', 'a', 'an', 'of', 'in', 'on',
        'at', 'how', 'when', 'where', 'why', 'which', 'are', 'was', 'were', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
        'could', 'may', 'might', 'must', 'can', 'that', 'this', 'these', 'those'
    }
    
    QUESTION_PATTERNS = [
        r"what (?:is|are) (?:the )?(?:preferred )?(?:term|terminology|definition|meaning) (?:for|of|to be used for) (.+?)[\?\.]*$",
        r"(?:define|explain|describe) (.+?)[\?\.]*$",
        r"what (?:is|does) (.+?) (?:mean|refer to)[\?\.]*$",
        r"tell me about (.+?)[\?\.]*$",
        r"(?:give|provide) (?:the )?(?:definition|meaning) (?:of|for) (.+?)[\?\.]*$",
    ]
    
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
        
        if requires_documents and project_id:
            try:
                keywords = self._extract_keywords(query)
                logger.info(f"   🔑 Keywords: {keywords}")
                logger.info(f"   🎯 Primary term: '{keywords[0]}'")
                
                documents = await self._multi_strategy_search(
                    query=query,
                    keywords=keywords,
                    project_id=project_id,
                    selected_files=selected_files
                )
                
                documents = self._merge_adjacent_chunks(documents)
                logger.info(f"✅ Retrieved {len(documents)} documents")
                
            except Exception as e:
                logger.error(f"❌ Retrieval error: {e}")
                import traceback
                logger.error(traceback.format_exc())
                state["error"] = f"Retrieval failed: {str(e)}"
        
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
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        Universal keyword extraction - CASE INSENSITIVE
        Works for any question format
        """
        # Convert to lowercase IMMEDIATELY (critical fix)
        query_lower = query.lower().strip()
        
        # Pattern matching
        for pattern in self.QUESTION_PATTERNS:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                extracted_term = match.group(1).strip()
                extracted_term = extracted_term.replace("?", "").replace(".", "").strip()
                logger.info(f"   📍 Pattern matched: '{extracted_term}'")
                context_keywords = ["preferred term", "terminology", "definition", "do not use"]
                return [extracted_term] + context_keywords
        
        # Fallback: stop word removal
        query_clean = re.sub(r'[^\w\s\-]', ' ', query_lower)
        words = query_clean.split()
        meaningful_words = [w for w in words if w not in self.STOP_WORDS and len(w) > 2]
        
        # Extract phrases
        phrases = []
        for i in range(len(words) - 1):
            if words[i] not in self.STOP_WORDS and words[i+1] not in self.STOP_WORDS:
                bigram = f"{words[i]} {words[i+1]}"
                if len(bigram) > 6:
                    phrases.append(bigram)
        
        all_keywords = phrases[:2] + meaningful_words
        
        # Deduplicate
        seen = set()
        unique_keywords = []
        for kw in all_keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:5] if unique_keywords else [query_lower]
    
    async def _multi_strategy_search(
        self,
        query: str,
        keywords: List[str],
        project_id: int,
        selected_files: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Three-tier search strategy with automatic fallback
        """
        project_id_str = str(project_id)
        must_conditions = [
            rest.FieldCondition(
                key="project_id",
                match=rest.MatchValue(value=project_id_str)
            )
        ]
        
        if selected_files and len(selected_files) > 0:
            logger.info(f"   - File filter: {selected_files}")
            must_conditions.append(
                rest.FieldCondition(
                    key="file_name",
                    match=rest.MatchAny(any=selected_files)
                )
            )
        
        search_filter = rest.Filter(must=must_conditions)
        search_query = " ".join(keywords[:3])
        query_vector = embedding.embed_query(search_query)
        
        # TIER 1: Semantic search
        logger.info(f"   🔍 TIER 1: Semantic search")
        search_results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=30,
            score_threshold=0.3
        )
        
        logger.info(f"   - Found {len(search_results)} semantic matches")
        
        if search_results:
            boosted_results = self._apply_keyword_boosting(search_results, keywords)
            
            # Check quality
            if boosted_results and boosted_results[0][1] > 1.5:
                logger.info(f"   ✅ TIER 1 SUCCESS (score: {boosted_results[0][1]:.2f})")
                return self._build_documents(boosted_results[:10])
        
        # TIER 2: Text-based search
        logger.info(f"   🔍 TIER 2: Text search for '{keywords[0]}'")
        try:
            text_search_results = qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=rest.Filter(
                    must=must_conditions + [
                        rest.FieldCondition(
                            key="text",
                            match=rest.MatchText(text=keywords[0])
                        )
                    ]
                ),
                limit=15
            )
            
            if text_search_results:
                logger.info(f"   ✅ TIER 2 SUCCESS ({len(text_search_results)} matches)")
                boosted = self._apply_keyword_boosting(text_search_results, keywords)
                return self._build_documents(boosted[:10])
                
        except Exception as e:
            logger.warning(f"   ⚠️ TIER 2 failed: {e}")
        
        # TIER 3: Fallback
        logger.info(f"   🔍 TIER 3: Fallback to best results")
        if search_results:
            boosted_results = self._apply_keyword_boosting(search_results, keywords)
            return self._build_documents(boosted_results[:10])
        
        logger.warning(f"   ⚠️ No results found")
        return []
    
    def _apply_keyword_boosting(
        self,
        search_results: List,
        keywords: List[str]
    ) -> List[Tuple[Any, float]]:
        """
        Boost scores with index page filtering
        """
        boosted_results = []
        
        for hit in search_results:
            content = hit.payload.get("text", "")
            content_lower = content.lower()
            score = hit.score
            
            # Check each keyword
            for idx, keyword in enumerate(keywords):
                keyword_lower = keyword.lower()
                
                if keyword_lower not in content_lower:
                    continue
                
                weight = 1.0 if idx == 0 else 0.3
                
                # Definition format check
                if self._is_definition_format(content_lower, keyword_lower):
                    score += (2.0 * weight)  # Increased from 1.5
                    logger.info(f"   ⭐ DEFINITION: '{keyword}' → +{2.0 * weight:.1f}")
                    break
                
                # Start match
                elif content_lower.startswith(keyword_lower):
                    score += (1.0 * weight)
                    logger.info(f"   ⭐ START: '{keyword}' → +{1.0 * weight:.1f}")
                    break
                
                # Exact match
                elif self._contains_exact_match(content_lower, keyword_lower):
                    score += (0.5 * weight)
                    logger.info(f"   ⭐ EXACT: '{keyword}' → +{0.5 * weight:.1f}")
                    break
                
                # Partial match
                else:
                    score += (0.1 * weight)
            
            boosted_results.append((hit, score))
        
        boosted_results.sort(key=lambda x: x[1], reverse=True)
        return boosted_results
    
    def _is_definition_format(self, content: str, term: str) -> bool:
        """
        Production-grade definition detection with index page filtering
        Works for any terminology document structure
        """
        content_lower = content.lower()
        content_start = content_lower[:500]
        
        # ❌ FILTER OUT: Index/TOC pages
        lines = [l.strip() for l in content_lower.split('\n') if l.strip()]
        
        if len(lines) > 15:
            short_term_lines = 0
            for line in lines[:20]:
                if len(line) < 60 and line.count(' ') < 5:
                    if not any(indicator in line for indicator in ['is', 'are', 'refers', 'describes', 'means', ':', '—', 'preferred']):
                        short_term_lines += 1
            
            if short_term_lines > 10:
                return False
        
        # ✅ DEFINITION FORMAT 1: "Do not use: term"
        if f"do not use: {term}" in content_start or f"do not use {term}" in content_start:
            return True
        
        if f"do not use\npreferred term" in content_start and term in content_start[:300]:
            return True
        
        # ✅ DEFINITION FORMAT 2: "term\nPreferred term:"
        term_pos = content_start.find(term)
        if term_pos != -1 and term_pos < 100:
            following_text = content_start[term_pos:term_pos+200]
            if "preferred term" in following_text or "preferred:" in following_text:
                return True
        
        # ✅ DEFINITION FORMAT 3: "term: definition"
        if f"{term}:" in content_start or f"{term} —" in content_start or f"{term} -" in content_start:
            term_pos = content_start.find(term)
            if term_pos != -1:
                after_term = content_start[term_pos:term_pos+150]
                if any(word in after_term for word in ['is', 'are', 'refers', 'should', 'use', 'describes']):
                    return True
        
        # ✅ DEFINITION FORMAT 4: Term at start with explanation
        first_line = lines[0] if lines else ""
        if first_line.startswith(term) or first_line == term:
            if len(lines) > 1:
                next_lines = ' '.join(lines[1:3]).lower()
                if any(word in next_lines for word in ['preferred', 'use', 'refers', 'describes', 'is', 'are', 'means']):
                    return True
        
        # ✅ DEFINITION FORMAT 5: Proximity check
        if term in content_start and "preferred term" in content_start:
            term_pos = content_start.find(term)
            pref_pos = content_start.find("preferred term")
            if abs(term_pos - pref_pos) < 200:
                return True
        
        return False
    
    def _contains_exact_match(self, content: str, term: str) -> bool:
        """Check if content contains exact term with word boundaries"""
        if term not in content:
            return False
        
        pattern = r'(?:^|\s|\n)' + re.escape(term) + r'(?:\s|\n|[.,;:!?]|$)'
        return bool(re.search(pattern, content, re.IGNORECASE))
    
    def _build_documents(self, scored_results: List[Tuple[Any, float]]) -> List[Dict[str, Any]]:
        """Convert Qdrant hits to document format"""
        documents = []
        
        for i, (hit, boosted_score) in enumerate(scored_results):
            logger.info(f"   - Result {i+1}: {hit.payload.get('file_name')} (score: {boosted_score:.2f})")
            
            doc = {
                "content": hit.payload.get("text", ""),
                "file_name": hit.payload.get("file_name", "Unknown"),
                "score": boosted_score,
                "data_type": hit.payload.get("data_type", "text_document"),
                "metadata": {
                    "project_id": hit.payload.get("project_id"),
                    "chunk_index": hit.payload.get("chunk_index"),
                    "page": hit.payload.get("page", "N/A")
                }
            }
            
            # Excel data
            if "rows_data" in hit.payload:
                doc["rows_data"] = hit.payload["rows_data"]
            if "column_names" in hit.payload:
                doc["column_names"] = hit.payload["column_names"]
            if "row_count" in hit.payload:
                doc["row_count"] = hit.payload["row_count"]
                doc["column_count"] = hit.payload.get("column_count", 0)
            
            documents.append(doc)
        
        return documents
    
    def _merge_adjacent_chunks(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge chunks from same file for complete context"""
        if not documents:
            return documents
        
        file_groups = {}
        for doc in documents:
            file_name = doc["file_name"]
            if file_name not in file_groups:
                file_groups[file_name] = []
            file_groups[file_name].append(doc)
        
        merged = []
        for file_name, file_docs in file_groups.items():
            if len(file_docs) == 1:
                merged.extend(file_docs)
            else:
                file_docs.sort(key=lambda x: x["score"], reverse=True)
                top_docs = file_docs[:3]
                
                merged_content = "\n\n".join([d["content"] for d in top_docs])
                
                merged_doc = {
                    "content": merged_content,
                    "file_name": file_name,
                    "score": max(d["score"] for d in top_docs),
                    "data_type": top_docs[0]["data_type"],
                    "metadata": top_docs[0]["metadata"]
                }
                
                if top_docs[0].get("rows_data"):
                    all_rows = []
                    for d in top_docs:
                        if d.get("rows_data"):
                            all_rows.extend(d["rows_data"])
                    merged_doc["rows_data"] = all_rows
                
                if top_docs[0].get("column_names"):
                    merged_doc["column_names"] = top_docs[0]["column_names"]
                
                if top_docs[0].get("row_count"):
                    merged_doc["row_count"] = sum(d.get("row_count", 0) for d in top_docs)
                    merged_doc["column_count"] = top_docs[0].get("column_count", 0)
                
                merged.append(merged_doc)
                logger.info(f"   📎 Merged {len(top_docs)} chunks from {file_name}")
        
        return merged
