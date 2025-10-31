# ArgoCD Application Creation Best Practices

## Overview

Guidelines for creating ArgoCD Application resources as YAML for GitOps deployments.

## Mandatory Requirements

### Namespace
- **MANDATORY**: `metadata.namespace` must be set to `openshift-gitops`
- Application name should match the directory name in the Git repository (typically the target namespace name)

### Source Configuration
- **MANDATORY**: `spec.source.repoURL` - Git repository URL containing application manifests
- `spec.source.path` - Directory path in Git repository (typically matches namespace name)
- `spec.source.targetRevision` - Git branch/tag (usually `main` or `HEAD`)

### Destination Configuration
- `spec.destination.server` - Target cluster (typically `https://kubernetes.default.svc` for same-cluster)
- **MANDATORY**: `spec.destination.namespace` - Target namespace where application deploys

### Sync Policy
- **MANDATORY**: `spec.syncPolicy.automated` - Enable automatic syncing
- `spec.syncPolicy.automated.prune: true` - Automatically delete resources removed from Git
- `spec.syncPolicy.automated.selfHeal: true` - Automatically sync when drift detected
- **MANDATORY**: `spec.syncPolicy.syncOptions` must include `CreateNamespace=true`

## Standard YAML Structure

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: <application-name>          # Typically matches target namespace
  namespace: openshift-gitops       # MANDATORY
spec:
  project: default                   # ArgoCD project (usually 'default')
  source:
    repoURL: <git-repository-url>   # GitOps repository URL
    targetRevision: main             # Git branch/tag
    path: <path-in-repo>             # Directory path (typically namespace name)
  destination:
    server: https://kubernetes.default.svc  # Target cluster
    namespace: <target-namespace>    # MANDATORY: Deployment target
  syncPolicy:
    automated:
      prune: true                    # Auto-delete removed resources
      selfHeal: true                 # Auto-sync on drift
    syncOptions:
      - CreateNamespace=true         # MANDATORY: Auto-create namespace
```

## Key Best Practices

1. **Application Naming**: Use descriptive names that typically match the target namespace
2. **Path Configuration**: Path in Git repository should match application structure (often namespace name)
3. **Automatic Sync**: Always enable automated sync for GitOps workflows
4. **Namespace Management**: Always include `CreateNamespace=true` in syncOptions
5. **Prune and Self-Heal**: Enable both for true GitOps automation
6. **Project Assignment**: Use `default` project unless using custom ArgoCD projects

## Validation Checklist

Before applying, ensure:
- ✅ Metadata namespace is `openshift-gitops`
- ✅ Source repository URL is correct
- ✅ Source path exists in repository
- ✅ Destination namespace is specified
- ✅ Automated sync is enabled
- ✅ CreateNamespace=true is in syncOptions
- ✅ Application name is unique and descriptive