"""
Database models for Pipeline Prediction Service
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, Float, BigInteger, Index
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models in this service."""
    pass

class WorkflowRunHistory(Base):
    """Stores raw workflow run data collected from GitHub"""
    __tablename__ = "workflow_run_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, nullable=False)
    org_name = Column(String, nullable=False, index=True)
    repo_name = Column(String, nullable=False, index=True)
    repo_full_name = Column(String, nullable=False)
    
    # GitHub run metadata
    github_run_id = Column(BigInteger, unique=True, nullable=False, index=True)
    workflow_name = Column(String, nullable=False)
    workflow_path = Column(String)
    run_number = Column(Integer)
    event = Column(String)  # push, pull_request, schedule, etc.
    status = Column(String)  # completed, in_progress, queued
    conclusion = Column(String)  # success, failure, cancelled, timed_out
    
    # Temporal features
    created_at = Column(DateTime, nullable=False, index=True)
    updated_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer) # Computed: completed_at - started_at
    
    # Commit metadata
    head_branch = Column(String)
    head_sha = Column(String)
    commit_message = Column(Text)
    
    # Author info
    actor_login = Column(String, index=True)
    actor_id = Column(Integer)
    
    # Code change metrics (fetched from commit)
    files_changed = Column(Integer, default=0)
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    
    # Collection metadata
    collected_at = Column(DateTime, default=datetime.utcnow)
    features_json = Column(JSON) # Pre-computed feature vector (cached)

    __table_args__ = (
        Index('idx_wfr_org_repo', 'org_name', 'repo_name'),
        Index('idx_wfr_created_desc', created_at.desc()),
    )


class MLModelRegistry(Base):
    """Stores trained model metadata and performance metrics"""
    __tablename__ = "ml_model_registry"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_name = Column(String, nullable=False, index=True)
    model_version = Column(Integer, nullable=False)
    model_type = Column(String, nullable=False) # random_forest, xgboost, gradient_boosting
    
    # Training metadata
    trained_at = Column(DateTime, default=datetime.utcnow)
    training_samples = Column(Integer)
    feature_count = Column(Integer)
    feature_names = Column(JSON) # List of feature column names
    
    # Performance metrics
    accuracy = Column(Float)
    precision_score = Column(Float)
    recall_score = Column(Float)
    f1_score = Column(Float)
    auc_roc = Column(Float)
    confusion_matrix = Column(JSON) # [[TP, FP], [FN, TN]]
    
    # Feature importance
    feature_importance = Column(JSON) # {feature_name: importance_score}
    
    # Model file
    model_path = Column(String) # Path to .joblib file
    is_active = Column(Boolean, default=True)
    
    # Class distribution in training data
    class_distribution = Column(JSON) # {success: N, failure: M}

    def __repr__(self):
        return f"<MLModelRegistry(org={self.org_name}, version={self.model_version}, type={self.model_type})>"


class PredictionHistory(Base):
    """Stores prediction history for auditing and feedback loops"""
    __tablename__ = "prediction_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_name = Column(String, nullable=False, index=True)
    repo_name = Column(String, nullable=False, index=True)
    branch = Column(String)
    commit_sha = Column(String)
    author = Column(String)
    
    # Prediction result
    failure_probability = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False) # low, medium, high, critical
    risk_factors = Column(JSON)
    recommendation = Column(Text)
    
    # Model used
    model_version = Column(Integer)
    model_type = Column(String)
    
    # Actual outcome (filled in later when run completes)
    actual_conclusion = Column(String) # success, failure, null (pending)
    prediction_correct = Column(Boolean) # Computed after actual is known
    
    # Timestamps
    predicted_at = Column(DateTime, default=datetime.utcnow, index=True)
    actual_completed_at = Column(DateTime)
