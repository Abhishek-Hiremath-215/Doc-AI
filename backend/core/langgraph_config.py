import os
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from pydantic import BaseModel
from core.config import settings

# =============================
# LangGraph State Definition
# =============================

class AgentState(TypedDict):
    """State passed between LangGraph agents"""
    messages: Sequence[dict]  # Conversation history
    query: str  # Current user query
    project_id: int | None  # Selected project
    selected_files: list[str]  # Selected files for context
    user_id: str  # Current user ID
    
    # Context from previous conversation
    conversation_context: str
    
    # Retrieved information
    documents: list[dict]  # Retrieved documents from RAG
    graph_data: dict | None  # Neo4j graph relationships
    
    # Agent decisions
    intent: str  # "document_query", "general_chat", "chart_request", "project_analysis"
    requires_documents: bool
    requires_graph: bool
    
    # Final output
    answer: str
    sources: list[dict]
    chart_data: dict | None
    
    # Metadata
    enhanced_query: str | None
    error: str | None


# =============================
# Checkpoint Configuration
# =============================

def get_checkpoint_connection_string():
    """Get PostgreSQL connection string for LangGraph checkpoints"""
    return settings.DATABASE_URL  # Use your existing database


# =============================
# LangGraph Configuration
# =============================

LANGGRAPH_CONFIG = {
    "max_iterations": 10,
    "recursion_limit": 25,
    "checkpoint_db": get_checkpoint_connection_string(),
}
