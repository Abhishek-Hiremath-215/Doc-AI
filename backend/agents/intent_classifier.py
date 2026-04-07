# """Intent classification agent - determines what type of query this is"""
# import logging

# logger = logging.getLogger("uvicorn")


# class IntentClassifier:
#     """Classifies user intent to route to appropriate agents"""
    
#     async def process(self, state: dict) -> dict:
#         """Classify the user's query intent"""
#         query = state["query"].lower()
        
#         logger.info(f"🔍 Classifying intent for query: {query[:100]}...")
        
#         # Chart detection
#         chart_keywords = ['chart', 'graph', 'plot', 'visualize', 'visualization', 
#                          'bar chart', 'pie chart', 'line chart', 'scatter plot']
#         is_chart_request = any(keyword in query for keyword in chart_keywords)
        
#         # Document query detection
#         document_keywords = ['document', 'file', 'pdf', 'according to', 'in the document',
#                             'based on', 'what does', 'explain', 'summarize']
#         needs_documents = any(keyword in query for keyword in document_keywords)
        
#         # Project analysis detection
#         project_keywords = ['project', 'analyze', 'compare', 'relationship', 'connection']
#         needs_graph = any(keyword in query for keyword in project_keywords)
        
#         # Determine intent
#         if is_chart_request:
#             intent = "chart_request"
#             requires_documents = True
#             requires_graph = False
#         elif state.get("project_id") and (needs_documents or needs_graph):
#             intent = "project_analysis"
#             requires_documents = needs_documents
#             requires_graph = needs_graph
#         elif state.get("project_id"):
#             intent = "document_query"
#             requires_documents = True
#             requires_graph = False
#         else:
#             intent = "general_chat"
#             requires_documents = False
#             requires_graph = False
        
#         logger.info(f"✅ Intent classified: {intent}")
#         logger.info(f"   - Requires documents: {requires_documents}")
#         logger.info(f"   - Requires graph: {requires_graph}")
        
#         return {
#             **state,
#             "intent": intent,
#             "requires_documents": requires_documents,
#             "requires_graph": requires_graph
#         }


"""Intent classification agent - determines query type"""
import logging

logger = logging.getLogger("uvicorn")

class IntentClassifier:
    """Classifies user intent to route to appropriate agents"""
    
    async def process(self, state: dict) -> dict:
        """Classify the user's query intent"""
        query = state["query"].lower()
        project_id = state.get("project_id")
        selected_files = state.get("selected_files", [])  # ✅ NEW
        
        logger.info(f"🔍 Classifying intent for query: {query[:100]}...")
        
        # Chart detection
        chart_keywords = ['chart', 'graph', 'plot', 'visualize', 'visualization',
                         'bar chart', 'pie chart', 'line chart', 'scatter plot']
        is_chart_request = any(keyword in query for keyword in chart_keywords)
        
        # Document query detection
        document_keywords = ['document', 'file', 'pdf', 'according to', 'in the document',
                            'based on', 'what does', 'explain', 'summarize', 'price', 
                            'data', 'value', 'cost', 'show me']  # ✅ Added more keywords
        needs_documents = any(keyword in query for keyword in document_keywords)
        
        # Project analysis detection
        project_keywords = ['project', 'analyze', 'compare', 'relationship', 'connection']
        needs_graph = any(keyword in query for keyword in project_keywords)
        
        # ✅ CRITICAL FIX: Files selected = document query
        has_files_selected = len(selected_files) > 0
        
        # Determine intent
        if is_chart_request:
            intent = "chart_request"
            requires_documents = True
            requires_graph = False
        
        elif has_files_selected or (project_id and needs_documents):
            # ✅ NEW: If files are selected, ALWAYS treat as document query
            intent = "document_query"
            requires_documents = True
            requires_graph = False
        
        elif project_id and needs_graph:
            intent = "project_analysis"
            requires_documents = needs_documents
            requires_graph = True
        
        elif project_id:
            # Project selected but no specific intent - default to document query
            intent = "document_query"
            requires_documents = True
            requires_graph = False
        
        else:
            intent = "general_chat"
            requires_documents = False
            requires_graph = False
        
        logger.info(f"✅ Intent classified: {intent}")
        logger.info(f"   - Requires documents: {requires_documents}")
        logger.info(f"   - Requires graph: {requires_graph}")
        logger.info(f"   - Files selected: {len(selected_files)}")  # ✅ NEW LOG
        
        return {
            **state,
            "intent": intent,
            "requires_documents": requires_documents,
            "requires_graph": requires_graph
        }
