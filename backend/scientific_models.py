from sqlalchemy import Column, String, Float, Integer, ForeignKey, Text, JSON, DateTime, Boolean, Enum, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import uuid
import enum

Base = declarative_base()

class IOType(enum.Enum):
    INPUT = "input"
    OUTPUT = "output"

class FileRecord(Base):
    __tablename__ = 'file_records'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    path = Column(String, nullable=False)
    sha256_hash = Column(String(64), unique=True, nullable=False, index=True)
    size_bytes = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    task_associations = relationship("TaskIO", back_populates="file")

class Project(Base):
    __tablename__ = 'projects'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    samples = relationship("Sample", back_populates="project")

class Sample(Base):
    __tablename__ = 'samples'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey('projects.id'), index=True)
    name = Column(String, nullable=False)
    condition = Column(String) # e.g., Tumor, Normal, Wild-type
    biological_source = Column(String) # e.g., Blood, Tissue
    metadata_json = Column(JSON) # Extended biological metadata

    project = relationship("Project", back_populates="samples")
    runs = relationship("WorkflowRun", back_populates="sample")

class ReferenceGenome(Base):
    __tablename__ = 'reference_genomes'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False) # e.g., hg38
    version = Column(String, nullable=False)
    fasta_hash = Column(String(64), unique=True)

class SoftwareEnvironment(Base):
    __tablename__ = 'software_environments'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tool_name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    conda_env_yaml = Column(Text)

class WorkflowRun(Base):
    __tablename__ = 'workflow_runs'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sample_id = Column(String, ForeignKey('samples.id'), index=True)
    name = Column(String)
    status = Column(String)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)

    sample = relationship("Sample", back_populates="runs")
    tasks = relationship("ScientificTask", back_populates="run")

class ScientificTask(Base):
    __tablename__ = 'scientific_tasks'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey('workflow_runs.id'), index=True)
    software_env_id = Column(String, ForeignKey('software_environments.id'))
    ref_genome_id = Column(String, ForeignKey('reference_genomes.id'), nullable=True)
    
    node_id = Column(String, nullable=False)
    name = Column(String)
    status = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration = Column(Float)

    run = relationship("WorkflowRun", back_populates="tasks")
    io_records = relationship("TaskIO", back_populates="task")
    quality_metrics = relationship("QualityMetric", back_populates="task")
    quality_distributions = relationship("QualityDistribution", back_populates="task")

class TaskIO(Base):
    __tablename__ = 'task_io'
    id = Column(Integer, primary_key=True)
    task_id = Column(String, ForeignKey('scientific_tasks.id'), index=True)
    file_id = Column(String, ForeignKey('file_records.id'), index=True)
    io_type = Column(Enum(IOType), nullable=False) # input or output

    task = relationship("ScientificTask", back_populates="io_records")
    file = relationship("FileRecord", back_populates="task_associations")

class QualityMetric(Base):
    __tablename__ = 'quality_metrics'
    id = Column(Integer, primary_key=True)
    task_id = Column(String, ForeignKey('scientific_tasks.id'), index=True)
    metric_name = Column(String, nullable=False) # e.g., mapping_rate, mean_coverage
    value = Column(Float, nullable=False)

    task = relationship("ScientificTask", back_populates="quality_metrics")

class QualityDistribution(Base):
    __tablename__ = 'quality_distributions'
    id = Column(Integer, primary_key=True)
    task_id = Column(String, ForeignKey('scientific_tasks.id'), index=True)
    name = Column(String, nullable=False) # e.g., phred_score_distribution
    data = Column(JSON, nullable=False) # JSON array of values or histograms

    task = relationship("ScientificTask", back_populates="quality_distributions")

# Database Initialization Helper
def setup_scientific_db(db_url="sqlite:///biograph_science.db"):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
