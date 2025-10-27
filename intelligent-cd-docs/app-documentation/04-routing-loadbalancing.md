# Routing and Load Balancing
## Route Configuration and Traffic Management

**Document Version:** 2.1.4  
**Last Updated:** December 2024  
**Document Owner:** Platform Engineering Team  
**Contact:** platform-engineering@company.com  
**Related Documents:** [01-intro.md](01-intro.md), [03-network-security.md](03-network-security.md)

---

## Table of Contents

1. [Route Configuration](#route-configuration)
2. [Route Types and Use Cases](#route-types-and-use-cases)
3. [Load Balancer Configuration](#load-balancer-configuration)
4. [TLS Certificate Management](#tls-certificate-management)
5. [Traffic Routing Strategies](#traffic-routing-strategies)
6. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)

---

## Route Configuration

Contact **networking@company.com** for route creation and management. Routes in OpenShift provide external access to your application services.

### Route Overview

Routes in OpenShift are Kubernetes resources that expose services at a hostname, allowing external traffic to reach your application. They handle TLS termination, load balancing, and traffic routing.

### Route Components

- **Hostname:** External DNS name for your application
- **Service:** Internal service that receives traffic
- **Port:** Target port on the service
- **TLS:** Certificate configuration for HTTPS
- **Annotations:** Custom routing behavior

---

## Route Types and Use Cases

### Route Classification

| Route Type | Purpose | Contact | Approval Required | Implementation Time |
|------------|---------|---------|-------------------|---------------------|
| **Public Route** | External internet access | networking@company.com | Yes - Security | 2-3 business days |
| **Internal Route** | Cluster-only access | networking@company.com | No | 1 business day |
| **Secure Route** | HTTPS with TLS | security@company.com | Yes - Security | 3-5 business days |
| **Wildcard Route** | Multiple subdomains | networking@company.com | Yes - Architecture | 5-7 business days |

### Route Use Cases by Environment

#### Development Environment
- **Purpose:** Developer testing and debugging
- **Access:** Internal network only
- **TLS:** Self-signed certificates (optional)
- **Contact:** devops@company.com

#### Staging Environment
- **Purpose:** QA testing and pre-production validation
- **Access:** Internal network + VPN
- **TLS:** Internal CA certificates
- **Contact:** devops@company.com

#### Production Environment
- **Purpose:** End-user access
- **Access:** Public internet
- **TLS:** Public CA certificates (required)
- **Contact:** networking@company.com + security@company.com

---

## Route Creation Process

### Standard Route Request

**Step 1: Submit Request**
- **Contact:** networking@company.com
- **Subject:** "Route Request - [Application Name]"
- **Required Information:**
  - Service name and namespace
  - Hostname requirements
  - TLS certificate needs
  - Access control requirements
  - Expected traffic volume

**Step 2: Initial Review**
- **Timeline:** 1-2 business days
- **Deliverables:** Initial assessment and feedback
- **Contact:** networking@company.com

**Step 3: Security Review (if required)**
- **Timeline:** 2-3 business days
- **Contact:** security@company.com
- **Deliverables:** Security assessment and recommendations

**Step 4: Final Approval**
- **Timeline:** 1-2 business days
- **Contact:** networking@company.com
- **Deliverables:** Approved route or rejection with feedback

**Step 5: Implementation**
- **Timeline:** 1 business day after approval
- **Contact:** networking@company.com
- **Deliverables:** Active route configuration

### Required Documentation

#### Route Specification
- **Hostname:** Desired external DNS name
- **Service Details:** Service name, namespace, and port
- **Traffic Requirements:** Expected request volume and patterns
- **Security Requirements:** Authentication and authorization needs

#### Business Justification
- **Purpose:** Why external access is needed
- **User Base:** Who will access the application
- **Business Impact:** What happens if the route is not created
- **Alternative Solutions:** Other access methods considered

#### Security Assessment
- **Data Classification:** Sensitivity of data being exposed
- **Access Control:** How access will be restricted
- **Monitoring Requirements:** How traffic will be monitored
- **Incident Response:** How security incidents will be handled

---

## Route Configuration Examples

### Basic HTTP Route

#### Simple Route Configuration
```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: intelligent-cd-route
  namespace: intelligent-cd
  annotations:
    openshift.io/host.generated: "false"
spec:
  host: intelligent-cd.apps.company.com
  to:
    kind: Service
    name: intelligent-cd-service
    weight: 100
  port:
    targetPort: 8080
```

#### Route with Custom Annotations
```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: intelligent-cd-route
  namespace: intelligent-cd
  annotations:
    openshift.io/host.generated: "false"
    haproxy.router.openshift.io/timeout: "30s"
    haproxy.router.openshift.io/rate-limit-connections: "100"
    haproxy.router.openshift.io/rate-limit-http-requests: "200"
spec:
  host: intelligent-cd.apps.company.com
  to:
    kind: Service
    name: intelligent-cd-service
    weight: 100
  port:
    targetPort: 8080
```

### Secure HTTPS Route

#### Edge TLS Termination
```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: intelligent-cd-secure-route
  namespace: intelligent-cd
  annotations:
    openshift.io/host.generated: "false"
spec:
  host: intelligent-cd.company.com
  to:
    kind: Service
    name: intelligent-cd-service
    weight: 100
  port:
    targetPort: 8080
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
    certificate: |
      -----BEGIN CERTIFICATE-----
      [Your certificate content here]
      -----END CERTIFICATE-----
    key: |
      -----BEGIN PRIVATE KEY-----
      [Your private key content here]
      -----END PRIVATE KEY-----
```

#### Passthrough TLS Termination
```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: intelligent-cd-passthrough-route
  namespace: intelligent-cd
  annotations:
    openshift.io/host.generated: "false"
spec:
  host: intelligent-cd.company.com
  to:
    kind: Service
    name: intelligent-cd-service
    weight: 100
  port:
    targetPort: 8080
  tls:
    termination: passthrough
```

### Advanced Route Configurations

#### Route with Multiple Services (Blue-Green)
```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: intelligent-cd-blue-green-route
  namespace: intelligent-cd
  annotations:
    openshift.io/host.generated: "false"
spec:
  host: intelligent-cd.company.com
  to:
    kind: Service
    name: intelligent-cd-blue-service
    weight: 80
  alternateBackends:
  - kind: Service
    name: intelligent-cd-green-service
    weight: 20
  port:
    targetPort: 8080
```

#### Route with Custom Headers
```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: intelligent-cd-custom-headers-route
  namespace: intelligent-cd
  annotations:
    openshift.io/host.generated: "false"
    haproxy.router.openshift.io/set-header: "X-Custom-Header: IntelligentCD"
    haproxy.router.openshift.io/set-header: "X-Environment: Production"
spec:
  host: intelligent-cd.company.com
  to:
    kind: Service
    name: intelligent-cd-service
    weight: 100
  port:
    targetPort: 8080
```

---

## Load Balancer Configuration

### Load Balancer Types

| Load Balancer Type | Use Case | Contact | Approval | Implementation Time |
|--------------------|----------|---------|----------|---------------------|
| **Application Load Balancer** | HTTP/HTTPS traffic | networking@company.com | No | 1-2 business days |
| **Network Load Balancer** | TCP/UDP traffic | networking@company.com | Yes - Architecture | 3-5 business days |
| **Classic Load Balancer** | Legacy applications | networking@company.com | Yes - Architecture | 3-5 business days |
| **Internal Load Balancer** | Cluster-only traffic | networking@company.com | No | 1 business day |

### Load Balancer Selection Criteria

#### Application Load Balancer (ALB)
**Best For:**
- HTTP/HTTPS applications
- Path-based routing
- Host-based routing
- SSL/TLS termination
- Cookie-based session affinity

**Contact:** networking@company.com

#### Network Load Balancer (NLB)
**Best For:**
- TCP/UDP applications
- High throughput requirements
- Static IP addresses
- Cross-zone load balancing
- Protocol-specific features

**Contact:** networking@company.com + architecture@company.com

### Load Balancer Configuration Process

**Step 1: Load Balancer Selection**
- **Contact:** networking@company.com
- **Timeline:** 1 business day
- **Deliverables:** Load balancer type recommendation

**Step 2: Configuration Design**
- **Contact:** networking@company.com
- **Timeline:** 2-3 business days
- **Deliverables:** Load balancer configuration design

**Step 3: Implementation**
- **Contact:** networking@company.com
- **Timeline:** 1-2 business days
- **Deliverables:** Active load balancer configuration

### Load Balancer Configuration Examples

#### Application Load Balancer Configuration
```yaml
apiVersion: v1
kind: Service
metadata:
  name: intelligent-cd-alb-service
  namespace: intelligent-cd
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
  selector:
    app: intelligent-cd
```

#### Network Load Balancer Configuration
```yaml
apiVersion: v1
kind: Service
metadata:
  name: intelligent-cd-nlb-service
  namespace: intelligent-cd
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
spec:
  type: LoadBalancer
  ports:
  - port: 8080
    targetPort: 8080
    protocol: TCP
  selector:
    app: intelligent-cd
```

---

## TLS Certificate Management

### Certificate Types

| Certificate Type | Use Case | Contact | Approval | Implementation Time |
|------------------|----------|---------|----------|---------------------|
| **Self-Signed** | Development/testing | devops@company.com | No | Immediate |
| **Internal CA** | Staging/internal | security@company.com | Yes - Security | 2-3 business days |
| **Public CA** | Production/external | security@company.com | Yes - Security | 5-7 business days |
| **Wildcard** | Multiple subdomains | security@company.com | Yes - Security | 7-10 business days |

### Certificate Request Process

**Step 1: Certificate Type Selection**
- **Contact:** security@company.com
- **Timeline:** 1 business day
- **Deliverables:** Certificate type recommendation

**Step 2: Certificate Request**
- **Contact:** security@company.com
- **Timeline:** 2-3 business days
- **Deliverables:** Certificate request approval

**Step 3: Certificate Generation**
- **Contact:** security@company.com
- **Timeline:** 1-2 business days
- **Deliverables:** Generated certificate files

**Step 4: Certificate Installation**
- **Contact:** networking@company.com
- **Timeline:** 1 business day
- **Deliverables:** Active certificate configuration

### Certificate Configuration Examples

#### Self-Signed Certificate Generation
```bash
# Generate private key
openssl genrsa -out intelligent-cd.key 2048

# Generate certificate signing request
openssl req -new -key intelligent-cd.key -out intelligent-cd.csr -subj "/CN=intelligent-cd.apps.company.com"

# Generate self-signed certificate
openssl x509 -req -in intelligent-cd.csr -signkey intelligent-cd.key -out intelligent-cd.crt -days 365
```

#### Route with Self-Signed Certificate
```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: intelligent-cd-self-signed-route
  namespace: intelligent-cd
spec:
  host: intelligent-cd.apps.company.com
  to:
    kind: Service
    name: intelligent-cd-service
    weight: 100
  port:
    targetPort: 8080
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
    certificate: |
      -----BEGIN CERTIFICATE-----
      [Self-signed certificate content]
      -----END CERTIFICATE-----
    key: |
      -----BEGIN PRIVATE KEY-----
      [Private key content]
      -----END PRIVATE KEY-----
```

---

## Traffic Routing Strategies

### Routing Patterns

#### Round Robin (Default)
- **Description:** Distributes traffic evenly across all endpoints
- **Use Case:** General load balancing
- **Configuration:** Default OpenShift behavior

#### Session Affinity
- **Description:** Routes requests from the same client to the same endpoint
- **Use Case:** Stateful applications
- **Configuration:** Requires custom annotations

#### Weighted Routing
- **Description:** Routes traffic based on configured weights
- **Use Case:** Blue-green deployments, canary releases
- **Configuration:** Multiple backends with weights

### Advanced Routing Examples

#### Canary Deployment Route
```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: intelligent-cd-canary-route
  namespace: intelligent-cd
  annotations:
    openshift.io/host.generated: "false"
spec:
  host: intelligent-cd.company.com
  to:
    kind: Service
    name: intelligent-cd-stable-service
    weight: 90
  alternateBackends:
  - kind: Service
    name: intelligent-cd-canary-service
    weight: 10
  port:
    targetPort: 8080
```

#### Path-Based Routing
```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: intelligent-cd-api-route
  namespace: intelligent-cd
  annotations:
    openshift.io/host.generated: "false"
spec:
  host: intelligent-cd.company.com
  path: /api
  to:
    kind: Service
    name: intelligent-cd-api-service
    weight: 100
  port:
    targetPort: 8080
```

---

## Monitoring and Troubleshooting

### Route Health Monitoring

#### Health Check Endpoints
| Endpoint | Purpose | Expected Response | Contact |
|----------|---------|-------------------|---------|
| **/health** | Basic health check | HTTP 200 OK | platform-engineering@company.com |
| **/ready** | Readiness check | HTTP 200 OK | platform-engineering@company.com |
| **/metrics** | Prometheus metrics | HTTP 200 OK + metrics | monitoring@company.com |

#### Route Status Monitoring
```bash
# Check route status
oc get routes -n intelligent-cd

# Describe specific route
oc describe route <route-name> -n intelligent-cd

# Check route endpoints
oc get endpoints -n intelligent-cd
```

### Common Route Issues

#### Route Not Accessible
**Symptoms:**
- External requests failing
- DNS resolution issues
- TLS certificate problems

**Diagnostic Steps:**
1. Check route configuration
2. Verify DNS resolution
3. Check TLS certificate validity
4. Review network policies

**Contact:** networking@company.com

#### TLS Certificate Issues
**Symptoms:**
- Browser security warnings
- Certificate expiration errors
- TLS handshake failures

**Diagnostic Steps:**
1. Check certificate expiration
2. Verify certificate chain
3. Check private key configuration
4. Review certificate installation

**Contact:** security@company.com

### Troubleshooting Commands

#### Route Diagnostics
```bash
# Check route configuration
oc get routes -n intelligent-cd -o yaml

# Test route connectivity
curl -v -H "Host: intelligent-cd.company.com" http://localhost:8080

# Check TLS certificate
openssl s_client -connect intelligent-cd.company.com:443 -servername intelligent-cd.company.com
```

#### Load Balancer Diagnostics
```bash
# Check service endpoints
oc get endpoints -n intelligent-cd

# Check service configuration
oc get service -n intelligent-cd -o yaml

# Check pod readiness
oc get pods -n intelligent-cd --show-labels
```

---

## Route Templates

### Standard Route Template
```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: {{ .AppName }}-route
  namespace: {{ .Namespace }}
  annotations:
    openshift.io/host.generated: "false"
spec:
  host: {{ .Hostname }}
  to:
    kind: Service
    name: {{ .ServiceName }}
    weight: 100
  port:
    targetPort: {{ .Port }}
```

### Secure Route Template
```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: {{ .AppName }}-secure-route
  namespace: {{ .Namespace }}
  annotations:
    openshift.io/host.generated: "false"
spec:
  host: {{ .Hostname }}
  to:
    kind: Service
    name: {{ .ServiceName }}
    weight: 100
  port:
    targetPort: {{ .Port }}
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
```

---

**For questions or updates to this document, contact:** networking@company.com

**Document ID:** INT-CD-ROUTING-2024-001  
**Classification:** Internal Use Only (IUO)  
**Next Review Date:** March 2025
