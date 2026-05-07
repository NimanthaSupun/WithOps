"""
Synthetic Data Generator for Pipeline Prediction Service

Generates realistic CI/CD workflow run data with known failure patterns
embedded. This allows the ML model to be trained and validated even when
real historical data is scarce.

Embedded Patterns (the model should discover these):
────────────────────────────────────────────────────
1. TEMPORAL:   Late-night commits (10PM–6AM) fail ~3× more often
2. TEMPORAL:   Weekend commits fail ~2× more often
3. CHANGESET:  >15 files changed → ~55% failure rate (vs ~10% for <5 files)
4. CHANGESET:  >500 total line changes → higher failure
5. AUTHOR:     Some authors are consistently riskier than others
6. BRANCH:     hotfix/* branches fail more (rushed fixes)
7. BRANCH:     Direct pushes to main fail more than PRs
8. CASCADE:    3+ failures in last 24h → next run ~45% likely to fail
9. EVENT:      pull_request events have lower failure (code review)
10. DURATION:  Failing runs tend to take longer (timeout patterns)

Usage:
    # As a module
    from core.synthetic_data import SyntheticDataGenerator
    generator = SyntheticDataGenerator()
    runs = generator.generate(num_runs=1500)

    # As a standalone script
    python -m core.synthetic_data --runs 1500 --org NimanthaSupun
"""

import uuid
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION — Tunable parameters for data generation
# ============================================================================

# Organization / Repository configuration
DEFAULT_ORG = "NimanthaSupun"
REPOSITORIES = [
    {"name": "WithOps", "full_name": "NimanthaSupun/WithOps", "primary": True},
    {"name": "api-gateway", "full_name": "NimanthaSupun/api-gateway"},
    {"name": "frontend-app", "full_name": "NimanthaSupun/frontend-app"},
    {"name": "infra-config", "full_name": "NimanthaSupun/infra-config"},
    {"name": "auth-module", "full_name": "NimanthaSupun/auth-module"},
]

# Authors with personality profiles (name, base_skill: 0-1 where 1 = very careful)
AUTHORS = [
    {"login": "supun", "id": 1001, "skill": 0.85},
    {"login": "dev-alice", "id": 1002, "skill": 0.90},
    {"login": "dev-bob", "id": 1003, "skill": 0.60},
    {"login": "dev-charlie", "id": 1004, "skill": 0.75},
    {"login": "dev-diana", "id": 1005, "skill": 0.70},
    {"login": "junior-dev", "id": 1006, "skill": 0.45},
    {"login": "intern-01", "id": 1007, "skill": 0.35},
    {"login": "contractor-x", "id": 1008, "skill": 0.55},
]

# Workflow definitions
WORKFLOWS = [
    {"name": "CI/CD Pipeline", "path": ".github/workflows/ci-cd.yml"},
    {"name": "Build and Test", "path": ".github/workflows/build-test.yml"},
    {"name": "Deploy to Staging", "path": ".github/workflows/deploy-staging.yml"},
    {"name": "Deploy to Production", "path": ".github/workflows/deploy-prod.yml"},
    {"name": "Security Scan", "path": ".github/workflows/security-scan.yml"},
    {"name": "Lint and Format", "path": ".github/workflows/lint.yml"},
]

# Branch patterns
BRANCHES = [
    {"pattern": "main", "weight": 15, "type": "main"},
    {"pattern": "develop", "weight": 20, "type": "develop"},
    {"pattern": "feature/add-auth", "weight": 8, "type": "feature"},
    {"pattern": "feature/new-dashboard", "weight": 8, "type": "feature"},
    {"pattern": "feature/api-refactor", "weight": 8, "type": "feature"},
    {"pattern": "feature/db-migration", "weight": 6, "type": "feature"},
    {"pattern": "feature/user-settings", "weight": 5, "type": "feature"},
    {"pattern": "hotfix/critical-bug", "weight": 5, "type": "hotfix"},
    {"pattern": "hotfix/security-patch", "weight": 4, "type": "hotfix"},
    {"pattern": "release/v1.2.0", "weight": 4, "type": "release"},
    {"pattern": "release/v1.3.0", "weight": 3, "type": "release"},
    {"pattern": "experiment/ml-test", "weight": 3, "type": "other"},
    {"pattern": "chore/deps-update", "weight": 5, "type": "other"},
    {"pattern": "bugfix/login-issue", "weight": 6, "type": "feature"},
]

