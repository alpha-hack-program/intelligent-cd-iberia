"""Node: clean_resources — deterministic YAML cleanup in pure Python."""

from __future__ import annotations

import json
import re

from pipeline.state import PipelineState
from utils import get_logger

logger = get_logger("pipeline.clean")

_METADATA_KEYS_TO_REMOVE = {
    "namespace", "resourceVersion", "uid", "creationTimestamp",
    "generation", "managedFields", "selfLink", "finalizers",
    "ownerReferences",
}

_ANNOTATION_PATTERNS_TO_REMOVE = [
    re.compile(r"^kubectl\.kubernetes\.io/"),
    re.compile(r"^argocd\.argoproj\.io/"),
    re.compile(r"^deployment\.kubernetes\.io/"),
    re.compile(r"^kubernetes\.io/"),
    re.compile(r"^openshift\.io/"),
]


def clean_single_resource(resource: dict) -> dict:
    """Apply deterministic cleanup rules to a single resource dict."""
    res = json.loads(json.dumps(resource))

    meta = res.get("metadata", {})
    for key in list(meta.keys()):
        if key in _METADATA_KEYS_TO_REMOVE:
            del meta[key]

    annotations = meta.get("annotations", {})
    if annotations:
        for key in list(annotations.keys()):
            if any(p.match(key) for p in _ANNOTATION_PATTERNS_TO_REMOVE):
                del annotations[key]
        if not annotations:
            del meta["annotations"]

    res.pop("status", None)

    tmpl_meta = (
        res.get("spec", {})
        .get("template", {})
        .get("metadata", {})
    )
    tmpl_meta.pop("creationTimestamp", None)

    kind = res.get("kind", "")

    if kind == "Service":
        spec = res.get("spec", {})
        spec.pop("clusterIP", None)
        spec.pop("clusterIPs", None)

    if kind == "Route":
        spec = res.get("spec", {})
        spec.pop("host", None)

    return res


def clean_resources_node(state: PipelineState) -> dict:
    """Clean all raw resources by removing cluster-specific metadata."""
    raw = state.get("raw_resources", [])
    from pipeline.graph import live_progress

    log = state.get("progress_log", [])[:]
    msg = f"Cleaning {len(raw)} resources (removing cluster-specific metadata)..."
    log.append(msg)
    live_progress(msg)

    cleaned = [clean_single_resource(r) for r in raw]
    log.append(f"  Cleaned {len(cleaned)} resources")

    return {"cleaned_resources": cleaned, "progress_log": log}
