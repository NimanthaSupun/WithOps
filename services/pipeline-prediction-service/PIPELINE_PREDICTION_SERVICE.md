# Pipeline Prediction Service - Comprehensive Documentation

**Service Name**: Pipeline Prediction Service  
**Port**: 8009  
**Framework**: FastAPI (Python 3.11+)  
**Purpose**: ML-based CI/CD pipeline failure prediction using scikit-learn, XGBoost, and historical workflow data.

---

## Table of Contents

1. [Service Overview](#service-overview)
2. [Current Implementation Status](#current-implementation-status)
3. [Architecture & Components](#architecture--components)
4. [API Endpoints](#api-endpoints)
5. [Database Schema](#database-schema)
6. [ML Model Deep Dive](#ml-model-deep-dive)
7. [Current Limitations](#current-limitations)
8. [Improvements & Enhancements](#improvements--enhancements)
9. [Implementation Roadmap](#implementation-roadmap)
10. [Deployment Considerations](#deployment-considerations)

---

## Service Overview

### What It Does

The Pipeline Prediction Service analyzes commit context (author, files changed, time of day, branch type, etc.) using a trained ML classifier to predict whether a CI/CD pipeline run will **pass or fail** before execution.

**Key Features**:

- 🎯 **19-feature ML pipeline** extracting patterns from commit metadata
- 🧠 **Human-explainable predictions** with risk factors and recommendations
- 📊 **Accuracy tracking** via prediction history and outcome comparison
- 🔄 **Model versioning** with active/inactive model management
- 📈 **Prometheus metrics** for monitoring predictions and training
- 🌍 **Distributed tracing** via OpenTelemetry → Jaeger
- 🗄️ **PostgreSQL async backend** for scalability

### Target Use Cases

1. **Pre-commit risk assessment** — Developers get instant feedback before pushing
2. **CI/CD resource allocation** — Prioritize resources for high-risk runs
3. **Team insights** — Identify risky authors, branches, or time windows
4. **Automation triggers** — Skip deployments for high-risk predictions
5. **Historical analysis** — Trend pipeline stability over time

---

## Current Implementation Status

### ✅ Completed Components

| Component               | Status | Details                                                |
| ----------------------- | ------ | ------------------------------------------------------ |
| **FastAPI Server**      | ✅     | Full app with lifespan, monitoring, error handling     |
| **ML Models**           | ✅     | Random Forest, XGBoost, Gradient Boosting support      |
| **Feature Engineering** | ✅     | 19-feature extraction pipeline                         |
| **Model Manager**       | ✅     | Versioning, save/load, metadata tracking               |
| **Prediction Engine**   | ✅     | Inference with confidence scores & risk factors        |
| **Synthetic Data Gen**  | ✅     | Realistic CI/CD data with embedded patterns            |
| **Database Models**     | ✅     | WorkflowRunHistory, MLModelRegistry, PredictionHistory |
| **Async Database**      | ✅     | PostgreSQL via asyncpg with retry logic                |
| **Monitoring**          | ✅     | Prometheus metrics (requests, predictions, training)   |
| **Tracing**             | ✅     | OpenTelemetry → Jaeger (configurable)                  |
| **Frontend Page**       | ✅     | `/predictor` page with PipelineRiskPanel component     |
| **API Client**          | ✅     | `pipelinePrediction.js` with all endpoints             |

### ⚠️ Partially Implemented

| Component                | Status | Gap                                                                   |
| ------------------------ | ------ | --------------------------------------------------------------------- |
| **Feedback Loop**        | ⚠️     | `PredictionHistory` table exists but `actual_conclusion` never filled |
| **Accuracy Tracking**    | ⚠️     | Schema ready but no comparison logic or dashboards                    |
| **Auto-Retraining**      | ⚠️     | Manual trigger only, no scheduler or auto-evaluation                  |
| **Real Data Collection** | ⚠️     | No GitHub webhook to capture pipeline outcomes                        |
| **Model Evaluation**     | ⚠️     | Training metrics computed but not surfaced to frontend                |

### ❌ Missing Components

| Feature                           | Impact                                           | Priority    |
| --------------------------------- | ------------------------------------------------ | ----------- |
| **GitHub Webhook Handler**        | Can't capture pipeline outcomes                  | 🔴 Critical |
| **Outcome Update Service**        | Can't link predictions to actual results         | 🔴 Critical |
| **Accuracy Monitor Dashboard**    | Can't track model drift                          | 🟠 High     |
| **Auto-Retraining Scheduler**     | Model becomes stale over time                    | 🟠 High     |
| **Drift Detection**               | Can't alert when performance degrades            | 🟡 Medium   |
| **Feature Importance Dashboard**  | Can't explain why model makes predictions        | 🟡 Medium   |
| **Model Rollback Mechanism**      | Can't recover if new model is worse              | 🟡 Medium   |
| **Real-time Pipeline Monitoring** | Can't show live pipeline state during prediction | 🟡 Medium   |

---

## Architecture & Components

### Directory Structure

```
services/pipeline-prediction-service/
├── main.py                          # FastAPI app, lifespan, monitoring setup
├── api/
│   ├── routes/
│   │   ├── prediction.py            # POST /predict, GET /history endpoints
│   │   └── training.py              # POST /train, POST /generate-data endpoints
│   └── __init__.py
├── core/
│   ├── trainer.py                   # ML training pipeline orchestration
│   ├── predictor.py                 # Inference engine with risk explanations
│   ├── feature_engineer.py          # 19-feature extraction + transformation
│   ├── model_manager.py             # Model versioning, save/load
│   ├── synthetic_data.py            # Realistic workflow data generation
│   ├── data_collector.py            # GitHub API integration for real data
│   └── __init__.py
├── database/
│   ├── config.py                    # Async DB manager, session factory
│   ├── models.py                    # SQLAlchemy ORM (WorkflowRunHistory, MLModelRegistry, PredictionHistory)
│   └── __init__.py
├── models/                          # Saved .joblib files (one per org/version)
│   ├── model_NimanthaSupun_v1.joblib
│   └── model_NimanthaSupun_v2.joblib
├── Dockerfile                       # Container image for Kubernetes/Docker
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
└── README.md                        # Setup instructions
```

### Technology Stack

**Core Dependencies**:

- `fastapi==0.104.1` — Async web framework
- `uvicorn[standard]==0.24.0` — ASGI server
- `sqlalchemy==2.0.23` — ORM for database operations
- `asyncpg==0.29.0` — Async PostgreSQL driver
- `psycopg2-binary==2.9.9` — PostgreSQL adapter

**ML Libraries**:

- `scikit-learn==1.3.2` — Random Forest, evaluation metrics
- `xgboost==2.0.3` — Gradient boosting classifier
- `pandas==2.1.4` — Data manipulation
- `numpy==1.26.2` — Numerical operations
- `joblib==1.3.2` — Model serialization
- `imbalanced-learn==0.11.0` — Handle class imbalance

**Observability**:

- `prometheus-client==0.19.0` — Metrics export
- `opentelemetry-api==1.21.0` — Tracing API
- `opentelemetry-sdk==1.21.0` — Core tracing
- `opentelemetry-instrumentation-fastapi==0.42b0` — Auto-instrumentation
- `opentelemetry-exporter-otlp==1.21.0` — Export to Jaeger

**Utilities**:

- `httpx[http2]==0.25.0` — Async HTTP client
- `tenacity==8.2.3` — Retry logic
- `pyyaml==6.0.1` — YAML parsing
- `python-dotenv==1.0.0` — Environment variables

---

## API Endpoints

### Prediction Endpoints

#### `POST /api/pipeline-prediction/predict`

**Purpose**: Predict pipeline failure probability for a commit

**Request Body**:

```json
{
  "org_name": "NimanthaSupun",
  "repo_name": "WithOps",
  "branch": "feature/new-dashboard",
  "author": "supun",
  "event_type": "push",
  "files_changed": 15,
  "additions": 342,
  "deletions": 89,
  "commit_message": "feat: add dashboard component"
}
```

**Response**:

```json
{
  "prediction": {
    "failure_probability": 0.3245,
    "success_probability": 0.6755,
    "risk_level": "medium",
    "confidence": 0.3490
  },
  "risk_factors": [
    {
      "factor": "Files Changed",
      "detail": "15 files changed — large changesets (>10 files) fail significantly more often",
      "importance": 0.24,
      "value": 15
    }
  ],
  "recommendation": "Moderate risk — consider running tests locally before pushing.",
  "context": {...},
  "model_info": {
    "version": 1,
    "type": "random_forest",
    "accuracy": 0.87
  },
  "prediction_id": "uuid",
  "predicted_at": "2026-04-10T15:30:45.123456"
}
```

---

#### `GET /api/pipeline-prediction/history/{org_name}/{repo_name}`

**Purpose**: Get prediction history for a specific repository

**Query Parameters**:

- `limit` (int, default=50) — Number of predictions to return

**Response**:

```json
{
  "org_name": "NimanthaSupun",
  "repo_name": "WithOps",
  "predictions": [
    {
      "id": "pred-123",
      "predicted_at": "2026-04-10T15:30:45",
      "branch": "main",
      "author": "supun",
      "failure_probability": 0.1234,
      "risk_level": "low",
      "actual_conclusion": "success",
      "prediction_correct": true
    }
  ],
  "stats": {
    "total_predictions": 1250,
    "showing": 50,
    "verified_predictions": 45,
    "accuracy": 0.8667
  }
}
```

---

#### `GET /api/pipeline-prediction/history/{org_name}`

**Purpose**: Get prediction history across all repos for an organization

**Response**: Similar to repo-level history but aggregated across all repos

---

### Training Endpoints

#### `POST /api/pipeline-prediction/generate-data`

**Purpose**: Generate synthetic CI/CD workflow data for training

**Request Body**:

```json
{
  "org_name": "NimanthaSupun",
  "num_runs": 1500,
  "clear_existing": false
}
```

**Response**:

```json
{
  "status": "success",
  "records_created": 1500,
  "org_name": "NimanthaSupun",
  "message": "Generated 1500 synthetic workflow runs..."
}
```

**Embedded Patterns** (model should learn these):

- Late-night commits (10PM–6AM) fail ~3× more
- Weekend commits fail ~2× more
- > 15 files changed → ~55% failure rate
- > 500 total line changes → elevated risk
- Some authors have higher failure rates
- hotfix/\* branches fail more
- Direct pushes fail more than PRs
- 3+ failures in 24h → next run ~45% failure
- PR events safer than push events

---

#### `POST /api/pipeline-prediction/train`

**Purpose**: Train ML model for pipeline failure prediction

**Request Body**:

```json
{
  "org_name": "NimanthaSupun",
  "model_type": "random_forest"
}
```

**Model Types**: `random_forest`, `xgboost`, `gradient_boosting`

**Response**:

```json
{
  "org_name": "NimanthaSupun",
  "model_type": "random_forest",
  "status": "success",
  "training_samples": 1200,
  "progress": {
    "data_collection": "completed (1500 runs loaded)",
    "feature_engineering": "completed (19 features extracted)",
    "model_training": "completed",
    "evaluation": "completed"
  },
  "metrics": {
    "accuracy": 0.8750,
    "precision": 0.8621,
    "recall": 0.8667,
    "f1": 0.8644,
    "auc_roc": 0.9234
  },
  "feature_importance": {
    "hour_of_day": 0.1542,
    "files_changed": 0.1203,
    "author_failure_rate": 0.1087,
    ...
  },
  "class_distribution": {
    "success": 1050,
    "failure": 150
  }
}
```

---

#### `GET /api/pipeline-prediction/train/status`

**Purpose**: Get result of last training run

**Response**: Last training result or "no_training_run" status

---

#### `GET /api/pipeline-prediction/model/{org_name}`

**Purpose**: Get info about active model for organization

**Response**:

```json
{
  "org_name": "NimanthaSupun",
  "version": 3,
  "model_type": "random_forest",
  "trained_at": "2026-04-08T12:30:00",
  "accuracy": 0.875,
  "precision": 0.8621,
  "recall": 0.8667,
  "f1": 0.8644,
  "auc_roc": 0.9234,
  "feature_count": 19,
  "training_samples": 1200,
  "class_distribution": {
    "success": 1050,
    "failure": 150
  }
}
```

---

#### `GET /api/pipeline-prediction/feature-importance/{org_name}`

**Purpose**: Get feature importance breakdown for model

**Response**:

```json
{
  "org_name": "NimanthaSupun",
  "model_version": 3,
  "features": [
    {
      "name": "hour_of_day",
      "importance": 0.1542,
      "rank": 1,
      "description": "Hour of day when commit was made (0-23)"
    },
    {
      "name": "files_changed",
      "importance": 0.1203,
      "rank": 2,
      "description": "Number of files modified in commit"
    }
  ]
}
```

---

## Database Schema

### `WorkflowRunHistory` Table

**Purpose**: Store raw GitHub workflow run data with commit metrics

```sql
CREATE TABLE workflow_run_history (
  id UUID PRIMARY KEY,
  organization_id VARCHAR,
  org_name VARCHAR NOT NULL (indexed),
  repo_name VARCHAR NOT NULL (indexed),
  repo_full_name VARCHAR NOT NULL,

  -- GitHub run metadata
  github_run_id BIGINT UNIQUE NOT NULL (indexed),
  workflow_name VARCHAR NOT NULL,
  workflow_path VARCHAR,
  run_number INTEGER,
  event VARCHAR,  -- push, pull_request, schedule, etc.
  status VARCHAR,  -- completed, in_progress, queued
  conclusion VARCHAR,  -- success, failure, cancelled, timed_out

  -- Temporal features
  created_at TIMESTAMP NOT NULL (indexed),
  updated_at TIMESTAMP,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  duration_seconds INTEGER,

  -- Commit metadata
  head_branch VARCHAR,
  head_sha VARCHAR,
  commit_message TEXT,

  -- Author info
  actor_login VARCHAR (indexed),
  actor_id INTEGER,

  -- Code change metrics
  files_changed INTEGER DEFAULT 0,
  additions INTEGER DEFAULT 0,
  deletions INTEGER DEFAULT 0,

  -- Collection metadata
  collected_at TIMESTAMP DEFAULT NOW(),
  features_json JSON
);

CREATE INDEX idx_wfr_org_repo ON workflow_run_history(org_name, repo_name);
CREATE INDEX idx_wfr_created_desc ON workflow_run_history(created_at DESC);
```

**Rows**: 1000s per organization (grows daily with pipelines)

---

### `MLModelRegistry` Table

**Purpose**: Track all trained models and their performance

```sql
CREATE TABLE ml_model_registry (
  id UUID PRIMARY KEY,
  org_name VARCHAR NOT NULL (indexed),
  model_version INTEGER NOT NULL,
  model_type VARCHAR NOT NULL,  -- random_forest, xgboost, gradient_boosting

  -- Training metadata
  trained_at TIMESTAMP DEFAULT NOW(),
  training_samples INTEGER,
  feature_count INTEGER,
  feature_names JSON,  -- List of feature column names

  -- Performance metrics
  accuracy FLOAT,
  precision_score FLOAT,
  recall_score FLOAT,
  f1_score FLOAT,
  auc_roc FLOAT,
  confusion_matrix JSON,  -- [[TP, FP], [FN, TN]]

  -- Feature importance
  feature_importance JSON,  -- {feature_name: score}

  -- Model file reference
  model_path VARCHAR,  -- /models/model_NimanthaSupun_v3.joblib
  is_active BOOLEAN DEFAULT TRUE,

  -- Class distribution
  class_distribution JSON  -- {success: N, failure: M}
);
```

**Rows**: 1-5 per organization (most are inactive versions)

---

### `PredictionHistory` Table

**Purpose**: Store all predictions for auditing and accuracy tracking

```sql
CREATE TABLE prediction_history (
  id UUID PRIMARY KEY,
  org_name VARCHAR NOT NULL (indexed),
  repo_name VARCHAR NOT NULL (indexed),
  branch VARCHAR,
  commit_sha VARCHAR,
  author VARCHAR,

  -- Prediction result
  failure_probability FLOAT NOT NULL,
  risk_level VARCHAR NOT NULL,  -- low, medium, high, critical
  risk_factors JSON,
  recommendation TEXT,

  -- Model used
  model_version INTEGER,
  model_type VARCHAR,

  -- Actual outcome (filled in later via webhook)
  actual_conclusion VARCHAR,  -- success, failure, null (pending)
  prediction_correct BOOLEAN,  -- Computed: predicted == actual

  -- Timestamps
  predicted_at TIMESTAMP DEFAULT NOW() (indexed),
  actual_completed_at TIMESTAMP
);
```

**Rows**: 10,000s+ per organization (grows hourly with predictions)

---

## ML Model Deep Dive

### 19-Feature Engineering Pipeline

| #   | Feature Name            | Type  | Source           | Range    | Description                                            |
| --- | ----------------------- | ----- | ---------------- | -------- | ------------------------------------------------------ |
| 0   | `hour_of_day`           | int   | `created_at`     | 0-23     | Hour commit was made                                   |
| 1   | `day_of_week`           | int   | `created_at`     | 0-6      | Day of week (0=Monday)                                 |
| 2   | `is_weekend`            | bool  | `created_at`     | 0/1      | True if weekend                                        |
| 3   | `is_business_hours`     | bool  | `created_at`     | 0/1      | 9AM-5PM on weekday                                     |
| 4   | `files_changed`         | int   | commit           | 0-1000+  | # files modified                                       |
| 5   | `additions`             | int   | commit           | 0-10000+ | # lines added                                          |
| 6   | `deletions`             | int   | commit           | 0-10000+ | # lines deleted                                        |
| 7   | `total_changes`         | int   | computed         | 0-20000+ | additions + deletions                                  |
| 8   | `change_ratio`          | float | computed         | 0-100+   | additions / max(deletions, 1)                          |
| 9   | `branch_type`           | int   | `head_branch`    | 0-4      | main(0), develop(1), feature(2), hotfix(3), release(4) |
| 10  | `is_pull_request`       | bool  | `event`          | 0/1      | True if PR event                                       |
| 11  | `event_type`            | int   | `event`          | 0-3      | push(0), pull_request(1), schedule(2), dispatch(3)     |
| 12  | `workflow_name_encoded` | int   | `workflow_name`  | 0-100+   | Hashed workflow name                                   |
| 13  | `author_total_runs`     | int   | history          | 0-1000+  | # runs by this author                                  |
| 14  | `author_failure_rate`   | float | history          | 0-1      | Fraction of failures by author                         |
| 15  | `repo_failure_rate_7d`  | float | history          | 0-1      | Repo failure rate last 7 days                          |
| 16  | `avg_duration_last_10`  | float | history          | 0-3600+  | Avg runtime of last 10 runs                            |
| 17  | `failures_last_24h`     | int   | history          | 0-100+   | # failures in last 24h                                 |
| 18  | `commit_message_length` | int   | `commit_message` | 0-500+   | Length of commit message                               |

### Feature Engineering Code Path

1. **Load workflow run data** → 19 raw columns per run
2. **Extract temporal features** → hour, weekday, business hours
3. **Compute code metrics** → file count, additions/deletions, ratios
4. **Encode categoricals** → branch type (0-4), event type (0-3)
5. **Historical aggregation** → author stats, repo trends, cascade detection
6. **Missing value imputation** → Fill NaNs with 0 or mean

### Model Selection

**Random Forest** (Default):

- ✅ Fast training (seconds)
- ✅ Good explainability (feature importance)
- ✅ Handles non-linear patterns
- ✅ No hyperparameter tuning needed
- ❌ Can overfit on small datasets
- **Best for**: Quick bootstrap training

**XGBoost** (Alternative):

- ✅ Better performance on imbalanced data
- ✅ Handles missing values natively
- ✅ Faster inference
- ❌ Slower training
- ❌ More hyperparameters to tune
- **Best for**: Production with real data

**Gradient Boosting** (Fallback):

- ✅ Sklearn built-in, no extra deps
- ❌ Slowest training
- ❌ Can overfit
- **Best for**: Fallback when XGBoost unavailable

### Class Imbalance Handling

**Problem**: Most runs succeed (~90%), few fail (~10%) → model biased to predict success

**Solutions**:

1. **Stratified train-test split** — Preserve class ratio in splits
2. **class_weight="balanced"** — Penalize false negatives more
3. **Scale positive weight** — `scale_pos = n_success / n_failure`
4. **Evaluation metrics** — Use precision/recall/F1, not just accuracy

### Risk Factor Explanations

For each prediction, model generates **top 5 human-readable risk factors**:

```python
RISK_EXPLANATIONS = {
    "hour_of_day": {
        "check": lambda v: v >= 22 or v < 6,
        "message": lambda v: f"Late-night commit at {int(v)}:00 — failure rate is 3× higher after 10 PM"
    },
    "files_changed": {
        "check": lambda v: v > 10,
        "message": lambda v: f"{int(v)} files changed — large changesets (>10 files) fail significantly more often"
    },
    # ... 18 more explanations
}
```

**Selection Logic**:

1. For each feature, check if value triggers risk explanation
2. Sort by feature importance (from model)
3. Return top 5 most important factors

---

## Current Limitations

### 🔴 Critical Limitations

#### 1. **No Feedback Loop / Outcome Tracking**

**Problem**:

- Predictions stored in `PredictionHistory` but `actual_conclusion` field **never populated**
- No mechanism to match pipeline completions back to predictions
- Model accuracy **cannot be evaluated** against real outcomes

**Impact**:

- ❌ Can't detect model drift
- ❌ Can't trigger retraining when accuracy drops
- ❌ Can't verify predictions vs reality
- ❌ Users don't know if model is actually correct

**Root Cause**: No GitHub webhook handler to capture pipeline success/failure events

---

#### 2. **One-Time Training Only (No Continuous Learning)**

**Problem**:

- Model trained once via `POST /train`
- Stays frozen indefinitely
- Zero automatic adaptation to new data patterns

**Impact**:

- 📉 Accuracy degrades over time (data drift)
- 🔄 Manual retraining required (not scalable)
- 🆕 New team members/workflows not reflected in model

**Example**:

```
Week 1: Train on 1500 runs → 87% accuracy
Week 8: Same model → 71% accuracy (new devs, infra changes)
Year 1: Same model → 45% accuracy (completely obsolete)
```

---

#### 3. **Synthetic Data Only (No Real Data Integration)**

**Problem**:

- Model trains on artificially generated workflow data
- Patterns invented, not observed from real pipelines
- Thresholds (e.g., >15 files = risky) may be wrong for your org

**Impact**:

- 🎯 Test accuracy: 87%
- 🌍 Real-world accuracy: 60-70% initially
- 📊 Systematic bias toward synthetic patterns

**Example Mismatch**:

```
Synthetic assumes: >15 files = 55% failure rate
Reality in your org: >15 files = 15% failure rate (different codebase)
Result: Model over-predicts failures by 40%
```

---

#### 4. **No Drift Detection / Monitoring**

**Problem**:

- No automated way to detect when model becomes inaccurate
- No alerts when accuracy drops below threshold
- No comparison of model versions

**Impact**:

- 🚨 Stale predictions go unnoticed
- 👥 Users lose trust in model
- 💰 Time wasted on irrelevant predictions

---

### 🟠 High-Priority Limitations

#### 5. **Manual Model Versioning**

**Problem**:

- No automatic trigger to train new versions
- `MLModelRegistry` tracks versions but selection is manual
- No rollback mechanism if new model is worse

**Impact**:

- ⚙️ Requires manual intervention to update
- 🔧 Doesn't scale to many organizations
- ⚠️ No safety net if new model degrades

---

#### 6. **No Real-Time Pipeline State Integration**

**Problem**:

- Model predicts in vacuum (doesn't know current pipeline health)
- Can't incorporate active run counts, current outages, etc.
- Prediction made at push time (before run context known)

**Impact**:

- 📍 Predictions are point-in-time estimates
- 🕐 Don't adapt as more info available
- ❌ Can't explain why run actually failed

---

#### 7. **No Accuracy Dashboard**

**Problem**:

- Accuracy metrics computed but never surfaced to users
- No way to see top risk factors contributing to failures
- No comparison of model versions

**Impact**:

- 📊 Users can't evaluate model trustworthiness
- 🔍 Can't identify systematic biases
- 📉 No visibility into model health

---

### 🟡 Medium-Priority Limitations

#### 8. **Limited Historical Context**

**Problem**:

- Predictor looks back only 200 runs for context
- May be insufficient for orgs with 1000s of daily runs
- Can't detect longer-term patterns (monthly cycles, seasonal trends)

**Impact**:

- 📉 Cascade detection unreliable at large scale
- 🔄 Circular dependencies not fully captured

---

#### 9. **No Author Skill Learning**

**Problem**:

- Author failure rate computed from history
- But new authors have zero history
- New devs always appear as high-risk (cold start problem)

**Impact**:

- 🆕 Overly cautious on new team members
- 👤 Unfair risk scoring for juniors

---

#### 10. **Insufficient Test Coverage**

**Problem**:

- No unit tests for feature engineering
- No integration tests for training pipeline
- No regression tests for accuracy

**Impact**:

- 🐛 Silent bugs in feature extraction
- 📉 Accuracy regressions not caught

---

#### 11. **No Cost/Resource Optimization**

**Problem**:

- Model training uses default parameters
- No hyperparameter tuning (grid search, Bayesian optimization)
- Training doesn't consider compute costs

**Impact**:

- 📈 Suboptimal accuracy (could be 2-5% better)
- 💰 Training takes longer than necessary

---

#### 12. **No Explainability Beyond Top 5 Factors**

**Problem**:

- Only top 5 risk factors shown to users
- Full feature importances not exposed
- SHAP values not computed (local explanations)

**Impact**:

- ❓ Users can't understand full reasoning
- 🤔 Hard to debug unexpected predictions

---

## Improvements & Enhancements

### Phase 1: Enable Feedback Loop (Critical, 2-3 weeks)

**Goal**: Connect predictions to actual outcomes

#### 1.1 Implement GitHub Webhook Handler

**What**: Listen for GitHub Actions workflow completion events

**Where**: Add to `backend/main.py` or new `services/events-integration-service`

**Implementation**:

```python
@app.post("/webhook/github/workflow-complete")
async def handle_workflow_completion(request: Request):
    """
    GitHub sends:
    {
      "action": "completed",
      "workflow_run": {
        "id": 12345,
        "conclusion": "success" | "failure" | "cancelled",
        "name": "CI/CD Pipeline",
        "repository": {"full_name": "NimanthaSupun/WithOps"},
        "head_commit": {"sha": "abc123..."},
        "completed_at": "2026-04-10T15:30:45Z"
      }
    }
    """

    # 1. Extract pipeline outcome
    run_id = request["workflow_run"]["id"]
    conclusion = request["workflow_run"]["conclusion"]

    # 2. Update WorkflowRunHistory with actual result
    await db.update_workflow_run(run_id, conclusion=conclusion)

    # 3. Find matching prediction, update PredictionHistory
    predictions = await db.query(PredictionHistory).filter(
        commit_sha == request["workflow_run"]["head_commit"]["sha"]
    )

    for pred in predictions:
        pred.actual_conclusion = conclusion
        pred.prediction_correct = (
            (pred.failure_probability > 0.5 and conclusion == "failure") or
            (pred.failure_probability <= 0.5 and conclusion == "success")
        )
        pred.actual_completed_at = now()
        await db.save(pred)

    # 4. Publish event to track
    await redis.publish("pipeline.outcome", {
        "run_id": run_id,
        "conclusion": conclusion,
        "prediction_correct": pred.prediction_correct
    })

    return {"status": "recorded"}
```

**GitHub Setup**:

```yaml
# In GitHub org settings:
Webhooks → Add Webhook
Payload URL: https://withops.com/webhook/github/workflow-complete
Content type: application/json
Events: Workflow runs
```

#### 1.2 Create Outcome Reconciliation Job

**What**: Periodic sync to fill in missed outcomes

**Where**: `services/pipeline-prediction-service/core/outcome_reconciler.py`

```python
async def reconcile_outcomes():
    """
    Daily job: For all pending predictions, query GitHub API
    to get actual pipeline outcome if webhook missed it.
    """
    pending = await db.query(PredictionHistory).filter(
        actual_conclusion == None,
        predicted_at < datetime.now() - timedelta(hours=24)
    ).all()

    for pred in pending:
        # Query GitHub API for this run
        run_info = await github_client.get_run(pred.org_name, pred.commit_sha)
        if run_info and run_info["conclusion"]:
            pred.actual_conclusion = run_info["conclusion"]
            pred.prediction_correct = (pred.failure_probability > 0.5) == \
                                      (run_info["conclusion"] == "failure")
            pred.actual_completed_at = run_info["completed_at"]
            await db.save(pred)
```

**Scheduler**:

```python
# In main.py lifespan
scheduler = APScheduler()
scheduler.add_job(reconcile_outcomes, trigger="cron", hour=2)  # 2 AM daily
scheduler.start()
```

---

#### 1.3 Add Accuracy Computation Endpoint

**What**: Query and compute accuracy stats

**Where**: `api/routes/metrics.py` (new)

```python
@router.get("/api/pipeline-prediction/metrics/{org_name}")
async def get_org_metrics(org_name: str):
    """Get accuracy metrics for org's model"""

    predictions = await db.query(PredictionHistory).filter(
        org_name == org_name,
        prediction_correct != None  # Only completed predictions
    ).all()

    if not predictions:
        return {"status": "no_data"}

    correct = sum(1 for p in predictions if p.prediction_correct)

    return {
        "org_name": org_name,
        "total_predictions": len(predictions),
        "correct_predictions": correct,
        "accuracy": correct / len(predictions),
        "by_risk_level": {
            "low": compute_accuracy(predictions, "low"),
            "medium": compute_accuracy(predictions, "medium"),
            "high": compute_accuracy(predictions, "high"),
            "critical": compute_accuracy(predictions, "critical")
        }
    }
```

---

### Phase 2: Implement Continuous Learning (2-3 weeks)

**Goal**: Auto-detect when accuracy drops and retrain model

#### 2.1 Create Model Evaluation Service

**What**: Periodic accuracy monitoring

```python
async def evaluate_model_accuracy():
    """
    Weekly job: Compute accuracy on last 500 completed predictions.
    If accuracy < 75%, trigger retrain.
    """

    for org in organizations:
        recent_predictions = await db.query(PredictionHistory).filter(
            org_name == org,
            prediction_correct != None
        ).order_by(predicted_at.desc()).limit(500).all()

        if len(recent_predictions) < 100:
            continue  # Not enough data

        accuracy = sum(1 for p in recent_predictions if p.prediction_correct) / \
                   len(recent_predictions)

        # Get baseline accuracy
        baseline = (await model_manager.get_metadata(org))["metrics"]["accuracy"]

        logger.info(f"{org}: Current {accuracy:.2%}, Baseline {baseline:.2%}")

        # If dropped >5%, alert + retrain
        if accuracy < baseline - 0.05:
            logger.warning(f"⚠️ {org} accuracy dropped from {baseline:.2%} to {accuracy:.2%}")
            await trigger_retrain(org)
```

#### 2.2 Create Auto-Retraining Scheduler

**What**: Periodically trigger training on new real data

```python
async def auto_retrain():
    """
    Bi-weekly job: Collect last 2000 real workflow runs,
    train new model, compare with current, deploy if better.
    """

    for org in organizations:
        runs = await db.query(WorkflowRunHistory).filter(
            org_name == org,
            created_at > datetime.now() - timedelta(days=14)
        ).order_by(created_at.desc()).limit(2000).all()

        if len(runs) < 500:
            logger.info(f"{org}: Only {len(runs)} runs, skipping retrain")
            continue

        # Train new model
        new_result = await trainer.train(
            org_name=org,
            model_type="random_forest"
        )

        # Compare with current
        current_model = await model_manager.get_metadata(org)
        current_accuracy = current_model["metrics"]["accuracy"]
        new_accuracy = new_result["metrics"]["accuracy"]

        # If better, activate new model
        if new_accuracy > current_accuracy + 0.01:  # 1% improvement threshold
            await model_manager.mark_active(org, new_result["version"])
            logger.info(f"✅ {org}: Activated v{new_result['version']} "
                       f"({new_accuracy:.2%} vs {current_accuracy:.2%})")
        else:
            logger.info(f"⏭️ {org}: New model not better, keeping v{current_model['version']}")
```

---

### Phase 3: Add Monitoring Dashboard (2-3 weeks)

**Goal**: Frontend visibility into model accuracy and drift

#### 3.1 Create Accuracy Dashboard Page

**Frontend**: `frontend/src/routes/github/workspace/[org]/predictor/accuracy/+page.svelte`

**Features**:

- Accuracy trend over time (line chart)
- Accuracy by risk level (bar chart)
- Feature importance visualization (top 10 features)
- Model comparison (v1 vs v2 vs v3)
- Recent false positives/negatives
- Training history & retraining logs

#### 3.2 Create Model Management UI

**Frontend**: `frontend/src/routes/github/workspace/[org]/predictor/model-management/+page.svelte`

**Features**:

- List all model versions with metrics
- Compare models side-by-side
- Manually trigger retrain
- Rollback to previous version
- View training logs
- Estimate time until next auto-retrain

#### 3.3 Add System Health Panel

**Status page showing**:

- Current model accuracy
- Days since last retrain
- Total predictions made this week
- Top at-risk repos / authors
- Model drift alert (if accuracy <75%)

---

### Phase 4: Improve Model & Data (2-4 weeks)

#### 4.1 Hyperparameter Optimization

**What**: Grid search or Bayesian optimization

```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [5, 10, 15],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4]
}

grid_search = GridSearchCV(
    RandomForestClassifier(class_weight='balanced'),
    param_grid,
    cv=5,
    scoring='f1',
    n_jobs=-1
)

grid_search.fit(X_train, y_train)
best_model = grid_search.best_estimator_
```

**Expected gain**: +2-4% accuracy

#### 4.2 Feature Engineering Enhancements

**Add new features**:

- `is_feature_branch` — Binary from branch name
- `files_by_type` — Code vs docs vs config changes
- `commit_frequency_7d` — How often this author commits
- `repo_test_coverage` — From GitHub Actions logs
- `code_review_feedback_time` — From PR history
- `deployment_frequency_7d` — How often repo deploys
- `previous_failures_context` — Related PRs that also failed

**Expected gain**: +3-6% accuracy

#### 4.3 Ensemble Methods

**What**: Combine multiple models

```python
from sklearn.ensemble import VotingClassifier

ensemble = VotingClassifier(
    estimators=[
        ('rf', RandomForestClassifier(n_estimators=100)),
        ('xgb', XGBClassifier(n_estimators=100)),
        ('gb', GradientBoostingClassifier(n_estimators=100))
    ],
    voting='soft'
)
```

**Expected gain**: +2-3% accuracy

#### 4.4 Cold-Start Solution for New Authors

**Problem**: New devs appear high-risk (no history)

**Solution**:

- Use team/department baseline instead of individual history
- Gradually shift to individual stats as data accumulates
- Transfer learning from similar authors

```python
def get_author_failure_rate(author, repo):
    # Get directly observed rate (if enough data)
    direct = query(f"author failures / author runs")
    if direct and direct["runs"] > 20:
        return direct["rate"]

    # Fallback: repo baseline
    repo_rate = query(f"repo failures / repo runs")

    # Blend: (author_data * author_weight) + (repo_baseline * (1-weight))
    weight = min(author_runs / 20, 1.0)  # Increase weight as data accumulates
    return direct * weight + repo_rate * (1 - weight)
```

---

### Phase 5: Advanced Monitoring (1-2 weeks)

#### 5.1 Drift Detection

**What**: Statistically detect when data distribution changes

```python
from scipy.stats import ks_2samp

def detect_drift(X_recent):
    """Compare recent 100 runs vs training data distribution"""
    X_train = load_training_features()

    for feature_idx, feature_name in enumerate(FEATURE_NAMES):
        # Kolmogorov-Smirnov test
        statistic, p_value = ks_2samp(X_train[:, feature_idx],
                                      X_recent[:, feature_idx])

        if p_value < 0.05:  # Statistically significant difference
            logger.warning(f"⚠️ Drift detected in {feature_name} "
                          f"(KS stat={statistic:.3f}, p={p_value:.4f})")
            trigger_alert(org, f"Data drift in {feature_name}")
```

#### 5.2 Outlier Detection

**What**: Flag unusual predictions for manual review

```python
from sklearn.ensemble import IsolationForest

anomaly_detector = IsolationForest(contamination=0.05)
X_predictions = get_recent_feature_vectors()
anomalies = anomaly_detector.predict(X_predictions)

for i, is_anomaly in enumerate(anomalies):
    if is_anomaly:
        logger.warning(f"Unusual prediction: {X_predictions[i]}")
        flag_for_manual_review(predictions[i])
```

#### 5.3 SHAP Explanations

**What**: Local explanations beyond top 5 factors

```python
import shap

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# For each prediction, get contribution of each feature
for idx in range(len(X_test)):
    contributions = {
        FEATURE_NAMES[i]: shap_values[idx][i]
        for i in range(len(FEATURE_NAMES))
    }
    # Visualize with waterfall plot
```

---

## Implementation Roadmap

### T+0-2 weeks: Phase 1 (Feedback Loop)

- [ ] Implement GitHub webhook handler
- [ ] Create outcome reconciliation job
- [ ] Add accuracy computation endpoint
- [ ] Test with live pipeline data

**Success Criteria**:

- ✅ 80%+ of predictions linked to actual outcomes
- ✅ Accuracy metrics displayed in history endpoint
- ✅ No prediction older than 24h without outcome

---

### T+2-4 weeks: Phase 2 (Continuous Learning)

- [ ] Create model evaluation service
- [ ] Implement auto-retraining scheduler
- [ ] Add model versioning & rollback
- [ ] Set up alert system for accuracy drops

**Success Criteria**:

- ✅ Weekly model accuracy computed
- ✅ Auto-retrain triggered if accuracy <75%
- ✅ New model deployed if >1% improvement
- ✅ Zero manual intervention needed

---

### T+4-7 weeks: Phase 3 (Dashboard)

- [ ] Build accuracy trends page
- [ ] Create model comparison UI
- [ ] Add system health panel
- [ ] Create retraining logs viewer

**Success Criteria**:

- ✅ Users can view model accuracy
- ✅ Model versions comparable
- ✅ Training history visible
- ✅ Drift alerts displayed

---

### T+7-11 weeks: Phase 4 (Model Improvements)

- [ ] Hyperparameter tuning (grid search)
- [ ] Add 5-8 new features
- [ ] Implement ensemble methods
- [ ] Cold-start solution for new authors

**Success Criteria**:

- ✅ Accuracy improves 5-10% total
- ✅ New author bias eliminated
- ✅ Model training automated

---

### T+11-13 weeks: Phase 5 (Advanced Monitoring)

- [ ] Implement drift detection
- [ ] Add outlier detection
- [ ] Compute SHAP explanations
- [ ] Create advanced troubleshooting UI

**Success Criteria**:

- ✅ Data drift detected within 24h
- ✅ Anomalies flagged for review
- ✅ Full feature explanations available

---

## Deployment Considerations

### Environment Variables Required

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/withops

# GitHub Integration
GITHUB_SERVICE_URL=http://github-service:8002
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY_PATH=/secrets/github-key.pem

# Observability
ENABLE_TRACING=true
OTLP_ENDPOINT=http://jaeger:4318/v1/traces
PROMETHEUS_PORT=9091

# Model Storage
MODELS_DIR=/models

# Service
ENVIRONMENT=production
SERVICE_NAME=pipeline-prediction-service
```

### Kubernetes Manifest Considerations

**Compute Requirements**:

- **CPU**: 500m base → 2000m during training
- **Memory**: 512Mi base → 2Gi during training
- **Disk**: 5Gi for model storage
- **GPU**: Optional (only if running XGBoost optimizations)

**Scaling**:

- **HPA**: Scale based on `ml_predictions_total` metric
- **Min replicas**: 2 (for HA)
- **Max replicas**: 10 (training is CPU-intensive)

**Storage**:

- PersistentVolume for `/models` directory
- Shared across replicas
- Daily backups to S3

**Health Checks**:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8009
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8009
  initialDelaySeconds: 10
  periodSeconds: 5
```

### Monitoring & Alerting

**Key Metrics** (Prometheus):

```
ml_predictions_total{org_name, risk_level}       # Total predictions by risk level
ml_training_runs_total{org_name, status}         # Training attempts
http_request_duration_seconds                    # API latency
model_accuracy{org_name, version}                # Model accuracy per org
prediction_correct_ratio{org_name}               # Fraction of correct predictions
```

**Alert Rules**:

```yaml
- alert: PredictionAccuracyDrop
  expr: |
    (prediction_correct_ratio < 0.75) and
    (prediction_correct_ratio < base_accuracy - 0.05)
  for: 1h

- alert: ModelTrainingFailure
  expr: ml_training_runs_total{status="failed"} > 0
  for: 30m

- alert: HighPredictionLatency
  expr: histogram_quantile(0.95, http_request_duration_seconds{path="/predict"}) > 2
  for: 5m
```

### Data Retention Policy

```
WorkflowRunHistory:  Keep 6 months (1-2GB per org)
MLModelRegistry:     Keep all versions (100MB per org)
PredictionHistory:   Keep 1 year (500MB-1GB per org)

Archive Strategy:
- Compress & archive monthly (gzip to S3)
- Quarterly: Delete predictions older than 1 year
- Bi-annual: Delete models older than 2 years
```

---

## Timeline & Effort Estimate

| Phase                        | Duration       | Effort            | Priority    |
| ---------------------------- | -------------- | ----------------- | ----------- |
| Phase 1: Feedback Loop       | 2-3 weeks      | 2 engineers       | 🔴 Critical |
| Phase 2: Continuous Learning | 2-3 weeks      | 2 engineers       | 🔴 Critical |
| Phase 3: Dashboard           | 2-3 weeks      | 1 engineer        | 🟠 High     |
| Phase 4: Model Improvements  | 2-4 weeks      | 1-2 engineers     | 🟠 High     |
| Phase 5: Advanced Monitoring | 1-2 weeks      | 1 engineer        | 🟡 Medium   |
| **Total**                    | **9-15 weeks** | **2-3 engineers** | -           |

---

## Success Metrics

### By End of Phase 1

- ✅ 100% of predictions tracked to outcomes
- ✅ Accuracy metrics visible
- ✅ No manual intervention needed for outcome tracking

### By End of Phase 2

- ✅ Model retrains automatically weekly
- ✅ Accuracy improves week-over-week
- ✅ Drift detected within 24h

### By End of Phase 3

- ✅ Users can understand model health
- ✅ Trends visible over time
- ✅ Dashboard used by team for decision-making

### By End of Phase 4

- ✅ Accuracy reaches 80-85% on real data
- ✅ New authors fairly scored
- ✅ False positives reduced by 30%

### By End of Phase 5

- ✅ Drift automatically detected
- ✅ Anomalies flagged for review
- ✅ Full transparency into model reasoning

---

## Conclusion

The **Pipeline Prediction Service is 50% complete** as-is:

- ✅ Strong foundation (FastAPI, ML pipeline, databases)
- ✅ Production-ready code quality
- ❌ Missing feedback loop (critical blocker)
- ❌ No continuous learning (model becomes stale)
- ❌ No user dashboards (black box to users)

**To go from "works" to "trusted production system"**: Implement Phases 1-2 (6-8 weeks, 2-3 engineers).

**To maximize accuracy**: Layer in Phases 3-5 (additional 6-8 weeks).

---

**Document Generated**: April 10, 2026  
**Service Version**: 1.0.0  
**Last Updated**: 2026-04-10
