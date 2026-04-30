"""
DORA Metrics Database Models
Stores deployment events and computed DORA metric snapshots for
DevOps performance measurement (Deployment Frequency, Lead Time,
Change Failure Rate, Mean Time to Recovery).
"""

from sqlalchemy import Column, String, Integer, DateTime, Float, Date, BigInteger, Text
from datetime import datetime
import uuid

from .models import Base


class DeploymentEvent(Base):
    """
    Records individual deployment events captured from GitHub workflow_run webhooks.
    Each record represents a completed workflow run on a default branch,
    which constitutes a "deployment" in DORA terminology.
    """
    __tablename__ = "deployment_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_name = Column(String, nullable=False, index=True)
    repo_name = Column(String, nullable=False, index=True)
    repo_full_name = Column(String, nullable=False)

    # GitHub workflow run metadata
    workflow_run_id = Column(BigInteger, nullable=False)
    workflow_name = Column(String)
    run_number = Column(Integer)
    commit_sha = Column(String(40))
    branch = Column(String(255), nullable=False)
    trigger_event = Column(String(50))          # push, pull_request, schedule, etc.
    actor = Column(String(255))                 # GitHub username who triggered it

    # Outcome
    conclusion = Column(String(20), nullable=False)  # success, failure, cancelled, timed_out

    # Timestamps from GitHub
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)

    # For lead time calculation: when the PR was merged (if deployment was from a PR merge)
    pr_merged_at = Column(DateTime(timezone=True))

    # Record metadata
    created_at = Column(DateTime, default=datetime.utcnow)


class DORAMetricSnapshot(Base):
    """
    Stores pre-computed DORA metric snapshots for a given organisation
    over a specific time period. These snapshots power the trends charts
    and avoid recalculating metrics on every dashboard load.
    """
    __tablename__ = "dora_metric_snapshots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_name = Column(String, nullable=False, index=True)

    # Time period this snapshot covers
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    period_type = Column(String(10), nullable=False)  # daily, weekly, monthly

    # The 4 DORA metrics
    deployment_frequency = Column(Float)        # deployments per day
    lead_time_seconds = Column(Float)           # median lead time in seconds
    change_failure_rate = Column(Float)         # 0.0 to 1.0
    mttr_seconds = Column(Float)               # mean time to recovery in seconds

    # Classification based on Google DORA benchmarks
    classification = Column(String(10))         # elite, high, medium, low

    # Supporting counts
    total_deployments = Column(Integer, default=0)
    successful_deployments = Column(Integer, default=0)
    failed_deployments = Column(Integer, default=0)
    repos_measured = Column(Integer, default=0)

    # Computed at
    computed_at = Column(DateTime, default=datetime.utcnow)