# Realistic commit message templates
COMMIT_MESSAGES = {
    "feature": [
        "feat: add user authentication flow",
        "feat: implement dashboard analytics component",
        "feat: add WebSocket support for real-time updates",
        "feat: create new API endpoint for workspace management",
        "feat: implement role-based access control",
        "feat: add Docker multi-stage build support",
        "feat: integrate Redis caching layer",
        "feat: add GitHub webhook handling",
        "feat: implement threat modeling STRIDE analysis",
        "feat: add Prometheus metrics collection",
    ],
    "fix": [
        "fix: resolve database connection pool exhaustion",
        "fix: correct CORS configuration for production",
        "fix: handle null pointer in user session",
        "fix: resolve race condition in event bus",
        "fix: correct Docker volume mount paths",
        "fix: patch security vulnerability in auth flow",
        "fix: resolve memory leak in WebSocket handler",
        "fix: correct timezone handling in timestamps",
    ],
    "refactor": [
        "refactor: extract service layer from controller",
        "refactor: optimize database queries with proper indexing",
        "refactor: clean up unused dependencies",
        "refactor: restructure project for microservice architecture",
        "refactor: improve error handling patterns",
    ],
    "chore": [
        "chore: update dependencies to latest versions",
        "chore: configure ESLint and Prettier rules",
        "chore: add CI/CD pipeline configuration",
        "chore: update Docker base images",
        "chore: bump Python to 3.11",
    ],
    "docs": [
        "docs: update README with setup instructions",
        "docs: add API documentation",
        "docs: update architecture diagrams",
    ],
}

# Event types with weights
EVENTS = [
    {"type": "push", "weight": 50},
    {"type": "pull_request", "weight": 35},
    {"type": "schedule", "weight": 5},
    {"type": "workflow_dispatch", "weight": 10},
]


# ============================================================================
# SYNTHETIC DATA GENERATOR
# ============================================================================

