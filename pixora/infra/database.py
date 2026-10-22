"""PostgreSQL async database layer — replaces all in-memory stores.

SQLite for dev (zero config), PostgreSQL for production.
Set PIXORA_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/pixora
"""
from __future__ import annotations
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, JSON, func
from datetime import datetime

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class UserDB(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), default="")
    name: Mapped[str] = mapped_column(String(255), default="")
    google_id: Mapped[str] = mapped_column(String(255), default="", index=True)
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class TenantDB(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(50), default="free_trial")
    docs_used: Mapped[int] = mapped_column(Integer, default=0)
    docs_limit: Mapped[int] = mapped_column(Integer, default=50)
    billing_email: Mapped[str] = mapped_column(String(255), default="")
    stripe_customer_id: Mapped[str] = mapped_column(String(255), default="")
    stripe_subscription_id: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TenantMemberDB(Base):
    __tablename__ = "tenant_members"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    role: Mapped[str] = mapped_column(String(20), default="admin")
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DocumentJobDB(Base):
    __tablename__ = "document_jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[str] = mapped_column(String(32), default="")
    filename: Mapped[str] = mapped_column(String(500))
    doc_type: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    tier: Mapped[str] = mapped_column(String(20), default="agentic")
    extraction: Mapped[dict] = mapped_column(JSON, default=dict)
    markdown: Mapped[str] = mapped_column(Text, default="")
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    grounding_rate: Mapped[float] = mapped_column(Float, default=0.0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    engine_used: Mapped[str] = mapped_column(String(50), default="")
    file_s3_key: Mapped[str] = mapped_column(String(500), default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class APIKeyDB(Base):
    __tablename__ = "api_keys"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(32), index=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    prefix: Mapped[str] = mapped_column(String(10), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_used: Mapped[datetime] = mapped_column(DateTime, nullable=True)


_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        from pixora.config.settings import settings
        url = settings.database_url
        if url.startswith("sqlite"):
            _engine = create_async_engine(url, echo=False)
        else:
            _engine = create_async_engine(url, echo=False, pool_size=10, max_overflow=20)
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")
