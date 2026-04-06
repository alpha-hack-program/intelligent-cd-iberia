"""Node: apply_best_practices — LLM enhancement via RAG + diff computation."""

from __future__ import annotations

import difflib

import yaml

from pipeline.state import PipelineState
from utils import get_logger

logger = get_logger("pipeline.best_practices")


def _resource_to_yaml(resource: dict) -> str:
    return yaml.dump(resource, default_flow_style=False, sort_keys=False).rstrip()



def _compute_diff_summary(before_yaml: str, after_yaml: str, kind: str, name: str) -> list[str]:
    """Compare before/after YAML and produce human-readable change lines."""
    before_lines = before_yaml.splitlines()
    after_lines = after_yaml.splitlines()
    diff = list(difflib.unified_diff(before_lines, after_lines, lineterm=""))

    changes: list[str] = []
    for line in diff:
        stripped = line.strip()
        if line.startswith("+") and not line.startswith("+++"):
            for keyword in (
                "livenessProbe", "readinessProbe", "resources",
                "requests", "limits", "labels", "startupProbe",
            ):
                if keyword in stripped:
                    changes.append(f"  + Added {keyword}")
                    break
        elif line.startswith("-") and not line.startswith("---"):
            for keyword in (
                "progressDeadlineSeconds", "dnsPolicy", "restartPolicy",
                "schedulerName", "terminationGracePeriodSeconds",
                "revisionHistoryLimit", "strategy",
            ):
                if keyword in stripped:
                    changes.append(f"  - Removed {keyword} (K8s default)")
                    break

    seen = set()
    unique: list[str] = []
    for c in changes:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    if unique:
        return [f"{kind} '{name}':"] + unique
    return []


def apply_best_practices_node(state: PipelineState) -> dict:
    """Apply LLM best practices to each cleaned resource via RAG.

    This node requires ``llm_caller`` to be injected into the state at
    runtime by the Gradio wrapper (it's a callable, not serialisable).
    """
    from pipeline.graph import get_shared_context

    ctx = get_shared_context()
    call_responses = ctx["call_responses_api"]
    bp_config = ctx["config_apply_best_practices"]

    cleaned = state.get("cleaned_resources", [])
    log = state.get("progress_log", [])[:]

    total = len(cleaned)
    enhanced_yamls: list[str] = []
    all_changes: list[str] = []

    from pipeline.graph import live_progress

    for idx, res in enumerate(cleaned, start=1):
        kind = res.get("kind", "Unknown")
        name = res.get("metadata", {}).get("name", "unknown")
        msg = f"Applying best practices to {kind} '{name}' ({idx}/{total})..."
        log.append(msg)
        live_progress(msg)

        before_yaml = _resource_to_yaml(res)
        message = (
            f"Here is a pre-cleaned Kubernetes {kind} YAML resource.\n"
            f"Apply best practices from the documentation and return ONLY the improved YAML.\n"
            f"Do NOT include any explanation, commentary, or tool call syntax.\n"
            f"Your entire response must be valid YAML and nothing else.\n\n"
            f"{before_yaml}"
        )
        try:
            after_yaml = call_responses(message, bp_config).strip()
            enhanced_yamls.append(after_yaml)
            diff_lines = _compute_diff_summary(before_yaml, after_yaml, kind, name)
            all_changes.extend(diff_lines)
        except Exception as exc:
            logger.error(f"LLM enhancement failed for {kind}/{name}: {exc}")
            warn = f"  WARNING: LLM enhancement failed for {kind} '{name}', using cleaned version"
            log.append(warn)
            live_progress(warn)
            enhanced_yamls.append(before_yaml)

    log.append(f"Done. {total} resources processed.")

    final_yaml = "---\n" + "\n---\n".join(enhanced_yamls) + "\n"

    return {
        "enhanced_yaml": final_yaml,
        "changes_applied": all_changes,
        "progress_log": log,
        "current_phase": 1,
    }
