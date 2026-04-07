# Implementation Plan: CI/CD Pipeline Failure Prediction Service

> **Project**: WithOps DevSecOps Platform
> **Service Name**: `pipeline-prediction-service`
> **Internal Port**: `8009`
> **External Port**: `9109`
> **Kong Route**: `/api/pipeline-prediction/*`

---

## 1. Problem Statement

Developers push code and wait for CI/CD pipelines to complete — often 5-15 minutes — only to discover failures. This wastes compute resources and developer time. By analyzing historical workflow run patterns, we can **predict the likelihood of failure before or during a run** and explain the risk factors.

## 2. Solution

Build a FastAPI microservice that:
1. **Collects** historical GitHub Actions workflow run data via the existing `github-service`
2. **Engineers features** from temporal, code-change, author, and workflow metadata
3. **Trains** a Random Forest / XGBoost classifier on labeled run outcomes
4. **Serves predictions** via a REST API — "Will this pipeline pass or fail?"
5. **Explains** predictions with feature importance (top risk factors)
6. **Exposes** the capability via MCP for AI assistant integration

---

## 3. Architecture

### 3.1 System Context

```
Frontend (SvelteKit)
    │
    ▼
Kong Gateway (:9000)
    ├── /api/pipeline-prediction/* → pipeline-prediction-service:8009
    ├── /api/github/*              → github-service:8002
    └── /api/workspace-intel/*     → workspace-intelligence-service:8004
    
pipeline-prediction-service
    ├── Fetches training data from → github-service (internal HTTP)
    ├── Stores run history in     → PostgreSQL (Supabase)
    ├── Caches predictions in     → Redis
    ├── Publishes events to       → Redis Pub/Sub → Events Hub → WebSocket
    └── Exposes metrics to        → Prometheus
```

### 3.2 Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                    TRAINING FLOW                        │
│                                                         │
│  github-service ──(HTTP)──► Data Collector              │
│                              │                          │
│                              ▼                          │
│                         Feature Extractor               │
│                              │                          │
│                              ▼                          │
│                     Training Pipeline                   │
│                     (scikit-learn / XGBoost)            │
│                              │                          │
│                              ▼                          │
│                    models/model_v{N}.joblib             │
│                    + models/metadata.json               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   INFERENCE FLOW                        │
│                                                         │
│  Kong ──► /api/pipeline-prediction/predict              │
│              │                                          │
│              ▼                                          │
│         Load cached model from memory                   │
│              │                                          │
│              ▼                                          │
│         Extract features from request                   │
│         + fetch live context from github-service        │
│              │                                          │
│              ▼                                          │
│         model.predict_proba(features)                   │
│              │                                          │
│              ▼                                          │
│         Return { probability, risk_level,               │
│                  risk_factors[], recommendation }       │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Directory Structure

```
services/pipeline-prediction-service/
├── .env                          # Local environment variables
├── .env.example                  # Template for env vars
├── Dockerfile                    # Multi-stage Docker build
├── requirements.txt              # Python dependencies
├── main.py                       # FastAPI application entry point
├── api/
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       ├── prediction.py         # POST /predict, GET /predict/{org}/{repo}
│       ├── training.py           # POST /train, GET /training/status
│       └── health.py             # GET /health, GET /model/info
├── core/
│   ├── __init__.py
│   ├── data_collector.py         # Fetch workflow runs from github-service
│   ├── feature_engineer.py       # Transform raw data → feature vectors
│   ├── model_manager.py          # Load/save/version models
│   ├── predictor.py              # Inference engine with explainability
│   ├── trainer.py                # Training pipeline (fit, evaluate, save)
│   ├── redis_cache.py            # Redis caching (reuse pattern)
│   └── event_bus.py              # Event publishing (reuse pattern)
├── database/
│   ├── __init__.py
│   ├── config.py                 # DB connection manager (reuse pattern)
│   └── models.py                 # SQLAlchemy models for this service
├── models/                       # Serialized ML models (gitignored)
│   ├── .gitkeep
│   └── (model_v1.joblib)         # Generated at runtime
└── tests/
    ├── test_features.py
    ├── test_predictor.py
    └── test_api.py
```
---

## 5. Database Schema

### 5.1 New Tables (in existing Supabase PostgreSQL)

