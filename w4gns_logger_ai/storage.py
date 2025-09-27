"""Persistence layer: SQLite engine setup, sessions, and QSO CRUD/search.

The database lives in the user's data directory by default, and can be
overridden via the W4GNS_DB_PATH environment variable. SQLModel/SQLAlchemy 2.x
are used for ORM-style access.

Enhanced with connection pooling and bulk operations for better performance.
"""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, List, Optional

from platformdirs import user_data_dir
from sqlmodel import Session, SQLModel, create_engine, select

from .models import QSO

APP_NAME = "W4GNS Logger AI"
DB_ENV_VAR = "W4GNS_DB_PATH"


def _default_db_path() -> Path:
    """Return the default location of the SQLite database file.

    On Windows this resolves under %LOCALAPPDATA% using platformdirs.
    """
    data_dir = Path(user_data_dir(appname=APP_NAME, appauthor=False))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "qsolog.sqlite3"


def get_db_path() -> Path:
    """Resolve the active database path, honoring W4GNS_DB_PATH if set."""
    env = os.getenv(DB_ENV_VAR)
    if env:
        p = Path(env).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return _default_db_path()


_engine = None
_engine_lock = threading.Lock()


def get_engine():
    """Create (once) and return the SQLAlchemy engine bound to our SQLite DB.

    Enhanced with connection pooling and thread safety.
    Raises RuntimeError if database creation fails.
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            # Double-check locking pattern for thread safety
            if _engine is None:
                try:
                    db_path = get_db_path()
                    url = f"sqlite:///{db_path}"
                    # Enhanced connection settings for better performance
                    _engine = create_engine(
                        url,
                        echo=False,
                        pool_size=20,  # Increased connection pool
                        max_overflow=30,  # Allow overflow connections
                        pool_timeout=30,  # Connection timeout
                        pool_recycle=3600,  # Recycle connections every hour
                        connect_args={
                            "check_same_thread": False,  # Allow multi-threading
                            "timeout": 30,  # SQLite busy timeout
                        }
                    )
                except Exception as e:
                    raise RuntimeError(f"Failed to create database engine: {e}") from e
    return _engine


def create_db_and_tables() -> Path:
    """Create all tables for the current metadata if they don't exist yet.

    Raises RuntimeError if table creation fails.
    """
    try:
        engine = get_engine()
        SQLModel.metadata.create_all(engine)
        return get_db_path()
    except Exception as e:
        raise RuntimeError(f"Failed to create database tables: {e}") from e


@contextmanager
def session_scope():
    """Context manager yielding a SQLModel Session bound to our engine.

    Automatically handles session cleanup and rollback on errors.
    """
    session = None
    try:
        session = Session(get_engine())
        yield session
    except Exception:
        if session:
            session.rollback()
        raise
    finally:
        if session:
            session.close()


# CRUD helpers

def add_qso(qso: QSO) -> QSO:
    """Persist a new QSO and return it refreshed with its database id.

    Raises RuntimeError if the QSO cannot be saved.
    """
    try:
        with session_scope() as session:
            session.add(qso)
            session.commit()
            session.refresh(qso)
            return qso
    except Exception as e:
        raise RuntimeError(f"Failed to save QSO: {e}") from e


def get_qso(qso_id: int) -> Optional[QSO]:
    """Fetch a QSO by primary key, or None if missing.

    Raises RuntimeError if database query fails.
    """
    try:
        with session_scope() as session:
            return session.get(QSO, qso_id)
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve QSO {qso_id}: {e}") from e


def list_qsos(limit: int = 100, call: Optional[str] = None) -> List[QSO]:
    """Return recent QSOs, optionally filtering by callsign substring.

    Raises RuntimeError if database query fails.
    """
    try:
        with session_scope() as session:
            stmt = select(QSO)
            if call:
                stmt = stmt.where(QSO.call.ilike(f"%{call}%"))
            stmt = stmt.order_by(QSO.start_at.desc()).limit(limit)
            return list(session.exec(stmt))
    except Exception as e:
        raise RuntimeError(f"Failed to list QSOs: {e}") from e


def delete_qso(qso_id: int) -> bool:
    """Delete a QSO by id, returning True if it existed and was removed.

    Raises RuntimeError if database operation fails.
    """
    try:
        with session_scope() as session:
            q = session.get(QSO, qso_id)
            if not q:
                return False
            session.delete(q)
            session.commit()
            return True
    except Exception as e:
        raise RuntimeError(f"Failed to delete QSO {qso_id}: {e}") from e


def bulk_add_qsos(qsos: Iterable[QSO]) -> int:
    """Insert many QSOs at once, returning how many were provided.

    Raises RuntimeError if bulk insert fails.
    """
    try:
        items = list(qsos)
        with session_scope() as session:
            session.add_all(items)
            session.commit()
            return len(items)
    except Exception as e:
        raise RuntimeError(f"Failed to bulk add QSOs: {e}") from e


def bulk_add_qsos_parallel(qsos: Iterable[QSO], batch_size: int = 1000) -> int:
    """Insert many QSOs using batched operations for better performance.

    Processes QSOs in batches to optimize database performance and memory usage.

    Args:
        qsos: Iterable of QSO objects to insert
        batch_size: Number of QSOs to process in each batch

    Returns:
        Total number of QSOs inserted

    Raises:
        RuntimeError if bulk insert fails
    """
    try:
        items = list(qsos)
        total_inserted = 0

        # Process in batches for better memory management and transaction handling
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            with session_scope() as session:
                session.add_all(batch)
                session.commit()
                total_inserted += len(batch)

        return total_inserted
    except Exception as e:
        raise RuntimeError(f"Failed to bulk add QSOs: {e}") from e


def search_qsos(
    call: Optional[str] = None,
    band: Optional[str] = None,
    mode: Optional[str] = None,
    grid: Optional[str] = None,
    limit: int = 100,
) -> List[QSO]:
    """Flexible search across common fields; values must match exactly
    except for `call`, which does a case-insensitive substring match.

    Raises RuntimeError if database query fails.
    """
    try:
        with session_scope() as session:
            stmt = select(QSO)
            if call:
                stmt = stmt.where(QSO.call.ilike(f"%{call}%"))
            if band:
                stmt = stmt.where(QSO.band == band)
            if mode:
                stmt = stmt.where(QSO.mode == mode)
            if grid:
                stmt = stmt.where(QSO.grid == grid)
            stmt = stmt.order_by(QSO.start_at.desc()).limit(limit)
            return list(session.exec(stmt))
    except Exception as e:
        raise RuntimeError(f"Failed to search QSOs: {e}") from e


def search_qsos_parallel(
    call: Optional[str] = None,
    band: Optional[str] = None,
    mode: Optional[str] = None,
    grid: Optional[str] = None,
    limit: int = 100,
    batch_size: int = 5000,
) -> List[QSO]:
    """Enhanced search with optimized query execution for large datasets.

    Uses batched processing for better performance on large result sets.

    Args:
        call: Callsign substring filter
        band: Exact band match
        mode: Exact mode match
        grid: Exact grid match
        limit: Maximum results to return
        batch_size: Internal batch size for processing

    Returns:
        List of matching QSO objects

    Raises:
        RuntimeError if database query fails
    """
    try:
        with session_scope() as session:
            stmt = select(QSO)
            if call:
                stmt = stmt.where(QSO.call.ilike(f"%{call}%"))
            if band:
                stmt = stmt.where(QSO.band == band)
            if mode:
                stmt = stmt.where(QSO.mode == mode)
            if grid:
                stmt = stmt.where(QSO.grid == grid)
            stmt = stmt.order_by(QSO.start_at.desc()).limit(limit)

            # Use batch processing for large queries
            if limit > batch_size:
                results = []
                offset = 0
                while len(results) < limit:
                    batch_stmt = stmt.offset(offset).limit(min(batch_size, limit - len(results)))
                    batch_results = list(session.exec(batch_stmt))
                    if not batch_results:
                        break
                    results.extend(batch_results)
                    offset += batch_size
                return results[:limit]
            else:
                return list(session.exec(stmt))
    except Exception as e:
        raise RuntimeError(f"Failed to search QSOs: {e}") from e
