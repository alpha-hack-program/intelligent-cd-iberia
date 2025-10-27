# Deployment Constraints and Requirements
## Security, Resources, and Application Standards

**Document Version:** 2.1.4  
**Last Updated:** December 2024  
**Document Owner:** Platform Engineering Team  
**Contact:** platform-engineering@company.com  
**Related Documents:** [01-intro.md](01-intro.md)

---

## Table of Contents

1. [Security Context Constraints (SCC)](#security-context-constraints-scc)
2. [Resource Allocation](#resource-allocation)
3. [Statelessness Requirements](#statelessness-requirements)
4. [Logging Standards](#logging-standards)
5. [Port Configuration](#port-configuration)
6. [Container Image Requirements](#container-image-requirements)

---

## Security Context Constraints (SCC)

Your application must **not** require special Security Context Constraints (SCCs). The deployment should be able to run with the default `restricted` SCC. This is a fundamental security practice on OpenShift.

### SCC Requirements

The application must:

- **Not run as the root user** - Must use UID 1000 or higher
- **Not require privileged access** - No CAP_SYS_ADMIN or similar capabilities
- **Not mount host paths** - Use persistent volumes instead
- **Not use host networking** - Use service networking only
- **Not require host IPC or PID namespaces**
- **Not use host ports** - Use service ports only
- **Not require SELinux context changes** - Use default contexts

### SCC Exception Process

**Contact for SCC Exceptions:** security@company.com with subject "SCC Exception Request - [Application Name]"

**Approval Process:**
1. Submit request to security@company.com
2. Include business justification and risk assessment
3. Security team review (2-3 business days)
4. Architecture team approval (1-2 business days)
5. Final approval from CISO office (1 business day)

**Required Documentation:**
- Business justification
- Risk assessment matrix
- Alternative solutions considered
- Mitigation strategies
- Rollback plan

### SCC Compliance Checklist

- [ ] Application runs as non-root user (UID ≥ 1000)
- [ ] No privileged capabilities required
- [ ] No host path mounts
- [ ] No host networking
- [ ] No host IPC/PID namespaces
- [ ] No host ports
- [ ] Default SELinux contexts used

---

## Resource Allocation

Properly sizing your application is crucial for performance and cost management. You must define **resource requests and limits** for CPU and memory in your deployment configuration.

### Resource Requirements by Environment

| Environment | CPU Request | CPU Limit | Memory Request | Memory Limit | Replicas | Contact |
|-------------|-------------|-----------|----------------|--------------|----------|---------|
| **Development** | 100m | 200m | 128Mi | 256Mi | 1-2 | devops@company.com |
| **Staging** | 250m | 500m | 256Mi | 512Mi | 2-3 | devops@company.com |
| **Production** | 500m | 1000m | 512Mi | 1Gi | 3-5 | architecture@company.com |

### Resource Configuration Examples

#### Development Environment
```yaml
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "200m"
    memory: "256Mi"
```

#### Staging Environment
```yaml
resources:
  requests:
    cpu: "250m"
    memory: "256Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

#### Production Environment
```yaml
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "1000m"
    memory: "1Gi"
```

### Resource Management Best Practices

- **CPU Limits:** Set to 2x requests to allow for burst capacity
- **Memory Limits:** Set to 1.5x requests to prevent OOM kills
- **Resource Monitoring:** Use Prometheus/Grafana for tracking
- **Horizontal Scaling:** Implement HPA for production workloads
- **Database Resources:** Contact database@company.com for sizing

### Resource Scaling Approval

| Environment | Approval Required | Contact | Timeline |
|-------------|-------------------|---------|----------|
| **Development** | DevOps team | devops@company.com | 1 business day |
| **Staging** | DevOps team | devops@company.com | 1-2 business days |
| **Production** | Architecture team | architecture@company.com | 3-5 business days |

**Production Scaling Process:**
1. Submit request to architecture@company.com
2. Include performance metrics and justification
3. Architecture review (3-5 business days)
4. CTO approval for significant changes
5. Implementation by DevOps team

---

## Statelessness Requirements

The application must be **stateless**. This means that it should not store any session data, temporary files, or other state on its local filesystem.

### Stateful Components Management

| Component | Storage Type | Contact | Approval Required | Timeline |
|-----------|--------------|---------|-------------------|----------|
| **User Sessions** | Redis Cluster | database@company.com | Yes - Architecture | 5-7 days |
| **File Uploads** | S3-Compatible Storage | storage@company.com | Yes - Storage Team | 3-5 days |
| **Application Logs** | Centralized Logging | logging@company.com | No - Standard | Immediate |
| **Configuration** | ConfigMaps/Secrets | platform-engineering@company.com | No - Standard | Immediate |
| **Temporary Files** | EmptyDir volumes | platform-engineering@company.com | No - Standard | Immediate |

### Stateful Requirements Process

**Step 1: Submit Request**
- Contact: architecture@company.com
- Include: Storage requirements and data lifecycle
- Timeline: Initial response within 1 business day

**Step 2: Architecture Review**
- Contact: architecture@company.com
- Timeline: 3-5 business days
- Deliverables: Architecture assessment and recommendations

**Step 3: Storage Team Assessment**
- Contact: storage@company.com
- Timeline: 2-3 business days
- Deliverables: Storage solution design and cost estimate

**Step 4: Security Review**
- Contact: security@company.com
- Timeline: 2-3 business days
- Deliverables: Security assessment and data classification

**Step 5: Final Approval**
- Contact: Architecture Review Board
- Timeline: 1-2 business days
- Deliverables: Final approval or rejection with feedback

### Statelessness Checklist

- [ ] No local file storage
- [ ] No session state in memory
- [ ] No temporary file accumulation
- [ ] All state externalized to services
- [ ] Configuration via ConfigMaps/Secrets
- [ ] Logs to stdout/stderr only

---

## Logging Standards

Your application should **write all logs to standard output (stdout) and standard error (stderr)**. OpenShift's logging system automatically collects logs from these streams.

### Logging Standards by Level

| Log Level | Output Stream | Retention | Contact | Response Time |
|------------|---------------|-----------|---------|---------------|
| **ERROR** | stderr | 90 days | logging@company.com | 4 hours |
| **WARN** | stdout | 30 days | logging@company.com | 8 hours |
| **INFO** | stdout | 7 days | logging@company.com | 24 hours |
| **DEBUG** | stdout | 3 days | logging@company.com | 48 hours |

### Logging Configuration

#### Python Logging Setup
```python
import logging
import sys

# Configure logging to stdout/stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)

# Set specific levels for different streams
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.addFilter(lambda record: record.levelno < logging.ERROR)

stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.ERROR)

# Add handlers to root logger
logging.getLogger().addHandler(stdout_handler)
logging.getLogger().addHandler(stderr_handler)
```

#### Structured Logging (Recommended)
```python
import json
import logging
import sys

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        return json.dumps(log_entry)

# Configure structured logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

### Logging Best Practices

- **Structured Logging:** Use JSON format for better parsing
- **Context Information:** Include request IDs, user IDs, and correlation IDs
- **Performance Metrics:** Log response times and resource usage
- **Security Events:** Log authentication, authorization, and access attempts
- **Business Events:** Log important business operations and state changes

### Logging Issues Contact

- **General Issues:** logging@company.com
- **Urgent Issues:** oncall-platform@company.com
- **Performance Issues:** monitoring@company.com
- **Security Issues:** security@company.com

---

## Port Configuration

Your application should be configured to listen on port **8080**. OpenShift automatically handles routing traffic to this port.

### Port Configuration by Service Type

| Service Type | Port | Protocol | Contact | Approval Required |
|--------------|------|----------|---------|-------------------|
| **HTTP API** | 8080 | TCP | networking@company.com | No |
| **Health Check** | 8080 | TCP | platform-engineering@company.com | No |
| **Metrics** | 8080 | TCP | monitoring@company.com | No |
| **Admin Interface** | 8080 | TCP | security@company.com | Yes - Security |

### Port Change Process

**Standard Port (8080):**
- No approval required
- Automatic routing by OpenShift
- Standard health check endpoints

**Non-Standard Ports:**
1. Submit request to networking@company.com
2. Include business justification and impact assessment
3. Network team review (1-2 business days)
4. Security review if non-standard port (1 business day)
5. Implementation by networking team

### Port Configuration Examples

#### Standard Configuration
```yaml
apiVersion: v1
kind: Service
metadata:
  name: intelligent-cd-service
spec:
  ports:
  - port: 8080
    targetPort: 8080
    protocol: TCP
  selector:
    app: intelligent-cd
```

#### Health Check Configuration
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: intelligent-cd
spec:
  template:
    spec:
      containers:
      - name: intelligent-cd
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

---

## Container Image Requirements

The application must be built into a **container image**. Use a multi-stage Dockerfile to create a small, efficient, and secure image.

### Image Requirements

| Requirement | Specification | Contact | Approval Required |
|-------------|---------------|---------|-------------------|
| **Base Image** | Red Hat UBI 9 minimal | security@company.com | Yes - Security |
| **Size Limit** | < 200MB | devops@company.com | Yes - DevOps |
| **Security Scan** | Passes Trivy/Clair | security@company.com | Yes - Security |
| **Registry** | company-registry.company.com | devops@company.com | Yes - DevOps |
| **Tagging** | Semantic versioning | devops@company.com | No |
| **Signing** | Digital signature required | security@company.com | Yes - Security |

### Image Build Process

**Step 1: Dockerfile Review**
- Submit Dockerfile to devops@company.com
- Include: Base image justification and security considerations
- Timeline: 1-2 business days

**Step 2: Security Scan**
- Security team runs Trivy/Clair scans
- Contact: security@company.com
- Timeline: 1 business day
- Deliverables: Security scan report and approval

**Step 3: Build and Push**
- DevOps team builds and pushes to registry
- Contact: devops@company.com
- Timeline: 1 business day
- Deliverables: Built image in registry

**Step 4: Image Signing**
- Security team signs image with digital signature
- Contact: security@company.com
- Timeline: 1 business day
- Deliverables: Signed and verified image

### Dockerfile Best Practices

#### Multi-Stage Build Example
```dockerfile
# Build stage
FROM registry.access.redhat.com/ubi9/python-311:latest AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM registry.access.redhat.com/ubi9/python-311:latest

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

WORKDIR /app
COPY --from=builder /home/appuser/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Set Python path
ENV PATH=/home/appuser/.local/bin:$PATH

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "main.py"]
```

### Security Scanning

**Required Scans:**
- **Trivy:** Vulnerability scanning
- **Clair:** Container security analysis
- **Snyk:** Dependency vulnerability check
- **Custom:** Company-specific security policies

**Scan Results:**
- **Pass:** Image approved for deployment
- **Warnings:** Review required, may proceed with approval
- **Failures:** Image rejected, fixes required

**Contact for Security Issues:** security@company.com

---

## Compliance Checklist

### Security Compliance
- [ ] SCC requirements met
- [ ] Non-root user configuration
- [ ] No privileged capabilities
- [ ] Security scans passed
- [ ] Image signed and verified

### Resource Compliance
- [ ] Resource requests defined
- [ ] Resource limits defined
- [ ] Environment-appropriate sizing
- [ ] Scaling policies configured

### Application Compliance
- [ ] Stateless design implemented
- [ ] Logging to stdout/stderr
- [ ] Port 8080 configuration
- [ ] Health check endpoints
- [ ] Container image requirements met

---

**For questions or updates to this document, contact:** platform-engineering@company.com

**Document ID:** INT-CD-CONSTRAINTS-2024-001  
**Classification:** Internal Use Only (IUO)  
**Next Review Date:** March 2025
