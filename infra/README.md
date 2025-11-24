# WithOps Infrastructure

Infrastructure configuration and monitoring for WithOps microservices.

## Services

### API Gateway (Kong)

- **URL**: http://localhost:8000
- **Admin API**: http://localhost:8001
- **Config**: `kong/kong.yml`

Routes all requests to appropriate microservices.

### Monitoring Stack

#### Prometheus (Metrics)

- **URL**: http://localhost:9090
- Collects metrics from all services
- Config: `monitoring/prometheus.yml`

#### Grafana (Dashboards)

- **URL**: http://localhost:3000
- **Default credentials**: admin / admin
- Visualizes metrics from Prometheus

#### Jaeger (Distributed Tracing)

- **URL**: http://localhost:16686
- Traces requests across microservices

#### Loki (Logging)

- **URL**: http://localhost:3100
- Centralized log aggregation

## Quick Start

Start all infrastructure services:

```powershell
docker-compose up kong redis prometheus grafana jaeger loki
```

Start full stack:

```powershell
docker-compose up
```

## Service Ports

| Service                 | Internal Port | External Port |
| ----------------------- | ------------- | ------------- |
| Kong (Gateway)          | 8000          | 8000          |
| Backend                 | 8000          | 8100          |
| AI Service              | 8001          | 8101          |
| GitHub Service          | 8002          | 8102          |
| Threat Modeling Service | 8003          | 8103          |
| Workspace Intelligence  | 8004          | 8004          |
| Collaboration Service   | 8105          | 8105          |
| Authentication Service  | 8006          | 8106          |
| Prometheus              | 9090          | 9090          |
| Grafana                 | 3000          | 3000          |
| Jaeger                  | 16686         | 16686         |
| Loki                    | 3100          | 3100          |
| Redis                   | 6379          | 16379         |

## Configuration Files

- `kong/kong.yml` - API Gateway routing
- `monitoring/prometheus.yml` - Prometheus scrape config
- `monitoring/grafana-datasources.yml` - Grafana data sources
- `monitoring/loki-config.yml` - Loki logging config

## Adding New Services

1. Add service to `docker-compose.yml`
2. Update Kong routing in `kong/kong.yml`
3. Add Prometheus scrape config in `monitoring/prometheus.yml`
4. Restart services: `docker-compose restart kong prometheus`
