from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

# PostgreSQL connection URL
DATABASE_URL = "postgresql://postgres:system@localhost:5432/ai"

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set True for debugging SQL queries
    pool_pre_ping=True  # Helps with stale connections
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🔥 NEW: LangGraph Checkpointer Connection String
def get_checkpoint_connection_string():
    """
    Get PostgreSQL connection string for LangGraph checkpointer.
    
    Returns:
        str: Database connection URL
    """
    return DATABASE_URL
