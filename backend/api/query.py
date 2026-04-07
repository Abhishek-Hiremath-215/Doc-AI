import os
import io
import re
import uuid
import json
import base64
import logging
from typing import List, Optional, Tuple

import matplotlib
from pydantic import BaseModel
matplotlib.use("Agg")  # ✅ headless backend for servers
import matplotlib.pyplot as plt

from fastapi import APIRouter, Depends, HTTPException

from core.config import graph_manager, qdrant_client, embedding, collection_name
from langchain_ollama import OllamaLLM
from langchain_qdrant import Qdrant
from qdrant_client import models as rest
from dependencies import get_current_active_user
from models import User
from langchain_community.vectorstores import Qdrant as QdrantVectorStore

router = APIRouter()
logger = logging.getLogger("uvicorn")

# ===============================
# Schemas
# ===============================
class AskQuery(BaseModel):
    query: str
    selected_files: List[str]
    project_id: int
    top_k: Optional[int] = 5

class QueryRequest(BaseModel):
    query: str
    project_id: int
    selected_files: List[str] = []
    top_k: int = 5

# ===============================
# Chart Helpers
# ===============================
GENERATED_CHARTS_DIR = "generated_charts"
os.makedirs(GENERATED_CHARTS_DIR, exist_ok=True)  # ✅ auto-create once

def _try_parse_json_block(text: str):
    """Best-effort JSON extraction from raw LLM text (handles code fences + mixed text)."""
    logger.info(f"🔍 Attempting to parse JSON from text: {text[:200]}...")
    
    # 1) direct parse
    try:
        result = json.loads(text)
        logger.info(f"✅ Direct JSON parse successful")
        return result
    except Exception:
        logger.info(f"⚠️ Direct JSON parse failed, trying alternatives")

    # 2) code fence `````` or ``````
    patterns = [
        r"``````",
        r"``````",
        r"`(.*?)`"
    ]
    
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            try:
                result = json.loads(candidate)
                logger.info(f"✅ Code fence JSON parse successful")
                return result
            except Exception:
                continue

    # 3) scan first balanced JSON object
    def first_json_object(s: str) -> Optional[str]:
        depth = 0
        start = None
        for i, ch in enumerate(s):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start is not None:
                        return s[start : i + 1]
        return None

    block = first_json_object(text)
    if block:
        try:
            result = json.loads(block)
            logger.info(f"✅ Balanced object JSON parse successful")
            return result
        except Exception:
            logger.warning(f"⚠️ Balanced object parse failed")

    logger.warning(f"⚠️ All JSON parsing attempts failed")
    return None

def _validate_xy(x, y):
    if not isinstance(x, list) or not isinstance(y, list):
        raise HTTPException(status_code=400, detail="Chart x and y must be lists.")
    if len(x) != len(y):
        raise HTTPException(status_code=400, detail="Chart x and y must have the same length.")

def generate_chart(chart_data: dict) -> Tuple[str, str]:
    """Generate a chart from JSON-like dict, save to generated_charts/, and return (base64_str, file_url)."""
    logger.info(f"🎨 Generating chart with data: {chart_data}")
    
    filename = f"chart_{uuid.uuid4().hex}.png"
    filepath = os.path.join(GENERATED_CHARTS_DIR, filename)

    chart_type = (chart_data.get("type") or "bar").lower()
    title = chart_data.get("title", "Chart from Document Data")
    xlabel = chart_data.get("xlabel", "Categories")
    ylabel = chart_data.get("ylabel", "Values")

    # Create figure with better styling
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Set style
    plt.style.use('default')

    if chart_type == "pie":
        labels = chart_data.get("labels", [])
        values = chart_data.get("values", [])
        if not labels or not values or len(labels) != len(values):
            raise HTTPException(status_code=400, detail="Pie charts require equal-length 'labels' and 'values'.")
        
        # Create pie chart with better colors
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3', '#54A0FF', '#5F27CD']
        wedges, texts, autotexts = ax.pie(values, labels=labels, autopct="%1.1f%%", 
                                         colors=colors[:len(values)], startangle=90)
        
        # Improve text styling
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            
    else:
        x = chart_data.get("x", [])
        y = chart_data.get("y", [])
        _validate_xy(x, y)

        if chart_type == "bar":
            bars = ax.bar(x, y, color='#4ECDC4', alpha=0.8, edgecolor='#2C3E50', linewidth=1)
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}', ha='center', va='bottom', fontweight='bold')
                       
        elif chart_type == "line":
            ax.plot(x, y, marker="o", linewidth=3, markersize=8, color='#FF6B6B', 
                   markerfacecolor='#FF6B6B', markeredgecolor='white', markeredgewidth=2)
            ax.grid(True, alpha=0.3)
            
        elif chart_type == "scatter":
            ax.scatter(x, y, alpha=0.7, s=100, color='#45B7D1', edgecolors='#2C3E50')
            ax.grid(True, alpha=0.3)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported chart type: {chart_type}")

        ax.set_xlabel(xlabel, fontsize=12, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
        
        # Rotate x-axis labels if they're too long
        if any(len(str(label)) > 8 for label in x):
            plt.xticks(rotation=45, ha='right')

    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    
    # Improve overall appearance
    fig.patch.set_facecolor('white')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()

    # Save PNG to disk
    fig.savefig(filepath, format="png", bbox_inches="tight", dpi=150, facecolor='white')

    # Also return base64 for inline preview
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150, facecolor='white')
    buf.seek(0)
    base64_str = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()

    plt.close(fig)
    
    logger.info(f"✅ Chart saved to: {filepath}")
    return base64_str, f"/chat/charts/{filename}"


