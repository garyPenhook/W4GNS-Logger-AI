from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, List, Optional

from platformdirs import user_data_dir
from sqlmodel import Session, SQLModel, create_engine, select

from .models import QSO

APP_NAME = "W4GNS Logger AI"
DB_ENV_VAR = "W4GNS_DB_PATH"


def _default_db_path() -> Path:
    data_dir = Path(user_data_dir(appname=APP_NAME, appauthor=False))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "qsolog.sqlite3"


def get_db_path() -> Path:
    env = os.getenv(DB_ENV_VAR)
    if env:
        p = Path(env).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return _default_db_path()


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        db_path = get_db_path()
        url = f"sqlite:///{db_path}"
        _engine = create_engine(url, echo=False)
    return _engine


def create_db_and_tables() -> Path:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    return get_db_path()


@contextmanager
def session_scope():
    with Session(get_engine()) as session:
        yield session


# CRUD helpers

def add_qso(qso: QSO) -> QSO:
    with session_scope() as session:
        session.add(qso)
        session.commit()
        session.refresh(qso)
        return qso


def get_qso(qso_id: int) -> Optional[QSO]:
    with session_scope() as session:
        return session.get(QSO, qso_id)


def list_qsos(limit: int = 100, call: Optional[str] = None) -> List[QSO]:
    with session_scope() as session:
        stmt = select(QSO)
        if call:
            stmt = stmt.where(QSO.call.ilike(f"%{call}%"))
        stmt = stmt.order_by(QSO.start_at.desc()).limit(limit)
        return list(session.exec(stmt))


def delete_qso(qso_id: int) -> bool:
    with session_scope() as session:
        q = session.get(QSO, qso_id)
        if not q:
            return False
        session.delete(q)
        session.commit()
        return True


def bulk_add_qsos(qsos: Iterable[QSO]) -> int:
    items = list(qsos)
    with session_scope() as session:
        session.add_all(items)
        session.commit()
        return len(items)


def search_qsos(
    call: Optional[str] = None,
    band: Optional[str] = None,
    mode: Optional[str] = None,
    grid: Optional[str] = None,
    limit: int = 100,
) -> List[QSO]:
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
