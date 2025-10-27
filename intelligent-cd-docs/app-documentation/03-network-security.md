# Network Policies and Security
## Network Configuration and Security Requirements

**Document Version:** 2.1.4  
**Last Updated:** December 2024  
**Document Owner:** Platform Engineering Team  
**Contact:** platform-engineering@company.com  
**Related Documents:** [01-intro.md](01-intro.md), [02-deployment-constraints.md](02-deployment-constraints.md)

---

## Table of Contents

1. [Network Policy Requirements](#network-policy-requirements)
2. [Default Network Policies](#default-network-policies)
3. [Custom Network Policy Process](#custom-network-policy-process)
4. [Firewall and Security Groups](#firewall-and-security-groups)
5. [Network Security Best Practices](#network-security-best-practices)
6. [Troubleshooting Network Issues](#troubleshooting-network-issues)

---

## Network Policy Requirements

All applications must implement network policies to control pod-to-pod communication. Contact **networking@company.com** for policy creation and review.

### Network Policy Overview

Network policies in OpenShift control how pods communicate with each other and with external endpoints. They provide fine-grained control over network traffic and are essential for implementing the principle of least privilege.

### Policy Enforcement

- **Default Behavior:** All traffic is denied unless explicitly allowed
- **Policy Scope:** Namespace-level enforcement
- **Traffic Types:** Ingress (incoming) and Egress (outgoing)
- **Protocol Support:** TCP, UDP, and ICMP

---

## Default Network Policies

The following network policies are automatically applied to all namespaces and cannot be modified without approval.

### Default Deny All Policy

| Policy Name | Purpose | Contact | Approval | Implementation |
|-------------|---------|---------|----------|----------------|
| **default-deny-all** | Deny all ingress/egress | networking@company.com | Standard | Automatic |
| **allow-dns** | Allow DNS resolution | networking@company.com | Standard | Automatic |
| **allow-health-checks** | Allow health check traffic | networking@company.com | Standard | Automatic |
| **allow-kube-system** | Allow OpenShift system traffic | networking@company.com | Standard | Automatic |

### Policy Details

#### default-deny-all
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: intelligent-cd
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  # No rules specified = deny all
```

#### allow-dns
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: intelligent-cd
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to: []
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

#### allow-health-checks
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-health-checks
  namespace: intelligent-cd
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: TCP
      port: 8080
```

---

## Custom Network Policy Process

### Policy Creation Workflow

**Step 1: Submit Request**
- **Contact:** networking@company.com
- **Subject:** "Network Policy Request - [Application Name]"
- **Required Information:**
  - Source and destination namespaces
  - Port and protocol requirements
  - Business justification
  - Security impact assessment
  - Traffic flow diagram

**Step 2: Initial Review**
- **Timeline:** 1-2 business days
- **Deliverables:** Initial assessment and feedback
- **Contact:** networking@company.com

**Step 3: Security Review**
- **Timeline:** 2-3 business days
- **Contact:** security@company.com
- **Deliverables:** Security assessment and recommendations

**Step 4: Final Approval**
- **Timeline:** 1-2 business days
- **Contact:** networking@company.com
- **Deliverables:** Approved policy or rejection with feedback

**Step 5: Implementation**
- **Timeline:** 1-2 business days after approval
- **Contact:** networking@company.com
- **Deliverables:** Active network policy

### Required Documentation

#### Business Justification
- **Purpose:** Clear explanation of why the policy is needed
- **Business Impact:** What happens if the policy is not implemented
- **Alternative Solutions:** Other approaches considered

#### Security Impact Assessment
- **Risk Level:** Low/Medium/High risk assessment
- **Mitigation Strategies:** How risks will be minimized
- **Monitoring Requirements:** How the policy will be monitored

#### Traffic Flow Diagram
- **Source Pods:** Which pods will initiate connections
- **Destination Pods:** Which pods will receive connections
- **Ports and Protocols:** Specific communication requirements
- **Data Flow:** Direction and frequency of communication

### Policy Approval Matrix

| Policy Type | Risk Level | Approval Required | Contact | Timeline |
|-------------|------------|-------------------|---------|----------|
| **Standard Ports** | Low | Networking Team | networking@company.com | 2-3 days |
| **Non-Standard Ports** | Medium | Security + Networking | security@company.com | 3-5 days |
| **Cross-Namespace** | Medium | Security + Networking | security@company.com | 3-5 days |
| **External Access** | High | Security + Architecture | security@company.com | 5-7 days |

---

## Custom Network Policy Examples

### Basic Application Communication

#### Allow Frontend to Backend Communication
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: intelligent-cd-frontend-backend
  namespace: intelligent-cd
spec:
  podSelector:
    matchLabels:
      app: intelligent-cd-frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: intelligent-cd-backend
    ports:
    - protocol: TCP
      port: 8080
```

#### Allow Backend to Database Communication
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: intelligent-cd-backend-database
  namespace: intelligent-cd
spec:
  podSelector:
    matchLabels:
      app: intelligent-cd-backend
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
    ports:
    - protocol: TCP
      port: 5432
```

### Advanced Communication Patterns

#### Allow Monitoring Access
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: intelligent-cd-monitoring
  namespace: intelligent-cd
spec:
  podSelector:
    matchLabels:
      app: intelligent-cd
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 8080
```

#### Allow External API Access
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: intelligent-cd-external-api
  namespace: intelligent-cd
spec:
  podSelector:
    matchLabels:
      app: intelligent-cd
  policyTypes:
  - Egress
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 80
```

### Complete Application Network Policy

#### Comprehensive Network Policy for Intelligent CD
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: intelligent-cd-comprehensive
  namespace: intelligent-cd
spec:
  podSelector:
    matchLabels:
      app: intelligent-cd
  policyTypes:
  - Ingress
  - Egress
  
  # Ingress rules
  ingress:
  # Allow health checks from OpenShift
  - from:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: TCP
      port: 8080
  
  # Allow monitoring access
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 8080
  
  # Allow ingress controller traffic
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-controller
    ports:
    - protocol: TCP
      port: 8080
  
  # Egress rules
  egress:
  # Allow DNS resolution
  - to: []
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  
  # Allow database access
  - to:
    - namespaceSelector:
        matchLabels:
          name: database
    ports:
    - protocol: TCP
      port: 5432
  
  # Allow Redis access
  - to:
    - namespaceSelector:
        matchLabels:
          name: cache
    ports:
    - protocol: TCP
      port: 6379
  
  # Allow external HTTPS access
  - to: []
    ports:
    - protocol: TCP
      port: 443
```

---

## Firewall and Security Groups

### Environment-Specific Firewall Rules

| Environment | Firewall Rules | Contact | Approval Required | Implementation Time |
|-------------|----------------|---------|-------------------|---------------------|
| **Development** | Standard rules | networking@company.com | No | 1 business day |
| **Staging** | Standard + monitoring | networking@company.com | No | 1-2 business days |
| **Production** | Custom rules | security@company.com | Yes - Security Team | 3-5 business days |

### Firewall Rule Categories

#### Standard Rules (Auto-applied)
- **HTTP/HTTPS:** Ports 80 and 443
- **DNS:** Port 53 (UDP/TCP)
- **NTP:** Port 123 (UDP)
- **SSH:** Port 22 (restricted to jump hosts)

#### Monitoring Rules
- **Prometheus:** Port 9090
- **Grafana:** Port 3000
- **Node Exporter:** Port 9100
- **Alert Manager:** Port 9093

#### Application-Specific Rules
- **Intelligent CD API:** Port 8080
- **Database:** Port 5432
- **Redis:** Port 6379
- **Load Balancer Health Checks:** Port 8080

### Firewall Change Process

**Standard Rules (Development/Staging):**
1. Submit request to networking@company.com
2. Include port and protocol requirements
3. Implementation within 1-2 business days

**Custom Rules (Production):**
1. Submit request to security@company.com
2. Include business justification and risk assessment
3. Security review (2-3 business days)
4. Network implementation (1 business day)

### Security Group Configuration

#### Development Security Group
```yaml
# Development environment security group
SecurityGroup:
  Name: intelligent-cd-dev-sg
  Description: Security group for Intelligent CD development environment
  Rules:
    Inbound:
      - Port: 8080, Source: 10.0.0.0/8, Protocol: TCP
      - Port: 22, Source: 10.0.0.0/8, Protocol: TCP
    Outbound:
      - Port: 443, Destination: 0.0.0.0/0, Protocol: TCP
      - Port: 53, Destination: 0.0.0.0/0, Protocol: UDP
```

#### Production Security Group
```yaml
# Production environment security group
SecurityGroup:
  Name: intelligent-cd-prod-sg
  Description: Security group for Intelligent CD production environment
  Rules:
    Inbound:
      - Port: 8080, Source: 10.0.0.0/8, Protocol: TCP
      - Port: 22, Source: 10.0.0.0/8, Protocol: TCP
      - Port: 9090, Source: 10.0.0.0/8, Protocol: TCP
    Outbound:
      - Port: 443, Destination: 0.0.0.0/0, Protocol: TCP
      - Port: 53, Destination: 0.0.0.0/0, Protocol: UDP
      - Port: 5432, Destination: 10.0.0.0/8, Protocol: TCP
```

---

## Network Security Best Practices

### Policy Design Principles

#### Least Privilege
- **Default Deny:** Start with denying all traffic
- **Specific Allow:** Only allow necessary communication paths
- **Regular Review:** Periodically review and update policies

#### Segmentation
- **Namespace Isolation:** Separate applications by namespace
- **Tier Separation:** Separate frontend, backend, and database tiers
- **Environment Isolation:** Separate development, staging, and production

#### Monitoring and Logging
- **Traffic Logging:** Log all network policy decisions
- **Alerting:** Alert on policy violations
- **Metrics:** Track policy effectiveness

### Security Checklist

- [ ] Network policies implemented for all applications
- [ ] Default deny policies in place
- [ ] Specific allow rules documented and justified
- [ ] Cross-namespace communication restricted
- [ ] External access limited and monitored
- [ ] Firewall rules aligned with network policies
- [ ] Security groups properly configured
- [ ] Monitoring and alerting configured
- [ ] Regular policy reviews scheduled

---

## Troubleshooting Network Issues

### Common Network Problems

#### Pod Cannot Connect to Service
**Symptoms:**
- Connection timeouts
- "Connection refused" errors
- Pods cannot reach other services

**Diagnostic Steps:**
1. Check network policies
2. Verify service endpoints
3. Check pod labels and selectors
4. Review namespace isolation

**Contact:** networking@company.com

#### Network Policy Blocking Traffic
**Symptoms:**
- Unexpected connection failures
- Traffic blocked between expected endpoints
- Policy violations in logs

**Diagnostic Steps:**
1. Review network policy rules
2. Check pod selectors
3. Verify namespace labels
4. Test with temporary policy relaxation

**Contact:** networking@company.com

#### Firewall Blocking Connections
**Symptoms:**
- External connections failing
- Load balancer health checks failing
- Monitoring tools cannot reach applications

**Diagnostic Steps:**
1. Check firewall rules
2. Verify security group configuration
3. Test connectivity from different sources
4. Review network ACLs

**Contact:** networking@company.com

### Debugging Commands

#### Check Network Policies
```bash
# List all network policies in namespace
oc get networkpolicies -n intelligent-cd

# Describe specific network policy
oc describe networkpolicy <policy-name> -n intelligent-cd

# Check network policy status
oc get networkpolicies -n intelligent-cd -o yaml
```

#### Check Pod Connectivity
```bash
# Test connectivity from pod to service
oc exec -it <pod-name> -n intelligent-cd -- curl -v <service-name>:8080

# Check pod labels
oc get pods -n intelligent-cd --show-labels

# Verify service endpoints
oc get endpoints -n intelligent-cd
```

#### Check Network Configuration
```bash
# Check OpenShift network configuration
oc get clusternetwork

# Check network policies at cluster level
oc get networkpolicies --all-namespaces

# Check firewall rules (if accessible)
oc get nodes -o wide
```

### Escalation Path

#### Level 1: Basic Troubleshooting
- **Contact:** networking@company.com
- **Timeline:** 2-4 hours
- **Actions:** Basic diagnostics and common fixes

#### Level 2: Advanced Troubleshooting
- **Contact:** networking@company.com + security@company.com
- **Timeline:** 4-8 hours
- **Actions:** Deep dive analysis and policy adjustments

#### Level 3: Emergency Response
- **Contact:** oncall-networking@company.com
- **Timeline:** Immediate response
- **Actions:** Emergency policy changes and incident management

---

## Network Policy Templates

### Standard Application Template
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ .AppName }}-network-policy
  namespace: {{ .Namespace }}
spec:
  podSelector:
    matchLabels:
      app: {{ .AppName }}
  policyTypes:
  - Ingress
  - Egress
  
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-controller
    ports:
    - protocol: TCP
      port: {{ .Port }}
  
  egress:
  - to: []
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### Database Access Template
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ .AppName }}-database-access
  namespace: {{ .Namespace }}
spec:
  podSelector:
    matchLabels:
      app: {{ .AppName }}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: {{ .DatabaseNamespace }}
    ports:
    - protocol: TCP
      port: {{ .DatabasePort }}
```

---

**For questions or updates to this document, contact:** networking@company.com

**Document ID:** INT-CD-NETWORK-2024-001  
**Classification:** Internal Use Only (IUO)  
**Next Review Date:** March 2025
