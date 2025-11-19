"""Database models and connection setup."""

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    BigInteger,
    Boolean,
    TIMESTAMP,
    Float,
    Time,
    LargeBinary,
    ForeignKey,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from datetime import datetime
from app.config import settings

# SQLAlchemy setup
engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class MediaQueue(Base):
    """Media queue table for remote and local media playback."""

    __tablename__ = "media_queue"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(Text, nullable=True)
    local_path = Column(Text, nullable=True)
    title = Column(Text, nullable=False)
    thumbnail_url = Column(Text, nullable=True)
    media_type = Column(String(20), nullable=False)  # 'video', 'audio', 'photo'
    duration = Column(Integer, nullable=True)  # seconds
    file_size = Column(BigInteger, nullable=True)  # bytes
    queued_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    played_at = Column(TIMESTAMP, nullable=True)
    status = Column(String(20), default="queued")  # 'queued', 'playing', 'played', 'error'
    source = Column(String(20), default="remote")  # 'remote', 'local'


class MediaLibrary(Base):
    """Local media library table."""

    __tablename__ = "media_library"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(Text, unique=True, nullable=False)
    filename = Column(Text, nullable=False)
    media_type = Column(String(20), nullable=False)  # 'video', 'audio', 'photo'
    duration = Column(Integer, nullable=True)  # seconds
    resolution = Column(String(20), nullable=True)  # e.g., '1920x1080'
    file_size = Column(BigInteger, nullable=True)  # bytes
    thumbnail_path = Column(Text, nullable=True)
    added_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    last_played = Column(TIMESTAMP, nullable=True)
    play_count = Column(Integer, default=0)


class Settings(Base):
    """Application settings table."""

    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSONB, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class CalendarEvent(Base):
    """Cached calendar events."""

    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(255), unique=True, nullable=False)
    summary = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=False)
    all_day = Column(Boolean, default=False)
    location = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class VoiceCommand(Base):
    """Voice command history and processing."""

    __tablename__ = "voice_commands"

    id = Column(Integer, primary_key=True, index=True)
    transcript = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True)
    response = Column(Text, nullable=True)
    confidence = Column(Integer, nullable=True)  # 0-100
    processed_at = Column(TIMESTAMP, default=datetime.utcnow)
    duration_ms = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)


class Alarm(Base):
    """Alarms and timers."""

    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False)  # 'alarm' or 'timer'
    time = Column(TIMESTAMP, nullable=False)
    duration = Column(Integer, nullable=True)  # for timers, in seconds
    label = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    repeat_days = Column(String(20), nullable=True)  # e.g., 'MON,WED,FRI'
    sound_file = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class Person(Base):
    """Person profiles for face recognition and personalization."""

    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    face_encoding = Column(LargeBinary, nullable=True)  # Serialized numpy array
    photo_samples = Column(ARRAY(Text), nullable=True)  # Paths to training images
    greeting_morning = Column(Text, nullable=True)
    greeting_afternoon = Column(Text, nullable=True)
    greeting_evening = Column(Text, nullable=True)
    typical_wake_time = Column(Time, nullable=True)
    typical_bed_time = Column(Time, nullable=True)
    preferences = Column(JSONB, nullable=True)  # Custom settings per person
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationship to detections
    detections = relationship("Detection", back_populates="person")


class Detection(Base):
    """Face detection log."""

    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    detected_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    confidence = Column(Float, nullable=True)
    first_of_day = Column(Boolean, default=False)
    greeted = Column(Boolean, default=False)

    # Relationship to person
    person = relationship("Person", back_populates="detections")


class APIIntegration(Base):
    """API integration configurations."""

    __tablename__ = "api_integrations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    method = Column(String(10), default="GET")
    headers = Column(JSONB, nullable=True)
    auth_type = Column(String(20), nullable=True)  # 'none', 'api_key', 'bearer', 'basic'
    auth_credentials = Column(JSONB, nullable=True)
    schedule_interval = Column(Integer, nullable=True)  # Seconds between calls
    data_mapping = Column(JSONB, nullable=True)  # JSON paths to extract fields
    enabled = Column(Boolean, default=True)
    last_run = Column(TIMESTAMP, nullable=True)
    next_run = Column(TIMESTAMP, nullable=True)
    last_response = Column(JSONB, nullable=True)
    error_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationship to data history
    history = relationship("APIDataHistory", back_populates="api_integration")


class APIDataHistory(Base):
    """Historical API response data."""

    __tablename__ = "api_data_history"

    id = Column(Integer, primary_key=True, index=True)
    api_id = Column(Integer, ForeignKey("api_integrations.id"), nullable=False)
    response_data = Column(JSONB, nullable=False)
    fetched_at = Column(TIMESTAMP, default=datetime.utcnow)
    response_time_ms = Column(Integer, nullable=True)
    status_code = Column(Integer, nullable=True)

    # Relationship to API integration
    api_integration = relationship("APIIntegration", back_populates="history")


class ResponseRule(Base):
    """Custom automation rules."""

    __tablename__ = "response_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    trigger_type = Column(String(50), nullable=False)  # 'person', 'time', 'data', 'manual'
    trigger_config = Column(JSONB, nullable=False)
    conditions = Column(ARRAY(JSONB), nullable=True)  # Array of condition objects
    actions = Column(ARRAY(JSONB), nullable=False)  # Array of action objects
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    last_triggered = Column(TIMESTAMP, nullable=True)
    trigger_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationship to executions
    executions = relationship("RuleExecution", back_populates="rule")


class RuleExecution(Base):
    """Rule execution history."""

    __tablename__ = "rule_executions"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("response_rules.id"), nullable=False)
    executed_at = Column(TIMESTAMP, default=datetime.utcnow)
    trigger_data = Column(JSONB, nullable=True)
    actions_completed = Column(JSONB, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # Relationship to rule
    rule = relationship("ResponseRule", back_populates="executions")


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


def drop_db():
    """Drop all database tables (use with caution!)."""
    Base.metadata.drop_all(bind=engine)
    print("Database tables dropped!")
