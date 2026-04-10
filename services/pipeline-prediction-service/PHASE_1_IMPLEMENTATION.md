# Phase 1 Implementation Guide - Feedback Loop & Outcome Tracking

**Phase**: Phase 1 (Critical)  
**Duration**: 2-3 weeks  
**Status**: ✅ IMPLEMENTATION COMPLETE

## Overview

Phase 1 enables the critical feedback loop that allows the model to:

- ✅ Track actual pipeline outcomes (success/failure)
- ✅ Compare predictions vs reality
- ✅ Calculate accuracy metrics
- ✅ Detect when model performance degrades
- ✅ Provide data for continuous learning (Phase 2)

Without Phase 1, predictions are made in a vacuum with **no way to measure success**.

---

## What Was Implemented

### 1. GitHub Webhook Handler (`api/routes/webhook.py`)

**Purpose**: Receive GitHub Actions workflow completion events in real-time

**Features**:

- ✅ HMAC-SHA256 signature verification (security)
- ✅ Extracts pipeline conclusion from webhook payload
- ✅ Updates `PredictionHistory` with actual outcomes
- ✅ Computes `prediction_correct` (did prediction match reality?)
- ✅ Publishes events to Redis for real-time updates

**Endpoint**: `POST /webhook/github/workflow-complete`

**How it works**:

```
1. GitHub sends: workflow_run.conclusion = "success" or "failure"
2. Webhook extracts: run_id, conclusion, commit_sha, org/repo
3. System finds matching predictions by commit_sha
4. Updates: actual_conclusion, actual_completed_at, prediction_correct
5. Publishes event to Redis: pipeline.workflow_completed
```

**Security**:

- HMAC signature verification required
- Set `GITHUB_WEBHOOK_SECRET` in environment
- Webhook validation prevents spoofing

---

### 2. Outcome Reconciliation Job (`core/outcome_reconciler.py`)

**Purpose**: Fallback sync for predictions that didn't get webhook callbacks

**Features**:

- ✅ Runs daily at 2 AM UTC (configurable)
- ✅ Finds predictions older than 24h without outcomes
- ✅ Queries GitHub API to find actual run status
- ✅ Updates database for missed webhooks

**Why needed?**

- Webhooks might fail (network issues, timeouts)
- Need backup mechanism to ensure all predictions get outcomes
- Prevents "stuck" predictions from accumulating

**How it works**:

```
1. Scheduler triggers daily: APScheduler @ 02:00 UTC
2. Query: SELECT * FROM PredictionHistory WHERE actual_conclusion IS NULL AND predicted_at < NOW() - 24h
3. For each prediction: Call GitHub API with commit_sha
4. Get actual run conclusion from GitHub
5. Update PredictionHistory with outcome
```

---

### 3. Accuracy Metrics Endpoints (`api/routes/metrics.py`)

**Purpose**: Expose model accuracy and prediction quality data

**Endpoints**:

#### `GET /api/pipeline-prediction/metrics/{org_name}?days=7`

```json
{
  "org_name": "NimanthaSupun",
  "time_period": { "days": 7, "start": "...", "end": "..." },
  "overall": {
    "total_predictions": 1250,
    "predictions_with_outcomes": 1200,
    "incomplete_predictions": 50,
    "correct_predictions": 1020,
    "accuracy": 0.85
  },
  "by_risk_level": {
    "low": { "total": 500, "correct": 475, "accuracy": 0.95 },
    "medium": { "total": 400, "correct": 340, "accuracy": 0.85 },
    "high": { "total": 200, "correct": 150, "accuracy": 0.75 },
    "critical": { "total": 100, "correct": 55, "accuracy": 0.55 }
  },
  "by_date": {...},
  "current_model_version": 3
}
```

#### `GET /api/pipeline-prediction/errors/{org_name}?limit=50`

Get false positives and false negatives to identify model biases

```json
{
  "false_positives": [
    {
      "prediction_id": "...",
      "predicted_fail": true,
      "actual": "success",
      "...": "..."
    }
  ],
  "false_negatives": [
    {
      "prediction_id": "...",
      "predicted_pass": true,
      "actual": "failure",
      "...": "..."
    }
  ]
}
```

