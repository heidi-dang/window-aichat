import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


def _default_sqlite_path() -> str:
    base_dir = Path(os.path.expanduser("~")) / ".aichatdesktop"
    base_dir.mkdir(parents=True, exist_ok=True)
    return str((base_dir / "window_aichat.db").resolve())


def get_database_url() -> str:
    url = os.getenv("WINDOW_AICHAT_DB_URL")
    if url:
        return url
    return f"sqlite:///{_default_sqlite_path()}"


engine = create_engine(
    get_database_url(),
    connect_args=(
        {"check_same_thread": False}
        if get_database_url().startswith("sqlite:///")
        else {}
    ),
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
