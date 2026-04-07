"""LangGraph workflow - Production version using chat_messages for context"""
import logging
from typing import Literal
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from agents.intent_classifier import IntentClassifier
from agents.retrieval_agent import RetrievalAgent
from agents.response_agent import ResponseAgent

logger = logging.getLogger("uvicorn")


class AgentState(TypedDict):
    messages: list
    query: str
    project_id: int | None
    selected_files: list
    user_id: str
    conversation_context: str
    documents: list
    graph_data: dict | None
    intent: str
    requires_documents: bool
    requires_graph: bool
    answer: str
    sources: list
    chart_data: dict | None
    enhanced_query: str | None
    error: str | None


def create_agent_workflow():
    """Create the main LangGraph workflow"""
    
    intent_classifier = IntentClassifier()
    retrieval_agent = RetrievalAgent()
    response_agent = ResponseAgent()
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("classify_intent", intent_classifier.process)
    workflow.add_node("retrieve_context", retrieval_agent.process)
    workflow.add_node("generate_response", response_agent.process)
    
    workflow.set_entry_point("classify_intent")
    
    def should_retrieve(state: AgentState) -> Literal["retrieve", "respond"]:
        return "retrieve" if (state.get("requires_documents") or state.get("requires_graph")) else "respond"
    
    workflow.add_conditional_edges(
        "classify_intent",
        should_retrieve,
        {
            "retrieve": "retrieve_context",
            "respond": "generate_response"
        }
    )
    
    workflow.add_edge("retrieve_context", "generate_response")
    workflow.add_edge("generate_response", END)
    
    compiled_workflow = workflow.compile()
    
    logger.info("✅ LangGraph workflow compiled")
    logger.info("   💾 Memory: chat_messages table (PostgreSQL)")
    logger.info("   ⚡ Context: Short summaries (no token limits)")
    logger.info("   🎯 Production ready & Windows compatible")
    
    return compiled_workflow


agent_workflow = create_agent_workflow()