```sql
-- Stores raw workflow run data collected from GitHub
CREATE TABLE workflow_run_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id VARCHAR NOT NULL,
    org_name        VARCHAR NOT NULL,
    repo_name       VARCHAR NOT NULL,
    repo_full_name  VARCHAR NOT NULL,
    
    -- GitHub run metadata
    github_run_id   BIGINT NOT NULL UNIQUE,
    workflow_name   VARCHAR NOT NULL,
    workflow_path   VARCHAR,
    run_number      INTEGER,
    event           VARCHAR,          -- push, pull_request, schedule, etc.
    status          VARCHAR,          -- completed, in_progress, queued
    conclusion      VARCHAR,          -- success, failure, cancelled, timed_out
    
    -- Temporal features
    created_at      TIMESTAMP NOT NULL,
    updated_at      TIMESTAMP,
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    duration_seconds INTEGER,         -- Computed: completed_at - started_at
    
    -- Commit metadata
    head_branch     VARCHAR,
    head_sha        VARCHAR,
    commit_message  TEXT,
    
    -- Author info
    actor_login     VARCHAR,
    actor_id        INTEGER,
    
    -- Code change metrics (fetched from commit)
    files_changed   INTEGER DEFAULT 0,
    additions       INTEGER DEFAULT 0,
    deletions       INTEGER DEFAULT 0,
    
    -- Collection metadata
    collected_at    TIMESTAMP DEFAULT NOW(),
    features_json   JSONB             -- Pre-computed feature vector (cached)
);

CREATE INDEX idx_wfr_org_repo ON workflow_run_history(org_name, repo_name);
CREATE INDEX idx_wfr_conclusion ON workflow_run_history(conclusion);
CREATE INDEX idx_wfr_actor ON workflow_run_history(actor_login);
CREATE INDEX idx_wfr_created ON workflow_run_history(created_at DESC);

-- Stores trained model metadata and performance metrics
CREATE TABLE ml_model_registry (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_name        VARCHAR NOT NULL,
    model_version   INTEGER NOT NULL,
    model_type      VARCHAR NOT NULL,  -- random_forest, xgboost, gradient_boosting
    
    -- Training metadata
    trained_at      TIMESTAMP DEFAULT NOW(),
    training_samples INTEGER,
    feature_count   INTEGER,
    feature_names   JSONB,            -- List of feature column names
    
    -- Performance metrics
    accuracy        FLOAT,
    precision_score FLOAT,
    recall_score    FLOAT,
    f1_score        FLOAT,
    auc_roc         FLOAT,
    confusion_matrix JSONB,           -- [[TP, FP], [FN, TN]]
    
    -- Feature importance
    feature_importance JSONB,         -- {feature_name: importance_score}
    
    -- Model file
    model_path      VARCHAR,          -- Path to .joblib file
    is_active       BOOLEAN DEFAULT TRUE,
    
    -- Class distribution in training data
    class_distribution JSONB,         -- {success: N, failure: M}
    
    UNIQUE(org_name, model_version)
);

-- Stores prediction history for auditing and feedback loops
CREATE TABLE prediction_history (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_name            VARCHAR NOT NULL,
    repo_name           VARCHAR NOT NULL,
    branch              VARCHAR,
    commit_sha          VARCHAR,
    author              VARCHAR,
    
    -- Prediction result
    failure_probability FLOAT NOT NULL,
    risk_level          VARCHAR NOT NULL,  -- low, medium, high, critical
    risk_factors        JSONB,
    recommendation      TEXT,
    
    -- Model used
    model_version       INTEGER,
    model_type          VARCHAR,
    
    -- Actual outcome (filled in later when run completes)
    actual_conclusion   VARCHAR,          -- success, failure, null (pending)
    prediction_correct  BOOLEAN,          -- Computed after actual is known
    
    -- Timestamps
    predicted_at        TIMESTAMP DEFAULT NOW(),
    actual_completed_at TIMESTAMP
);

CREATE INDEX idx_ph_org_repo ON prediction_history(org_name, repo_name);
CREATE INDEX idx_ph_predicted ON prediction_history(predicted_at DESC);
```

---

## 6. Feature Engineering (Detailed)

### 6.1 Feature Vector (19 features)

