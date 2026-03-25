"""Node: generate_helm — call LLM to produce a Helm chart from enhanced YAML."""

from __future__ import annotations

from pipeline.state import PipelineState
from utils import get_logger

logger = get_logger("pipeline.helm")


def generate_helm_node(state: PipelineState) -> dict:
    """Call the Responses API to generate a Helm chart from the enhanced YAML."""
    from pipeline.graph import get_shared_context

    ctx = get_shared_context()
    call_responses = ctx["call_responses_api"]
    helm_config = ctx["config_generate_helm"]

    chart_name = state.get("chart_name", state.get("namespace", "chart"))
    enhanced_yaml = state.get("enhanced_yaml", "")
    log = state.get("progress_log", [])[:]

    from pipeline.graph import live_progress

    msg = f"Generating Helm chart '{chart_name}' from {len(enhanced_yaml)} chars of YAML..."
    log.append(msg)
    live_progress(msg)

    message = (
        f"Generate a Helm chart named '{chart_name}' from these Kubernetes resources:\n\n"
        f"{enhanced_yaml if enhanced_yaml else 'No resources provided.'}"
    )

    try:
        helm_chart = call_responses(message, helm_config)
        log.append(f"  Helm chart generated ({len(helm_chart)} characters)")
    except Exception as exc:
        logger.error(f"Helm generation failed: {exc}")
        return {"error": f"Helm generation failed: {exc}", "progress_log": log}

    return {"helm_chart": helm_chart, "progress_log": log}
