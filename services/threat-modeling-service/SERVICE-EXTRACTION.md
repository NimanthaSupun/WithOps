# Threat Modeling Service - Extraction Complete ✅

## Service Overview

The Threat Modeling Service has been successfully extracted from the monolithic backend into an independent microservice.

**Port:** 8003 (Docker: 8103)  
**Service Name:** `threat-modeling-service`  
**Status:** Ready for testing

---

## 📁 Service Structure

```
services/threat-modeling-service/
├── app/
│   ├── core/                    # Core utilities
│   │   ├── ai_client.py        # AI Service HTTP client
│   │   ├── security.py         # JWT authentication
│   │   ├── document_processor.py # PDF/DOCX processing
│   │   └── __init__.py
│   ├── models/                  # Pydantic schemas
│   │   ├── schemas.py          # Request/response models
│   │   └── __init__.py
│   ├── routes/                  # API endpoints
│   │   ├── threat_models.py    # All threat modeling routes
│   │   └── __init__.py
│   ├── services/                # Business logic
│   │   ├── threat_analysis.py  # STRIDE analysis, risk scoring
│   │   └── __init__.py
│   └── __init__.py
├── database/                    # Database layer
│   ├── models.py               # 7 threat modeling tables
│   ├── config.py               # Database connection manager
│   └── __init__.py
├── migrations/                  # Database migrations
│   └── init_database.py        # Table initialization
├── tests/                       # Unit tests (to be added)
├── uploads/documents/           # Document storage
├── main.py                      # FastAPI entry point
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container configuration
├── .env                         # Environment variables
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
└── README.md                    # Service documentation
```

---

## 🗄️ Database Models (7 Tables)

1. **ThreatModel** - Main threat model entity
2. **ThreatModelElement** - Diagram components (process, datastore, etc.)
3. **ThreatAssessment** - STRIDE/LINDDUN assessments
4. **ThreatModelCollaborator** - Multi-user collaboration
5. **ThreatModelVersion** - Version history
6. **AIAnalysisHistory** - Complete AI analysis history
7. **ThreatLibrary** - Predefined threat patterns

---

## 🔌 API Endpoints

### Threat Models CRUD

- `POST /api/v1/models` - Create threat model
- `GET /api/v1/models` - List models (with filters)
- `GET /api/v1/models/{id}` - Get specific model
- `PUT /api/v1/models/{id}` - Update model
- `DELETE /api/v1/models/{id}` - Delete model

### Analysis

- `POST /api/v1/models/{id}/comprehensive-analysis` - Perform STRIDE analysis
- `GET /api/v1/models/{id}/analyses` - Get analysis history
- `POST /api/v1/models/{id}/analyses` - Save analysis
- `DELETE /api/v1/models/{id}/analysis/{analysis_id}` - Delete analysis

### Documents

- `POST /api/v1/models/{id}/upload-document` - Upload PDF/DOCX for enhanced context

### Reference Data

- `GET /api/v1/library` - Get threat library patterns
- `GET /api/v1/dashboard` - Get dashboard statistics

### Health

- `GET /health` - Service health check
- `GET /metrics` - Prometheus metrics

---

## 🔗 Service Dependencies

### Internal Services

- **AI Service** (port 8001) - Threat analysis via HTTP
- **Authentication Service** - JWT token validation (via shared JWT secret)

### Infrastructure

- **PostgreSQL** - Data persistence
- **Redis** - Caching layer
- **Prometheus** - Metrics collection
- **Jaeger** - Distributed tracing

---

## 🚀 Running the Service

### Local Development

```bash
cd services/threat-modeling-service

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python migrations/init_database.py

# Run service
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

### Docker

```bash
# Build and run all services
docker-compose build threat-modeling-service
docker-compose up threat-modeling-service

# Or run specific service
docker-compose up -d threat-modeling-service

# View logs
docker-compose logs -f threat-modeling-service
```

### Access Service

- **Service:** http://localhost:8103 (Docker) or http://localhost:8003 (Local)
- **Health:** http://localhost:8103/health
- **API Docs:** http://localhost:8103/docs (Swagger UI)
- **Metrics:** http://localhost:8103/metrics

---

## 🧪 Testing

### Manual Testing

```bash
# Health check
curl http://localhost:8103/health

# Create threat model (requires JWT token)
curl -X POST http://localhost:8103/api/v1/models \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Threat Model",
    "description": "Test",
    "methodology": "STRIDE",
    "organization_id": "org-123"
  }'