class SyntheticDataGenerator:
    """
    Generates realistic CI/CD workflow run history with embedded
    failure patterns that an ML model can learn to detect.
    """

    def __init__(self, org_name: str = DEFAULT_ORG, seed: int = 42):
        self.org_name = org_name
        self.rng = random.Random(seed)
        self.recent_failures: Dict[str, List[datetime]] = {}  # repo -> list of failure timestamps

    def generate(self, num_runs: int = 1500, days_back: int = 90) -> List[Dict[str, Any]]:
        """
        Generate synthetic workflow run records.

        Args:
            num_runs: Total number of runs to generate
            days_back: How many days of history to simulate

        Returns:
            List of dictionaries matching the WorkflowRunHistory schema
        """
        logger.info(f"🏗️ Generating {num_runs} synthetic workflow runs over {days_back} days...")

        now = datetime.utcnow()
        start_date = now - timedelta(days=days_back)
        runs = []

        # Generate timestamps spread across the time range
        # More recent runs are more frequent (realistic growth pattern)
        timestamps = self._generate_timestamps(num_runs, start_date, now)
        timestamps.sort()

        for i, created_at in enumerate(timestamps):
            run = self._generate_single_run(i + 1, created_at)
            runs.append(run)

            # Track failures for cascade pattern
            if run["conclusion"] == "failure":
                repo = run["repo_name"]
                if repo not in self.recent_failures:
                    self.recent_failures[repo] = []
                self.recent_failures[repo].append(created_at)

            # Clean old failures (keep only last 48h for cascade tracking)
            self._clean_old_failures(created_at)

        # Statistics
        total = len(runs)
        failures = sum(1 for r in runs if r["conclusion"] == "failure")
        successes = sum(1 for r in runs if r["conclusion"] == "success")
        timed_out = sum(1 for r in runs if r["conclusion"] == "timed_out")

        logger.info(f"✅ Generated {total} runs:")
        logger.info(f"   Success:   {successes} ({successes/total*100:.1f}%)")
        logger.info(f"   Failure:   {failures} ({failures/total*100:.1f}%)")
        logger.info(f"   Timed out: {timed_out} ({timed_out/total*100:.1f}%)")

        return runs

    def _generate_timestamps(self, count: int, start: datetime, end: datetime) -> List[datetime]:
        """
        Generate timestamps with realistic distribution:
        - More activity on weekdays
        - Peak hours 9AM-6PM
        - Slight increase in recent weeks (project growth)
        """
        timestamps = []
        total_seconds = (end - start).total_seconds()

        for _ in range(count):
            # Bias toward recent dates (exponential distribution)
            # This makes the last 30 days have more runs than the first 30
            rand = self.rng.random()
            biased = rand ** 0.7  # Slight bias toward 1.0 (recent)
            offset_seconds = biased * total_seconds
            ts = start + timedelta(seconds=offset_seconds)

            # Add hour-of-day bias: more commits during work hours
            hour = self.rng.choices(
                range(24),
                weights=[
                    1, 1, 1, 1, 1, 2,     # 00-05: very low
                    3, 5, 8, 10, 10, 10,   # 06-11: ramping up
                    8, 10, 10, 10, 9, 8,   # 12-17: peak + slight lunch dip
                    6, 5, 4, 3, 3, 2,      # 18-23: winding down
                ],
                k=1
            )[0]
            minute = self.rng.randint(0, 59)
            second = self.rng.randint(0, 59)

            ts = ts.replace(hour=hour, minute=minute, second=second)
            timestamps.append(ts)

        return timestamps

    def _generate_single_run(self, run_number: int, created_at: datetime) -> Dict[str, Any]:
        """Generate a single workflow run record with embedded failure patterns."""

        # Select random components
        repo = self.rng.choices(
            REPOSITORIES,
            weights=[r.get("primary", False) and 40 or 15 for r in REPOSITORIES],
            k=1
        )[0]
        author = self.rng.choice(AUTHORS)
        workflow = self.rng.choice(WORKFLOWS)
        branch_info = self.rng.choices(
            BRANCHES,
            weights=[b["weight"] for b in BRANCHES],
            k=1
        )[0]
        event_info = self.rng.choices(
            EVENTS,
            weights=[e["weight"] for e in EVENTS],
            k=1
        )[0]

        # Generate code change metrics
        files_changed, additions, deletions = self._generate_code_changes()

        # Generate commit message
        msg_type = self.rng.choice(list(COMMIT_MESSAGES.keys()))
        commit_message = self.rng.choice(COMMIT_MESSAGES[msg_type])

        # ================================================================
        # FAILURE PROBABILITY CALCULATION — This is where patterns live
        # ================================================================
        failure_prob = self._calculate_failure_probability(
            created_at=created_at,
            author=author,
            branch_info=branch_info,
            event_info=event_info,
            workflow=workflow,
            repo=repo,
            files_changed=files_changed,
            additions=additions,
            deletions=deletions,
        )

        # Determine conclusion
        conclusion, status = self._determine_conclusion(failure_prob)

        # Generate duration based on conclusion
        duration_seconds = self._generate_duration(conclusion, workflow)

        # Compute timestamps
        started_at = created_at + timedelta(seconds=self.rng.randint(5, 30))  # Queue time
        completed_at = started_at + timedelta(seconds=duration_seconds)
        updated_at = completed_at

        # Build the record
        return {
            "id": str(uuid.uuid4()),
            "organization_id": str(uuid.uuid4()),
            "org_name": self.org_name,
            "repo_name": repo["name"],
            "repo_full_name": repo["full_name"],

            # GitHub metadata — Unique space per org to avoid collisions
            "github_run_id": 7000000000 + (abs(hash(self.org_name)) % 1000000) * 10000 + run_number,
            "workflow_name": workflow["name"],
            "workflow_path": workflow["path"],
            "run_number": run_number,
            "event": event_info["type"],
            "status": status,
            "conclusion": conclusion,

            # Temporal
            "created_at": created_at,
            "updated_at": updated_at,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_seconds": duration_seconds,

            # Commit
            "head_branch": branch_info["pattern"],
            "head_sha": uuid.uuid4().hex[:40],
            "commit_message": commit_message,

            # Author
            "actor_login": author["login"],
            "actor_id": author["id"],

            # Code changes
            "files_changed": files_changed,
            "additions": additions,
            "deletions": deletions,

            # Metadata
            "collected_at": datetime.utcnow(),
            "features_json": None,
        }

    def _calculate_failure_probability(
        self,
        created_at: datetime,
        author: Dict,
        branch_info: Dict,
        event_info: Dict,
        workflow: Dict,
        repo: Dict,
        files_changed: int,
        additions: int,
        deletions: int,
    ) -> float:
        """
        Calculate failure probability based on multiple risk factors.
        Each factor adjusts the base probability.

        This is the GROUND TRUTH the model should learn.
        """
        # Base failure rate: ~15%
        base_prob = 0.15

        # ── PATTERN 1: Temporal — Hour of day ──
        hour = created_at.hour
        if hour >= 22 or hour < 6:
            # Late night: 3× more likely to fail
            base_prob += 0.25
        elif 6 <= hour < 9:
            # Early morning: slightly elevated
            base_prob += 0.05
        elif 9 <= hour <= 17:
            # Business hours: slightly lower (focused work)
            base_prob -= 0.03

        # ── PATTERN 2: Temporal — Day of week ──
        day = created_at.weekday()  # 0=Mon, 6=Sun
        if day >= 5:  # Weekend
            base_prob += 0.15
        elif day == 4:  # Friday
            base_prob += 0.05  # Friday deployments are risky

        # ── PATTERN 3: Changeset size ──
        if files_changed > 20:
            base_prob += 0.30
        elif files_changed > 15:
            base_prob += 0.20
        elif files_changed > 10:
            base_prob += 0.10
        elif files_changed < 3:
            base_prob -= 0.05  # Small, focused changes are safer

        # ── PATTERN 4: Total line changes ──
        total_changes = additions + deletions
        if total_changes > 500:
            base_prob += 0.15
        elif total_changes > 200:
            base_prob += 0.08

        # ── PATTERN 5: Author skill level ──
        # Lower skill = higher failure rate
        author_risk = (1.0 - author["skill"]) * 0.25
        base_prob += author_risk

        # ── PATTERN 6: Branch type ──
        branch_type = branch_info["type"]
        if branch_type == "hotfix":
            base_prob += 0.12  # Rushed fixes break things
        elif branch_type == "main":
            base_prob += 0.08  # Direct pushes to main are risky
        elif branch_type == "release":
            base_prob += 0.05
        elif branch_type == "develop":
            base_prob -= 0.03  # Integration branch, usually stable
        elif branch_type == "feature":
            base_prob -= 0.02

        # ── PATTERN 7: Event type ──
        if event_info["type"] == "pull_request":
            base_prob -= 0.08  # Code review reduces failures
        elif event_info["type"] == "push":
            base_prob += 0.03
        elif event_info["type"] == "schedule":
            base_prob -= 0.05  # Scheduled runs are stable

        # ── PATTERN 8: Workflow type ──
        wf_name = workflow["name"].lower()
        if "deploy" in wf_name and "prod" in wf_name:
            base_prob += 0.10  # Production deployments are risky
        elif "deploy" in wf_name:
            base_prob += 0.05
        elif "lint" in wf_name:
            base_prob -= 0.05  # Linting rarely fails
        elif "security" in wf_name:
            base_prob += 0.03

        # ── PATTERN 9: Cascade effect ──
        repo_name = repo["name"]
        if repo_name in self.recent_failures:
            recent = [f for f in self.recent_failures[repo_name]
                      if (created_at - f).total_seconds() < 86400]  # Last 24h
            if len(recent) >= 3:
                base_prob += 0.20  # Instability cascade
            elif len(recent) >= 2:
                base_prob += 0.10

        # ── PATTERN 10: Combination effects ──
        # Weekend + late night + large changeset = very dangerous
        is_weekend = day >= 5
        is_late = hour >= 22 or hour < 6
        is_large = files_changed > 10
        if is_weekend and is_late and is_large:
            base_prob += 0.15  # Bonus penalty for dangerous combo

        # Clamp to [0.02, 0.95]
        return max(0.02, min(0.95, base_prob))

    def _determine_conclusion(self, failure_prob: float) -> Tuple[str, str]:
        """
        Determine run conclusion based on failure probability.
        Returns (conclusion, status).
        """
        roll = self.rng.random()

        if roll < failure_prob:
            # Failed — decide between failure and timed_out
            if self.rng.random() < 0.15:  # 15% of failures are timeouts
                return "timed_out", "completed"
            return "failure", "completed"
        else:
            return "success", "completed"

    def _generate_code_changes(self) -> Tuple[int, int, int]:
        """
        Generate realistic code change metrics.
        Distribution:
          - Most commits are small (1-5 files)
          - Some are medium (5-15 files)
          - Few are large (15-50 files)
        """
        # Files changed: log-normal distribution centered around small changes
        files = max(1, int(self.rng.lognormvariate(1.2, 0.9)))
        files = min(files, 60)  # Cap at 60

        # Additions per file: 5-50 lines typically
        avg_additions_per_file = self.rng.randint(5, 50)
        additions = max(1, int(files * avg_additions_per_file * self.rng.uniform(0.5, 1.5)))

        # Deletions: typically 30-70% of additions
        deletion_ratio = self.rng.uniform(0.1, 0.8)
        deletions = max(0, int(additions * deletion_ratio))

        return files, additions, deletions

    def _generate_duration(self, conclusion: str, workflow: Dict) -> int:
        """
        Generate realistic run duration in seconds.
        Successful runs: 60-600s (1-10 min)
        Failed runs: 30-900s (tend to be shorter or timeout-long)
        Timed out: 900-1800s (15-30 min)
        """
        wf_name = workflow["name"].lower()

        # Base duration depends on workflow type
        if "lint" in wf_name:
            base = self.rng.randint(30, 120)
        elif "security" in wf_name:
            base = self.rng.randint(60, 300)
        elif "deploy" in wf_name and "prod" in wf_name:
            base = self.rng.randint(180, 600)
        elif "deploy" in wf_name:
            base = self.rng.randint(120, 480)
        else:
            base = self.rng.randint(90, 420)

        if conclusion == "success":
            # Normal variance around base
            return max(30, int(base * self.rng.uniform(0.8, 1.3)))
        elif conclusion == "timed_out":
            # Timeouts are long
            return self.rng.randint(900, 1800)
        else:
            # Failures can be quick (early fail) or long (late fail)
            if self.rng.random() < 0.4:
                # Early failure (build error, lint fail)
                return self.rng.randint(15, 90)
            else:
                # Late failure (test failure, integration issue)
                return max(60, int(base * self.rng.uniform(0.7, 1.5)))

    def _clean_old_failures(self, current_time: datetime):
        """Remove failure records older than 48 hours to save memory."""
        cutoff = current_time - timedelta(hours=48)
        for repo in self.recent_failures:
            self.recent_failures[repo] = [
                f for f in self.recent_failures[repo] if f > cutoff
            ]

    def get_embedded_patterns_description(self) -> List[Dict[str, str]]:
        """
        Return a human-readable description of embedded patterns.
        Useful for documentation and model validation.
        """
        return [
            {
                "pattern": "Late Night Commits",
                "description": "Commits between 10PM-6AM have ~3× higher failure rate",
                "expected_feature": "hour_of_day, is_business_hours"
            },
            {
                "pattern": "Weekend Commits",
                "description": "Weekend commits have ~2× higher failure rate",
                "expected_feature": "day_of_week, is_weekend"
            },
            {
                "pattern": "Large Changesets",
                "description": ">15 files changed increases failure rate to ~55%",
                "expected_feature": "files_changed, total_changes"
            },
            {
                "pattern": "Author Skill Level",
                "description": "Less experienced authors have higher failure rates",
                "expected_feature": "author_failure_rate, author_total_runs"
            },
            {
                "pattern": "Hotfix Branches",
                "description": "hotfix/* branches fail more (rushed code)",
                "expected_feature": "branch_type"
            },
            {
                "pattern": "Pull Request Safety",
                "description": "PR-based runs fail less (code review effect)",
                "expected_feature": "is_pull_request, event_type"
            },
            {
                "pattern": "Failure Cascades",
                "description": "3+ failures in 24h increases next failure probability",
                "expected_feature": "failures_last_24h"
            },
            {
                "pattern": "Production Deployments",
                "description": "Deploy-to-production workflows have higher failure rates",
                "expected_feature": "workflow_name_encoded"
            },
            {
                "pattern": "Dangerous Combinations",
                "description": "Weekend + late night + large changeset = very high risk",
                "expected_feature": "is_weekend AND hour_of_day AND files_changed"
            },
            {
                "pattern": "Friday Deployments",
                "description": "Friday commits have slightly elevated failure rates",
                "expected_feature": "day_of_week"
            },
        ]