| # | Feature | Type | How Computed |
|---|---------|------|-------------|
| 1 | `hour_of_day` | int (0-23) | From `created_at` timestamp |
| 2 | `day_of_week` | int (0-6) | Monday=0 ... Sunday=6 |
| 3 | `is_weekend` | bool (0/1) | day_of_week >= 5 |
| 4 | `is_business_hours` | bool (0/1) | 9 <= hour <= 17 AND not weekend |
| 5 | `files_changed` | int | From GitHub commit API |
| 6 | `additions` | int | Lines added |
| 7 | `deletions` | int | Lines deleted |
| 8 | `change_ratio` | float | additions / max(deletions, 1) |
| 9 | `total_changes` | int | additions + deletions |
| 10 | `branch_type` | int (encoded) | 0=main/master, 1=develop, 2=feature/*, 3=hotfix/*, 4=other |
| 11 | `is_pull_request` | bool (0/1) | event == "pull_request" |
| 12 | `event_type` | int (encoded) | push=0, pull_request=1, schedule=2, workflow_dispatch=3 |
| 13 | `workflow_name_encoded` | int | LabelEncoded workflow name |
| 14 | `author_total_runs` | int | Total runs by this author in this repo (last 90 days) |
| 15 | `author_failure_rate` | float (0-1) | author failures / author total runs (last 90 days) |
| 16 | `repo_failure_rate_7d` | float (0-1) | Repo-wide failure rate in last 7 days |
| 17 | `avg_duration_last_10` | float | Avg run duration of last 10 completed runs (seconds) |
| 18 | `failures_last_24h` | int | Count of failures in this repo in last 24 hours |
| 19 | `commit_message_length` | int | len(commit_message) |

### 6.2 Label

```python
# Binary classification
label = 1 if conclusion in ["failure", "timed_out"] else 0
# Exclude: "cancelled", "skipped" (not informative)
```

### 6.3 Data Preprocessing

```python
# Handle missing values
- files_changed, additions, deletions: fill with 0
- author_failure_rate: fill with repo_failure_rate_7d (cold-start fallback)
- avg_duration_last_10: fill with global median

# Handle class imbalance (most pipelines succeed)
- Use SMOTE or class_weight="balanced" in the classifier
- Expected ratio: ~80% success, ~20% failure

# Feature scaling
- StandardScaler on continuous features (for XGBoost comparison)
- Not strictly needed for Random Forest but good practice
```

---

## 7. API Specification (Detailed)

### 7.1 Prediction Endpoints

#### `POST /api/pipeline-prediction/predict`
Predict failure probability for a new/upcoming run.

**Request:**
```json
{
    "org_name": "NimanthaSupun",
    "repo_name": "WithOps",
    "branch": "feature/new-dashboard",
    "author": "supun",
    "commit_sha": "abc123def",
    "event_type": "push",
    "files_changed": 15,
    "additions": 342,
    "deletions": 89,
    "commit_message": "feat: add new dashboard component with API integration"
}
```

**Response (200):**
```json
{
    "prediction": {
        "failure_probability": 0.72,
        "success_probability": 0.28,
        "risk_level": "high",
        "confidence": 0.85
    },
    "risk_factors": [
        {
            "factor": "High file count",
            "detail": "15 files changed (avg for successful runs: 4.2)",
            "importance": 0.23
        },
        {
            "factor": "Author history",
            "detail": "Author has 35% failure rate in last 90 days",
            "importance": 0.18
        },
        {
            "factor": "Off-hours commit",
            "detail": "Pushed at 11:30 PM (failure rate 2.1x higher after 10 PM)",
            "importance": 0.14
        }
    ],
    "recommendation": "Consider running tests locally first. This commit changes 15 files — similar-sized commits have failed 68% of the time in this repository.",
    "model_info": {
        "version": 3,
        "type": "random_forest",
        "accuracy": 0.84,
        "trained_on_samples": 847
    }
}
```

#### `GET /api/pipeline-prediction/history/{org_name}/{repo_name}`
Get prediction history for a repository.

**Response (200):**
```json
{
    "predictions": [
        {
            "id": "uuid",
            "predicted_at": "2026-04-01T10:30:00Z",
            "branch": "feature/auth-fix",
            "failure_probability": 0.32,
            "risk_level": "low",
            "actual_conclusion": "success",
            "prediction_correct": true
        }
    ],
    "stats": {
        "total_predictions": 142,
        "accuracy": 0.83,
        "true_positives": 28,
        "false_positives": 6,
        "true_negatives": 90,
        "false_negatives": 18
    }
}
```

### 7.2 Training Endpoints

#### `POST /api/pipeline-prediction/train`
Trigger model training for an organization.

**Request:**
```json
{
    "org_name": "NimanthaSupun",
    "force_refresh": true,
    "model_type": "random_forest"
}
```

**Response (202 Accepted):**
```json
{
    "task_id": "uuid",
    "status": "training_started",
    "message": "Collecting data and training model for NimanthaSupun. This may take 1-2 minutes."
}
```

#### `GET /api/pipeline-prediction/train/status/{task_id}`
Check training task status.

**Response:**
```json
{
    "task_id": "uuid",
    "status": "completed",
    "progress": {
        "data_collection": "completed (847 runs collected)",
        "feature_engineering": "completed (19 features extracted)", 
        "model_training": "completed",
        "evaluation": "completed"
    },
    "metrics": {
        "accuracy": 0.84,
        "precision": 0.79,
        "recall": 0.73,
        "f1_score": 0.76,
        "auc_roc": 0.88
    }
}
```

### 7.3 Model Info Endpoints

#### `GET /api/pipeline-prediction/model/{org_name}`
Get current model info for an organization.

#### `GET /api/pipeline-prediction/feature-importance/{org_name}`
Get feature importance chart data.

### 7.4 Health & Metrics

#### `GET /health`
```json
{
    "status": "healthy",
    "service": "pipeline-prediction-service",
    "model_loaded": true,
    "active_models": 2
}
```

#### `GET /metrics` (Prometheus)

---

## 8. Docker & Infrastructure Integration

### 8.1 docker-compose.yml Addition

```yaml
  # Pipeline Prediction Service - ML-based CI/CD failure prediction
  pipeline-prediction-service:
    build:
      context: .
      dockerfile: services/pipeline-prediction-service/Dockerfile
    container_name: withops-pipeline-prediction
    env_file:
      - services/pipeline-prediction-service/.env
    ports:
      - "9109:8009"
    depends_on:
      - redis
      - github-service
      - prometheus
    environment:
      - DATABASE_URL=postgresql://postgres.fcmcsbmsntmpeyjltqbi:5m19NTF6y0x1fJgr@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
      - REDIS_URL=redis://redis:6379
      - GITHUB_SERVICE_URL=http://github-service:8002
      - ENABLE_METRICS=true
      - ENABLE_TRACING=true
      - OTLP_ENDPOINT=http://jaeger:4318/v1/traces
    restart: unless-stopped
    volumes:
      - pipeline_models:/app/models  # Persist trained models
```

Add to `volumes:` section:
```yaml
  pipeline_models:
    driver: local
```

### 8.2 Kong Gateway Addition (infra/kong/kong.yml)

```yaml
  # Pipeline Prediction Service - ML-based CI/CD failure prediction
  - name: pipeline-prediction-service
    url: http://pipeline-prediction-service:8009
    routes:
      - name: pipeline-prediction-routes
        paths:
          - /api/pipeline-prediction
        strip_path: false
```

### 8.3 Prometheus Scrape Target (infra/monitoring/prometheus.yml)

```yaml
  - job_name: "pipeline-prediction-service"
    static_configs:
      - targets: ["pipeline-prediction-service:8009"]
        labels:
          service: "pipeline-prediction-service"
    metrics_path: "/metrics"
```

### 8.4 CI/CD Pipeline Update (.github/workflows/ci-cd.yml)

Add to `backend-ci` matrix:
```yaml
- { name: pipeline-prediction-service, path: services/pipeline-prediction-service }
```

Add to `build-and-push` matrix:
```yaml
- { name: pipeline-prediction-service, dockerfile: services/pipeline-prediction-service/Dockerfile }
```

### 8.5 K8s Manifest (k8s/pipeline-prediction-service.yaml)
Create a new manifest following the pattern of existing service YAMLs.

---

## 9. Cold Start Strategy

When a new organization/repo has zero historical data:

| Scenario | Handling |
|----------|---------|
| **No model trained yet** | Return `{"risk_level": "unknown", "message": "Insufficient data. Train a model first by clicking 'Collect Data'."}` |
| **< 50 runs collected** | Use **heuristic rules** instead of ML (e.g., >10 files = medium risk, weekend = higher risk) |
| **50-200 runs** | Train model but flag low confidence: `"confidence": "low"` |
| **200+ runs** | Full ML prediction with normal confidence |
| **Author not seen before** | Use repo-wide averages for author-specific features |

---

## 10. Training Pipeline Detail

```python
# core/trainer.py - Simplified flow

async def train_model(org_name: str, model_type: str = "random_forest"):
    # Step 1: Collect data
    runs = await data_collector.fetch_all_runs(org_name)  # From github-service
    
    # Step 2: Filter valid runs (exclude cancelled, skipped)
    valid_runs = [r for r in runs if r["conclusion"] in ["success", "failure", "timed_out"]]
    
    # Step 3: Engineer features  
    X, y, feature_names = feature_engineer.transform(valid_runs)
    
    # Step 4: Train-test split (80/20, stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    
    # Step 5: Train model
    if model_type == "random_forest":
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            class_weight="balanced",  # Handle imbalance
            random_state=42,
            n_jobs=-1
        )
    elif model_type == "xgboost":
        model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            scale_pos_weight=len(y_train[y_train==0]) / max(len(y_train[y_train==1]), 1),
            random_state=42
        )
    
    model.fit(X_train, y_train)
    
    # Step 6: Evaluate
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
        "auc_roc": roc_auc_score(y_test, y_proba),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist()
    }
    
    # Step 7: Extract feature importance
    importance = dict(zip(feature_names, model.feature_importances_))
    
    # Step 8: Save model  
    version = await model_manager.save(model, org_name, metrics, importance)
    
    return version, metrics
```

---

## 11. Explainability — Risk Factor Generation

```python
# core/predictor.py

def explain_prediction(features: dict, feature_importance: dict, prediction_proba: float):
    """Generate human-readable risk factors from feature values and importance"""
    
    risk_factors = []
    
    # Sort features by importance
    sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
    
    for feature_name, importance in sorted_features[:5]:  # Top 5 factors
        value = features[feature_name]
        
        # Generate human-readable explanation
        if feature_name == "files_changed" and value > 10:
            risk_factors.append({
                "factor": "Large changeset",
                "detail": f"{value} files changed (threshold: 10)",
                "importance": round(importance, 3)
            })
        elif feature_name == "author_failure_rate" and value > 0.3:
            risk_factors.append({
                "factor": "Author failure history",
                "detail": f"Author has {value:.0%} failure rate in recent history",
                "importance": round(importance, 3)
            })
        elif feature_name == "is_weekend" and value == 1:
            risk_factors.append({
                "factor": "Weekend deployment",
                "detail": "Weekend commits have higher failure rates historically",
                "importance": round(importance, 3)
            })
        elif feature_name == "failures_last_24h" and value > 2:
            risk_factors.append({
                "factor": "Recent instability",
                "detail": f"{value} failures in the last 24 hours in this repo",
                "importance": round(importance, 3)
            })
        # ... more rules for each feature
    
    return risk_factors
```

---

## 12. Frontend Integration

### 12.1 New Components

**Pipeline Risk Badge** — Shown in workspace dashboard and repo views:
```
┌─────────────────────────────────────────┐
│  🔴 Pipeline Risk: HIGH (72%)           │
│  ├ 15 files changed (avg: 4.2)          │
│  ├ Author failure rate: 35%             │
│  └ Off-hours commit (11:30 PM)          │
│                                         │
│  💡 Consider running tests locally first│
└─────────────────────────────────────────┘
```

**Model Performance Dashboard** — Under Intelligence page:
- Accuracy, precision, recall gauges
- Feature importance bar chart (D3.js)
- Prediction history timeline
- Confusion matrix heatmap

### 12.2 Frontend Files to Create/Modify

| File | Action |
|------|--------|
| `frontend/src/lib/api/pipelinePrediction.js` | **Create** — API client for prediction endpoints |
| `frontend/src/routes/github/workspace/[org]/intelligence/+page.svelte` | **Modify** — Add Pipeline Risk section |
| `frontend/src/routes/github/workspace/[org]/+page.svelte` | **Modify** — Add risk badge to workspace overview |
| `frontend/src/lib/components/PipelineRiskBadge.svelte` | **Create** — Reusable risk badge component |
| `frontend/src/lib/components/ModelPerformance.svelte` | **Create** — Model metrics dashboard |

---

## 13. Event Bus Integration

### Events Published

| Event | Channel | When |
|-------|---------|------|
| `pipeline.prediction.completed` | `pipeline_prediction_events` | After each prediction |
| `pipeline.model.trained` | `pipeline_prediction_events` | After model training completes |
| `pipeline.data.collected` | `pipeline_prediction_events` | After data collection finishes |

### Events Consumed (from github-service)

| Event | Source Channel | Action |
|-------|---------------|--------|
| `workflow_run.completed` | `github_events` | Update `actual_conclusion` in prediction_history, collect new training data point |

Backend Events Hub will subscribe to `pipeline_prediction_events` and forward to WebSocket for frontend real-time updates.

---

## 14. MCP Integration

### Tool Definition
```python
Tool(
    name="predict_pipeline_failure",
    description="Predict whether a CI/CD pipeline run will pass or fail based on commit context",
    inputSchema={
        "type": "object",
        "properties": {
            "org_name": {"type": "string", "description": "GitHub organization name"},
            "repo_name": {"type": "string", "description": "Repository name"},
            "branch": {"type": "string", "description": "Branch name"},
            "author": {"type": "string", "description": "Commit author username"},
            "files_changed": {"type": "integer", "description": "Number of files changed"}
        },
        "required": ["org_name", "repo_name"]
    }
)
```

---

## 15. Implementation Phases

### Phase 1: Service Skeleton & Data Collection (3-4 days)

**Deliverables:**
1. Create `services/pipeline-prediction-service/` with full directory structure
2. `main.py` — FastAPI app with health check, metrics, tracing (copy pattern from other services)
3. `Dockerfile` — Multi-stage build (copy pattern from workspace-intelligence-service)
4. `requirements.txt` — FastAPI + scikit-learn + xgboost + joblib
5. `.env` / `.env.example`
6. `database/config.py` + `database/models.py` — SQLAlchemy models for the 3 tables
7. `core/data_collector.py` — Fetch workflow runs from github-service via HTTP
8. Add service to `docker-compose.yml`, `kong.yml`, `prometheus.yml`
9. Add to CI/CD pipeline matrix

**Verification:** Service starts, returns `/health`, appears in Prometheus targets.

### Phase 2: Feature Engineering & Training Pipeline (3-4 days)

**Deliverables:**
1. `core/feature_engineer.py` — Transform raw run data → 19-feature vector
2. `core/trainer.py` — Full training pipeline with evaluation metrics
3. `core/model_manager.py` — Save/load/version models on disk + register in DB
4. `api/routes/training.py` — POST /train + GET /train/status endpoints
5. Collect real data from your GitHub organizations
6. Train initial model, record baseline metrics

**Verification:** Can trigger training via API, model saved to disk, metrics in response.

### Phase 3: Inference & Explainability (2-3 days)

**Deliverables:**
1. `core/predictor.py` — Load model, run inference, generate risk factors
2. `api/routes/prediction.py` — POST /predict + GET /history endpoints
3. Cold-start handling (heuristic fallback)
4. Redis caching for predictions
5. Event bus integration (publish prediction events)

**Verification:** Can make predictions via API with risk factor explanations.

### Phase 4: Frontend Integration (2-3 days)

**Deliverables:**
1. `PipelineRiskBadge.svelte` component
2. `ModelPerformance.svelte` component
3. API client (`pipelinePrediction.js`)
4. Integration into Intelligence dashboard
5. Real-time WebSocket updates for predictions

**Verification:** Risk badges visible in UI, training triggered from dashboard.

### Phase 5: MCP + Polish (1-2 days)

**Deliverables:**
1. Add `predict_pipeline_failure` tool to MCP server
2. K8s manifest
3. API documentation
4. End-to-end testing

---

## 16. Dependencies / Requirements

```
# Core
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
httpx[http2]==0.25.0

# Database
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
asyncpg==0.29.0

# ML/Data Science
scikit-learn==1.3.2
xgboost==2.0.3
pandas==2.1.4
numpy==1.26.2
joblib==1.3.2
imbalanced-learn==0.11.0   # For SMOTE

# Caching & Events
redis[asyncio]==5.0.1

# Monitoring
prometheus-client==0.19.0
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-instrumentation-fastapi==0.42b0
opentelemetry-exporter-otlp==1.21.0
```

---

## 17. Risk Factors & Mitigations

| Risk | Mitigation |
|------|-----------|
| Not enough training data (<50 runs) | Heuristic fallback + synthetic data generation |
| Class imbalance (most runs succeed) | SMOTE + class_weight="balanced" |
| Model staleness | Auto-retrain weekly or when accuracy drops below threshold |
| github-service API rate limits | Batch collection during off-hours, cache aggressively |
| Cold-start for new repos/authors | Use org-wide averages as fallback features |
| Model file too large for container | Random Forest with max_depth=10 stays under 5MB |

---

## 18. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Model Accuracy** | > 80% | `accuracy_score` on test set |
| **Precision (failure)** | > 70% | Minimize false alarms |
| **Recall (failure)** | > 65% | Catch most actual failures |
| **AUC-ROC** | > 0.80 | Overall discriminative ability |
| **Inference Latency** | < 200ms | Time from request to response |
| **Training Time** | < 2 min | For 1000 runs dataset |