# List models
curl http://localhost:8103/api/v1/models \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get threat library
curl http://localhost:8103/api/v1/library
```

### Unit Tests (To be added)

```bash
pytest tests/
```

---

## 📊 Key Features

### ✅ Threat Analysis

- **STRIDE Methodology** - Comprehensive threat categorization
- **Risk Scoring** - Complexity and risk assessment
- **Critical Component Detection** - High-risk component identification
- **Security Gap Analysis** - Identify missing controls
- **Compliance Guidance** - GDPR, HIPAA, PCI DSS, ISO 27001

### ✅ Document Integration

- **PDF Processing** - Extract text from PDF documents
- **DOCX Processing** - Parse Word documents
- **Technology Detection** - Identify technologies mentioned
- **Security Keyword Extraction** - Find security-related terms
- **Enhanced AI Context** - Use documents for better threat analysis

### ✅ Collaboration

- **Multi-user Support** - Share models with team members
- **Version Control** - Track changes over time
- **Role-based Permissions** - Owner, editor, reviewer, viewer

### ✅ Canvas Support

- **Visual Threat Modeling** - Store diagram data as JSON
- **Element Types** - Process, datastore, external entity, trust boundary
- **Connections** - Track data flows between components

### ✅ Observability

- **Prometheus Metrics** - Request counts, durations
- **Distributed Tracing** - Jaeger integration
- **Structured Logging** - JSON logs with correlation IDs
- **Health Checks** - Database and service health

---

## 🔧 Configuration

### Environment Variables

See `.env.example` for all available configuration options.

Key variables:

- `DATABASE_URL` - PostgreSQL connection string
- `AI_SERVICE_URL` - AI Service endpoint
- `JWT_SECRET_KEY` - JWT validation secret
- `REDIS_URL` - Redis connection string
- `OTLP_ENDPOINT` - Jaeger tracing endpoint

---

## 📈 Monitoring

### Prometheus Metrics

- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request duration histogram

### Jaeger Tracing

All requests are traced with OpenTelemetry and exported to Jaeger for distributed tracing visualization.

### Logs

Structured JSON logs with:

- Timestamp
- Log level
- Service name
- Request ID
- User ID
- Error details

---

## 🔄 Next Steps

1. **Test Service Startup**

   ```bash
   docker-compose up threat-modeling-service
   ```

2. **Verify Database Connection**

   - Check health endpoint
   - Run init_database.py

3. **Test API Endpoints**

   - Create threat model
   - Perform analysis
   - Upload document

4. **Update Kong Gateway** (if using)

   - Add routes for threat-modeling-service
   - Configure rate limiting

5. **Integration Testing**

   - Test AI Service integration
   - Test authentication flow
   - Test document processing

6. **Production Deployment**
   - Set production JWT secret
   - Configure production database
   - Enable HTTPS
   - Set proper CORS origins

---

## 🎯 Migration Status

### ✅ Completed

- [x] Service structure and configuration
- [x] Database models (7 tables)
- [x] API routes (14 endpoints)
- [x] Business logic (STRIDE analysis)
- [x] Core utilities (AI client, security, document processor)
- [x] Main entry point with observability
- [x] Docker configuration
- [x] Documentation

### 🔄 Remaining Tasks

- [ ] Unit tests
- [ ] Integration tests
- [ ] Kong gateway configuration
- [ ] Update frontend to call new service
- [ ] Data migration from monolith (if needed)
- [ ] Production deployment
- [ ] Performance testing
- [ ] Security audit

---

## 📝 Notes

- Service follows the same pattern as AI Service and GitHub Service
- Uses FastAPI with async/await for performance
- Includes comprehensive error handling and logging
- Ready for horizontal scaling
- Database migrations can be managed with Alembic (to be set up)

---

## 🆘 Troubleshooting

### Service won't start

- Check `.env` file exists and has correct values
- Verify database is accessible
- Check port 8003/8103 is available
- Review logs: `docker-compose logs threat-modeling-service`

### Database connection issues

- Verify DATABASE_URL is correct
- Check PostgreSQL is running
- Run `python migrations/init_database.py`

### AI Service integration failing

- Verify AI_SERVICE_URL is correct
- Check AI Service is running on port 8001
- Test AI Service health: `curl http://ai-service:8001/health`

### Authentication errors

- Verify JWT_SECRET_KEY matches other services
- Check token is not expired
- Ensure Authorization header format: `Bearer <token>`

---

**Service extracted successfully! 🎉**

The Threat Modeling Service is now ready for testing and deployment as an independent microservice.
