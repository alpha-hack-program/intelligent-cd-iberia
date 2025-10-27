# Resource Management and Monitoring
## Resource Quotas, Monitoring, and Health Checks

**Document Version:** 2.1.4  
**Last Updated:** December 2024  
**Document Owner:** Platform Engineering Team  
**Contact:** platform-engineering@company.com  
**Related Documents:** [01-intro.md](01-intro.md), [02-deployment-constraints.md](02-deployment-constraints.md)

---

## Table of Contents

1. [Resource Management](#resource-management)
2. [Resource Quotas and Limits](#resource-quotas-and-limits)
3. [Monitoring Setup](#monitoring-setup)
4. [Health Check Endpoints](#health-check-endpoints)
5. [Alerting Configuration](#alerting-configuration)
6. [Performance Optimization](#performance-optimization)

---

## Resource Management

Contact **platform-engineering@company.com** for resource allocation and quota management. Proper resource management ensures optimal performance and cost efficiency.

### Resource Management Overview

Resource management in OpenShift involves allocating CPU, memory, and storage resources to applications while ensuring efficient utilization and preventing resource contention. The Intelligent CD application requires careful resource planning across all environments.

### Resource Types

- **CPU Resources:** Processing power allocation and limits
- **Memory Resources:** RAM allocation and limits
- **Storage Resources:** Persistent and temporary storage
- **Network Resources:** Bandwidth and connection limits
- **GPU Resources:** Specialized processing units (if required)

---

## Resource Quotas and Limits

### Environment-Specific Resource Quotas

| Namespace | CPU Limit | Memory Limit | Storage Limit | Replicas | Contact |
|-----------|-----------|--------------|---------------|----------|---------|
| **intelligent-cd-dev** | 4 CPU | 8Gi | 100Gi | 1-2 | platform-engineering@company.com |
| **intelligent-cd-staging** | 8 CPU | 16Gi | 200Gi | 2-3 | platform-engineering@company.com |
| **intelligent-cd-prod** | 16 CPU | 32Gi | 500Gi | 3-5 | platform-engineering@company.com |

### Resource Quota Configuration

#### Development Environment Quota
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: intelligent-cd-dev-quota
  namespace: intelligent-cd-dev
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    requests.storage: 100Gi
    persistentvolumeclaims: "10"
    services: "20"
    configmaps: "50"
    secrets: "50"
```

#### Staging Environment Quota
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: intelligent-cd-staging-quota
  namespace: intelligent-cd-staging
spec:
  hard:
    requests.cpu: "8"
    requests.memory: 16Gi
    limits.cpu: "16"
    limits.memory: 32Gi
    requests.storage: 200Gi
    persistentvolumeclaims: "20"
    services: "30"
    configmaps: "100"
    secrets: "100"
```

#### Production Environment Quota
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: intelligent-cd-prod-quota
  namespace: intelligent-cd-prod
spec:
  hard:
    requests.cpu: "16"
    requests.memory: 32Gi
    limits.cpu: "32"
    limits.memory: 64Gi
    requests.storage: 500Gi
    persistentvolumeclaims: "50"
    services: "50"
    configmaps: "200"
    secrets: "200"
```

### Resource Limit Ranges

#### CPU and Memory Limits
```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: intelligent-cd-limits
  namespace: intelligent-cd
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 250m
      memory: 256Mi
    type: Container
    max:
      cpu: 2
      memory: 2Gi
    min:
      cpu: 100m
      memory: 128Mi
```

#### Storage Limits
```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: intelligent-cd-storage-limits
  namespace: intelligent-cd
spec:
  limits:
  - type: PersistentVolumeClaim
    max:
      storage: 100Gi
    min:
      storage: 1Gi
```

### Resource Scaling Policies

#### Horizontal Pod Autoscaler (HPA)
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: intelligent-cd-hpa
  namespace: intelligent-cd
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: intelligent-cd
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```

#### Vertical Pod Autoscaler (VPA)
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: intelligent-cd-vpa
  namespace: intelligent-cd
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: intelligent-cd
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: 1
        memory: 1Gi
      controlledValues: RequestsAndLimits
```

---

## Monitoring Setup

Contact **monitoring@company.com** for monitoring setup and configuration.

### Monitoring Architecture

#### Monitoring Stack Components
| Component | Purpose | Contact | Access Level | Configuration |
|-----------|---------|---------|--------------|---------------|
| **Prometheus** | Metrics collection | monitoring@company.com | Read-only | Automated |
| **Grafana** | Dashboards and visualization | monitoring@company.com | Read-only | Automated |
| **AlertManager** | Alert routing and management | monitoring@company.com | Admin | Manual |
| **Thanos** | Long-term storage | monitoring@company.com | Read-only | Automated |
| **Jaeger** | Distributed tracing | monitoring@company.com | Read-only | Manual |

#### Monitoring Data Flow
1. **Application Metrics:** Exported via /metrics endpoint
2. **Infrastructure Metrics:** Collected by node exporters
3. **Custom Metrics:** Business-specific measurements
4. **Logs:** Centralized logging via Loki/Elasticsearch

### Prometheus Configuration

#### Service Monitor for Intelligent CD
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: intelligent-cd-monitor
  namespace: intelligent-cd
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app: intelligent-cd
  endpoints:
  - port: 8080
    path: /metrics
    interval: 30s
    scrapeTimeout: 10s
    honorLabels: true
  namespaceSelector:
    matchNames:
    - intelligent-cd
```

#### Prometheus Rule for Alerts
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: intelligent-cd-rules
  namespace: intelligent-cd
  labels:
    release: prometheus
    prometheus: kube-prometheus
    role: alert-rules
spec:
  groups:
  - name: intelligent-cd.rules
    rules:
    - alert: IntelligentCDHighCPUUsage
      expr: container_cpu_usage_seconds_total{container="intelligent-cd"} > 0.8
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High CPU usage detected"
        description: "Container {{ $labels.container }} has high CPU usage"
    
    - alert: IntelligentCDHighMemoryUsage
      expr: container_memory_usage_bytes{container="intelligent-cd"} > 1.5e9
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High memory usage detected"
        description: "Container {{ $labels.container }} has high memory usage"
    
    - alert: IntelligentCDPodDown
      expr: up{job="intelligent-cd"} == 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "Intelligent CD pod is down"
        description: "Pod {{ $labels.pod }} has been down for more than 1 minute"
```

### Grafana Dashboard Configuration

#### Application Overview Dashboard
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: intelligent-cd-grafana-dashboard
  namespace: intelligent-cd
  labels:
    grafana_dashboard: "1"
data:
  intelligent-cd-overview.json: |
    {
      "dashboard": {
        "id": null,
        "title": "Intelligent CD Overview",
        "tags": ["intelligent-cd", "overview"],
        "timezone": "browser",
        "panels": [
          {
            "id": 1,
            "title": "CPU Usage",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(container_cpu_usage_seconds_total{container=\"intelligent-cd\"}[5m])",
                "legendFormat": "{{pod}}"
              }
            ]
          },
          {
            "id": 2,
            "title": "Memory Usage",
            "type": "graph",
            "targets": [
              {
                "expr": "container_memory_usage_bytes{container=\"intelligent-cd\"}",
                "legendFormat": "{{pod}}"
              }
            ]
          },
          {
            "id": 3,
            "title": "HTTP Request Rate",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(http_requests_total{job=\"intelligent-cd\"}[5m])",
                "legendFormat": "{{method}} {{endpoint}}"
              }
            ]
          }
        ]
      }
    }
```

---

## Health Check Endpoints

### Health Check Overview

Health check endpoints provide real-time information about application status and readiness. They are essential for load balancers, monitoring systems, and automated health assessments.

### Required Health Check Endpoints

| Endpoint | Purpose | Expected Response | Response Time | Contact |
|----------|---------|-------------------|---------------|---------|
| **/health** | Basic health check | HTTP 200 OK | < 100ms | platform-engineering@company.com |
| **/ready** | Readiness check | HTTP 200 OK | < 200ms | platform-engineering@company.com |
| **/live** | Liveness check | HTTP 200 OK | < 100ms | platform-engineering@company.com |
| **/metrics** | Prometheus metrics | HTTP 200 OK + metrics | < 500ms | monitoring@company.com |

### Health Check Implementation

#### Python FastAPI Health Checks
```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import psycopg2
import redis
import time
import logging

app = FastAPI(title="Intelligent CD API")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    try:
        # Check basic application health
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "2.1.4",
            "environment": "production"
        }
        return JSONResponse(content=health_status, status_code=200)
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# Readiness check endpoint
@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    try:
        # Check database connectivity
        db_healthy = check_database_health()
        
        # Check Redis connectivity
        redis_healthy = check_redis_health()
        
        if db_healthy and redis_healthy:
            readiness_status = {
                "status": "ready",
                "timestamp": time.time(),
                "database": "connected",
                "redis": "connected",
                "dependencies": ["database", "redis"]
            }
            return JSONResponse(content=readiness_status, status_code=200)
        else:
            readiness_status = {
                "status": "not_ready",
                "timestamp": time.time(),
                "database": "connected" if db_healthy else "disconnected",
                "redis": "connected" if redis_healthy else "disconnected",
                "dependencies": ["database", "redis"]
            }
            return JSONResponse(content=readiness_status, status_code=503)
    except Exception as e:
        logging.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")

# Liveness check endpoint
@app.get("/live")
async def liveness_check():
    """Liveness check endpoint"""
    try:
        # Check if application is responsive
        liveness_status = {
            "status": "alive",
            "timestamp": time.time(),
            "uptime": get_uptime(),
            "memory_usage": get_memory_usage(),
            "cpu_usage": get_cpu_usage()
        }
        return JSONResponse(content=liveness_status, status_code=200)
    except Exception as e:
        logging.error(f"Liveness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not alive")

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    try:
        # Generate Prometheus metrics
        metrics_data = generate_prometheus_metrics()
        return Response(content=metrics_data, media_type="text/plain")
    except Exception as e:
        logging.error(f"Metrics generation failed: {e}")
        raise HTTPException(status_code=503, detail="Metrics unavailable")

# Health check helper functions
def check_database_health():
    """Check database connectivity"""
    try:
        # Database health check logic
        conn = psycopg2.connect(
            host="intelligent-cd-database",
            database="intelligent_cd",
            user="intelligent_cd_user",
            password="intelligent_cd_password"
        )
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Database health check failed: {e}")
        return False

def check_redis_health():
    """Check Redis connectivity"""
    try:
        # Redis health check logic
        r = redis.Redis(host="intelligent-cd-redis", port=6379, db=0)
        r.ping()
        return True
    except Exception as e:
        logging.error(f"Redis health check failed: {e}")
        return False

def get_uptime():
    """Get application uptime"""
    # Implementation to get uptime
    return "24h 30m 15s"

def get_memory_usage():
    """Get current memory usage"""
    # Implementation to get memory usage
    return "512MB"

def get_cpu_usage():
    """Get current CPU usage"""
    # Implementation to get CPU usage
    return "25%"

def generate_prometheus_metrics():
    """Generate Prometheus metrics"""
    metrics = []
    
    # HTTP request metrics
    metrics.append("# HELP http_requests_total Total number of HTTP requests")
    metrics.append("# TYPE http_requests_total counter")
    metrics.append("http_requests_total{method=\"GET\",endpoint=\"/health\"} 150")
    metrics.append("http_requests_total{method=\"GET\",endpoint=\"/ready\"} 120")
    
    # Response time metrics
    metrics.append("# HELP http_request_duration_seconds HTTP request duration in seconds")
    metrics.append("# TYPE http_request_duration_seconds histogram")
    metrics.append("http_request_duration_seconds_bucket{le=\"0.1\"} 100")
    metrics.append("http_request_duration_seconds_bucket{le=\"0.5\"} 200")
    metrics.append("http_request_duration_seconds_bucket{le=\"1.0\"} 250")
    metrics.append("http_request_duration_seconds_bucket{le=\"+Inf\"} 250")
    
    return "\n".join(metrics)
```

#### Kubernetes Health Check Configuration
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: intelligent-cd
  namespace: intelligent-cd
spec:
  replicas: 3
  selector:
    matchLabels:
      app: intelligent-cd
  template:
    metadata:
      labels:
        app: intelligent-cd
    spec:
      containers:
      - name: intelligent-cd
        image: intelligent-cd:2.1.4
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /live
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        startupProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 30
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
```

---

## Alerting Configuration

### Alerting Overview

Contact **monitoring@company.com** for alert setup and management. Proper alerting ensures timely response to issues and maintains system reliability.

### Alert Severity Levels

| Severity | Description | Response Time | Contact | Escalation |
|----------|-------------|---------------|---------|------------|
| **Critical** | Service completely down | 5 minutes | oncall-platform@company.com | Immediate |
| **High** | Major functionality affected | 15 minutes | platform-engineering@company.com | 1 hour |
| **Medium** | Minor functionality affected | 1 hour | platform-engineering@company.com | 4 hours |
| **Low** | Informational alerts | 4 hours | monitoring@company.com | 24 hours |

### Critical Alerts

#### Pod Down Alert
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: intelligent-cd-critical-alerts
  namespace: intelligent-cd
spec:
  groups:
  - name: critical.alerts
    rules:
    - alert: IntelligentCDPodDown
      expr: up{job="intelligent-cd"} == 0
      for: 1m
      labels:
        severity: critical
        team: platform-engineering
      annotations:
        summary: "Intelligent CD pod is down"
        description: "Pod {{ $labels.pod }} has been down for more than 1 minute"
        runbook_url: "https://runbooks.company.com/intelligent-cd/pod-down"
        slack_channel: "#platform-alerts"
        pagerduty_service: "platform-engineering"
```

#### Database Connection Failure Alert
```yaml
    - alert: IntelligentCDDatabaseConnectionFailure
      expr: intelligent_cd_database_connections_active == 0
      for: 2m
      labels:
        severity: critical
        team: platform-engineering
      annotations:
        summary: "Database connection failure"
        description: "Intelligent CD cannot connect to database"
        runbook_url: "https://runbooks.company.com/intelligent-cd/database-failure"
        slack_channel: "#platform-alerts"
        pagerduty_service: "platform-engineering"
```

### Warning Alerts

#### High Resource Usage Alerts
```yaml
  - name: warning.alerts
    rules:
    - alert: IntelligentCDHighCPUUsage
      expr: container_cpu_usage_seconds_total{container="intelligent-cd"} > 0.8
      for: 5m
      labels:
        severity: warning
        team: platform-engineering
      annotations:
        summary: "High CPU usage detected"
        description: "Container {{ $labels.container }} has high CPU usage"
        runbook_url: "https://runbooks.company.com/intelligent-cd/high-cpu"
        slack_channel: "#platform-warnings"
    
    - alert: IntelligentCDHighMemoryUsage
      expr: container_memory_usage_bytes{container="intelligent-cd"} > 1.5e9
      for: 5m
      labels:
        severity: warning
        team: platform-engineering
      annotations:
        summary: "High memory usage detected"
        description: "Container {{ $labels.container }} has high memory usage"
        runbook_url: "https://runbooks.company.com/intelligent-cd/high-memory"
        slack_channel: "#platform-warnings"
```

### AlertManager Configuration

#### Alert Routing Rules
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
      slack_api_url: 'https://hooks.slack.com/services/YOUR_SLACK_WEBHOOK'
    
    route:
      group_by: ['alertname', 'cluster', 'service']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      receiver: 'platform-engineering'
      routes:
      - match:
          severity: critical
        receiver: 'platform-engineering-critical'
        continue: true
      - match:
          severity: warning
        receiver: 'platform-engineering-warning'
    
    receivers:
    - name: 'platform-engineering'
      slack_configs:
      - channel: '#platform-alerts'
        title: '{{ template "slack.title" . }}'
        text: '{{ template "slack.text" . }}'
        actions:
        - type: button
          text: 'View in Grafana'
          url: '{{ template "slack.grafana" . }}'
    
    - name: 'platform-engineering-critical'
      slack_configs:
      - channel: '#platform-critical'
        title: '🚨 CRITICAL: {{ template "slack.title" . }}'
        text: '{{ template "slack.text" . }}'
      pagerduty_configs:
      - service_key: 'your-pagerduty-service-key'
        description: '{{ template "pagerduty.description" . }}'
    
    - name: 'platform-engineering-warning'
      slack_configs:
      - channel: '#platform-warnings'
        title: '⚠️ WARNING: {{ template "slack.title" . }}'
        text: '{{ template "slack.text" . }}'
```

---

## Performance Optimization

### Performance Monitoring

#### Key Performance Indicators (KPIs)
| Metric | Target | Measurement | Contact |
|--------|--------|-------------|---------|
| **Response Time** | < 200ms (95th percentile) | Prometheus metrics | monitoring@company.com |
| **Throughput** | 1000+ requests/second | Load testing | platform-engineering@company.com |
| **Error Rate** | < 0.1% | Application logs | monitoring@company.com |
| **Availability** | 99.9% uptime | Uptime monitoring | monitoring@company.com |

#### Performance Testing
- **Load Testing:** Simulate production load
- **Stress Testing:** Test system limits
- **Endurance Testing:** Long-running performance
- **Spike Testing:** Sudden load increases

### Resource Optimization

#### CPU Optimization
- **Horizontal Scaling:** Add more replicas
- **Vertical Scaling:** Increase CPU limits
- **Code Optimization:** Profile and optimize code
- **Caching:** Implement application-level caching

#### Memory Optimization
- **Memory Profiling:** Identify memory leaks
- **Garbage Collection:** Optimize GC settings
- **Connection Pooling:** Efficient resource usage
- **Data Structures:** Optimize data handling

#### Storage Optimization
- **IOPS Optimization:** Right-size storage volumes
- **Caching Strategy:** Multi-layer caching
- **Data Compression:** Reduce storage footprint
- **Lifecycle Management:** Automated data management

---

## Monitoring Best Practices

### Monitoring Checklist

- [ ] All critical metrics are monitored
- [ ] Health check endpoints are implemented
- [ ] Alerting is configured for critical issues
- [ ] Dashboards provide actionable insights
- [ ] Performance baselines are established
- [ ] Monitoring covers all environments
- [ ] Alert fatigue is minimized
- [ ] Runbooks are available for common issues

### Monitoring Tools Integration

#### Prometheus Integration
- **Service Discovery:** Automatic target discovery
- **Metrics Collection:** Regular scraping intervals
- **Data Retention:** Appropriate retention policies
- **High Availability:** Prometheus cluster setup

#### Grafana Integration
- **Dashboard Design:** User-friendly visualizations
- **Alert Integration:** Prometheus alerting
- **User Management:** Role-based access control
- **Template Variables:** Dynamic dashboard content

#### Logging Integration
- **Centralized Logging:** Loki/Elasticsearch
- **Log Aggregation:** Structured log collection
- **Log Analysis:** Search and filtering capabilities
- **Log Retention:** Appropriate retention policies

---

**For questions or updates to this document, contact:** monitoring@company.com

**Document ID:** INT-CD-MONITORING-2024-001  
**Classification:** Internal Use Only (IUO)  
**Next Review Date:** March 2025
