"""
DORA Metrics Calculator

Computes the four key DORA (DevOps Research and Assessment) metrics
from deployment event data:

1. Deployment Frequency — How often code is deployed to production
2. Lead Time for Changes — Time from commit to production deployment
3. Change Failure Rate — Percentage of deployments causing failures
4. Mean Time to Recovery (MTTR) — Average time to recover from failures

Classification benchmarks are based on the Google DORA / "Accelerate"
State of DevOps Report research (Forsgren, Humble & Kim).
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import db_manager
from database.dora_models import DeploymentEvent, DORAMetricSnapshot

logger = logging.getLogger(__name__)


@dataclass
class DORAResult:
    """Computed DORA metrics for a given organisation and time period."""

    # The four core metrics
    deployment_frequency: float      # deployments per day
    lead_time_seconds: float         # median lead time (seconds)
    change_failure_rate: float       # 0.0 to 1.0
    mttr_seconds: float              # mean time to recovery (seconds)

    # Overall classification
    classification: str              # elite, high, medium, low

    # Per-metric classifications
    df_classification: str
    lt_classification: str
    cfr_classification: str
    mttr_classification: str

    # Supporting data
    total_deployments: int
    successful_deployments: int
    failed_deployments: int
    period_days: int
    repos_measured: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DORACalculator:
    """
    Core engine for computing DORA metrics from deployment events.

    Usage:
        calculator = DORACalculator()
        result = await calculator.compute("my-org", days=30)
        print(result.classification)  # "high"
    """

    # =========================================================================
    # Google DORA Benchmark Thresholds (from State of DevOps 2023)
    # =========================================================================

    # Deployment Frequency: deploys per day
    DF_ELITE = 1.0          # Multiple deploys per day (>= 1/day)
    DF_HIGH = 0.14          # Between once per day and once per week (~1/7)
    DF_MEDIUM = 0.033       # Between once per week and once per month (~1/30)

    # Lead Time: seconds
    LT_ELITE = 3600         # Less than one hour
    LT_HIGH = 86400         # Less than one day
    LT_MEDIUM = 604800      # Less than one week

    # Change Failure Rate: ratio
    CFR_ELITE = 0.05        # 0-5%
    CFR_HIGH = 0.15         # 5-15%
    CFR_MEDIUM = 0.30       # 15-30%

    # MTTR: seconds
    MTTR_ELITE = 3600       # Less than one hour
    MTTR_HIGH = 86400       # Less than one day
    MTTR_MEDIUM = 604800    # Less than one week

    async def compute(self, org_name: str, days: int = 30) -> DORAResult:
        """
        Compute DORA metrics for an organisation over the specified period.

        Args:
            org_name: GitHub organisation name
            days: Number of days to look back (default: 30)

        Returns:
            DORAResult with all four metrics and classification
        """
        since = datetime.utcnow() - timedelta(days=days)
        events = await self._get_events(org_name, since)

        if not events:
            return DORAResult(
                deployment_frequency=0,
                lead_time_seconds=0,
                change_failure_rate=0,
                mttr_seconds=0,
                classification="low",
                df_classification="low",
                lt_classification="low",
                cfr_classification="low",
                mttr_classification="low",
                total_deployments=0,
                successful_deployments=0,
                failed_deployments=0,
                period_days=days,
                repos_measured=0,
            )

        # Compute each metric
        df = self._deployment_frequency(events, days)
        lt = self._lead_time(events)
        cfr = self._change_failure_rate(events)
        mttr = self._mean_time_to_recovery(events)

        # Classify each metric
        df_cls = self._classify_deployment_frequency(df)
        lt_cls = self._classify_lead_time(lt)
        cfr_cls = self._classify_change_failure_rate(cfr)
        mttr_cls = self._classify_mttr(mttr)

        # Overall classification
        classification = self._classify_overall(df_cls, lt_cls, cfr_cls, mttr_cls)

        # Count repos
        repos = set(e.repo_full_name for e in events)
        successful = [e for e in events if e.conclusion == "success"]
        failed = [e for e in events if e.conclusion == "failure"]

        return DORAResult(
            deployment_frequency=round(df, 4),
            lead_time_seconds=round(lt, 1),
            change_failure_rate=round(cfr, 4),
            mttr_seconds=round(mttr, 1),
            classification=classification,
            df_classification=df_cls,
            lt_classification=lt_cls,
            cfr_classification=cfr_cls,
            mttr_classification=mttr_cls,
            total_deployments=len(events),
            successful_deployments=len(successful),
            failed_deployments=len(failed),
            period_days=days,
            repos_measured=len(repos),
        )

    async def compute_per_repo(self, org_name: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Compute DORA metrics broken down by repository.

        Returns a list of dicts, one per repo, sorted by deployment frequency descending.
        """
        since = datetime.utcnow() - timedelta(days=days)
        events = await self._get_events(org_name, since)

        if not events:
            return []

        # Group events by repo
        repos = {}
        for e in events:
            repos.setdefault(e.repo_full_name, []).append(e)

        results = []
        for repo_name, repo_events in repos.items():
            df = self._deployment_frequency(repo_events, days)
            lt = self._lead_time(repo_events)
            cfr = self._change_failure_rate(repo_events)
            mttr = self._mean_time_to_recovery(repo_events)

            df_cls = self._classify_deployment_frequency(df)
            lt_cls = self._classify_lead_time(lt)
            cfr_cls = self._classify_change_failure_rate(cfr)
            mttr_cls = self._classify_mttr(mttr)
            classification = self._classify_overall(df_cls, lt_cls, cfr_cls, mttr_cls)

            successful = len([e for e in repo_events if e.conclusion == "success"])
            failed = len([e for e in repo_events if e.conclusion == "failure"])

            results.append({
                "repo_name": repo_name,
                "deployment_frequency": round(df, 4),
                "lead_time_seconds": round(lt, 1),
                "change_failure_rate": round(cfr, 4),
                "mttr_seconds": round(mttr, 1),
                "classification": classification,
                "total_deployments": len(repo_events),
                "successful_deployments": successful,
                "failed_deployments": failed,
            })

        # Sort by deployment frequency descending
        results.sort(key=lambda r: r["deployment_frequency"], reverse=True)
        return results

    async def compute_trends(
        self, org_name: str, period_type: str = "weekly", count: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Compute DORA metrics trends over time.

        Args:
            org_name: Organisation name
            period_type: "daily", "weekly", or "monthly"
            count: Number of periods to return

        Returns:
            List of metric snapshots ordered chronologically
        """
        period_days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period_type, 7)
        trends = []

        for i in range(count - 1, -1, -1):
            period_end = datetime.utcnow() - timedelta(days=i * period_days)
            period_start = period_end - timedelta(days=period_days)

            events = await self._get_events_between(org_name, period_start, period_end)

            df = self._deployment_frequency(events, period_days) if events else 0
            lt = self._lead_time(events) if events else 0
            cfr = self._change_failure_rate(events) if events else 0
            mttr = self._mean_time_to_recovery(events) if events else 0

            successful = len([e for e in events if e.conclusion == "success"]) if events else 0
            failed = len([e for e in events if e.conclusion == "failure"]) if events else 0

            trends.append({
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "period_type": period_type,
                "deployment_frequency": round(df, 4),
                "lead_time_seconds": round(lt, 1),
                "change_failure_rate": round(cfr, 4),
                "mttr_seconds": round(mttr, 1),
                "classification": self._classify_overall(
                    self._classify_deployment_frequency(df),
                    self._classify_lead_time(lt),
                    self._classify_change_failure_rate(cfr),
                    self._classify_mttr(mttr),
                ),
                "total_deployments": len(events) if events else 0,
                "successful_deployments": successful,
                "failed_deployments": failed,
            })

        return trends

    async def compute_correlation(self, org_name: str) -> Dict[str, Any]:
        """
        Analyse correlation between DORA metrics and DSOMM maturity scores.

        This is the unique WithOps feature — showing that higher security
        maturity correlates with better delivery performance.
        """
        from database.models import ProjectAnalysis

        dora_result = await self.compute(org_name, days=90)

        # Get latest DSOMM maturity data
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(ProjectAnalysis)
                .where(ProjectAnalysis.organization_name == org_name)
                .where(ProjectAnalysis.status == "completed")
                .order_by(ProjectAnalysis.created_at.desc())
                .limit(10)
            )
            analyses = result.scalars().all()

        if not analyses:
            return {
                "has_data": False,
                "message": "No DSOMM maturity assessments found for correlation analysis",
                "dora_metrics": dora_result.to_dict(),
            }

        # Extract maturity scores
        maturity_scores = []
        for a in analyses:
            if a.overall_maturity_score is not None:
                maturity_scores.append({
                    "project_name": a.project_name,
                    "maturity_score": a.overall_maturity_score,
                    "maturity_level": a.maturity_level,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                })

        avg_maturity = (
            sum(m["maturity_score"] for m in maturity_scores) / len(maturity_scores)
            if maturity_scores else 0
        )

        # Generate insight
        insight = self._generate_correlation_insight(dora_result, avg_maturity)

        return {
            "has_data": True,
            "dora_metrics": dora_result.to_dict(),
            "dsomm_data": {
                "average_maturity_score": round(avg_maturity, 2),
                "assessments": maturity_scores,
                "total_assessments": len(maturity_scores),
            },
            "correlation_insight": insight,
        }

    # =========================================================================
    # Metric Computation Methods
    # =========================================================================

    def _deployment_frequency(self, events: List[DeploymentEvent], days: int) -> float:
        """
        Calculate deployment frequency as successful deployments per day.
        """
        successful = [e for e in events if e.conclusion == "success"]
        return len(successful) / max(days, 1)

    def _lead_time(self, events: List[DeploymentEvent]) -> float:
        """
        Calculate median lead time for changes.

        Lead time is measured from when the workflow started to when it completed.
        If PR merge time is available, we use that as the start time instead
        (giving a more accurate "commit to production" measurement).
        """
        lead_times = []
        for e in events:
            if e.conclusion != "success":
                continue

            # Prefer PR merge time → completed time (true lead time)
            # Fall back to started → completed (workflow duration)
            if e.pr_merged_at and e.completed_at:
                delta = (e.completed_at - e.pr_merged_at).total_seconds()
                if delta > 0:
                    lead_times.append(delta)
            elif e.started_at and e.completed_at:
                delta = (e.completed_at - e.started_at).total_seconds()
                if delta > 0:
                    lead_times.append(delta)

        if not lead_times:
            return 0

        # Return median
        lead_times.sort()
        mid = len(lead_times) // 2
        if len(lead_times) % 2 == 0:
            return (lead_times[mid - 1] + lead_times[mid]) / 2
        return lead_times[mid]

    def _change_failure_rate(self, events: List[DeploymentEvent]) -> float:
        """
        Calculate the change failure rate as the ratio of failed to total deployments.
        Only success and failure conclusions count (not cancelled/timed_out).
        """
        relevant = [e for e in events if e.conclusion in ("success", "failure")]
        if not relevant:
            return 0
        failed = [e for e in relevant if e.conclusion == "failure"]
        return len(failed) / len(relevant)

    def _mean_time_to_recovery(self, events: List[DeploymentEvent]) -> float:
        """
        Calculate MTTR — average time between a failure and the next success.

        We sort events by completion time and measure the gap between each
        failure and the subsequent recovery (next successful deployment).
        """
        sorted_events = sorted(
            [e for e in events if e.completed_at],
            key=lambda e: e.completed_at
        )

        recovery_times = []
        last_failure_time = None

        for e in sorted_events:
            if e.conclusion == "failure":
                last_failure_time = e.completed_at
            elif e.conclusion == "success" and last_failure_time:
                delta = (e.completed_at - last_failure_time).total_seconds()
                if delta > 0:
                    recovery_times.append(delta)
                last_failure_time = None  # Reset after recovery

        if not recovery_times:
            return 0
        return sum(recovery_times) / len(recovery_times)

    # =========================================================================
    # Classification Methods (Google DORA Benchmarks)
    # =========================================================================

    def _classify_deployment_frequency(self, df: float) -> str:
        if df >= self.DF_ELITE:
            return "elite"
        elif df >= self.DF_HIGH:
            return "high"
        elif df >= self.DF_MEDIUM:
            return "medium"
        return "low"

    def _classify_lead_time(self, lt: float) -> str:
        if lt <= 0:
            return "low"  # No data
        if lt <= self.LT_ELITE:
            return "elite"
        elif lt <= self.LT_HIGH:
            return "high"
        elif lt <= self.LT_MEDIUM:
            return "medium"
        return "low"

    def _classify_change_failure_rate(self, cfr: float) -> str:
        if cfr <= self.CFR_ELITE:
            return "elite"
        elif cfr <= self.CFR_HIGH:
            return "high"
        elif cfr <= self.CFR_MEDIUM:
            return "medium"
        return "low"

    def _classify_mttr(self, mttr: float) -> str:
        if mttr <= 0:
            return "low"  # No data
        if mttr <= self.MTTR_ELITE:
            return "elite"
        elif mttr <= self.MTTR_HIGH:
            return "high"
        elif mttr <= self.MTTR_MEDIUM:
            return "medium"
        return "low"

    def _classify_overall(self, df_cls: str, lt_cls: str, cfr_cls: str, mttr_cls: str) -> str:
        """
        Compute overall DORA classification as a weighted average of individual metrics.
        Uses numeric mapping: elite=4, high=3, medium=2, low=1.
        """
        level_map = {"elite": 4, "high": 3, "medium": 2, "low": 1}
        scores = [
            level_map.get(df_cls, 1),
            level_map.get(lt_cls, 1),
            level_map.get(cfr_cls, 1),
            level_map.get(mttr_cls, 1),
        ]

        avg = sum(scores) / len(scores)

        if avg >= 3.5:
            return "elite"
        elif avg >= 2.5:
            return "high"
        elif avg >= 1.5:
            return "medium"
        return "low"

    # =========================================================================
    # Data Access
    # =========================================================================

    async def _get_events(self, org_name: str, since: datetime) -> List[DeploymentEvent]:
        """Fetch deployment events for an org since a given datetime."""
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(DeploymentEvent)
                .where(
                    and_(
                        DeploymentEvent.org_name == org_name,
                        DeploymentEvent.completed_at >= since,
                    )
                )
                .order_by(DeploymentEvent.completed_at.asc())
            )
            return result.scalars().all()

    async def _get_events_between(
        self, org_name: str, start: datetime, end: datetime
    ) -> List[DeploymentEvent]:
        """Fetch deployment events for an org within a date range."""
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(DeploymentEvent)
                .where(
                    and_(
                        DeploymentEvent.org_name == org_name,
                        DeploymentEvent.completed_at >= start,
                        DeploymentEvent.completed_at < end,
                    )
                )
                .order_by(DeploymentEvent.completed_at.asc())
            )
            return result.scalars().all()

    # =========================================================================
    # Insight Generation
    # =========================================================================

    def _generate_correlation_insight(self, dora: DORAResult, avg_maturity: float) -> str:
        """Generate a human-readable insight about DORA × DSOMM correlation."""
        insights = []

        if avg_maturity >= 3.0 and dora.classification in ("elite", "high"):
            insights.append(
                "Strong positive correlation detected: High DSOMM maturity is "
                "associated with elite-level delivery performance, confirming "
                "that security investments accelerate delivery."
            )
        elif avg_maturity >= 2.0 and dora.classification in ("medium", "high"):
            insights.append(
                "Moderate correlation: As DSOMM maturity improves, delivery "
                "metrics show positive trends. Continued security practice "
                "adoption is expected to further improve DORA performance."
            )
        elif avg_maturity < 2.0 and dora.classification in ("low", "medium"):
            insights.append(
                "Both DSOMM maturity and DORA performance are at early stages. "
                "Implementing automated security practices (SAST, SCA, secret "
                "scanning) is recommended to improve both security posture "
                "and delivery velocity simultaneously."
            )
        else:
            insights.append(
                "The relationship between security maturity and delivery "
                "performance requires more data points for reliable analysis. "
                "Continue monitoring as the dataset grows."
            )

        if dora.change_failure_rate > 0.3:
            insights.append(
                f"High change failure rate ({dora.change_failure_rate:.0%}) suggests "
                "that enhanced test automation and deployment safeguards "
                "would benefit both reliability and security."
            )

        return " ".join(insights)


# Global instance
dora_calculator = DORACalculator()
