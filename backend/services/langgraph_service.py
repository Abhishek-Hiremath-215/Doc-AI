"""LangGraph service - Production version using chat_messages for context"""
import logging
from typing import Dict, Any
from uuid import UUID
from agents.workflow import agent_workflow


logger = logging.getLogger("uvicorn")



class LangGraphService:
    """Service for executing LangGraph agent workflows"""
    
    def __init__(self):
        self.workflow = agent_workflow
        logger.info("✅ LangGraphService initialized")
    
    async def process_query(
        self,
        query: str,
        user_id: UUID,
        project_id: int = None,
        selected_files: list = None,
        conversation_context: str = "",
        session_id: UUID = None
    ) -> Dict[str, Any]:
        """
        Process query through LangGraph
        Context is managed via chat_messages table in chat.py
        """
        
        logger.info(f"🚀 Processing query: {query[:100]}...")
        
        # 🆕 AUTO-INFER PROJECT FROM FILES IF NOT PROVIDED
        if selected_files and not project_id:
            logger.info(f"📁 No project_id provided, inferring from files: {selected_files}")
            try:
                from core.config import qdrant_client, collection_name
                from qdrant_client.http import models as rest
                
                # Query Qdrant to find project_id from file metadata
                search_result = qdrant_client.scroll(
                    collection_name=collection_name,
                    scroll_filter=rest.Filter(
                        must=[
                            rest.FieldCondition(
                                key="file_name",
                                match=rest.MatchAny(any=selected_files)
                            )
                        ]
                    ),
                    limit=1,
                    with_payload=True
                )
                
                if search_result and search_result[0]:
                    project_id_str = search_result[0][0].payload.get("project_id")
                    if project_id_str:
                        project_id = int(project_id_str)
                        logger.info(f"✅ Inferred project_id={project_id} from Qdrant metadata")
                    else:
                        logger.warning(f"⚠️ No project_id found in Qdrant for files: {selected_files}")
                else:
                    logger.warning(f"⚠️ No documents found in Qdrant for files: {selected_files}")
                    
            except Exception as e:
                logger.error(f"❌ Error inferring project from Qdrant: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        initial_state = {
            "messages": [],
            "query": query,
            "project_id": project_id,
            "selected_files": selected_files or [],
            "user_id": str(user_id),
            "conversation_context": conversation_context,  # From chat_messages table
            "documents": [],
            "graph_data": None,
            "intent": "",
            "requires_documents": False,
            "requires_graph": False,
            "answer": "",
            "sources": [],
            "chart_data": None,
            "enhanced_query": None,
            "error": None
        }
        
        try:
            result = await self.workflow.ainvoke(initial_state)
            
            chart_data = result.get("chart_data")
            chart_data_response = None
            
            if chart_data and isinstance(chart_data, dict) and chart_data.get("has_chart"):
                chart_data_response = chart_data
                logger.info(f"📊 Chart generated: {chart_data.get('chartUrl')}")
            
            logger.info(f"✅ Complete - Intent: {result.get('intent')}")
            
            return {
                "answer": result.get("answer", ""),
                "sources": result.get("sources", []),
                "intent": result.get("intent"),
                "documents": result.get("documents", []),
                "graph_data": result.get("graph_data"),
                "enhanced_query": result.get("enhanced_query"),
                "error": result.get("error"),
                "context_used": bool(conversation_context),
                "chart_data": chart_data_response,
                "has_chart": bool(chart_data_response)
            }
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "answer": f"Error: {str(e)}",
                "sources": [],
                "error": str(e),
                "chart_data": None,
                "has_chart": False
            }
