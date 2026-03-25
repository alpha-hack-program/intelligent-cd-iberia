KUBERNETES/OPENSHIFT - DEPLOYMENT CONFIGURATION BEST PRACTICES
                
DEPLOYMENT RESOURCE SPECIFICATIONS FOR APPLICATIONS:

RESOURCE REQUESTS AND LIMITS:
- Always specify resource requests and limits for applications
- CPU requests: Start with 100m (0.1 CPU core) for microservices
- Memory requests: Start with 256Mi for applications
- CPU limits: Set 2-3x higher than requests for burstability
- Memory limits: Set 1.5-2x higher than requests

MANDATORY DEPLOYMENT RESOURCE CONFIGURATION TO ADD IF MISSING:
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"

HEALTH CHECKS FOR APPLICATION SERVICES:

MANDATORY LIVENESS PROBE TO ADD IF MISSING:
livenessProbe:
  failureThreshold: 3
  httpGet:
    path: /q/health/live
    port: 8080
    scheme: HTTP
  initialDelaySeconds: 30
  periodSeconds: 30
  successThreshold: 1
  timeoutSeconds: 10

MANDATORY READINESS PROBE TO ADD IF MISSING:
readinessProbe:
  failureThreshold: 3
  httpGet:
    path: /q/health/ready
    port: 8080
    scheme: HTTP
  initialDelaySeconds: 5
  periodSeconds: 30
  successThreshold: 1
  timeoutSeconds: 10

CONFIGMAP INTEGRATION PATTERNS:
- Use environment variables from ConfigMaps for application configuration
- Mount ConfigMaps as volumes for complex configuration files
- Separate configuration by environment (dev, staging, prod)

EXAMPLE CONFIGMAP USAGE IN DEPLOYMENT:
env:
- name: APP_CONFIG_VALUE
  valueFrom:
    configMapKeyRef:
      name: app-config
      key: config-value
- name: DATABASE_URL
  valueFrom:
    configMapKeyRef:
      name: app-config
      key: database-url

KUBERNETES DEFAULT FIELDS TO REMOVE:
The Kubernetes API server injects many default values when creating resources.
These MUST be removed when cleaning resources for GitOps or Helm chart generation:
- progressDeadlineSeconds: 600
- revisionHistoryLimit: 10
- strategy.type: RollingUpdate (with default maxSurge: 25%, maxUnavailable: 25%)
- terminationMessagePath: /dev/termination-log
- terminationMessagePolicy: File
- dnsPolicy: ClusterFirst
- restartPolicy: Always
- schedulerName: default-scheduler
- terminationGracePeriodSeconds: 30
- securityContext: {} (if empty)
Only keep these fields if the user explicitly set non-default values.
