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


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    game: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "game": self.game,
            "start_date": self.start_date,
            "end_date": self.end_date,
        }


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    short_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    roster_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self) -> Dict:
        return {"id": self.id, "name": self.name, "short_name": self.short_name}


class Player(Base):
    __tablename__ = "players"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    gamertag: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    team_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stats: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "gamertag": self.gamertag,
            "team_id": self.team_id,
            "role": self.role,
        }


class TrackedSelection(Base):
    __tablename__ = "tracked_selection"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    team: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    def to_dict(self) -> Dict:
        return {"id": self.id, "match_id": self.match_id, "team": self.team}


engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Create tables (idempotent)."""
    Base.metadata.create_all(bind=engine)


def get_tracked_selection() -> Dict:
    """Return the latest tracked selection row as a dict, or an empty dict."""
    with SessionLocal() as session:
        row = session.query(TrackedSelection).order_by(TrackedSelection.id.desc()).first()
        if not row:
            return {}
        return row.to_dict()


def set_tracked_selection(match_id: Optional[str], team: Optional[str]) -> Dict:
    """Persist a new tracked selection and return it."""
    with SessionLocal() as session:
        inst = TrackedSelection(match_id=str(match_id) if match_id else None, team=team)
        session.add(inst)
        session.commit()
        session.refresh(inst)
        return inst.to_dict()


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
