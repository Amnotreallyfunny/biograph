from sqlalchemy import Column, String, Float, Integer, ForeignKey, Text, JSON, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import uuid
import os

Base = declarative_base()

class Run(Base):
    __tablename__ = 'runs'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    status = Column(String, default='pending')
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    error_type = Column(String)
    suggested_fix = Column(Text)
    tasks = relationship("Task", back_populates="run")

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey('runs.id'))
    node_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    status = Column(String, default='pending') # pending, running, success, failed, suspicious
    command = Column(Text)
    stdout = Column(Text)
    stderr = Column(Text)
    exit_code = Column(Integer)
    
    # New Scientific Validation Fields
    validation_status = Column(String) # success, suspicious, failed
    validation_messages = Column(JSON) # List of strings
    
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration = Column(Float)

    run = relationship("Run", back_populates="tasks")

class QualityMetric(Base):
    __tablename__ = 'quality_metrics'
    id = Column(Integer, primary_key=True)
    task_id = Column(String, ForeignKey('tasks.id'))
    name = Column(String, nullable=False)
    value = Column(Float, nullable=False)

def init_db(db_url=None):
    if db_url is None:
        db_path = os.path.join(os.path.expanduser("~/biograph/backend"), "biograph_hardened.db")
        db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
