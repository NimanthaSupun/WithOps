"""
Feature Engineering for Pipeline Prediction Service

Transforms raw workflow run data into a numerical feature vector (19 features)
that can be fed into the ML classifier.

Feature Vector Layout:
──────────────────────
 #  | Feature                  | Type       | Source
────┼──────────────────────────┼────────────┼──────────────────
 0  | hour_of_day              | int (0-23) | created_at
 1  | day_of_week              | int (0-6)  | created_at
 2  | is_weekend               | bool (0/1) | created_at
 3  | is_business_hours        | bool (0/1) | created_at
 4  | files_changed            | int        | commit data
 5  | additions                | int        | commit data
 6  | deletions                | int        | commit data
 7  | total_changes            | int        | additions + deletions
 8  | change_ratio             | float      | additions / max(deletions, 1)
 9  | branch_type              | int (0-4)  | head_branch
 10 | is_pull_request          | bool (0/1) | event
 11 | event_type               | int (0-3)  | event
 12 | workflow_name_encoded    | int        | workflow_name
 13 | author_total_runs        | int        | computed from history
 14 | author_failure_rate      | float      | computed from history
 15 | repo_failure_rate_7d     | float      | computed from history
 16 | avg_duration_last_10     | float      | computed from history
 17 | failures_last_24h        | int        | computed from history
 18 | commit_message_length    | int        | commit_message
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ============================================================================
# ENCODING MAPS
# ============================================================================

BRANCH_TYPE_MAP = {
    "main": 0,
    "master": 0,
    "develop": 1,
    "development": 1,
    "feature": 2,
    "bugfix": 2,
    "hotfix": 3,
    "release": 4,
}

EVENT_TYPE_MAP = {
    "push": 0,
    "pull_request": 1,
    "schedule": 2,
    "workflow_dispatch": 3,
}

FEATURE_NAMES = [
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "is_business_hours",
    "files_changed",
    "additions",
    "deletions",
    "total_changes",
    "change_ratio",
    "branch_type",
    "is_pull_request",
    "event_type",
    "workflow_name_encoded",
    "author_total_runs",
    "author_failure_rate",
    "repo_failure_rate_7d",
    "avg_duration_last_10",
    "failures_last_24h",
    "commit_message_length",
]


# ============================================================================
# FEATURE ENGINEER
# ============================================================================

class FeatureEngineer:
    """
    Transforms raw workflow run data into ML-ready feature vectors.
    
    Handles:
    - Temporal feature extraction
    - Code change metrics
    - Categorical encoding (branch type, event type, workflow)
    - Historical aggregations (author stats, repo stats, cascades)
    - Missing value imputation
    """

    def __init__(self):
        self.workflow_encoder: Dict[str, int] = {}
        self._next_workflow_id = 0

    def transform_dataset(self, runs: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Transform a full dataset of runs into feature matrix X and label vector y.

        Args:
            runs: List of workflow run dictionaries (from DB or synthetic generator)

        Returns:
            X: numpy array of shape (n_samples, 19) — feature matrix
            y: numpy array of shape (n_samples,) — labels (0=success, 1=failure)
            feature_names: list of feature column names
        """
        logger.info(f"🔧 Engineering features for {len(runs)} runs...")

        # Sort runs by created_at for proper historical feature computation
        sorted_runs = sorted(runs, key=lambda r: r["created_at"])

        # Filter out non-informative conclusions (cancelled, skipped)
        valid_conclusions = {"success", "failure", "timed_out"}
        filtered = [r for r in sorted_runs if r.get("conclusion") in valid_conclusions]

        if len(filtered) < len(sorted_runs):
            logger.info(f"   Filtered out {len(sorted_runs) - len(filtered)} "
                        f"cancelled/skipped runs")

        # Build the feature matrix row by row
        features = []
        labels = []

        for i, run in enumerate(filtered):
            # Get historical context (all previous runs)
            history = filtered[:i]

            # Extract feature vector
            feature_vec = self._extract_features(run, history)
            features.append(feature_vec)

            # Extract label
            label = 1 if run["conclusion"] in ("failure", "timed_out") else 0
            labels.append(label)

        X = np.array(features, dtype=np.float64)
        y = np.array(labels, dtype=np.int32)

        # Handle any NaN values
        X = np.nan_to_num(X, nan=0.0)

        logger.info(f"✅ Feature matrix: {X.shape[0]} samples × {X.shape[1]} features")
        logger.info(f"   Label distribution: {np.sum(y == 0)} success, {np.sum(y == 1)} failure")

        return X, y, FEATURE_NAMES

    def transform_single(self, run: Dict[str, Any],
                          history: Optional[List[Dict[str, Any]]] = None) -> np.ndarray:
        """
        Transform a single run into a feature vector for inference.

        Args:
            run: Single workflow run dictionary
            history: Optional historical runs for context (if not provided,
                     historical features default to 0)

        Returns:
            1D numpy array of 19 features
        """
        feature_vec = self._extract_features(run, history or [])
        return np.array(feature_vec, dtype=np.float64).reshape(1, -1)

    def _extract_features(self, run: Dict[str, Any],
                           history: List[Dict[str, Any]]) -> List[float]:
        """Extract the 19-feature vector from a single run + its history."""

        created_at = run.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        # ── Temporal Features ──
        hour = created_at.hour if created_at else 12
        day = created_at.weekday() if created_at else 2  # 0=Mon
        is_weekend = 1 if day >= 5 else 0
        is_business = 1 if (9 <= hour <= 17 and day < 5) else 0

        # ── Code Change Features ──
        files_changed = run.get("files_changed", 0) or 0
        additions = run.get("additions", 0) or 0
        deletions = run.get("deletions", 0) or 0
        total_changes = additions + deletions
        change_ratio = additions / max(deletions, 1)

        # ── Branch Type ──
        branch = (run.get("head_branch") or "other").lower()
        branch_type = self._encode_branch(branch)

        # ── Event Type ──
        event = (run.get("event") or "push").lower()
        is_pr = 1 if event == "pull_request" else 0
        event_type = EVENT_TYPE_MAP.get(event, 3)

        # ── Workflow Encoding ──
        workflow_name = run.get("workflow_name", "unknown")
        workflow_encoded = self._encode_workflow(workflow_name)

        # ── Historical / Aggregated Features ──
        author = run.get("actor_login", "unknown")
        repo = run.get("repo_name", "unknown")

        author_total, author_fail_rate = self._compute_author_stats(
            author, history
        )
        repo_fail_rate_7d = self._compute_repo_failure_rate_7d(
            repo, history, created_at
        )
        avg_duration = self._compute_avg_duration_last_n(
            repo, history, n=10
        )
        failures_24h = self._compute_failures_last_24h(
            repo, history, created_at
        )

        # ── Commit Message Length ──
        msg = run.get("commit_message") or ""
        msg_length = len(msg)

        return [
            hour,               # 0: hour_of_day
            day,                # 1: day_of_week
            is_weekend,         # 2: is_weekend
            is_business,        # 3: is_business_hours
            files_changed,      # 4: files_changed
            additions,          # 5: additions
            deletions,          # 6: deletions
            total_changes,      # 7: total_changes
            change_ratio,       # 8: change_ratio
            branch_type,        # 9: branch_type
            is_pr,              # 10: is_pull_request
            event_type,         # 11: event_type
            workflow_encoded,   # 12: workflow_name_encoded
            author_total,       # 13: author_total_runs
            author_fail_rate,   # 14: author_failure_rate
            repo_fail_rate_7d,  # 15: repo_failure_rate_7d
            avg_duration,       # 16: avg_duration_last_10
            failures_24h,       # 17: failures_last_24h
            msg_length,         # 18: commit_message_length
        ]

    # ════════════════════════════════════════════════════════════════════════
    # ENCODING HELPERS
    # ════════════════════════════════════════════════════════════════════════

    def _encode_branch(self, branch: str) -> int:
        """Encode branch name to integer category."""
        # Check exact match first
        if branch in BRANCH_TYPE_MAP:
            return BRANCH_TYPE_MAP[branch]
        # Check prefix match
        for prefix, code in BRANCH_TYPE_MAP.items():
            if branch.startswith(prefix):
                return code
        return 4  # "other"

    def _encode_workflow(self, workflow_name: str) -> int:
        """Label-encode workflow names (learned incrementally)."""
        if workflow_name not in self.workflow_encoder:
            self.workflow_encoder[workflow_name] = self._next_workflow_id
            self._next_workflow_id += 1
        return self.workflow_encoder[workflow_name]

    # ════════════════════════════════════════════════════════════════════════
    # HISTORICAL AGGREGATION HELPERS
    # ════════════════════════════════════════════════════════════════════════

    def _compute_author_stats(self, author: str,
                               history: List[Dict]) -> Tuple[int, float]:
        """
        Compute author's total runs and failure rate from history.
        Returns (total_runs, failure_rate).
        """
        author_runs = [r for r in history if r.get("actor_login") == author]
        total = len(author_runs)
        if total == 0:
            return 0, 0.0

        failures = sum(1 for r in author_runs
                       if r.get("conclusion") in ("failure", "timed_out"))
        return total, failures / total

    def _compute_repo_failure_rate_7d(self, repo: str,
                                       history: List[Dict],
                                       current_time: datetime) -> float:
        """Compute repo-wide failure rate in the last 7 days."""
        if not current_time:
            return 0.0

        cutoff = current_time - timedelta(days=7)
        recent = [r for r in history
                  if r.get("repo_name") == repo
                  and r.get("created_at") and r["created_at"] > cutoff]

        if len(recent) == 0:
            return 0.0

        failures = sum(1 for r in recent
                       if r.get("conclusion") in ("failure", "timed_out"))
        return failures / len(recent)

    def _compute_avg_duration_last_n(self, repo: str,
                                      history: List[Dict],
                                      n: int = 10) -> float:
        """Compute average duration of last N completed runs for this repo."""
        repo_runs = [r for r in history
                     if r.get("repo_name") == repo
                     and r.get("duration_seconds") is not None
                     and r.get("status") == "completed"]

        if len(repo_runs) == 0:
            return 0.0

        last_n = repo_runs[-n:]
        durations = [r["duration_seconds"] for r in last_n]
        return sum(durations) / len(durations)

    def _compute_failures_last_24h(self, repo: str,
                                    history: List[Dict],
                                    current_time: datetime) -> int:
        """Count failures in the last 24 hours for this repo."""
        if not current_time:
            return 0

        cutoff = current_time - timedelta(hours=24)
        failures = sum(
            1 for r in history
            if r.get("repo_name") == repo
            and r.get("conclusion") in ("failure", "timed_out")
            and r.get("created_at") and r["created_at"] > cutoff
        )
        return failures


# Global instance
feature_engineer = FeatureEngineer()
