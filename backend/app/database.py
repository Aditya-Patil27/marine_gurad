from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session
from typing import Generator
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# SessionLocal factory for standalone scripts
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)

def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session"""
    with Session(engine) as session:
        yield session

def init_db():
    """Initialize database - create all tables using SQLModel metadata"""
    # Import all models to ensure they're registered with SQLModel.metadata
    from app.models import vessel, pollution, mpa, health  # noqa: F401
    SQLModel.metadata.create_all(bind=engine)
