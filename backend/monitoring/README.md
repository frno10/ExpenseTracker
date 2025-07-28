# Expense Tracker Monitoring Stack

This directory contains the monitoring and observability stack for the Expense Tracker API, including distributed tracing, metrics collection, and alerting.

## Components

### 🔍 **Jaeger** - Distributed Tracing
- **URL**: http://localhost:16686
- **Purpose**: Visualize request traces across services
- **Features**: 
  - End-to-end request tracing
  - Performance bottleneck identification
  - Service dependency mapping

### 📊 **Prometheus** - Metrics Collection
- **URL**: http://localhost:9090
- **Purpose**: Collect and store time-series metrics
- **Metrics Collected**:
  - HTTP request rates and durations
  - Database query performance
  - Error rates and counts
  - System resource usage

### 📈 **Grafana** - Visualization
- **URL**: http://localhost:3001
- **Credentials**: admin/admin
- **Purpose**: Create dashboards and visualizations
- **Pre-configured Dashboards**:
  - API Performance Overview
  - Database Performance
  - Error Tracking
  - System Health

### 🚨 **AlertManager** - Alerting
- **URL**: http://localhost:9093
- **Purpose**: Handle alerts from Prometheus
- **Alert Rules**:
  - High error rates (>10% for 2 minutes)
  - Slow response times (>1s 95th percentile)
  - Database connection errors
  - API endpoint downtime

## Quick Start

### 1. Start Monitoring Stack
```bash
cd backend/monitoring
docker-compose up -d
```

### 2. Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Start the API with Observability
```bash
cd backend
# Set environment variables for observability
export JAEGER_AGENT_HOST=localhost
export JAEGER_AGENT_PORT=6831
export PROMETHEUS_PORT=8000

# Start the API
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 4. Access Monitoring Tools
- **Jaeger UI**: http://localhost:16686
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)
- **AlertManager**: http://localhost:9093

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JAEGER_AGENT_HOST` | localhost | Jaeger agent hostname |
| `JAEGER_AGENT_PORT` | 6831 | Jaeger agent port |
| `PROMETHEUS_PORT` | 8000 | Port for Prometheus metrics endpoint |

### Metrics Endpoints

The API exposes metrics at:
- **Application Metrics**: http://localhost:8080/metrics (via Prometheus client)
- **OpenTelemetry Metrics**: Automatically scraped by Prometheus

## Key Metrics

### HTTP Metrics
- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request duration histogram

### Database Metrics
- `database_queries_total` - Total database queries by operation and table
- `database_query_duration_seconds` - Database query duration histogram

### Error Metrics
- `errors_total` - Total errors by type and endpoint

### System Metrics
- `process_resident_memory_bytes` - Memory usage
- `process_cpu_seconds_total` - CPU usage

## Tracing

### Automatic Instrumentation
The following components are automatically instrumented:
- **FastAPI**: HTTP requests and responses
- **SQLAlchemy**: Database queries
- **AsyncPG**: PostgreSQL connections
- **Requests**: HTTP client calls

### Custom Spans
Add custom spans in your code:
```python
from app.core.telemetry import get_tracer

tracer = get_tracer()

with tracer.start_span("custom_operation") as span:
    span.set_attribute("custom.attribute", "value")
    # Your code here
```

## Logging

### Structured Logging
All logs are structured with:
- Timestamp (ISO 8601)
- Log level
- Logger name
- Message
- Correlation ID
- Trace ID and Span ID (when available)
- Additional context

### Log Levels
- **DEBUG**: Detailed debugging information
- **INFO**: General information
- **WARNING**: Warning messages
- **ERROR**: Error conditions
- **CRITICAL**: Critical errors

### Correlation IDs
Every request gets a unique correlation ID for tracking across services:
- Automatically generated if not provided
- Can be set via `X-Correlation-ID` header
- Included in all log entries and traces

## Alerting Rules

### Critical Alerts
- **HighErrorRate**: Error rate > 10% for 2 minutes
- **DatabaseConnectionErrors**: DB error rate > 5% for 2 minutes
- **APIEndpointDown**: API not responding for 1 minute

### Warning Alerts
- **HighResponseTime**: 95th percentile > 1 second for 5 minutes
- **HighMemoryUsage**: Memory usage > 500MB for 5 minutes

## Troubleshooting

### Common Issues

1. **Jaeger not receiving traces**
   - Check `JAEGER_AGENT_HOST` and `JAEGER_AGENT_PORT` environment variables
   - Ensure Jaeger container is running: `docker-compose ps`

2. **Prometheus not scraping metrics**
   - Verify API is exposing metrics at `/metrics` endpoint
   - Check Prometheus targets: http://localhost:9090/targets

3. **Grafana dashboards not loading**
   - Ensure Prometheus datasource is configured
   - Check dashboard JSON syntax in `grafana/dashboards/`

4. **High memory usage**
   - Monitor trace sampling rates
   - Adjust batch span processor settings
   - Check for memory leaks in application code

### Logs and Debugging

View container logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f jaeger
docker-compose logs -f prometheus
docker-compose logs -f grafana
```

### Performance Tuning

1. **Trace Sampling**: Adjust sampling rates for high-traffic environments
2. **Metric Retention**: Configure Prometheus retention policies
3. **Batch Processing**: Tune OpenTelemetry batch processors
4. **Resource Limits**: Set appropriate Docker resource limits

## Development

### Adding New Metrics
1. Define metric in `app/core/telemetry.py`
2. Record metric values in your code
3. Update Grafana dashboards
4. Add alert rules if needed

### Custom Dashboards
1. Create dashboard in Grafana UI
2. Export JSON configuration
3. Save to `grafana/dashboards/`
4. Restart Grafana container

### Testing Observability
Run the telemetry tests:
```bash
cd backend
python -m pytest tests/test_telemetry.py -v
```

## Production Considerations

1. **Security**: Configure authentication for monitoring tools
2. **Persistence**: Use external volumes for data persistence
3. **Scaling**: Consider Prometheus federation for multiple instances
4. **Retention**: Configure appropriate data retention policies
5. **Backup**: Regular backups of Grafana dashboards and Prometheus data