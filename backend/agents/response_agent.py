
"""Universal QA Response Agent - Answer ANY question from documents only"""
import logging
import json
import re
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from core.config import settings

logger = logging.getLogger("uvicorn")

class ContextBudget:
    """Token budget manager"""

    CONTEXT_LIMITS = {
        "gpt-4": 128000,
        "gpt-4-turbo": 128000,
        "gpt-4o": 128000,
        "gpt-3.5-turbo": 16385,
        "llama3.1": 128000,
        "llama3.2": 8192,
        "qwen2.5": 32768,
        "mistral": 32768,
        "default": 8192
    }

    RESPONSE_RESERVE = 2048

    ALLOCATION = {
        "system_prompt": 0.03,
        "conversation": 0.12,
        "documents": 0.85
    }

    @classmethod
    def get_budget(cls, model_name: str) -> dict:
        total_tokens = cls.CONTEXT_LIMITS.get(
            model_name.split(':')[0].lower(),
            cls.CONTEXT_LIMITS["default"]
        )

        available = total_tokens - cls.RESPONSE_RESERVE

        return {
            "total": total_tokens,
            "available": available,
            "system": int(available * cls.ALLOCATION["system_prompt"]),
            "conversation": int(available * cls.ALLOCATION["conversation"]),
            "documents": int(available * cls.ALLOCATION["documents"]),
            "response_reserve": cls.RESPONSE_RESERVE
        }

