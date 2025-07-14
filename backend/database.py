from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base  # Assuming models.py defines Base
from config import DATABASE_URL

# Setup SQLAlchemy engine and session
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,  # Recycle connections every 5 minutes
    pool_size=10,  # Connection pool size
    max_overflow=20,  # Allow extra connections if needed
    echo=False,  # Set to True for SQL debugging
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create database tables
Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    """Dependency to get DB session with proper error handling."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        print(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()
