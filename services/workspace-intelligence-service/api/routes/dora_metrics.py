"""
DORA Metrics API Routes

Provides endpoints for computing and retrieving DORA (DevOps Research
and Assessment) performance metrics for organisations connected to WithOps.

Endpoints:
    GET /api/dora/{org_name}/metrics     — Current DORA metrics with classification
    GET /api/dora/{org_name}/trends      — Historical trends over time
    GET /api/dora/{org_name}/repos       — Per-repository breakdown
    GET /api/dora/{org_name}/correlation — DORA × DSOMM correlation analysis
    GET /api/dora/{org_name}/summary     — Dashboard summary card data
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from core.dora_calculator import dora_calculator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dora", tags=["DORA Metrics"])


@router.get("/{org_name}/metrics")
async def get_dora_metrics(
    org_name: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyse"),
):
    """
    Compute current DORA metrics for an organisation.

    Returns all four DORA metrics with individual and overall classification
    based on Google DORA benchmarks (Elite/High/Medium/Low).
    """
    try:
        result = await dora_calculator.compute(org_name, days=days)
        return {
            "status": "success",
            "org_name": org_name,
            "metrics": result.to_dict(),
        }
    except Exception as e:
        logger.error(f"❌ DORA metrics computation failed for {org_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compute DORA metrics: {str(e)}")


@router.get("/{org_name}/trends")
async def get_dora_trends(
    org_name: str,
    period: str = Query(default="weekly", regex="^(daily|weekly|monthly)$"),
    count: int = Query(default=12, ge=1, le=52, description="Number of periods to return"),
):
    """
    Get DORA metric trends over time for charting.

    Returns an array of metric snapshots ordered chronologically,
    suitable for rendering time-series charts on the dashboard.
    """
    try:
        trends = await dora_calculator.compute_trends(
            org_name, period_type=period, count=count
        )
        return {
            "status": "success",
            "org_name": org_name,
            "period_type": period,
            "count": len(trends),
            "trends": trends,
        }
    except Exception as e:
        logger.error(f"❌ DORA trends computation failed for {org_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compute DORA trends: {str(e)}")


@router.get("/{org_name}/repos")
async def get_dora_by_repo(
    org_name: str,
    days: int = Query(default=30, ge=1, le=365),
):
    """
    Get per-repository DORA metrics breakdown.

    Returns metrics for each repository in the organisation, sorted by
    deployment frequency (most active first). Useful for benchmarking
    repos against each other and identifying bottlenecks.
    """
    try:
        repos = await dora_calculator.compute_per_repo(org_name, days=days)
        return {
            "status": "success",
            "org_name": org_name,
            "period_days": days,
            "repo_count": len(repos),
            "repositories": repos,
        }
    except Exception as e:
        logger.error(f"❌ DORA per-repo computation failed for {org_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compute repo metrics: {str(e)}")


@router.get("/{org_name}/correlation")
async def get_dora_dsomm_correlation(org_name: str):
    """
    Analyse the correlation between DORA delivery performance and DSOMM
    security maturity for this organisation.

    This is WithOps' unique capability — demonstrating that security
    investments and delivery velocity are positively correlated.
    """
    try:
        correlation = await dora_calculator.compute_correlation(org_name)
        return {
            "status": "success",
            "org_name": org_name,
            **correlation,
        }
    except Exception as e:
        logger.error(f"❌ DORA correlation analysis failed for {org_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compute correlation: {str(e)}")


@router.get("/{org_name}/summary")
async def get_dora_summary(
    org_name: str,
    days: int = Query(default=30, ge=1, le=365),
):
    """
    Get a compact summary of DORA metrics for dashboard cards.

    Returns formatted values suitable for direct display (e.g., "2.3/day",
    "4h 12m", "12%", "38 min") along with classification and trend direction.
    """
    try:
        current = await dora_calculator.compute(org_name, days=days)
        previous = await dora_calculator.compute(org_name, days=days * 2)

        def trend(current_val: float, previous_val: float) -> str:
            if previous_val == 0:
                return "neutral"
            change = (current_val - previous_val) / max(previous_val, 0.0001)
            if change > 0.05:
                return "improving"
            elif change < -0.05:
                return "declining"
            return "stable"

        def format_duration(seconds: float) -> str:
            if seconds <= 0:
                return "N/A"
            if seconds < 60:
                return f"{int(seconds)}s"
            if seconds < 3600:
                return f"{int(seconds / 60)}m"
            if seconds < 86400:
                hours = int(seconds / 3600)
                mins = int((seconds % 3600) / 60)
                return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
            days_val = seconds / 86400
            return f"{days_val:.1f}d"

        # For change failure rate trend, lower is better (invert trend direction)
        cfr_trend = trend(current.change_failure_rate, previous.change_failure_rate)
        if cfr_trend == "improving":
            cfr_trend = "declining"  # Lower CFR = improving
        elif cfr_trend == "declining":
            cfr_trend = "improving"  # Higher CFR = declining

        # Same inversion for lead time and MTTR (lower is better)
        lt_trend = trend(current.lead_time_seconds, previous.lead_time_seconds)
        if lt_trend == "improving":
            lt_trend = "declining"
        elif lt_trend == "declining":
            lt_trend = "improving"

        mttr_trend_val = trend(current.mttr_seconds, previous.mttr_seconds)
        if mttr_trend_val == "improving":
            mttr_trend_val = "declining"
        elif mttr_trend_val == "declining":
            mttr_trend_val = "improving"

        return {
            "status": "success",
            "org_name": org_name,
            "classification": current.classification,
            "cards": [
                {
                    "metric": "Deployment Frequency",
                    "value": current.deployment_frequency,
                    "formatted": f"{current.deployment_frequency:.1f}/day",
                    "classification": current.df_classification,
                    "trend": trend(current.deployment_frequency, previous.deployment_frequency),
                },
                {
                    "metric": "Lead Time for Changes",
                    "value": current.lead_time_seconds,
                    "formatted": format_duration(current.lead_time_seconds),
                    "classification": current.lt_classification,
                    "trend": lt_trend,
                },
                {
                    "metric": "Change Failure Rate",
                    "value": current.change_failure_rate,
                    "formatted": f"{current.change_failure_rate:.0%}",
                    "classification": current.cfr_classification,
                    "trend": cfr_trend,
                },
                {
                    "metric": "Mean Time to Recovery",
                    "value": current.mttr_seconds,
                    "formatted": format_duration(current.mttr_seconds),
                    "classification": current.mttr_classification,
                    "trend": mttr_trend_val,
                },
            ],
            "total_deployments": current.total_deployments,
            "period_days": days,
        }
    except Exception as e:
        logger.error(f"❌ DORA summary computation failed for {org_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to compute DORA summary: {str(e)}")
