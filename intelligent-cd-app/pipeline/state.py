"""Pipeline state definition for the LangGraph-orchestrated CD workflow."""

from __future__ import annotations

from typing import TypedDict


class PipelineState(TypedDict, total=False):
    # -- Inputs (set once at pipeline start) --
    namespace: str
    chart_name: str
    workload_type: str
    supporting_resources: list[str]

    # -- Phase 1: Fetch + Clean + Best Practices --
    raw_resources: list[dict]
    cleaned_resources: list[dict]
    enhanced_yaml: str
    changes_applied: list[str]

    # -- Phase 2: Validate (LLM+MCP) --
    validation_namespace: str
    validation_result: str
    validation_attempts: int
    validation_passed: bool

    # -- Phase 3: Helm + Push --
    helm_chart: str
    pushed_files: list[str]
    push_errors: list[str]

    # -- Phase 4: ArgoCD --
    argocd_yaml: str
    argocd_deployed: bool

    # -- Phase 5: Validate GitOps --
    argocd_validation_result: str
    argocd_validation_passed: bool

    # -- Control --
    current_phase: int
    error: str | None
    progress_log: list[str]