# ============================================================================
# DATABASE PERSISTENCE
# ============================================================================

async def populate_database(num_runs: int = 1500, org_name: str = DEFAULT_ORG):
    """
    Generate synthetic data and insert it into the database.
    This is the main entry point for populating the DB with training data.
    """
    from database.config import db_manager
    from database.models import WorkflowRunHistory
    from sqlalchemy import select, func

    generator = SyntheticDataGenerator(org_name=org_name)
    runs = generator.generate(num_runs=num_runs)

    async with db_manager.get_session() as session:
        # Check how many records already exist
        result = await session.execute(
            select(func.count()).select_from(WorkflowRunHistory)
            .where(WorkflowRunHistory.org_name == org_name)
        )
        existing_count = result.scalar()

        if existing_count > 0:
            logger.warning(
                f"⚠️ Found {existing_count} existing records for {org_name}. "
                f"Skipping insert to prevent duplicates. "
                f"Delete existing records first if you want to regenerate."
            )
            return existing_count

        # Insert in batches of 100
        batch_size = 100
        inserted = 0

        for i in range(0, len(runs), batch_size):
            batch = runs[i:i + batch_size]
            records = [WorkflowRunHistory(**run_data) for run_data in batch]
            session.add_all(records)
            await session.flush()
            inserted += len(batch)
            logger.info(f"   📥 Inserted batch {i//batch_size + 1} ({inserted}/{len(runs)})")

        await session.commit()
        logger.info(f"✅ Successfully inserted {inserted} synthetic records into database")

    return inserted


