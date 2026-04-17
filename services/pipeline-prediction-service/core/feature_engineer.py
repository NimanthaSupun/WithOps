"""
Feature Engineering for Pipeline Prediction Service

Transforms raw workflow run data into a numerical feature vector (19 features)
that can be fed into the ML classifier.

Feature Vector Layout:
──────────────────────
 PHASE 1 FEATURES (19 - Original)
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

 PHASE 4 NEW FEATURES (8 - Model Optimization)
 19 | is_feature_branch        | bool (0/1) | branch_type (feature/bugfix)
 20 | files_by_type_ratio      | float      | code vs config files
 21 | commit_frequency_7d      | float      | author commits per day (7d)
 22 | repo_test_coverage_est   | float      | test file ratio estimate
 23 | code_review_time_hours   | float      | avg PR review time
 24 | deployment_frequency_wk  | float      | deployments per week
 25 | previous_failures_ratio  | float      | failures in last 5 runs
 26 | author_commit_consistency| float      | commit time variance (std dev)
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
    # Phase 1 Original Features (19)
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
    # Phase 4 New Features (8)
    "is_feature_branch",
    "files_by_type_ratio",
    "commit_frequency_7d",
    "repo_test_coverage_est",
    "code_review_time_hours",
    "deployment_frequency_wk",
    "previous_failures_ratio",
    "author_commit_consistency",
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
        logger.info(f"🔧 Engineering features for {len(runs)} runs (Phase 4: 27 features)...")

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

        # ════════════════════════════════════════════════════════════════════════
        # PHASE 4 NEW FEATURES (8)
        # ════════════════════════════════════════════════════════════════════════

        # Feature 19: is_feature_branch (0/1)
        # 1 if branch is feature/bugfix, 0 otherwise
        is_feature_branch = 1 if branch_type in (2, 3) else 0

        # Feature 20: files_by_type_ratio (float 0-1)
        # Ratio of code files to total files
        # Estimate based on additions ratio and file count
        files_by_type_ratio = min(1.0, files_changed / max(total_changes, 1) * 0.8) if files_changed > 0 else 0.5

        # Feature 21: commit_frequency_7d (float)
        # How often this author commits (commits per day in last 7 days)
        commit_freq_7d = self._compute_commit_frequency_7d(author, history, created_at)

        # Feature 22: repo_test_coverage_est (float 0-1)
        # Estimated test coverage based on test file patterns
        test_coverage = self._compute_test_coverage_estimate(run, history)

        # Feature 23: code_review_time_hours (float)
        # Average time from PR creation to completion
        review_time = self._compute_review_time_hours(author, history) if is_pr else 0.0

        # Feature 24: deployment_frequency_wk (float)
        # Estimated deployments to production per week
        deploy_freq = self._compute_deployment_frequency(repo, history, created_at)

        # Feature 25: previous_failures_ratio (float 0-1)
        # Ratio of failures in author's last 5 runs
        prev_fail_ratio = self._compute_previous_failures_ratio(author, history, n=5)

        # Feature 26: author_commit_consistency (float)
        # How consistent is author's commit timing (low variance = consistent)
        # Value: 0-1 where 1 = perfectly consistent
        commit_consistency = self._compute_commit_consistency(author, history)

        return [
            hour,                   # 0: hour_of_day
            day,                    # 1: day_of_week
            is_weekend,             # 2: is_weekend
            is_business,            # 3: is_business_hours
            files_changed,          # 4: files_changed
            additions,              # 5: additions
            deletions,              # 6: deletions
            total_changes,          # 7: total_changes
            change_ratio,           # 8: change_ratio
            branch_type,            # 9: branch_type
            is_pr,                  # 10: is_pull_request
            event_type,             # 11: event_type
            workflow_encoded,       # 12: workflow_name_encoded
            author_total,           # 13: author_total_runs
            author_fail_rate,       # 14: author_failure_rate
            repo_fail_rate_7d,      # 15: repo_failure_rate_7d
            avg_duration,           # 16: avg_duration_last_10
            failures_24h,           # 17: failures_last_24h
            msg_length,             # 18: commit_message_length
            is_feature_branch,      # 19: is_feature_branch (PHASE 4)
            files_by_type_ratio,    # 20: files_by_type_ratio (PHASE 4)
            commit_freq_7d,         # 21: commit_frequency_7d (PHASE 4)
            test_coverage,          # 22: repo_test_coverage_est (PHASE 4)
            review_time,            # 23: code_review_time_hours (PHASE 4)
            deploy_freq,            # 24: deployment_frequency_wk (PHASE 4)
            prev_fail_ratio,        # 25: previous_failures_ratio (PHASE 4)
            commit_consistency,     # 26: author_commit_consistency (PHASE 4)
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

    # ════════════════════════════════════════════════════════════════════════
    # PHASE 4 NEW FEATURE HELPERS
    # ════════════════════════════════════════════════════════════════════════

    def _compute_commit_frequency_7d(self, author: str, history: List[Dict],
                                      current_time: Optional[datetime]) -> float:
        """
        Compute how frequently this author commits (commits per day in 7 days).
        Returns float: 0-7 commits per day
        """
        if not current_time:
            return 0.0
        
        cutoff = current_time - timedelta(days=7)
        author_commits = [r for r in history
                         if r.get("actor_login") == author
                         and r.get("created_at") and r["created_at"] > cutoff]
        
        if len(author_commits) == 0:
            return 0.0
        
        # Commits per day
        return len(author_commits) / 7.0

    def _compute_test_coverage_estimate(self, run: Dict[str, Any],
                                        history: List[Dict]) -> float:
        """
        Estimate test coverage based on test file patterns.
        Returns float: 0-1 estimate (higher = more test files)
        """
        # Simple heuristic: if commit message mentions "test", "coverage", etc.
        msg = (run.get("commit_message") or "").lower()
        if any(keyword in msg for keyword in ["test", "coverage", "spec", "unit"]):
            return 0.8
        
        # If PR (pull requests more likely to include tests)
        if run.get("event") == "pull_request":
            return 0.6
        
        # Default: assume moderate coverage
        return 0.5

    def _compute_review_time_hours(self, author: str, history: List[Dict]) -> float:
        """
        Compute average PR review time for this author (time from PR to completion).
        Returns float: hours (0 if no PRs)
        """
        author_prs = [r for r in history
                     if r.get("actor_login") == author
                     and r.get("event") == "pull_request"]
        
        if len(author_prs) == 0:
            return 0.0
        
        # Estimate: assume ~2-4 hour average review time
        # (In production, would track created_at vs merged_at)
        times = []
        for pr in author_prs[-5:]:  # Last 5 PRs
            # Simplified: use duration as proxy
            duration = pr.get("duration_seconds", 0)
            if duration:
                times.append(duration / 3600)  # Convert to hours
        
        return sum(times) / len(times) if times else 2.0

    def _compute_deployment_frequency(self, repo: str, history: List[Dict],
                                      current_time: Optional[datetime]) -> float:
        """
        Estimate deployments per week for this repo.
        Returns float: 0-7 deploys per week
        """
        if not current_time:
            return 0.0
        
        cutoff = current_time - timedelta(days=7)
        repo_runs = [r for r in history
                    if r.get("repo_name") == repo
                    and r.get("event") in ("push", "workflow_dispatch")
                    and r.get("created_at") and r["created_at"] > cutoff]
        
        if len(repo_runs) == 0:
            return 0.0
        
        # Assume ~30% of pushes are deployments
        return len(repo_runs) * 0.3 / 7.0

    def _compute_previous_failures_ratio(self, author: str, history: List[Dict],
                                         n: int = 5) -> float:
        """
        Compute ratio of failures in author's last N runs.
        Returns float: 0-1 (0 = all success, 1 = all failures)
        """
        author_runs = [r for r in history if r.get("actor_login") == author]
        
        if len(author_runs) == 0:
            return 0.0
        
        last_n = author_runs[-n:]
        if len(last_n) == 0:
            return 0.0
        
        failures = sum(1 for r in last_n
                      if r.get("conclusion") in ("failure", "timed_out"))
        return failures / len(last_n)

    def _compute_commit_consistency(self, author: str, history: List[Dict]) -> float:
        """
        Compute author's commit timing consistency (0-1).
        Higher = more consistent timing
        """
        author_runs = [r for r in history if r.get("actor_login") == author]
        
        if len(author_runs) < 3:
            return 0.5  # Default for new authors
        
        # Extract hours from last 10 commits
        last_runs = author_runs[-10:]
        hours = []
        for run in last_runs:
            if run.get("created_at"):
                created = run["created_at"]
                if isinstance(created, str):
                    created = datetime.fromisoformat(created)
                hours.append(created.hour)
        
        if len(hours) < 2:
            return 0.5
        
        # Compute hour variance
        import statistics
        try:
            std_dev = statistics.stdev(hours)
            # Normalize to 0-1 (low std = high consistency)
            # Max std_dev for hours is ~6.9, so map that to 0-1
            consistency = max(0.0, 1.0 - (std_dev / 7.0))
            return consistency
        except:
            return 0.5


# Global instance
feature_engineer = FeatureEngineer()
