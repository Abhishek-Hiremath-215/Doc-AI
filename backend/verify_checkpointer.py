"""Verify PostgreSQL checkpointer is working"""
import asyncio
from services.langgraph_service import LangGraphService
from uuid import uuid4

async def test_checkpointer():
    service = LangGraphService()
    session_id = uuid4()
    
    print(f"🧪 Testing checkpointer with session: {session_id}")
    
    # First query
    result1 = await service.process_query(
        query="What is Python?",
        user_id=uuid4(),
        session_id=session_id
    )
    print(f"✅ Query 1: {result1['answer'][:100]}...")
    
    # Second query (should remember context)
    result2 = await service.process_query(
        query="What are its features?",
        user_id=uuid4(),
        session_id=session_id
    )
    print(f"✅ Query 2: {result2['answer'][:100]}...")
    
    # Check database
    from database import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM checkpoints WHERE thread_id = :sid"), {"sid": str(session_id)})
        count = result.scalar()
        print(f"\n📊 Checkpoints in DB for this session: {count}")
        
        if count > 0:
            print("✅ PostgreSQL checkpointer is WORKING!")
        else:
            print("⚠️ Checkpointer not saving to PostgreSQL - using in-memory")

if __name__ == "__main__":
    asyncio.run(test_checkpointer())