#### `GET /api/pipeline-prediction/completion-status/{org_name}`

Monitor how quickly predictions get outcomes

```json
{
  "total_predictions": 1250,
  "completed": 1200,
  "pending": 50,
  "completion_rate": 0.96,
  "avg_time_to_outcome_hours": 1.5,
  "oldest_pending": { "prediction_id": "...", "hours_pending": 30 }
}
```

#### `GET /api/pipeline-prediction/health`

System health dashboard

```json
{
  "system_status": "green",
  "models": { "active_count": 3, "by_org": [...] },
  "predictions": { "pending": 150, "recent_accuracy": 0.87 }
}
```

---

### 4. Enhanced Data Collection (`core/data_collector.py`)

**New Method**: `fetch_workflow_runs_by_commit()`

- Query GitHub for runs associated with a specific commit SHA
- Used during outcome reconciliation
- Fallback to direct GitHub API if service endpoint unavailable

---

### 5. Scheduler Setup (`main.py`)

**Features**:

- ✅ APScheduler for background jobs
- ✅ Outcome reconciliation: Daily @ 02:00 UTC
- ✅ Configurable via Cron triggers
- ✅ Graceful shutdown on app teardown

---

## Setup & Deployment

### Step 1: Install Dependencies

```bash
cd services/pipeline-prediction-service

# Update dependencies
pip install -r requirements.txt

# New dependency added:
# apscheduler==3.10.4
```

### Step 2: Generate GitHub Webhook Secret

```bash
# Generate random secret
WEBHOOK_SECRET=$(openssl rand -base64 32)
echo $WEBHOOK_SECRET

# Add to .env and Kubernetes secrets
echo "GITHUB_WEBHOOK_SECRET=$WEBHOOK_SECRET" >> .env
```

### Step 3: Configure GitHub Webhook

**In GitHub Organization Settings**:

1. Go to: **Organization → Settings → Webhooks**
2. Click **Add Webhook**
3. Fill in details:
   ```
   Payload URL: https://withops.your-domain.com/webhook/github/workflow-complete
   Content type: application/json
   Secret: [paste the generated secret]
   Which events would you like to trigger this webhook?
   → Select: Workflow runs
   → Make sure ONLY "Workflow runs" is checked
   Active: ✓ (checked)
   ```
4. Click **Add Webhook**
5. Verify green checkmark appears (GitHub tests connectivity)

### Step 4: Update Environment Variables

In `.env` or Kubernetes secrets:

```bash
# .env file
GITHUB_WEBHOOK_SECRET=your_generated_secret_here
GITHUB_TOKEN=github_pat_xxxxx  # Optional, for GitHub API fallback
SERVICE_NAME=pipeline-prediction-service
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
```

### Step 5: Update Kubernetes Secrets

If using Kubernetes:

```bash
# Create/update secret
kubectl -n withops create secret generic pipeline-prediction-secrets \
  --from-literal=GITHUB_WEBHOOK_SECRET="$WEBHOOK_SECRET" \
  --from-literal=GITHUB_TOKEN="github_pat_xxxxx" \
  --dry-run=client -o yaml | kubectl apply -f -

# Reference in K8s deployment:
# env:
# - name: GITHUB_WEBHOOK_SECRET
#   valueFrom:
#     secretKeyRef:
#       name: pipeline-prediction-secrets
#       key: GITHUB_WEBHOOK_SECRET
```

### Step 6: Database Setup

The system automatically creates the necessary tables on startup.

**Verify tables exist**:

```bash
# Connect to PostgreSQL
psql -h your-db-host -U postgres -d withops

# Check tables
\dt prediction_history
\dt ml_model_registry
\dt workflow_run_history

# Should show:
# public | prediction_history        | table
# public | ml_model_registry          | table
# public | workflow_run_history       | table
```

### Step 7: Deploy Service

**Development**:

```bash
cd services/pipeline-prediction-service
python main.py
# Runs on http://localhost:8009
```

**Docker**:

```bash
docker build -t pipeline-prediction:phase-1 .
docker run -e GITHUB_WEBHOOK_SECRET=$WEBHOOK_SECRET \
           -e DATABASE_URL=postgresql+asyncpg://... \
           -p 8009:8009 \
           pipeline-prediction:phase-1
```