def create_fallback_chart(document_content: str, query: str) -> Optional[dict]:
    """Create a simple chart from document content when LLM parsing fails"""
    try:
        logger.info(f"🔄 Creating fallback chart from document content")
        
        # Extract numbers from document
        numbers = re.findall(r'\b\d+\.?\d*\b', document_content)
        if len(numbers) >= 2:
            # Take first 5-10 numbers and create a simple bar chart
            values = []
            for n in numbers[:min(8, len(numbers))]:
                try:
                    values.append(float(n))
                except:
                    continue
            
            if len(values) >= 2:
                labels = [f"Data {i+1}" for i in range(len(values))]
                
                return {
                    "type": "bar",
                    "title": "Numerical Data from Document",
                    "xlabel": "Data Points",
                    "ylabel": "Values",
                    "x": labels,
                    "y": values
                }
    except Exception as e:
        logger.warning(f"⚠️ Fallback chart creation failed: {e}")
    
    return None

# ===============================
# ✅ IMPROVED PROCESS FUNCTIONS
# ===============================
def process_question_with_context(
    query: str,
    project_id: int,
    selected_files: list = None,
    top_k: int = 5,
    current_user: User = None,
    context: str = ""
):
    """Shared function for processing questions with optional conversation context"""
    logger.info(f"🔍 Starting process_question_with_context for user: {current_user.email if current_user else 'System'}, project_id: {project_id}")
    logger.info(f"🔍 Selected files: {selected_files}")
    logger.info(f"🔍 Context length: {len(context)} chars")
    
    try:
        # Check for chart request early
        chart_keywords = [
            'chart', 'graph', 'plot', 'visualize', 'visualization', 'show data', 
            'create chart', 'draw', 'bar chart', 'pie chart', 'line chart',
            'scatter plot', 'show me a graph', 'make a chart', 'generate chart',
            'display data', 'visual representation'
        ]
        wants_chart = any(keyword in query.lower() for keyword in chart_keywords)
        logger.info(f"🔍 Chart requested: {wants_chart}")

        # Debug the graph manager lookup
        project_node = graph_manager.get_project_by_id(project_id)
        logger.info(f"🔍 Project lookup result: {project_node}")
        
        if not project_node:
            logger.warning(f"⚠️ graph_manager.get_project_by_id({project_id}) returned None")
            
            try:
                with graph_manager.driver.session() as session:
                    direct_result = session.run(
                        "MATCH (p:Project {project_id: $id}) RETURN p.project_id, p.project_name, p",
                        id=project_id
                    ).single()
                    
                    if direct_result:
                        logger.info(f"✅ Direct Neo4j query found project: {direct_result['p.project_name']}")
                        project_node = dict(direct_result["p"])
                    else:
                        direct_result = session.run(
                            "MATCH (p:Project {project_id: $id}) RETURN p.project_id, p.project_name, p",
                            id=str(project_id)
                        ).single()
                        
                        if direct_result:
                            logger.info(f"✅ Direct Neo4j query with string found project: {direct_result['p.project_name']}")
                            project_node = dict(direct_result["p"])
                        else:
                            logger.error(f"❌ Direct Neo4j queries failed for project_id: {project_id}")
                            
            except Exception as neo4j_error:
                logger.error(f"❌ Neo4j direct query error: {neo4j_error}")
        
        if not project_node:
            logger.error(f"❌ Project with ID {project_id} not found after all attempts")
            raise HTTPException(status_code=404, detail=f"Project with ID {project_id} not found.")
        
        project_name = project_node.get("project_name", "Unknown Project")
        logger.info(f"✅ Project found: {project_name}")

        # Initialize Qdrant
        logger.info(f"🔍 Starting Qdrant retrieval...")
        qdrant = QdrantVectorStore(client=qdrant_client, collection_name=collection_name, embeddings=embedding)
        
        # Create filters
        def create_balanced_filter():
            filter_conditions = []
            
            try:
                filter_conditions.append(rest.FieldCondition(
                    key="metadata.project_id",
                    match=rest.MatchValue(value=project_id)
                ))
                logger.info(f"🔍 Added project filter: metadata.project_id = {project_id}")
            except:
                try:
                    filter_conditions.append(rest.FieldCondition(
                        key="project_id",
                        match=rest.MatchValue(value=project_id)
                    ))
                    logger.info(f"🔍 Added project filter: project_id = {project_id}")
                except:
                    logger.warning(f"⚠️ Could not add project filter")
            
            if selected_files and len(selected_files) > 0:
                try:
                    filter_conditions.append(rest.FieldCondition(
                        key="metadata.source",
                        match=rest.MatchAny(any=selected_files)
                    ))
                    logger.info(f"🔍 Added file filter: metadata.source in {selected_files}")
                except:
                    try:
                        filter_conditions.append(rest.FieldCondition(
                            key="source",
                            match=rest.MatchAny(any=selected_files)
                        ))
                        logger.info(f"🔍 Added file filter: source in {selected_files}")
                    except:
                        logger.warning(f"⚠️ Could not add file filter")
            
            return filter_conditions

        filter_conditions = create_balanced_filter()
        
        qdrant_filter = None
        if filter_conditions:
            try:
                qdrant_filter = rest.Filter(must=filter_conditions)
                logger.info(f"🔍 Created filter with {len(filter_conditions)} conditions")
            except Exception as filter_error:
                logger.warning(f"⚠️ Filter creation failed: {filter_error}, proceeding without filter")
                qdrant_filter = None

        # Enhanced query with context
        enhanced_query = query
        if context:
            enhanced_query = f"""
            Previous conversation context:
            {context}
            
            Current question: {query}
            
            Based on our conversation history and the documents, please answer the current question.
            """
            logger.info(f"🔍 Enhanced query with context (length: {len(context)} chars)")

        # Document search with fallback strategies
        docs = []
        search_strategies = [
            {"k": top_k, "filter": qdrant_filter, "score_threshold": 0.1},
            {"k": top_k, "filter": qdrant_filter, "score_threshold": 0.05},
            {"k": top_k * 2, "filter": qdrant_filter, "score_threshold": 0.05},
            {"k": top_k, "filter": None, "score_threshold": 0.1},
        ]
        
        for i, search_kwargs in enumerate(search_strategies):
            try:
                logger.info(f"🔍 Trying search strategy {i+1}: {search_kwargs}")
                retriever = qdrant.as_retriever(search_kwargs=search_kwargs)
                docs = retriever.invoke(enhanced_query)
                logger.info(f"🔍 Strategy {i+1} retrieved {len(docs)} documents")
                
                if docs:
                    break
                    
            except Exception as search_error:
                logger.warning(f"⚠️ Search strategy {i+1} failed: {search_error}")
                continue

        # Document validation
        if docs:
            logger.info(f"📄 Raw documents retrieved: {len(docs)}")
            
            validated_docs = []
            for doc in docs:
                doc_file = (doc.metadata.get('source') or 
                           doc.metadata.get('filename') or 
                           doc.metadata.get('file_name') or 'Unknown File')
                
                doc_project_id = str(doc.metadata.get('project_id', ''))
                
                if selected_files and len(selected_files) > 0:
                    if doc_file in selected_files:
                        validated_docs.append(doc)
                        logger.info(f"   ✅ SELECTED: {doc_file}")
                    else:
                        if doc_project_id == str(project_id):
                            validated_docs.append(doc)
                            logger.info(f"   ⚠️ INCLUDED (same project): {doc_file}")
                else:
                    if doc_project_id == str(project_id):
                        validated_docs.append(doc)
                        logger.info(f"   ✅ INCLUDED: {doc_file}")
            
            if len(validated_docs) == 0 and len(docs) > 0:
                logger.warning(f"⚠️ Strict validation removed all docs, using first {min(3, len(docs))} original docs")
                validated_docs = docs[:3]
            
            docs = validated_docs
            logger.info(f"🔍 After validation: {len(docs)} documents")

        if not docs:
            logger.warning("⚠️ No documents found with any search strategy")
            
            if selected_files and len(selected_files) > 0:
                error_msg = f"❌ No relevant content found in the selected files: {', '.join(selected_files)} from project '{project_name}'. Try selecting different files or check if the files contain information about your query."
            else:
                error_msg = f"❌ No relevant content found in project '{project_name}'. Please check if files have been uploaded and processed."
                
            return {
                "answer": error_msg,
                "sources": [],
                "chartBase64": None,
                "chartUrl": None,
                "context_used": bool(context),
                "enhanced_query": None,
                "has_chart": False,
                "chart_data": None,
                "chart_type": None
            }

        # ✅ CRITICAL FIX: Extract document content properly
        logger.info(f"📄 Preparing content from {len(docs)} documents")
        
        document_content = ""
        sources_info = []
        
        for i, doc in enumerate(docs[:5]):
            file_name = (doc.metadata.get('source') or 
                        doc.metadata.get('filename') or 
                        doc.metadata.get('file_name') or f'Document_{i+1}')
            
            content_text = doc.page_content.strip()
            
            logger.info(f"📄 Document {i+1}: {file_name}")
            logger.info(f"📄 Content length: {len(content_text)} chars")
            logger.info(f"📄 Content preview: {content_text[:200]}...")
            
            if content_text:
                document_content += f"\n\n=== CONTENT FROM {file_name} ===\n{content_text}\n"
                
                sources_info.append({
                    "filename": file_name,
                    "project_name": project_name,
                    "content_preview": content_text[:200] + "..." if len(content_text) > 200 else content_text
                })
            else:
                logger.warning(f"⚠️ No content found in document: {file_name}")

        if not document_content.strip():
            logger.error(f"❌ No document content extracted from {len(docs)} documents")
            return {
                "answer": f"❌ I found {len(docs)} documents but couldn't extract readable content. This could be due to:\n\n1. Documents are empty or corrupted\n2. Text extraction failed\n3. Documents are image-based PDFs without OCR\n\nPlease check if your documents contain readable text.",
                "sources": [],
                "chartBase64": None,
                "chartUrl": None,
                "context_used": bool(context),
                "enhanced_query": None,
                "has_chart": False,
                "chart_data": None,
                "chart_type": None
            }

        logger.info(f"✅ Final document content length: {len(document_content)} chars")

        sources_text = "\n".join(
            f"📄 **{doc.metadata.get('source') or doc.metadata.get('filename') or doc.metadata.get('file_name') or 'Unknown File'}** in 🗂️ **{doc.metadata.get('project_name', 'Unknown Project')}**"
            for doc in docs
        )

        # ✅ IMPROVED LLM PROCESSING WITH BETTER CHART HANDLING
        logger.info(f"🤖 Generating response with LLM...")
        logger.info(f"🤖 Document content length: {len(document_content)} chars")
        
        try:
            llm = OllamaLLM(model="llama3")
            
            if wants_chart:
                # ✅ IMPROVED CHART PROMPT
                prompt = f"""You are an AI assistant that analyzes documents and creates charts. Answer the user's question and provide chart data if possible.

{f"CONVERSATION CONTEXT: {context}" if context else ""}

DOCUMENT CONTENT:
{document_content}

USER QUERY: {query}

INSTRUCTIONS:
1. First, provide a comprehensive text answer based on the document content
2. If numerical data is available and a chart was requested, extract data for visualization
3. Respond in this EXACT JSON format:

{{
  "answer": "Your detailed text answer here based on document content",
  "chart": {{
    "type": "bar",
    "title": "Chart Title",
    "xlabel": "X-axis Label", 
    "ylabel": "Y-axis Label",
    "x": ["Category1", "Category2", "Category3"],
    "y": [10, 20, 30]
  }}
}}

For pie charts, use this format:
{{
  "answer": "Your answer",
  "chart": {{
    "type": "pie",
    "title": "Chart Title",
    "labels": ["Label1", "Label2"],
    "values": [60, 40]
  }}
}}

IMPORTANT:
- Only include chart data if you find actual numerical data in the documents
- If no suitable data for charts, omit the "chart" field entirely
- Make sure x and y arrays have the same length for bar/line charts
- Use meaningful labels and titles
- Extract real data from the document content

RESPONSE:"""
            else:
                # Regular prompt for non-chart requests
                prompt = f"""You are an AI assistant analyzing documents. Answer the user's question based ONLY on the provided document content.

{f"CONVERSATION CONTEXT: {context}" if context else ""}

DOCUMENT CONTENT:
{document_content}

CURRENT USER QUERY: {query}

INSTRUCTIONS:
- Answer based ONLY on the document content above
- Be specific and detailed
- Quote relevant parts from the documents
- If the information is not in the documents, say so clearly
- Do NOT provide generic responses

ANSWER:"""

            logger.info(f"🤖 LLM Prompt length: {len(prompt)} chars")
            
            llm_output = llm.invoke(prompt)
            logger.info(f"✅ LLM response received (length: {len(str(llm_output))})")
            logger.info(f"✅ LLM response preview: {str(llm_output)[:500]}...")
            
        except Exception as llm_error:
            logger.error(f"❌ Ollama LLM error: {llm_error}")
            llm_output = f"Based on the document content from {project_name}, I found relevant information but couldn't process it with the AI model. Error: {str(llm_error)}\n\nDocument sources: {[doc.metadata.get('source', 'Unknown') for doc in docs[:3]]}"

        answer_text = str(llm_output)
        chart_base64, chart_url = None, None
        chart_data = None

        # ✅ IMPROVED CHART PARSING
        if wants_chart:
            logger.info(f"🎨 Parsing LLM output for chart data...")
            try:
                parsed = _try_parse_json_block(str(llm_output))
                logger.info(f"🔍 Parsed result: {parsed}")
                
                if isinstance(parsed, dict):
                    answer_text = parsed.get("answer", answer_text)
                    chart_data = parsed.get("chart")
                    
                    if isinstance(chart_data, dict):
                        logger.info(f"🔍 Chart data found: {chart_data}")
                        
                        # Validate chart data
                        chart_type = chart_data.get("type", "bar").lower()
                        
                        if chart_type == "pie":
                            has_pie_data = bool(chart_data.get("labels")) and bool(chart_data.get("values"))
                            if has_pie_data and len(chart_data["labels"]) == len(chart_data["values"]):
                                logger.info(f"✅ Valid pie chart data found")
                                chart_base64, chart_url = generate_chart(chart_data)
                                logger.info(f"✅ Pie chart generated: {chart_url}")
                            else:
                                logger.warning(f"⚠️ Invalid pie chart data")
                                chart_data = None
                        else:
                            has_xy_data = bool(chart_data.get("x")) and bool(chart_data.get("y"))
                            if has_xy_data and len(chart_data["x"]) == len(chart_data["y"]):
                                logger.info(f"✅ Valid XY chart data found")
                                chart_base64, chart_url = generate_chart(chart_data)
                                logger.info(f"✅ {chart_type} chart generated: {chart_url}")
                            else:
                                logger.warning(f"⚠️ Invalid XY chart data")
                                chart_data = None
                    else:
                        logger.info(f"🔍 No chart data in parsed response")
                        
            except Exception as chart_error:
                logger.warning(f"⚠️ Chart parsing/generation failed: {chart_error}")
                # ✅ FALLBACK: Try to create a simple chart from document content
                try:
                    fallback_chart = create_fallback_chart(document_content, query)
                    if fallback_chart:
                        chart_base64, chart_url = generate_chart(fallback_chart)
                        chart_data = fallback_chart
                        logger.info(f"✅ Fallback chart generated: {chart_url}")
                except Exception as fallback_error:
                    logger.warning(f"⚠️ Fallback chart generation failed: {fallback_error}")

        # Format final answer
        final_answer = answer_text
        if chart_url:
            final_answer += f"\n\n📊 **Chart Generated**: Visual representation of the data has been created."
        
        final_answer += f"\n\n---\n**Retrieved from:**\n{sources_text}"

        # ✅ RETURN COMPLETE RESPONSE
        final_response = {
            "answer": final_answer,
            "sources": sources_info,
            "chartBase64": chart_base64,
            "chartUrl": chart_url,
            "enhanced_query": enhanced_query if context else None,
            "context_used": bool(context),
            "has_chart": bool(chart_base64),
            "chart_data": chart_data,
            "chart_type": chart_data.get("type") if chart_data else None
        }
        
        logger.info(f"✅ Successfully completed process_question_with_context")
        logger.info(f"✅ Chart generated: {bool(chart_base64)}")
        return final_response

    except HTTPException as http_error:
        logger.error(f"❌ HTTP Exception in process_question_with_context: {http_error.status_code} - {http_error.detail}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in process_question_with_context: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def process_general_question(query, context=None, current_user=None):
    """✅ IMPROVED: Process a general question without project context"""
    try:
        logger.info(f"🔍 Processing general question: {query}")
        logger.info(f"🔍 Context provided: {bool(context)}")
        
        # Enhanced general response with better AI integration
        if context:
            enhanced_query = f"""
            Previous conversation context:
            {context}
            
            Current question: {query}
            
            Please provide a helpful response considering the conversation history.
            """
        else:
            enhanced_query = query
        
        # ✅ IMPROVED: Try to use LLM for better general responses
        try:
            llm = OllamaLLM(model="llama3")
            
            general_prompt = f"""You are a helpful AI assistant. The user is asking a general question outside of document analysis.

{f"CONVERSATION CONTEXT: {context}" if context else ""}

USER QUESTION: {query}

Please provide a helpful, informative response. Since this is a general question (not document analysis), you can use your general knowledge to help the user.

If the user is asking about document analysis features, let them know they should select a project from the sidebar to analyze their documents.

RESPONSE:"""
            
            logger.info(f"🤖 Generating general response with LLM...")
            llm_response = llm.invoke(general_prompt)
            
            response = {
                "answer": str(llm_response),
                "sources": [],
                "context_used": bool(context),
                "enhanced_query": enhanced_query if context else None,
                "chartBase64": None,
                "chartUrl": None,
                "has_chart": False,
                "chart_data": None,
                "chart_type": None
            }
            
            logger.info(f"✅ General response generated successfully")
            return response
            
        except Exception as llm_error:
            logger.warning(f"⚠️ LLM failed for general question, using fallback: {llm_error}")
            # Fallback to simple response
            response = {
                "answer": f"I understand you're asking: {query}\n\nI'm your AI assistant. For document analysis with context memory, please select a project from the sidebar to access your files. For general questions, I can help with information, explanations, and assistance on a wide range of topics.\n\nHow can I help you further?",
                "sources": [],
                "context_used": bool(context),
                "enhanced_query": enhanced_query if context else None,
                "chartBase64": None,
                "chartUrl": None,
                "has_chart": False,
                "chart_data": None,
                "chart_type": None
            }
            
            return response
        
    except Exception as e:
        logger.error(f"❌ Error in process_general_question: {e}")
        # Return fallback response
        return {
            "answer": "I'm here to help! For document analysis, please select a project from the sidebar. For general questions, feel free to ask me anything.",
            "sources": [],
            "context_used": False,
            "enhanced_query": None,
            "chartBase64": None,
            "chartUrl": None,
            "has_chart": False,
            "chart_data": None,
            "chart_type": None
        }

# ===============================
# /enhance query
# ===============================
# class EnhanceQuery(BaseModel):
#     query: str

# @router.post("/enhance")
# def enhance_query(request: EnhanceQuery, current_user: User = Depends(get_current_active_user)):
#     """Transform a simple user query into a full, context-rich question for better retrieval."""
#     logger.info(f"🔧 Enhancing query: '{request.query}'")
    
#     try:
#         llm = OllamaLLM(model="llama3")
        
#         enhancement_prompt = f"""You are an expert assistant specializing in transforming user queries into full, clear, and context-rich questions optimized for document retrieval. Do not output extra text, just the rewritten question.

# Examples:
# User query: what is the name of person?
# Transformed query: What is the full name of the person mentioned in the document? Include any middle names, initials, or nicknames.

# User query: list skills
# Transformed query: What are the professional skills and competencies described in the document?

# User query: education
# Transformed query: What is the educational background of the person as stated in the document?

# User query: contact info
# Transformed query: What contact information such as email or phone number is available for the individual?

# User query: work experience
# Transformed query: What is the complete work history and professional experience of the person described in the document?

# User query: {request.query}
# Transformed query:"""

#         enhanced_query = llm.invoke(enhancement_prompt)
        
#         # Clean up the response
#         enhanced_query = enhanced_query.strip()
#         enhanced_query = enhanced_query.replace("Transformed query:", "").strip()
#         enhanced_query = enhanced_query.replace('"', '').strip()
        
#         # Remove any leading/trailing punctuation if needed
#         if enhanced_query.startswith(":"):
#             enhanced_query = enhanced_query[1:].strip()
        
#         # Fallback to original query if enhancement fails
#         if not enhanced_query or len(enhanced_query) < 5:
#             enhanced_query = request.query
#             logger.warning(f"⚠️ Using original query as fallback")
        
#         logger.info(f"✅ Query enhanced: '{enhanced_query}'")
        
#         return {
#             "original_query": request.query,
#             "enhanced_query": enhanced_query
#         }
        
#     except Exception as e:
#         logger.error(f"❌ Query enhancement failed: {e}")
#         raise HTTPException(status_code=500, detail="Failed to enhance query")


class EnhanceQuery(BaseModel):
    query: str

@router.post("/enhance")
def enhance_query(request: EnhanceQuery, current_user: User = Depends(get_current_active_user)):
    """Transform a simple user query into a clear, context-rich question for better document retrieval across all document types."""
    logger.info(f"🔧 Enhancing query: '{request.query}'")

    try:
        llm = OllamaLLM(model="llama3.1:8b-instruct-q4_K_M")

        enhancement_prompt = f"""
You are an expert AI assistant that rewrites short user queries into full, clear, and context-rich questions optimized for document retrieval.
The rewritten version should be more detailed and explicit about what information should be extracted from any kind of document (e.g., legal, technical, medical, academic, business, resume, invoice, or report).
Do not include explanations or extra text — only output the transformed query.

Examples:

User query: total revenue
Transformed query: What is the total revenue or income mentioned in the document, including any financial figures or reported earnings?

User query: key findings
Transformed query: What are the main results, conclusions, or key findings described in the document?

User query: author
Transformed query: Who is the author or creator of the document? Include any contributors or organizations responsible.

User query: payment terms
Transformed query: What payment terms or financial conditions are specified in the document?

User query: summary
Transformed query: Provide a concise summary of the main points, purpose, and context of the document.

User query: references
Transformed query: What references, sources, or citations are included or mentioned in the document?

User query: {request.query}
Transformed query:
"""

        enhanced_query = llm.invoke(enhancement_prompt)

        # Clean response
        enhanced_query = enhanced_query.strip()
        enhanced_query = enhanced_query.replace("Transformed query:", "").strip()
        enhanced_query = enhanced_query.replace('"', '').strip()

        if enhanced_query.startswith(":"):
            enhanced_query = enhanced_query[1:].strip()

        if not enhanced_query or len(enhanced_query) < 5:
            enhanced_query = request.query
            logger.warning("⚠️ Enhancement failed, using original query as fallback")

        logger.info(f"✅ Query enhanced: '{enhanced_query}'")

        return {
            "original_query": request.query,
            "enhanced_query": enhanced_query
        }

    except Exception as e:
        logger.error(f"❌ Query enhancement failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to enhance query")


# ===============================
# /search_files Endpoint
# ===============================
@router.post("/search_files")
async def search_files(query: QueryRequest, current_user: User = Depends(get_current_active_user)):
    project_node = graph_manager.get_project_by_id(query.project_id)
    if not project_node:
        return {"matched_files": [], "message": f"⚠️ Project with ID {query.project_id} not found."}
    
    matched_files = set()
    lowered_query = query.query.lower().strip()
    project_name = project_node["project_name"]
    
    # KG-based organization matching
    if "who" in lowered_query and ("worked at" in lowered_query or "worked in" in lowered_query):
        match = re.search(r'worked (?:at|in) (.+?)(?:\?|$)', lowered_query)
        if match:
            org = match.group(1).strip()
            try:
                with graph_manager.driver.session() as session:
                    result = session.run("""
                        MATCH (p:Person)-[:WORKED_AT]->(o:Organization)
                        WHERE toLower(o.name) CONTAINS toLower($org)
                        MATCH (p)-[:ASSOCIATED_WITH]->(proj:Project {project_id: $project_id})
                        MATCH (f:File)-[:BELONGS_TO]->(proj)
                        RETURN DISTINCT f.file_name AS file_name
                    """, org=org, project_id=query.project_id)
                    files = [r["file_name"] for r in result if r["file_name"]]
                    matched_files.update(files)
            except Exception as e:
                logger.error(f"[KG Retrieval Error] {e}")

    # Fallback: Qdrant semantic search
    if not matched_files:
        try:
            qdrant = Qdrant(client=qdrant_client, collection_name=collection_name, embeddings=embedding)
            qdrant_filter = rest.Filter(must=[rest.FieldCondition(
                key="metadata.project_id", match=rest.MatchValue(value=query.project_id)
            )])
            docs = qdrant.similarity_search(query.query, k=query.top_k, filter=qdrant_filter)
            for doc in docs:
                source = doc.metadata.get("source")
                if source:
                    matched_files.add(source)
        except Exception as e:
            logger.error(f"[Qdrant Retrieval Error] {e}")
    
    return {
        "matched_files": list(matched_files),
        "message": "Matched files retrieved successfully." if matched_files else "No files matched for your query."
    }


# 🔥 ADD THIS SINGLE FUNCTION TO YOUR EXISTING query.py:

def generate_chart_from_documents_for_langgraph(query: str, doc_context: str) -> dict:
    """Generate chart from document context - Called by LangGraph"""
    logger.info("📊 [LangGraph] Generating chart...")
    
    try:
        llm = OllamaLLM(model="llama3")
        
        # 🔥 IMPROVED PROMPT with strict validation
        prompt = f"""You are a data extraction AI. Extract numerical data from the text and create a chart.

TEXT:
{doc_context[:2000]}

USER REQUEST: {query}

IMPORTANT RULES:
1. Arrays 'x' and 'y' MUST have the SAME LENGTH
2. Extract REAL data from the text above
3. For education data, use institution names as x-axis
4. Use percentages/CGPA as y-axis values
5. Maximum 10 data points

Return ONLY valid JSON (no extra text):
{{
  "chart": {{
    "type": "bar",
    "title": "Chart Title",
    "xlabel": "Categories",
    "ylabel": "Values",
    "x": ["Item1", "Item2", "Item3"],
    "y": [10.5, 20.3, 15.8]
  }}
}}

EXAMPLE for education:
{{
  "chart": {{
    "type": "bar",
    "title": "Educational Performance",
    "xlabel": "Institution",
    "ylabel": "Score (%/CGPA)",
    "x": ["VTU", "PU College", "High School"],
    "y": [7.6, 71.66, 76.96]
  }}
}}

JSON:"""
        
        response = llm.invoke(prompt)
        logger.info(f"📊 LLM response: {response[:300]}...")
        
        # Parse JSON
        parsed = _try_parse_json_block(response)
        
        if not parsed or "chart" not in parsed:
            logger.warning("⚠️ No chart data in response")
            return {"has_chart": False}
        
        chart_data = parsed["chart"]
        
        # 🔥 VALIDATE array lengths
        chart_type = chart_data.get("type", "bar").lower()
        
        if chart_type == "pie":
            labels = chart_data.get("labels", [])
            values = chart_data.get("values", [])
            
            if not labels or not values or len(labels) != len(values):
                logger.error(f"❌ Pie chart validation failed: labels={len(labels)}, values={len(values)}")
                return {"has_chart": False, "error": "Invalid pie chart data"}
        else:
            x = chart_data.get("x", [])
            y = chart_data.get("y", [])
            
            if not x or not y:
                logger.error(f"❌ Missing x or y data")
                return {"has_chart": False, "error": "Missing chart data"}
            
            if len(x) != len(y):
                logger.error(f"❌ Array length mismatch: x={len(x)}, y={len(y)}")
                logger.error(f"   x={x}")
                logger.error(f"   y={y}")
                
                # 🔥 AUTO-FIX: Trim to shortest length
                min_len = min(len(x), len(y))
                chart_data["x"] = x[:min_len]
                chart_data["y"] = y[:min_len]
                logger.info(f"✅ Auto-fixed: trimmed to {min_len} elements")
        
        # Generate chart
        logger.info(f"🎨 Generating chart: {chart_data}")
        chart_base64, chart_url = generate_chart(chart_data)
        
        logger.info(f"✅ Chart generated successfully")
        return {
            "has_chart": True,
            "chartUrl": chart_url,
            "chartBase64": chart_base64,
            "chart_type": chart_type,
            "chart_data": chart_data
        }
        
    except HTTPException as he:
        logger.error(f"❌ Chart validation error: {he.detail}")
        return {"has_chart": False, "error": he.detail}
    
    except Exception as e:
        logger.error(f"❌ Chart generation error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"has_chart": False, "error": str(e)}