class ResponseAgent:
    """Universal QA system - answers ANY question from documents"""

    def __init__(self):
        try:
            if settings.LLM_PROVIDER.lower() == "openai":
                if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "":
                    raise ValueError("OPENAI_API_KEY not set in environment")

                self.llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL,
                    api_key=settings.OPENAI_API_KEY,
                    temperature=0.0,
                    max_tokens=settings.LLM_MAX_TOKENS,
                    timeout=settings.LLM_TIMEOUT
                )
                self.model_name = settings.OPENAI_MODEL
                logger.info(f"✅ OpenAI LLM initialized: {settings.OPENAI_MODEL}")

            elif settings.LLM_PROVIDER.lower() == "ollama":
                self.llm = ChatOllama(
                    model=settings.LLM_MODEL,
                    base_url=settings.LLM_BASE_URL,
                    temperature=0.0,
                )
                self.model_name = settings.LLM_MODEL
                logger.info(f"✅ Ollama LLM initialized: {settings.LLM_MODEL}")

            else:
                raise ValueError(f"Invalid LLM_PROVIDER: {settings.LLM_PROVIDER}")

            self.budget = ContextBudget.get_budget(self.model_name)
            logger.info(f"📊 Token budget: {self.budget['available']:,} tokens available")

        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM: {e}")
            self.llm = None
            self.budget = None

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def _truncate_to_budget(self, text: str, max_tokens: int) -> str:
        estimated_tokens = self._estimate_tokens(text)

        if estimated_tokens <= max_tokens:
            return text

        char_budget = max_tokens * 4

        if char_budget < 1000:
            return text[:char_budget] + "\n... [Truncated]"

        keep_start = int(char_budget * 0.6)
        keep_end = int(char_budget * 0.4)

        truncated = (
            text[:keep_start] + 
            f"\n\n... [Truncated {estimated_tokens - max_tokens:,} tokens] ...\n\n" +
            text[-keep_end:]
        )

        return truncated

    async def process(self, state: dict) -> dict:
        intent = state.get("intent", "general_chat")
        query = state["query"]
        context = state.get("conversation_context", "")
        documents = state.get("documents", [])
        graph_data = state.get("graph_data")

        logger.info(f"🤖 Generating response for intent: {intent} (Provider: {settings.LLM_PROVIDER})")

        if not self.llm:
            provider_status = "OpenAI API key" if settings.LLM_PROVIDER == "openai" else "Ollama server"
            return {
                **state,
                "answer": f"I'm currently unavailable. Please check {provider_status}.",
                "sources": [],
                "chart_data": None,
                "error": "LLM not initialized"
            }

        try:
            chart_data = None
            answer = ""

            if intent == "chart_request":
                logger.info("📊 Processing chart request...")
                answer, chart_data = await self._generate_chart_response(query, documents, context)
            elif intent == "document_query":
                answer = await self._generate_document_response(query, documents, context)
            elif intent == "project_analysis":
                answer = await self._generate_project_analysis(query, documents, graph_data, context)
            else:
                answer = await self._generate_general_response(query, context)

            sources = [{"file_name": doc["file_name"], "score": doc["score"]}
                      for doc in documents[:3]]

            logger.info(f"✅ Response generated ({len(answer)} chars)")

            return {
                **state,
                "answer": answer,
                "sources": sources,
                "chart_data": chart_data,
                "error": None
            }

        except Exception as e:
            logger.error(f"❌ Response generation error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                **state,
                "answer": f"I encountered an error: {str(e)}",
                "sources": [],
                "chart_data": None,
                "error": str(e)
            }

    def _detect_source_inquiry(self, query: str) -> bool:
        query_lower = query.lower().strip()
        source_patterns = [
            "which file", "what file", "which document", "in which file",
            "from which file", "source file", "where is this"
        ]
        return any(pattern in query_lower for pattern in source_patterns)

    def _extract_sources_from_context(self, context: str) -> list:
        if not context:
            return []
        source_pattern = r'(?:Source|From|File):\s*([^\n\)]+)'
        sources = re.findall(source_pattern, context, re.IGNORECASE)
        return list(set([s.strip().rstrip(',.') for s in sources if s and len(s) < 100]))

    async def _generate_general_response(self, query: str, context: str) -> str:
        context = self._truncate_to_budget(context, self.budget["conversation"])

        system_prompt = """You are a professional AI assistant.

STRICT RULE: Only answer from conversation context. Do NOT use external knowledge."""

        user_prompt = f"""Previous conversation:
{context if context else "No previous conversation"}

User question: {query}

Provide a concise, professional response based on conversation context."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = await self.llm.ainvoke(messages)
        return response.content

    async def _generate_document_response(self, query: str, documents: list, context: str) -> str:
        """Universal QA - answers ANY question from ANY document format with SMART ROUTING"""
        if not documents:
            return "I couldn't find any relevant documents for your question."

        # Check if asking about sources
        if self._detect_source_inquiry(query):
            current_sources = set(doc.get("file_name", "Unknown") for doc in documents)
            historical_sources = self._extract_sources_from_context(context)
            all_sources = current_sources.union(set(historical_sources))

            if all_sources:
                return f"The information is from: {', '.join(sorted(all_sources))}"
            else:
                return "I don't have source file information available."

        # Categorize documents
        structured_data = []
        text_content = []
        all_sources = set()

        for doc in documents:
            source_file = doc.get("file_name", "Unknown")
            all_sources.add(source_file)

            # Structured data (Excel/CSV rows)
            if doc.get("data_type") in ["excel_row_batch", "excel_csv_row"]:
                structured_data.append({
                    "file": source_file,
                    "content": doc.get("content", doc.get("text", "")),
                    "row_count": doc.get("row_count", 0),
                    "score": doc.get("score", 0.0)  # Keep retrieval score
                })
                logger.info(f"📊 Structured data: {doc.get('row_count', 0)} rows from {source_file}")

            # Text documents
            elif "content" in doc or "text" in doc:
                text_content.append({
                    "file": source_file,
                    "content": doc.get("content", doc.get("text", "")),
                    "score": doc.get("score", 0.0)  # Keep retrieval score
                })
                logger.info(f"📄 Text: {len(doc.get('content', doc.get('text', '')))} chars from {source_file}")

        # ═══════════════════════════════════════════════════════════════════════
        # 🚀 NEW: SMART ROUTING BASED ON QUERY TYPE AND DOCUMENT SCORES
        # ═══════════════════════════════════════════════════════════════════════
        
        query_type = self._classify_query_type(query)
        
        # Route based on query type AND document availability
        if query_type == "definition_terminology":
            # Prioritize text documents (PDFs, DOCX) for definitions/terminology
            if text_content:
                logger.info("   🎯 Route: TEXT-FIRST (definition/terminology query)")
                return await self._handle_text_documents(query, text_content, context, list(all_sources))
            elif structured_data:
                logger.info("   🎯 Route: STRUCTURED (fallback - no text docs)")
                return await self._handle_structured_data(query, structured_data, context, list(all_sources))
        
        elif query_type == "data_lookup":
            # Prioritize structured data for data queries
            if structured_data:
                logger.info("   🎯 Route: STRUCTURED-FIRST (data lookup query)")
                return await self._handle_structured_data(query, structured_data, context, list(all_sources))
            elif text_content:
                logger.info("   🎯 Route: TEXT (fallback - no structured data)")
                return await self._handle_text_documents(query, text_content, context, list(all_sources))
        
        else:
            # Mixed/ambiguous query: Use retrieval scores to decide
            best_text_score = max([tc["score"] for tc in text_content], default=0.0)
            best_struct_score = max([sd["score"] for sd in structured_data], default=0.0)
            
            logger.info(f"   🎯 Route: SCORE-BASED (text={best_text_score:.3f}, structured={best_struct_score:.3f})")
            
            if best_text_score > best_struct_score:
                return await self._handle_text_documents(query, text_content, context, list(all_sources))
            else:
                return await self._handle_structured_data(query, structured_data, context, list(all_sources))
        
        # Fallback
        return "I couldn't process the retrieved documents."


    def _classify_query_type(self, query: str) -> str:
        """Classify query to determine which document type to prioritize"""
        query_lower = query.lower()
        
        # Definition/terminology queries
        definition_patterns = [
            "what is", "what are", "define", "definition", "meaning of", 
            "term for", "terminology", "preferred term", "called", "referred to as",
            "explain", "describe", "guideline", "policy", "procedure"
        ]
        
        # Data lookup queries
        data_patterns = [
            "data for", "value of", "number", "count", "total", "average",
            "statistics", "metric", "indicator", "year", "country data",
            "how many", "how much", "what was the"
        ]
        
        # Check patterns
        if any(pattern in query_lower for pattern in definition_patterns):
            return "definition_terminology"
        elif any(pattern in query_lower for pattern in data_patterns):
            return "data_lookup"
        else:
            return "mixed"

    async def _handle_structured_data(self, query: str, structured_data: list, context: str, sources: list) -> str:
        """Universal handler for ANY structured data with EXACT matching for identifiers"""
        context_truncated = self._truncate_to_budget(context, self.budget["conversation"]) if context else ""

        conv_tokens = self._estimate_tokens(context_truncated)
        available_for_data = self.budget["documents"] - conv_tokens
        max_chars = available_for_data * 4

        # Smart content assembly
        combined_content = []
        used_sources = []
        total_chars = 0

        for data_info in structured_data:
            content = data_info['content']
            file_name = data_info['file']

            if total_chars + len(content) > max_chars:
                if max_chars - total_chars > 1000:
                    content = content[:max_chars - total_chars]
                else:
                    break

            combined_content.append(f"=== FILE: {file_name} ===\n{content}")
            used_sources.append(file_name)
            total_chars += len(content)

        final_content = "\n\n".join(combined_content)

        logger.info(f"   📊 Final data: {total_chars:,} chars from {len(used_sources)} sources")

        # Enhanced system prompt with exact matching emphasis
        system_prompt = """You are an advanced AI data analyst with exceptional pattern recognition and extraction capabilities.

