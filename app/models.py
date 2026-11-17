"""Database tables (same shape as the original Prisma schema)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def new_id() -> str:
    return uuid.uuid4().hex


def now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    startups: Mapped[list["Startup"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Startup(Base):
    __tablename__ = "startups"
    __table_args__ = (Index("ix_startups_public_created", "is_public", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_idea: Mapped[str] = mapped_column(Text)
    startup_name: Mapped[str] = mapped_column(String(200))
    tagline: Mapped[str] = mapped_column(String(300))
    elevator_pitch: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), default="General")
    generated_data: Mapped[dict] = mapped_column(JSON)  # the full plan as JSON
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    user: Mapped[User] = relationship(back_populates="startups")
