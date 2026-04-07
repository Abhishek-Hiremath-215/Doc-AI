import datetime
import json
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import ChatSession, ChatMessage, Project, User
from schemas import ChatSessionOut, ChatSessionDetail, ChatMessageOut, ChatQueryResponse
from core.role_enum import MessageType
from core.llm import get_llm_response  # Your existing LLM integration
from services.file_service import search_documents  # Your existing document search


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.max_context_messages = 10  # Last N messages for context
        self.max_context_length = 4000   # Token limit for context
    
    async def create_session(self, user_id: UUID, project_id: int, title: str = None) -> ChatSessionOut:
        """Create a new chat session"""
        # Verify project exists and user has access
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # TODO: Add project access validation based on your existing logic
        
        # Auto-generate title if not provided
        if not title:
            title = f"Chat - {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
        # Create session
        chat_session = ChatSession(
            user_id=user_id,
            project_id=project_id,
            title=title,
            is_active=True
        )
        
        self.db.add(chat_session)
        self.db.commit()
        self.db.refresh(chat_session)
        
        return ChatSessionOut.from_orm(chat_session)
    
    async def get_user_sessions(self, user_id: UUID, project_id: int = None) -> List[ChatSessionOut]:
        """Get all sessions for a user, optionally filtered by project"""
        query = self.db.query(ChatSession).filter(ChatSession.user_id == user_id)
        
        if project_id:
            query = query.filter(ChatSession.project_id == project_id)
        
        sessions = query.order_by(ChatSession.updated_at.desc()).all()
        
        # Add message count and last message time
        session_outs = []
        for session in sessions:
            session_out = ChatSessionOut.from_orm(session)
            
            # Get message stats
            message_count = self.db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id
            ).count()
            
            last_message = self.db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id
            ).order_by(ChatMessage.created_at.desc()).first()
            
            session_out.message_count = message_count
            session_out.last_message_at = last_message.created_at if last_message else None
            session_outs.append(session_out)
        
        return session_outs
    
    async def get_session_detail(self, session_id: UUID, user_id: UUID) -> ChatSessionDetail:
        """Get session with full message history"""
        session = self._get_user_session(session_id, user_id)
        
        # Get all messages for this session
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at).all()
        
        # Build response
        session_detail = ChatSessionDetail.from_orm(session)
        session_detail.messages = [ChatMessageOut.from_orm(msg) for msg in messages]
        session_detail.project_name = session.project.name if session.project else None
        
        return session_detail
    
    async def update_session(self, session_id: UUID, user_id: UUID, updates: Dict[str, Any]) -> ChatSessionOut:
        """Update session properties"""
        session = self._get_user_session(session_id, user_id)
        
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        session.updated_at = datetime.datetime.utcnow()
        self.db.commit()
        self.db.refresh(session)
        
        return ChatSessionOut.from_orm(session)
    
    async def delete_session(self, session_id: UUID, user_id: UUID):
        """Delete a chat session and all messages"""
        session = self._get_user_session(session_id, user_id)
        
        self.db.delete(session)  # Cascade will handle messages
        self.db.commit()
    
    async def ask_question_with_context(
        self, 
        session_id: UUID, 
        user_id: UUID, 
        query: str,
        use_context: bool = True
    ) -> ChatQueryResponse:
        """Ask a question considering conversation context"""
        session = self._get_user_session(session_id, user_id)
        
        # 1. Store user message
        user_message = ChatMessage(
            session_id=session_id,
            message_type=MessageType.user,
            content=query,
            metadata=json.dumps({"use_context": use_context})
        )
        self.db.add(user_message)
        self.db.flush()
        
        try:
            # 2. Build conversation context
            context = await self._build_conversation_context(session_id) if use_context else ""
            
            # 3. Enhance query with context (your existing logic from query.py)
            enhanced_query = await self._enhance_query_with_context(query, context, session.project_id)
            
            # 4. Search documents (your existing RAG logic)
            search_results = await search_documents(session.project_id, enhanced_query)
            
            # 5. Generate response with LLM
            llm_response = await self._generate_contextual_response(
                query=query,
                enhanced_query=enhanced_query,
                context=context,
                search_results=search_results
            )
            
            # 6. Store assistant message
            assistant_message = ChatMessage(
                session_id=session_id,
                message_type=MessageType.assistant,
                content=llm_response["answer"],
                metadata=json.dumps({
                    "sources": llm_response.get("sources", []),
                    "enhanced_query": enhanced_query,
                    "context_used": bool(context)
                })
            )
            self.db.add(assistant_message)
            self.db.commit()
            
            # 7. Update session timestamp
            session.updated_at = datetime.datetime.utcnow()
            self.db.commit()
            
            return ChatQueryResponse(
                answer=llm_response["answer"],
                sources=llm_response.get("sources", []),
                session_id=session_id,
                message_id=assistant_message.id,
                context_used=bool(context),
                enhanced_query=enhanced_query
            )
            
        except Exception as e:
            # Rollback on error
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")
    
    async def get_conversation_context(self, session_id: UUID, user_id: UUID):
        """Get conversation context for debugging"""
        self._get_user_session(session_id, user_id)
        
        recent_messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(self.max_context_messages).all()
        
        context_summary = {
            "session_id": session_id,
            "total_messages": len(recent_messages),
            "context_messages": [
                {
                    "type": msg.message_type.value,
                    "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                    "created_at": msg.created_at.isoformat()
                } for msg in reversed(recent_messages)
            ]
        }
        
        return context_summary
    
    def _get_user_session(self, session_id: UUID, user_id: UUID) -> ChatSession:
        """Get session ensuring user ownership"""
        session = self.db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return session
    
    async def _build_conversation_context(self, session_id: UUID) -> str:
        """Build conversation context from recent messages"""
        recent_messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(self.max_context_messages).all()
        
        if not recent_messages:
            return ""
        
        # Build context string
        context_parts = []
        for msg in reversed(recent_messages):  # Chronological order
            role = "User" if msg.message_type == MessageType.user else "Assistant"
            context_parts.append(f"{role}: {msg.content}")
        
        context = "\n".join(context_parts)
        
        # Truncate if too long
        if len(context) > self.max_context_length:
            context = context[-self.max_context_length:]
            # Try to start from a complete message
            first_newline = context.find('\n')
            if first_newline > 0:
                context = context[first_newline + 1:]
        
        return context
    
    async def _enhance_query_with_context(self, query: str, context: str, project_id: int) -> str:
        """Enhance query considering conversation context"""
        if not context:
            return query
        
        # This is a simplified version - you might want to use your LLM to enhance
        enhanced = f"""
        Based on our previous conversation:
        {context}
        
        Current question: {query}
        
        Please provide a comprehensive answer considering the conversation context.
        """
        return enhanced.strip()
    
    async def _generate_contextual_response(
        self, 
        query: str, 
        enhanced_query: str, 
        context: str, 
        search_results: List[Dict]
    ) -> Dict[str, Any]:
        """Generate response using your existing LLM integration"""
        # Use your existing LLM logic from core/llm.py
        # This is a placeholder - replace with your actual implementation
        
        prompt = f"""
        Conversation Context:
        {context}
        
        User Question: {query}
        
        Relevant Documents:
        {json.dumps(search_results, indent=2)}
        
        Please provide a comprehensive answer that:
        1. Considers the conversation history
        2. Uses the relevant documents
        3. Maintains context continuity
        """
        
        # Replace this with your actual LLM call
        response = await get_llm_response(prompt)
        
        return {
            "answer": response,
            "sources": search_results
        }
