from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url.replace("postgresql://", "postgresql+psycopg2://"),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,   # Fix: recycle connections after 1h to prevent PostgreSQL idle timeout (default ~8h)
    pool_timeout=30,     # Raise after 30s if no connection available (instead of hanging)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