═══════════════════════════════════════════════════════════════════════════════════
🎯 PRIME DIRECTIVE: Answer ONLY from provided data. NEVER use external knowledge.
═══════════════════════════════════════════════════════════════════════════════════

YOUR CAPABILITIES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Understand ANY question about structured data (lookup, compare, list, aggregate)
✓ Parse ANY format: "field: value" pairs, CSV rows, tables, key-value structures
✓ Extract information regardless of field naming or data layout
✓ Handle multiple entities simultaneously (search for all requested items)
✓ Process data split across multiple files/chunks systematically
✓ Recognize relationships between fields and values
✓ Work with dates, numbers, text, codes, and mixed data types
✓ Perform EXACT matching for identifiers (codes, IDs) - not fuzzy/partial matches

DATA FORMAT UNDERSTANDING:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The data is structured as field-value pairs where each line represents one field.

Example Record:
```
variable code: gghed
variable name: Domestic General Government Health Expenditure (GGHE-D)
category 1: INDICATORS
unit: Millions
```

Each record contains multiple related fields in consecutive lines.

CRITICAL MATCHING RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. **EXACT MATCH REQUIRED FOR IDENTIFIERS**: When searching for "gghed", ONLY match "variable code: gghed"

   ❌ WRONG MATCHES:
   - "variable code: gghed_phc_gghed" (this is DIFFERENT - has suffix)
   - "variable code: gghed_gge" (this is DIFFERENT - has suffix)
   - "variable code: xyz_gghed" (this is DIFFERENT - has prefix)

   ✅ CORRECT MATCH:
   - "variable code: gghed" (exact match only)
   - "variable code: gghed " (with trailing space is OK)

