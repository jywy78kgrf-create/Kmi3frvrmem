"""
Loam - Persistent Substrate for AI Cognition
Database Models
"""
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import json

Base = declarative_base()
engine = create_engine("sqlite:///loam.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class TaskStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class TaskPriority(int, PyEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    reasoning_style = Column(String(100), default="analytical")  # analytical, creative, skeptical, exploratory
    deadline = Column(DateTime, nullable=True)
    
    # Task configuration
    task_type = Column(String(50), default="research")  # research, code, analysis, synthesis, prediction
    parameters = Column(JSON, default=dict)  # Flexible task-specific config
    
    # Results
    result = Column(Text)
    result_summary = Column(Text)
    confidence_score = Column(Float, nullable=True)
    
    # Execution tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0)
    error_log = Column(Text)
    
    # Relationships
    memories = relationship("Memory", back_populates="task")
    predictions = relationship("Prediction", back_populates="task")

class Memory(Base):
    __tablename__ = "memories"
    
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    category = Column(String(100), default="insight")  # insight, fact, pattern, failure, hypothesis
    tags = Column(JSON, default=list)
    
    # Source tracking
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    source_url = Column(String(1000), nullable=True)
    source_type = Column(String(50), default="task")  # task, observation, reading, reflection
    
    # Quality metrics
    confidence = Column(Float, default=0.5)
    verified = Column(Integer, default=0)  # 0=unverified, 1=verified, -1=disproven
    
    # Graph connections (stored as JSON list of memory IDs)
    related_memories = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    task = relationship("Task", back_populates="memories")

class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True)
    statement = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    category = Column(String(100), default="general")
    
    # Resolution
    resolved = Column(Integer, default=0)  # 0=open, 1=resolved
    resolution = Column(String(50), nullable=True)  # correct, incorrect, ambiguous, expired
    resolved_at = Column(DateTime, nullable=True)
    actual_outcome = Column(Text, nullable=True)
    brier_score = Column(Float, nullable=True)  # (confidence - outcome)^2
    
    # Source
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    deadline = Column(DateTime, nullable=True)  # When should this be evaluated?
    
    task = relationship("Task", back_populates="predictions")

class Digest(Base):
    __tablename__ = "digests"
    
    id = Column(Integer, primary_key=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    content = Column(Text, nullable=False)
    
    # Stats for the period
    tasks_completed = Column(Integer, default=0)
    tasks_failed = Column(Integer, default=0)
    new_memories = Column(Integer, default=0)
    predictions_resolved = Column(Integer, default=0)
    avg_confidence = Column(Float, nullable=True)
    
    # Key highlights (JSON list)
    highlights = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    read = Column(Integer, default=0)  # 0=unread, 1=read

class WorkerLog(Base):
    __tablename__ = "worker_logs"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    level = Column(String(20), default="info")  # debug, info, warning, error
    message = Column(Text, nullable=False)
    log_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
