import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from uuid import UUID
from typing import List, Optional

from models import ChatSession, ChatMessage, User, Project, ProjectPermission
from schemas import (
    ChatSessionCreate, ChatSessionOut, ChatSessionDetail, ChatSessionUpdate,
    ChatMessageOut, ChatQueryRequest, ChatQueryResponse
)
from dependencies import get_db, get_current_active_user
from core.role_enum import MessageType

# 🔥 NEW: Import LangGraph service
from services.langgraph_service import LangGraphService

router = APIRouter()

# 🔥 Initialize LangGraph service
langgraph_service = LangGraphService()


@router.post("/sessions", response_model=ChatSessionOut)
async def create_chat_session(
    session_in: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a flexible chat session - NO project lock"""
    
    print(f"🔍 DEBUG: Creating FLEXIBLE session")
    
    title = session_in.title or f"New Chat - {datetime.datetime.utcnow().strftime('%m/%d %H:%M')}"
    
    chat_session = ChatSession(
        user_id=current_user.id,
        title=title.strip(),
        is_active=True
    )
    
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    
    print(f"✅ Flexible session created:")
    print(f"   - Session ID: {chat_session.id}")
    print(f"   - Title: {chat_session.title}")
    
    session_out = ChatSessionOut.model_validate(chat_session)
    session_out.message_count = 0
    session_out.last_message_at = None
    
    return session_out


@router.get("/sessions", response_model=List[ChatSessionOut])
async def list_user_sessions(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all flexible chat sessions"""
    
    query = db.query(ChatSession).filter(ChatSession.user_id == current_user.id)
    
    if not include_inactive:
        query = query.filter(ChatSession.is_active == True)
    
    sessions = query.order_by(ChatSession.updated_at.desc()).all()
    
    session_outs = []
    for session in sessions:
        message_stats = db.query(
            func.count(ChatMessage.id).label('count'),
            func.max(ChatMessage.created_at).label('last_message')
        ).filter(ChatMessage.session_id == session.id).first()
        
        session_out = ChatSessionOut.model_validate(session)
        session_out.message_count = message_stats.count or 0
        session_out.last_message_at = message_stats.last_message
        session_outs.append(session_out)
    
    return session_outs


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_session_detail(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get flexible session details"""
    
    session = db.query(ChatSession).filter(
        and_(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    session_detail = ChatSessionDetail.model_validate(session)
    session_detail.messages = [ChatMessageOut.model_validate(msg) for msg in messages]
    session_detail.project_name = None
    
    return session_detail


@router.post("/sessions/{session_id}/ask", response_model=ChatQueryResponse)
async def ask_question_with_context(
    session_id: UUID,
    query_request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """🔥 LANGGRAPH-POWERED FLEXIBLE CHAT with FULL CONVERSATION HISTORY"""
    
    session = db.query(ChatSession).filter(
        and_(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    selected_project_id = query_request.project_id
    
    print(f"🔍 DEBUG: LANGGRAPH FLEXIBLE CHAT")
    print(f"   - User selected project_id = {selected_project_id}")
    print(f"   - Query = {query_request.query}")
    print(f"   - Selected files = {query_request.selected_files}")
    
    chart_keywords = [
        'chart', 'graph', 'plot', 'visualize', 'visualization', 'show data',
        'create chart', 'draw', 'bar chart', 'pie chart', 'line chart',
        'scatter plot', 'show me a graph', 'make a chart', 'generate chart'
    ]
    is_chart_request = any(keyword in query_request.query.lower() for keyword in chart_keywords)
    print(f"🔍 DEBUG: Chart requested = {is_chart_request}")
    
    user_message = ChatMessage(
        session_id=session_id,
        user_id=current_user.id,
        message_type=MessageType.user,
        content=query_request.query,
        message_metadata=json.dumps({
            "use_context": query_request.use_context,
            "selected_files": query_request.selected_files,
            "project_id": selected_project_id,
            "question_type": "project_analysis" if selected_project_id else "general_chat",
            "is_chart_request": is_chart_request
        })
    )
    db.add(user_message)
    db.flush()

    try:
        if selected_project_id:
            print(f"🔍 DEBUG: PROJECT MODE - Analyzing project {selected_project_id}")
            
            project = db.query(Project).filter(
                Project.id == selected_project_id
            ).filter(
                or_(
                    Project.creator_id == current_user.id,
                    Project.permissions.any(ProjectPermission.user_id == current_user.id)
                )
            ).first()
            
            if not project:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Project {selected_project_id} not found or access denied"
                )
            
            print(f"✅ Project access validated: {project.name}")
        
        # 🔥 LOAD ALL MESSAGES (no limit!)
        recent_messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).all()  # ✅ ALL MESSAGES
        
        context = ""
        if recent_messages and len(recent_messages) > 1:
            context_msgs = []
            for msg in reversed(recent_messages[1:]):  # All except current
                role = "User" if msg.message_type == MessageType.user else "Assistant"
                # ✅ FULL MESSAGE CONTENT - no truncation
                context_msgs.append(f"{role}: {msg.content}")
            
            context = "\n".join(context_msgs)  # ✅ COMPLETE HISTORY
            print(f"📜 Using FULL conversation context:")
            print(f"   - Messages: {len(context_msgs)}")
            print(f"   - Total chars: {len(context)}")
            print(f"   - Estimated tokens: ~{len(context) // 4}")
        else:
            print(f"📜 No previous conversation context")
        
        print(f"🚀 Invoking LangGraph workflow...")
        
        langgraph_response = await langgraph_service.process_query(
            query=query_request.query,
            user_id=current_user.id,
            project_id=selected_project_id,
            selected_files=query_request.selected_files,
            conversation_context=context,  # ✅ FULL HISTORY
            session_id=session_id
        )
        
        print(f"✅ LangGraph processing complete:")
        print(f"   - Intent: {langgraph_response.get('intent')}")
        print(f"   - Documents retrieved: {len(langgraph_response.get('documents', []))}")
        print(f"   - Answer length: {len(langgraph_response.get('answer', ''))} chars")
        print(f"   - Error: {langgraph_response.get('error')}")
        
        ai_response_content = langgraph_response.get("answer", "No response generated")
        sources = langgraph_response.get("sources", [])
        context_used = langgraph_response.get("context_used", False)
        enhanced_query = langgraph_response.get("enhanced_query")
        error_occurred = langgraph_response.get("error")
        
        # 🔥 EXTRACT CHART DATA
        chart_base64 = None
        chart_url = None
        has_chart = False
        chart_type = None
        
        chart_data_obj = langgraph_response.get("chart_data")
        
        if chart_data_obj and isinstance(chart_data_obj, dict):
            if chart_data_obj.get("has_chart") == True:
                chart_base64 = chart_data_obj.get("chartBase64")
                chart_url = chart_data_obj.get("chartUrl")
                has_chart = True
                chart_type = chart_data_obj.get("chart_type")
                
                print(f"📊 ✅ Chart data received from LangGraph:")
                print(f"   - URL: {chart_url}")
                print(f"   - Type: {chart_type}")
        
        max_content_length = 10000
        original_length = len(ai_response_content)
        if original_length > max_content_length:
            print(f"⚠️ WARNING: Response too long ({original_length} chars), truncating to {max_content_length}")
            ai_response_content = ai_response_content[:max_content_length] + "... [Response truncated due to length]"
        
        # Metadata
        metadata_dict = {
            "sources": sources,
            "context_used": context_used,
            "selected_files": query_request.selected_files,
            "project_id": selected_project_id,
            "response_type": "project_analysis" if selected_project_id else "general_chat",
            "original_length": original_length,
            "truncated": original_length > max_content_length,
            "agent_system": "langgraph",
            "intent": langgraph_response.get("intent"),
            "documents_retrieved": len(langgraph_response.get("documents", [])),
            "graph_data_used": bool(langgraph_response.get("graph_data")),
            "enhanced_query": enhanced_query,
            "error": error_occurred,
            "has_chart": has_chart,
            "chart_url": chart_url,
            "chart_type": chart_type,
            "is_chart_request": is_chart_request,
            "context_messages_count": len(context_msgs) if context else 0,  # ✅ Track history size
            "context_chars": len(context)  # ✅ Track context size
        }
        
        try:
            metadata_json = json.dumps(metadata_dict)
        except Exception as json_error:
            print(f"⚠️ Metadata serialization error: {json_error}")
            metadata_json = json.dumps({
                "sources": [],
                "error": "Metadata serialization failed",
                "has_chart": has_chart,
                "chart_url": chart_url
            })
        
        assistant_message = ChatMessage(
            session_id=session_id,
            user_id=current_user.id,
            message_type=MessageType.assistant,
            content=ai_response_content,
            message_metadata=metadata_json
        )
        db.add(assistant_message)
        
        try:
            db.commit()
            db.refresh(assistant_message)
            print(f"✅ Messages saved successfully")
            print(f"   - User message ID: {user_message.id}")
            print(f"   - AI message ID: {assistant_message.id}")
            if has_chart:
                print(f"   - Chart saved: {chart_url}")
        except Exception as db_error:
            print(f"❌ Database save error: {db_error}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save messages: {str(db_error)}")
        
        response = ChatQueryResponse(
            answer=langgraph_response.get("answer", "No response generated"),
            sources=sources,
            session_id=session_id,
            message_id=assistant_message.id,
            user_message_id=user_message.id,
            context_used=context_used,
            enhanced_query=enhanced_query,
            chartBase64=chart_base64,
            chartUrl=chart_url,
            has_chart=has_chart
        )
        
        print(f"✅ Returning LangGraph-powered response with FULL context:")
        print(f"   - Answer length: {len(response.answer)}")
        print(f"   - Sources: {len(response.sources)}")
        print(f"   - Has chart: {response.has_chart}")
        
        return response

    except HTTPException:
        db.rollback()
        raise
    
    except Exception as e:
        db.rollback()
        print(f"❌ ERROR in LangGraph flexible chat processing: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        
        error_message = ChatMessage(
            session_id=session_id,
            user_id=current_user.id,
            message_type=MessageType.assistant,
            content=f"Sorry, I encountered an error: {str(e)}",
            message_metadata=json.dumps({
                "error": True, 
                "project_id": selected_project_id,
                "error_type": "processing_error",
                "agent_system": "langgraph",
                "has_chart": False
            })
        )
        db.add(error_message)
        db.commit()
        
        return ChatQueryResponse(
            answer=f"Sorry, I encountered an error: {str(e)}",
            sources=[],
            session_id=session_id,
            message_id=error_message.id,
            user_message_id=user_message.id,
            context_used=False,
            chartBase64=None,
            chartUrl=None,
            has_chart=False
        )


@router.put("/sessions/{session_id}", response_model=ChatSessionOut)
async def update_session(
    session_id: UUID,
    session_update: ChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update flexible session"""
    
    session = db.query(ChatSession).filter(
        and_(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    update_data = session_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(session, key):
            setattr(session, key, value)
    
    session.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(session)
    
    return ChatSessionOut.model_validate(session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete flexible session"""
    
    session = db.query(ChatSession).filter(
        and_(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    db.delete(session)
    db.commit()
    return None


@router.get("/charts/{filename}")
async def serve_chart(filename: str):
    """Serve generated chart files"""
    from fastapi.responses import FileResponse
    import os
    
    chart_path = os.path.join("generated_charts", filename)
    
    if not os.path.exists(chart_path):
        raise HTTPException(status_code=404, detail="Chart not found")
    
    return FileResponse(
        chart_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"}
    )