**Kubernetes**:

```bash
# Update k8s/pipeline-prediction-service.yaml
# - Add GITHUB_WEBHOOK_SECRET to env section
# - Ensure port 8009 exposed for webhook

kubectl apply -f k8s/pipeline-prediction-service.yaml
kubectl port-forward -n withops svc/pipeline-prediction-service 8009:8009
```

### Step 8: Verify Setup

```bash
# Test webhook endpoint
curl -X POST http://localhost:9000/webhook/github/workflow-complete \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=invalid" \
  -d '{"action": "ping"}'
# Should respond with 401 (invalid signature)

# Test health check
curl http://localhost:9000/api/pipeline-prediction/health
# Should respond with green status

# Test metrics
curl http://localhost:9000/api/pipeline-prediction/metrics/NimanthaSupun?days=7
# Should respond with metrics (or "no_data" if no predictions yet)
```

---

## Testing Phase 1

### Manual Testing

1. **Generate training data and train model**:

```bash
curl -X POST http://localhost:9000/api/pipeline-prediction/generate-data \
  -H "Content-Type: application/json" \
  -d '{"org_name": "NimanthaSupun", "num_runs": 1500}'

curl -X POST http://localhost:9000/api/pipeline-prediction/train \
  -H "Content-Type: application/json" \
  -d '{"org_name": "NimanthaSupun", "model_type": "random_forest"}'
```

2. **Make a prediction**:

```bash
curl -X POST http://localhost:9000/api/pipeline-prediction/predict \
  -H "Content-Type: application/json" \
  -d '{
    "org_name": "NimanthaSupun",
    "repo_name": "WithOps",
    "branch": "main",
    "author": "supun",
    "files_changed": 10,
    "additions": 100,
    "deletions": 50
  }'
```

3. **Simulate webhook (manual test)**:

```bash
# Generate valid signature for testing
python -c "
import hmac, hashlib, json
secret = 'test_secret'
payload = json.dumps({'action': 'completed', 'workflow_run': {'id': 123, 'conclusion': 'success', 'repository': {'full_name': 'NimanthaSupun/WithOps'}, 'head_commit': {'sha': 'abc123'}}}).encode()
sig = 'sha256=' + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
print(sig)
"

# Send webhook with valid signature
curl -X POST http://localhost:9000/webhook/github/workflow-complete \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=<generated-signature>" \
  -d '{
    "action": "completed",
    "workflow_run": {
      "id": 123,
      "conclusion": "success",
      "repository": {"full_name": "NimanthaSupun/WithOps"},
      "head_commit": {"sha": "abc123"}
    }
  }'
```

4. **Check metrics updated**:

```bash
curl http://localhost:9000/api/pipeline-prediction/metrics/NimanthaSupun?days=1
# Should show prediction_correct: true/false
```

### Automated Testing

Create `tests/test_phase1_webhook.py`:

```python
import pytest
import hmac
import hashlib
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_webhook_signature_verification():
    """Test that invalid signatures are rejected"""
    payload = b'{"action": "completed", "workflow_run": {}}'
    invalid_sig = "sha256=invalid"

    response = client.post(
        "/webhook/github/workflow-complete",
        content=payload,
        headers={"X-Hub-Signature-256": invalid_sig}
    )
    assert response.status_code == 401

def test_webhook_success():
    """Test successful outcome recording"""
    response = client.post(
        "/api/pipeline-prediction/metrics/TestOrg?days=1"
    )
    assert response.status_code == 200
    data = response.json()
    assert "overall" in data
    assert "accuracy" in data["overall"]
```

---

## Monitoring & Observability

### Prometheus Metrics Added

The service now tracks:

```
ml_predictions_updated{org_name, status}          # Webhook updates
webhook_processing_errors{endpoint}               # Webhook errors
outcome_reconciliation_jobs{org_name, status}     # Reconciliation runs
prediction_accuracy{org_name, risk_level}         # Accuracy by risk level
```

### Log Examples

**Successful webhook**:

