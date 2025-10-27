"""Database layer: SQLAlchemy models and helpers for matches.

This module uses DATABASE_URL env var. Defaults to in-memory SQLite for
local development/tests: "sqlite:///:memory:". For production use a
Postgres URL like: postgresql+psycopg2://user:pass@host:5432/dbname
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")


class Base(DeclarativeBase):
    pass


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scheduled_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self) -> Dict:
        return {"id": self.id, "title": self.title, "scheduled_time": self.scheduled_time}


engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Create tables (idempotent)."""
    Base.metadata.create_all(bind=engine)


def save_matches(matches: List[Dict]) -> int:
    """Upsert a list of normalized match dicts into the DB.

    Each match dict should have at least an "id" field. Returns number of saved rows.
    """
    saved = 0
    with SessionLocal() as session:
        for m in matches:
            mid = str(m.get("id") or m.get("match_id") or "")
            if not mid:
                continue
            inst = session.get(Match, mid)
            if inst is None:
                inst = Match(id=mid)
            inst.title = m.get("title")
            inst.scheduled_time = m.get("scheduled_time")
            # store raw JSON-ish string for debugging
            try:
                import json

                inst.raw = json.dumps(m)
            except Exception:
                inst.raw = str(m)
            session.add(inst)
            saved += 1
        session.commit()
    return saved


def get_matches(limit: int = 100) -> List[Dict]:
    with SessionLocal() as session:
        rows = session.query(Match).limit(limit).all()
        return [r.to_dict() for r in rows]
