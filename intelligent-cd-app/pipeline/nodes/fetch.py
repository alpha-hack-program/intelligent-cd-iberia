"""Node: fetch_resources — fetch raw K8s resources from the cluster via oc/kubectl."""

from __future__ import annotations

import json
import os
import subprocess
from typing import List

from pipeline.state import PipelineState
from utils import get_logger

logger = get_logger("pipeline.fetch")

RESOURCE_TYPE_MAP = {
    "Deployment": ("apps/v1", "Deployment", "deployments"),
    "StatefulSet": ("apps/v1", "StatefulSet", "statefulsets"),
    "Service": ("v1", "Service", "services"),
    "Route": ("route.openshift.io/v1", "Route", "routes"),
    "ConfigMap": ("v1", "ConfigMap", "configmaps"),
}


def _discover_referenced_configmaps(
    resources: List[dict], namespace: str
) -> List[dict]:
    existing_cm_names = {
        r["metadata"]["name"]
        for r in resources
        if r.get("kind") == "ConfigMap"
    }
    referenced_names: set = set()

    for res in resources:
        kind = res.get("kind", "")
        if kind not in ("Deployment", "StatefulSet"):
            continue
        containers = (
            res.get("spec", {})
            .get("template", {})
            .get("spec", {})
            .get("containers", [])
        )
        for container in containers:
            for env_from in container.get("envFrom", []):
                cm_ref = env_from.get("configMapRef", {})
                if cm_ref.get("name"):
                    referenced_names.add(cm_ref["name"])
            for env_var in container.get("env", []):
                vf = env_var.get("valueFrom", {})
                cm_key = vf.get("configMapKeyRef", {})
                if cm_key.get("name"):
                    referenced_names.add(cm_key["name"])
        volumes = (
            res.get("spec", {})
            .get("template", {})
            .get("spec", {})
            .get("volumes", [])
        )
        for vol in volumes:
            cm_vol = vol.get("configMap", {})
            if cm_vol.get("name"):
                referenced_names.add(cm_vol["name"])

    missing = referenced_names - existing_cm_names
    if not missing:
        return []

    logger.info(f"Auto-discovered {len(missing)} referenced ConfigMaps: {missing}")
    kube_cli = os.getenv("KUBE_CLI", "oc")
    discovered: List[dict] = []
    for name in missing:
        cmd = [kube_cli, "get", "configmap", name, "-n", namespace, "-o", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            try:
                discovered.append(json.loads(result.stdout))
            except json.JSONDecodeError:
                pass
        else:
            logger.warning(f"Could not fetch ConfigMap '{name}': {result.stderr.strip()}")
    return discovered


def fetch_resources_node(state: PipelineState) -> dict:
    """Fetch raw Kubernetes resources from the cluster."""
    namespace = state["namespace"]
    workload_type = state["workload_type"]
    supporting_resources = state.get("supporting_resources", [])

    from pipeline.graph import live_progress

    log: list[str] = state.get("progress_log", [])[:]
    msg = f"Fetching resources from namespace '{namespace}'..."
    log.append(msg)
    live_progress(msg)

    kube_cli = os.getenv("KUBE_CLI", "oc")
    types_to_fetch = [workload_type] + list(supporting_resources)
    resources: List[dict] = []

    for rtype in types_to_fetch:
        if rtype not in RESOURCE_TYPE_MAP:
            logger.warning(f"Unknown resource type '{rtype}', skipping")
            continue
        if rtype == "ConfigMap":
            continue

        _, _, plural = RESOURCE_TYPE_MAP[rtype]
        cmd = [kube_cli, "get", plural, "-n", namespace, "-o", "json"]
        logger.info(f"Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(f"oc get {plural} failed (rc={result.returncode}): {result.stderr.strip()}")
            continue

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse JSON from oc get {plural}: {exc}")
            continue

        items = data.get("items", [])
        logger.info(f"  Found {len(items)} {plural} in namespace '{namespace}'")
        resources.extend(items)

    if "ConfigMap" in types_to_fetch:
        discovered = _discover_referenced_configmaps(resources, namespace)
        resources.extend(discovered)
        log.append(f"  Found {len(discovered)} application ConfigMap(s) referenced by workloads")

    kind_counts: dict[str, int] = {}
    for r in resources:
        k = r.get("kind", "Unknown")
        kind_counts[k] = kind_counts.get(k, 0) + 1
    summary = ", ".join(f"{v} {k}(s)" for k, v in kind_counts.items())
    log.append(f"  Found: {summary}")

    if not resources:
        return {"raw_resources": [], "progress_log": log, "error": "No resources found"}

    return {"raw_resources": resources, "progress_log": log}
