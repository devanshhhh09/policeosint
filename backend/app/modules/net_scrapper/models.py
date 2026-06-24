"""
Net Scrapper & Intelligence Hub — Database Models
New tables: scraped_sources, extracted_content, extracted_indicators
Does NOT modify any existing tables.
"""
import enum, uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    Enum, ForeignKey, JSON, DateTime, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from typing import Optional, List
from app.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────
class SourcePlatform(str, enum.Enum):
    TELEGRAM  = "telegram"
    TWITTER   = "twitter"
    INSTAGRAM = "instagram"
    DARK_WEB  = "dark_web"
    WEBSITE   = "website"

class SourceStatus(str, enum.Enum):
    ACTIVE   = "active"
    PAUSED   = "paused"
    ERROR    = "error"
    PENDING  = "pending"

class ContentCategory(str, enum.Enum):
    FAKE_JOB          = "fake_job"
    INVESTMENT_SCAM   = "investment_scam"
    CRYPTO_SCAM       = "crypto_scam"
    ILLEGAL_CONTENT   = "illegal_content"
    LEAKED_DATA       = "leaked_data"
    NORMAL            = "normal"
    UNCLASSIFIED      = "unclassified"

class IndicatorType(str, enum.Enum):
    PHONE_NUMBER = "phone_number"
    UPI_ID       = "upi_id"
    EMAIL        = "email"
    URL          = "url"
    CRYPTO_BTC   = "crypto_btc"
    CRYPTO_ETH   = "crypto_eth"
    USERNAME     = "username"
    TERABOX_LINK = "terabox_link"
    FILE_LINK    = "file_link"


# ── SQLAlchemy Models ──────────────────────────────────────────────────────────
class ScrapedSource(Base):
    """Monitored Telegram channels, Twitter accounts, Instagram profiles."""
    __tablename__ = "scraped_sources"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform      = Column(Enum(SourcePlatform), nullable=False, index=True)
    identifier    = Column(String(500), nullable=False)   # @channel, t.me/link, URL
    display_name  = Column(String(255), nullable=True)
    description   = Column(Text, nullable=True)
    status        = Column(Enum(SourceStatus), default=SourceStatus.PENDING)
    is_auto       = Column(Boolean, default=False)        # True = pre-configured
    added_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    last_scraped  = Column(DateTime(timezone=True), nullable=True)
    message_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    meta          = Column(JSON, default=dict)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    content    = relationship("ExtractedContent",   back_populates="source", cascade="all, delete-orphan")
    indicators = relationship("ExtractedIndicator", back_populates="source", cascade="all, delete-orphan")


class ExtractedContent(Base):
    """Individual messages/posts scraped from monitored sources."""
    __tablename__ = "extracted_content"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id     = Column(UUID(as_uuid=True), ForeignKey("scraped_sources.id"), nullable=False)
    platform      = Column(Enum(SourcePlatform), nullable=False, index=True)
    message_id    = Column(String(100), nullable=True)    # Platform-specific ID
    content_text  = Column(Text, nullable=True)
    content_type  = Column(String(50), default="text")    # text, image, video, document
    author        = Column(String(255), nullable=True)
    category      = Column(Enum(ContentCategory), default=ContentCategory.UNCLASSIFIED, index=True)
    risk_score    = Column(Float, default=0.0, index=True)
    is_flagged    = Column(Boolean, default=False, index=True)
    raw_data      = Column(JSON, nullable=True)
    scraped_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    platform_ts   = Column(DateTime(timezone=True), nullable=True)  # Original post time
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    source     = relationship("ScrapedSource",      back_populates="content")
    indicators = relationship("ExtractedIndicator", back_populates="content", cascade="all, delete-orphan")


class ExtractedIndicator(Base):
    """IOCs extracted from content: phone numbers, UPI IDs, wallet addresses, URLs."""
    __tablename__ = "extracted_indicators"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id      = Column(UUID(as_uuid=True), ForeignKey("scraped_sources.id"), nullable=False)
    content_id     = Column(UUID(as_uuid=True), ForeignKey("extracted_content.id"), nullable=True)
    indicator_type = Column(Enum(IndicatorType), nullable=False, index=True)
    value          = Column(String(1000), nullable=False, index=True)
    platform       = Column(Enum(SourcePlatform), nullable=False)
    risk_score     = Column(Float, default=0.0)
    is_verified    = Column(Boolean, default=False)
    context        = Column(Text, nullable=True)   # Surrounding text
    meta           = Column(JSON, default=dict)
    first_seen     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    occurrence_count = Column(Integer, default=1)
    created_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    source  = relationship("ScrapedSource",  back_populates="indicators")
    content = relationship("ExtractedContent", back_populates="indicators")


# ── Pydantic Schemas ───────────────────────────────────────────────────────────
class SourceCreate(BaseModel):
    platform:   SourcePlatform
    identifier: str
    display_name: Optional[str] = None
    description:  Optional[str] = None

class SourceResponse(BaseModel):
    id:            str
    platform:      SourcePlatform
    identifier:    str
    display_name:  Optional[str]
    status:        SourceStatus
    is_auto:       bool
    message_count: int
    last_scraped:  Optional[datetime]
    created_at:    datetime
    model_config = {"from_attributes": True}

class ContentResponse(BaseModel):
    id:           str
    source_id:    str
    platform:     SourcePlatform
    content_text: Optional[str]
    author:       Optional[str]
    category:     ContentCategory
    risk_score:   float
    is_flagged:   bool
    scraped_at:   datetime
    model_config = {"from_attributes": True}

class IndicatorResponse(BaseModel):
    id:               str
    indicator_type:   IndicatorType
    value:            str
    platform:         SourcePlatform
    risk_score:       float
    occurrence_count: int
    first_seen:       datetime
    model_config = {"from_attributes": True}

class ScraperStats(BaseModel):
    total_sources:    int
    active_sources:   int
    total_content:    int
    flagged_content:  int
    total_indicators: int
    high_risk_indicators: int
    by_platform:      dict
    by_category:      dict