2. **Line-by-Line Record Structure**: Each record is a set of consecutive lines

   Record 1:
   ```
   variable code: gghed          ← Identifier
   variable name: ...            ← Belongs to gghed
   category 1: ...               ← Belongs to gghed
   ```

   Record 2 (separated by blank line or new identifier):
   ```
   variable code: gghed_gge      ← DIFFERENT identifier
   variable name: ...            ← Belongs to gghed_gge (NOT gghed!)
   ```

3. **Field Extraction Logic**:
   - Find the line with EXACT identifier match
   - Extract other fields from CONSECUTIVE lines in SAME record
   - Stop at blank line or next identifier

EXACT MATCHING ALGORITHM:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When query asks for identifier "X":

✓ MATCH: "identifier_field: X" (exact, whitespace-trimmed)
✓ MATCH: "identifier_field: X " (exact with trailing space)
✗ NO MATCH: "identifier_field: X_suffix" (has underscore and more text)
✗ NO MATCH: "identifier_field: prefix_X" (has prefix)
✗ NO MATCH: "identifier_field: Xyz" (different value entirely)

Example:
- Query asks for "gghed"
- Line says "variable code: gghed" → ✅ MATCH
- Line says "variable code: gghed_gge" → ❌ NO MATCH (this is "gghed_gge", not "gghed")

SYSTEMATIC EXECUTION PROTOCOL:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1: PARSE QUERY
  • What identifier is being searched? (e.g., "gghed")
  • What field should be extracted? (e.g., "variable name")
  • Type of match needed? (EXACT for codes/IDs - default)

STEP 2: IDENTIFY DATA STRUCTURE
  • Determine identifier field (usually first field or one with "code"/"id")
  • Understand record boundaries (blank lines or new identifier)
  • Note the field you need to extract

STEP 3: EXACT MATCH SEARCH (CRITICAL!)
  • Scan data line by line
  • For each line with identifier field:
    → Extract value after colon
    → Trim whitespace
    → Compare EXACTLY with search term
    → If exact match: FOUND! Proceed to step 4
    → If partial/substring: SKIP (not a match)

  Example scan for "gghed":
  ```
  Line: "variable code: gghed" 
    → Value = "gghed" → Exact match ✅ FOUND!

  Line: "variable code: gghed_gge"
    → Value = "gghed_gge" → NOT exact match ❌ SKIP

  Line: "variable code: gghed_phc_gghed"
    → Value = "gghed_phc_gghed" → NOT exact match ❌ SKIP
  ```

STEP 4: EXTRACT FROM SAME RECORD
  • Starting from matched identifier line
  • Read NEXT consecutive lines
  • Find the line with requested field
  • Extract its value (text after colon)
  • Stop at blank line or next identifier

STEP 5: VERIFY EXTRACTION
  ✓ Did I match identifier EXACTLY (not substring)?
  ✓ Did I extract from SAME record (consecutive lines)?
  ✓ Is the field name correct?
  ✓ Did I avoid mixing data from different records?