async def clear_synthetic_data(org_name: str = DEFAULT_ORG):
    """
    Clear all synthetic data for a given organization.
    Useful for regenerating data with different parameters.
    """
    from database.config import db_manager
    from database.models import WorkflowRunHistory
    from sqlalchemy import delete

    async with db_manager.get_session() as session:
        result = await session.execute(
            delete(WorkflowRunHistory).where(WorkflowRunHistory.org_name == org_name)
        )
        await session.commit()
        deleted = result.rowcount
        logger.info(f"🗑️ Deleted {deleted} records for {org_name}")
        return deleted


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Generate synthetic CI/CD workflow data")
    parser.add_argument("--runs", type=int, default=1500, help="Number of runs to generate")
    parser.add_argument("--org", type=str, default=DEFAULT_ORG, help="Organization name")
    parser.add_argument("--days", type=int, default=90, help="Days of history to simulate")
    parser.add_argument("--clear", action="store_true", help="Clear existing data first")
    parser.add_argument("--dry-run", action="store_true", help="Generate without saving to DB")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    if args.dry_run:
        # Just generate and print stats without DB
        generator = SyntheticDataGenerator(org_name=args.org)
        runs = generator.generate(num_runs=args.runs, days_back=args.days)

        # Print sample records
        print("\n📋 Sample Records (first 3):")
        for run in runs[:3]:
            print(f"  Run #{run['run_number']}: "
                  f"{run['actor_login']} → {run['repo_name']}:{run['head_branch']} "
                  f"| {run['event']} | {run['conclusion']} "
                  f"| {run['files_changed']} files | {run['duration_seconds']}s "
                  f"| {run['created_at'].strftime('%a %H:%M')}")

        # Print pattern summary
        print("\n📊 Embedded Patterns:")
        for p in generator.get_embedded_patterns_description():
            print(f"  • {p['pattern']}: {p['description']}")
    else:
        async def main():
            from dotenv import load_dotenv
            load_dotenv()

            if args.clear:
                await clear_synthetic_data(args.org)

            await populate_database(num_runs=args.runs, org_name=args.org)

        asyncio.run(main())
