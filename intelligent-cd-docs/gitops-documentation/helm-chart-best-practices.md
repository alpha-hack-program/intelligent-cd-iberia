KUBERNETES/OPENSHIFT - HELM CHART GENERATION BEST PRACTICES

CHART STRUCTURE:
A Helm chart must contain at minimum:
- Chart.yaml: Helm chart metadata
- values.yaml: Configurable parameters
- templates/_helpers.tpl: Reusable template helpers (labels, names, selectors)
- templates/: One template file per Kubernetes resource

CHART.YAML REQUIREMENTS:
- apiVersion: v2 (Helm 3)
- name: Use the application name (lowercase, hyphenated)
- version: Semantic versioning for the chart (e.g. 0.1.0)
- appVersion: MANDATORY — must match the container image tag from the Deployment (e.g. if image is app:v1.0.1, appVersion is "v1.0.1")
- description: Short description of the chart purpose

VALUES.YAML - WHAT TO EXTRACT AS PARAMETERS:

For Deployments:
- replicaCount: Number of replicas
- image.repository: Container image registry/name
- image.tag: Container image version tag
- image.pullPolicy: Image pull policy (IfNotPresent, Always, Never)
- resources.requests.cpu: CPU request
- resources.requests.memory: Memory request
- resources.limits.cpu: CPU limit
- resources.limits.memory: Memory limit

For Services:
- service.type: Service type (ClusterIP, NodePort, LoadBalancer)
- service.port: Service port number
- service.targetPort: Target container port

For Routes (OpenShift):
- route.targetPort: Target port name or number (e.g. 8080-tcp)
- route.tls.termination: TLS termination type (edge, passthrough, reencrypt)
- route.tls.insecureEdgeTerminationPolicy: Redirect or Allow

For ConfigMaps:
- MANDATORY: Extract EVERY field under data as a parameter in values.yaml
- Organize config values hierarchically (e.g. config.application.colour, config.quarkus.log.level)
- This allows environment-specific overrides without changing templates

TEMPLATE BEST PRACTICES:

NAMING CONVENTION:
- Use {{ .Release.Name }} as prefix for ALL resource names
- Pattern: {{ .Release.Name }}-<component-name>
- This enables multiple installations in the same namespace
- The configMapRef.name in Deployments MUST match the ConfigMap template name

SELECTOR LABELS - USE HELM STANDARD LABELS:
- MANDATORY: Generate a templates/_helpers.tpl file with named templates:
    * {{ .Chart.Name }}.name: chart name truncated to 63 chars
    * {{ .Chart.Name }}.fullname: release name or release-chart combined, truncated to 63 chars
    * {{ .Chart.Name }}.selectorLabels: app.kubernetes.io/name + app.kubernetes.io/instance
    * {{ .Chart.Name }}.labels: full set of labels including selectorLabels + version + managed-by
- Standard label values:
    app.kubernetes.io/name: {{ include "<chart>.name" . }}
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/version: {{ .Chart.AppVersion }}
    app.kubernetes.io/managed-by: {{ .Release.Service }}
- Use these helpers in ALL templates:
    * Deployment metadata.labels: {{ include "<chart>.labels" . }}
    * Deployment spec.selector.matchLabels: {{ include "<chart>.selectorLabels" . }}
    * Deployment spec.template.metadata.labels: {{ include "<chart>.selectorLabels" . }}
    * Service spec.selector: {{ include "<chart>.selectorLabels" . }} (MUST match pod labels)
- NEVER hardcode labels like "app: my-app". Always use the helper templates.

KUBERNETES DEFAULTS TO REMOVE FROM TEMPLATES:
These fields are injected by the Kubernetes API server and should NOT be in Helm templates:
- Deployment: progressDeadlineSeconds, revisionHistoryLimit, strategy (unless custom), terminationMessagePath, terminationMessagePolicy, dnsPolicy, restartPolicy, schedulerName, terminationGracePeriodSeconds
- Service: internalTrafficPolicy, ipFamilies, ipFamilyPolicy, sessionAffinity
- Route: wildcardPolicy
- All resources: securityContext: {} (if empty)
Only include these if the user explicitly set non-default values.

CROSS-RESOURCE REFERENCES:
- Service selector MUST match Deployment pod labels
- Route spec.to.name MUST reference the Service name using {{ .Release.Name }}
- ConfigMap name in envFrom/configMapRef MUST match the ConfigMap template name
- All references must be consistent to ensure the chart works when installed

YAML FORMAT IN TEMPLATES:
- Values must be properly quoted when they contain special characters
- Use {{ .Values.xxx | quote }} for string values that might need quoting
- Numeric values should NOT be quoted (port: {{ .Values.service.port }})
- Boolean values should NOT be quoted