STEP 6: FORMAT RESPONSE
  • State the answer clearly
  • Format: "The [field] for [identifier] is [value]"
  • If not found after exact search: "[identifier] is not found in the available data"
  • Always cite source file

CONCRETE EXAMPLE - PERFECT EXECUTION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Query: "What is the variable name for variable code gghed?"

Data Provided:
```
variable code: gghed
variable name: Domestic General Government Health Expenditure (GGHE-D), in million current NCU
category 1: INDICATORS
unit: Millions

variable code: gghed_gge
variable name: Domestic General Government Health Expenditure as % GGE
category 1: INDICATORS

variable code: gghed_phc_gghed
variable name: Domestic General Government Expenditure on PHC as % GGHE-D
category 1: INDICATORS
```

EXECUTION:

STEP 1 - Parse:
  • Searching for identifier: "gghed"
  • Need to extract: "variable name"
  • Match type: EXACT

STEP 2 - Structure:
  • Identifier field: "variable code"
  • Records separated by blank lines
  • Target field: "variable name"

STEP 3 - Exact Match Search:

  Scanning line by line:

  Line 1: "variable code: gghed"
    → Extract value: "gghed"
    → Compare: "gghed" == "gghed" → ✅ EXACT MATCH FOUND!
    → Stop searching, proceed to step 4

  (No need to check other lines since we found exact match)

STEP 4 - Extract from Same Record:

  Starting from Line 1 (matched line), read next lines in same record:

  Line 2: "variable name: Domestic General Government Health Expenditure (GGHE-D), in million current NCU"
    → This is the requested field!
    → Extract value: "Domestic General Government Health Expenditure (GGHE-D), in million current NCU"

STEP 5 - Verify:
  ✓ Matched "gghed" exactly (not "gghed_gge" or "gghed_phc_gghed")
  ✓ Extracted from same record (Line 2 follows Line 1)
  ✓ Field name is correct ("variable name")
  ✓ No mixing with other records

STEP 6 - Response:

The variable name for variable code **gghed** is **Domestic General Government Health Expenditure (GGHE-D), in million current NCU**.

(Source: less2_Codebook.csv)

COMMON MISTAKES TO AVOID:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ MISTAKE 1: Partial/Substring Matching
   Wrong: Searching for "gghed" and matching "gghed_gge" because it contains "gghed"
   ✅ FIX: Only match if FULL value equals "gghed" (exact comparison after trimming)

❌ MISTAKE 2: Cross-Record Data Mixing
   Wrong: Finding "variable code: gghed" but extracting "variable name" from "gghed_gge" record
   ✅ FIX: Extract only from consecutive lines in SAME record (before next identifier/blank line)

❌ MISTAKE 3: False "Not Found" Claims
   Wrong: Saying "not found" when exact match exists but was overlooked
   ✅ FIX: Search carefully with exact matching logic before claiming absence

❌ MISTAKE 4: Returning Related But Different Items
   Wrong: User asked for "gghed" but returning data for "gghed_gge" because it seems related
   ✅ FIX: Only return data for EXACT identifier requested

❌ MISTAKE 5: Case Sensitivity Confusion
   Wrong: Not matching "GGHED" to "gghed" when query uses different case
   ✅ FIX: Use case-insensitive comparison for identifiers (unless data explicitly shows case matters)