```
2026-04-10 15:30:45 INFO 📡 Webhook received: NimanthaSupun/WithOps run #42 conclusion=success
2026-04-10 15:30:45 INFO   ✅ Updated prediction abc123: predicted=PASS actual=PASS correct=True
2026-04-10 15:30:45 INFO ✅ Webhook processed: Updated 1 predictions
```

**Reconciliation run**:

```
2026-04-10 02:00:00 INFO 🔄 Starting outcome reconciliation...
2026-04-10 02:00:05 INFO   NimanthaSupun: Reconciled 45 predictions
2026-04-10 02:00:10 INFO ✅ Reconciliation complete: 120 predictions updated across 3 orgs
```

---

## Troubleshooting

### Webhook Not Arriving

1. **Check GitHub webhook logs**:
   - GitHub → Org Settings → Webhooks → Click webhook → Deliveries tab
   - Look for failed deliveries (red X)
   - Click on failed delivery to see response code

2. **Verify firewall/networking**:

   ```bash
   # Test if GitHub can reach your endpoint
   curl -v https://withops.your-domain.com/webhook/github/workflow-complete
   # Should get 405 (POST required) or 401 if no signature
   ```

3. **Check secret config**:
   ```bash
   # Verify secret is set in environment
   echo $GITHUB_WEBHOOK_SECRET
   # Should be non-empty
   ```

### Predictions Not Getting Outcomes

1. **Check prediction history**:

```bash
# View predictions without outcomes
psql -h... -d withops <<EOF
SELECT prediction_id, predicted_at, actual_conclusion
FROM prediction_history
WHERE actual_conclusion IS NULL
ORDER BY predicted_at DESC
LIMIT 10;
EOF
```

2. **Verify reconciliation is running**:

```bash
# Check logs for reconciliation job
docker logs pipeline-prediction-service | grep "reconciliation"
# Should show daily runs at 02:00 UTC
```

3. **Manually trigger reconciliation**:

```bash
# Can also trigger via API for testing
curl -X POST http://localhost:9000/api/pipeline-prediction/reconcile-now
```

### Accuracy Metrics Not Available

1. **Check if predictions have outcomes**:

```bash
curl http://localhost:9000/api/pipeline-prediction/metrics/YourOrg?days=7
# If no_data, need to wait for webhooks/reconciliation
```

2. **Verify database connectivity**:

```bash
curl http://localhost:9000/api/pipeline-prediction/health
# Check database status
```

---

## Next Steps

After Phase 1 is deployed and working:

### Short-term (Week 1-2)

- ✅ Verify webhooks delivering successfully (check GitHub logs)
- ✅ Confirm reconciliation job running (check logs @ 02:00 UTC)
- ✅ View metrics dashboard (hit metrics endpoint)
- ✅ Identify any accuracy issues

### Medium-term (Week 3-4)

- 🔄 **Proceed to Phase 2**: Auto-Retraining based on accuracy
- 🔄 Set up drift detection alerting
- 🔄 Create monitoring dashboards

### Long-term

- 🔄 Phase 3: Frontend accuracy dashboard
- 🔄 Phase 4: Model optimization
- 🔄 Phase 5: Advanced monitoring

---

## Success Criteria for Phase 1

Phase 1 is complete when:

- ✅ GitHub webhook configured and receiving events
- ✅ >90% of predictions linked to actual outcomes within 24h
- ✅ Accuracy metrics computed and displayed
- ✅ No errors in logs for webhook processing
- ✅ Reconciliation job running successfully daily
- ✅ False positives/negatives identifiable via metrics API
- ✅ System health dashboard green

---

## Quick Reference - Key Files

| File                         | Purpose                                     |
| ---------------------------- | ------------------------------------------- |
| `api/routes/webhook.py`      | GitHub webhook handler                      |
| `core/outcome_reconciler.py` | Daily reconciliation job                    |
| `api/routes/metrics.py`      | Accuracy & metrics endpoints                |
| `core/data_collector.py`     | Enhanced with commit-based queries          |
| `main.py`                    | Updated with scheduler & route registration |
| `.env.example`               | Added webhook secret config                 |

---

**Phase 1 Status**: ✅ READY FOR DEPLOYMENT

Next: [Phase 2 Implementation Guide](../PHASE_2_IMPLEMENTATION.md)
