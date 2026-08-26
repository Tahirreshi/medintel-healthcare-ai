import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from src.database.models import Base

DB_PATH = os.environ.get("MEDINTEL_DB_PATH", "medintel_healthcare.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)

def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    print(f"[Database] Tables initialized successfully at {DB_PATH}")

def get_db():
    """Dependency / context manager helper to obtain DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def execute_raw_sql(query_str, params=None):
    """Execute raw SQL query and return columns and rows as dicts."""
    with engine.connect() as conn:
        result = conn.execute(text(query_str), params or {})
        if result.returns_rows:
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            return {"columns": columns, "rows": rows, "count": len(rows)}
        return {"columns": [], "rows": [], "count": result.rowcount}