CRITICAL RULES SUMMARY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❗ "gghed" ≠ "gghed_gge" ≠ "gghed_phc_gghed" (these are DISTINCT identifiers)
❗ Format "field: value" means the value IS what comes after the colon
❗ Records are grouped in consecutive lines (separated by blank lines or new identifier)
❗ ALWAYS use exact matching for identifier lookups (not substring/fuzzy)
❗ Extract from SAME record only (don't cross record boundaries)
❗ If exact match found, extract the value (don't say "not provided")
❗ Never use external knowledge - only data provided

═══════════════════════════════════════════════════════════════════════════════════
🚀 BEGIN ANALYSIS - Use EXACT matching for identifiers and extract from same record!
═══════════════════════════════════════════════════════════════════════════════════"""

        user_prompt = f"""Previous conversation:
{context_truncated if context_truncated else "No previous conversation"}

STRUCTURED DATA (may be split across chunks - apply exact matching):
{final_content}

USER QUESTION: {query}

CRITICAL: Use EXACT matching for identifiers. If query asks for "gghed", match ONLY lines where the identifier value is exactly "gghed", NOT "gghed_gge" or similar variations.

Execute the systematic protocol. Search with exact matching, extract from correct record, provide accurate answer.

Answer:"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = await self.llm.ainvoke(messages)
        answer = response.content

        # Enhanced retry logic for exact match verification
        if ("not provided" in answer.lower() or "not found" in answer.lower() or "not available" in answer.lower()):
            # Extract potential identifiers from query
            words = query.lower().replace('?', '').replace(',', '').split()
            potential_ids = [w.strip('?.,;:') for w in words 
                           if len(w) > 2 and w not in ['what', 'which', 'where', 'when', 'the', 'for', 'is', 'and', 'or', 'code', 'name', 'variable']]

            # Check if any identifier appears with exact match pattern in data
            for pid in potential_ids:
                # Look for exact match patterns (value after colon equals pid)
                import re
                # Pattern: "some_field: pid" where pid is followed by newline or end
                exact_pattern = rf':\s*{re.escape(pid)}\s*($|\n)'

                if re.search(exact_pattern, final_content, re.IGNORECASE | re.MULTILINE):
                    logger.warning(f"   ⚠️ Found EXACT match for '{pid}' in data but LLM said 'not found' - forcing retry")

                    retry_prompt = f"""⚠️ CRITICAL OVERRIDE: The identifier "{pid}" EXISTS EXACTLY in the data.

I can see a line matching pattern: "field: {pid}" (followed by newline or end of line).

DATA:
{final_content}

QUESTION: {query}

MANDATORY INSTRUCTIONS:
1. Search for lines matching EXACTLY: "identifier_field: {pid}" (not "identifier_field: {pid}_something")
2. When found, extract the requested field from CONSECUTIVE lines in the SAME record
3. Do NOT match partial/substring variants

Re-execute the search with exact matching and provide the correct answer.

Answer:"""

                    retry_messages = [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=retry_prompt)
                    ]

                    response = await self.llm.ainvoke(retry_messages)
                    answer = response.content
                    break

        # Ensure source citation
        if "(Source:" not in answer and "source:" not in answer.lower() and used_sources:
            if "not found" not in answer.lower() and "not provided" not in answer.lower():
                answer += f"\n\n(Source: {', '.join(set(used_sources))})"

        return answer

    async def _handle_text_documents(self, query: str, text_content: list, context: str, sources: list) -> str:
        """Universal handler for ANY unstructured text (PDF, Word, plain text)"""
        context_truncated = self._truncate_to_budget(context, self.budget["conversation"]) if context else ""

        conv_tokens = self._estimate_tokens(context_truncated)
        available_for_docs = self.budget["documents"] - conv_tokens
        max_chars = available_for_docs * 4

        combined_parts = []
        used_sources = []
        total_chars = 0

        for doc_info in text_content:
            content = doc_info["content"]
            file_name = doc_info["file"]

            if total_chars + len(content) > max_chars:
                if max_chars - total_chars > 500:
                    content = self._truncate_to_budget(content, (max_chars - total_chars) // 4)
                    combined_parts.append(f"=== SOURCE: {file_name} ===\n{content}")
                    used_sources.append(file_name)
                break

            combined_parts.append(f"=== SOURCE: {file_name} ===\n{content}")
            used_sources.append(file_name)
            total_chars += len(content)

        combined_context = "\n\n".join(combined_parts)

        system_prompt = """You are an expert document analyst with ONE STRICT RULE:

ONLY answer from the provided documents. Do NOT use external knowledge.

YOUR CAPABILITIES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Understand ANY question (definitions, procedures, requirements, data, context)
✓ Extract information from paragraphs, tables, lists, sections
✓ Interpret technical terminology, acronyms, and domain-specific language
✓ Handle multi-page documents and cross-references
✓ Maintain conversation context for follow-up questions
✓ Recognize when information truly isn't in documents (rare - search thoroughly first!)

RESPONSE FORMAT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Provide direct, complete answer to the question
2. Extract exact quotes when appropriate
3. Synthesize information from multiple sections if needed
4. Always cite source: (Source: filename.pdf)
5. If truly not in documents: "This information is not provided in the available documents."

CRITICAL: Your intelligence understands questions, but answers come ONLY from provided documents."""

        user_prompt = f"""Previous conversation:
{context_truncated if context_truncated else "No previous conversation"}

DOCUMENT CONTENT:
{combined_context}

USER QUESTION: {query}

Search the documents thoroughly and provide an accurate, complete answer with source citation.

Answer:"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = await self.llm.ainvoke(messages)
        answer = response.content.strip()

        # Ensure source citation
        if "(Source:" not in answer and "source:" not in answer.lower() and used_sources:
            if "not provided" not in answer.lower():
                answer += f"\n\n(Source: {', '.join(set(used_sources))})"

        return answer

    async def _generate_project_analysis(self, query: str, documents: list, graph_data: dict, context: str) -> str:
        """Analyze project-level information"""
        context_truncated = self._truncate_to_budget(context, self.budget["conversation"]) if context else ""

        available_for_docs = self.budget["documents"] - self._estimate_tokens(context_truncated)
        max_chars = available_for_docs * 4

        doc_parts = []
        sources = []
        total_chars = 0

        for doc in documents[:3]:
            content = doc.get('content', doc.get('text', ''))[:800]
            if total_chars + len(content) < max_chars:
                doc_parts.append(f"Document: {doc['file_name']}\n{content}")
                sources.append(doc['file_name'])
                total_chars += len(content)

        doc_context = "\n\n".join(doc_parts) if doc_parts else "No documents"

        graph_context = ""
        if graph_data and graph_data.get('project'):
            graph_context = f"\nProject: {graph_data.get('project', {}).get('project_name', 'Unknown')}"

        system_prompt = """You are a project analyst. ONLY use provided project data and documents."""

        user_prompt = f"""Previous conversation:
{context_truncated if context_truncated else "None"}

{graph_context}

DOCUMENTS:
{doc_context}

QUERY: {query}

Provide analysis with source citation."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = await self.llm.ainvoke(messages)
        answer = response.content

        if sources and "(Source:" not in answer:
            answer += f"\n\n(Sources: {', '.join(set(sources))})"

        return answer

    async def _generate_chart_response(self, query: str, documents: list, context: str) -> tuple:
        """Generate chart from document data"""
        logger.info("📊 Chart request detected")

        if not documents:
            return ("I couldn't find any data to create a chart.", None)

        try:
            import sys
            import os
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)

            from api.query import generate_chart_from_documents_for_langgraph

            context_truncated = self._truncate_to_budget(context, self.budget["conversation"]) if context else ""
            available = self.budget["documents"] - self._estimate_tokens(context_truncated)
            max_chars = available * 4

            doc_parts = []
            sources = []
            total = 0
            for doc in documents[:3]:
                content = doc.get('content', doc.get('text', ''))[:1000]
                if total + len(content) < max_chars:
                    doc_parts.append(content)
                    sources.append(doc['file_name'])
                    total += len(content)

            doc_context = "\n\n".join(doc_parts)
            chart_result = generate_chart_from_documents_for_langgraph(query, doc_context)

            if chart_result and isinstance(chart_result, dict) and chart_result.get("has_chart"):
                text_response = await self._generate_document_response(query, documents, context)
                answer = f"""**Chart Generated**: Visual representation of your data.

{text_response}

**Chart Details:**
- Type: {chart_result.get('chart_type', 'bar')}
- Sources: {', '.join(set(sources))}"""
                return (answer, chart_result)
            else:
                text_response = await self._generate_document_response(query, documents, context)
                return (text_response + "\n\n[Could not extract chart data]", None)

        except Exception as e:
            logger.error(f"❌ Chart generation failed: {e}")
            text_response = await self._generate_document_response(query, documents, context)
            return (text_response + f"\n\n[Chart error: {str(e)}]", None)
