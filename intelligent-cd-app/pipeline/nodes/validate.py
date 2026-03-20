"""Node: validate_deployment — deploy YAML to a temp namespace, poll health via LLM+MCP, clean up."""

from __future__ import annotations

import os
import subprocess
import time

from pipeline.state import PipelineState
from utils import get_logger

logger = get_logger("pipeline.validate")

MAX_POLL_ITERATIONS = 10
POLL_SLEEP_SECONDS = 10
INITIAL_WAIT_SECONDS = 10


def _run_kubectl(args: list[str], stdin_data: str | None = None) -> tuple[int, str, str]:
    kube_cli = os.getenv("KUBE_CLI", "oc")
    cmd = [kube_cli] + args
    logger.info(f"Running: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = proc.communicate(input=stdin_data)
    return proc.returncode, stdout.strip(), stderr.strip()


def _log(log: list[str], msg: str) -> None:
    """Append to the node log AND push to the live UI buffer."""
    from pipeline.graph import live_progress
    log.append(msg)
    live_progress(msg)


def validate_deployment_node(state: PipelineState) -> dict:
    """Deploy enhanced YAML to a temporary namespace, poll health via LLM+MCP, then clean up.

    Flow:
      1. Python: create namespace, kubectl apply
      2. Wait 10s for pods to start
      3. Loop (max 10): call LLM with MCP OpenShift tools to check pod health
      4. Python (finally): delete namespace
    """
    from pipeline.graph import get_shared_context

    namespace = state["namespace"]
    enhanced_yaml = state.get("enhanced_yaml", "")
    val_ns = f"{namespace}-validation"
    log = state.get("progress_log", [])[:]

    ctx = get_shared_context()
    call_responses = ctx["call_responses_api"]
    validate_config = ctx.get("config_validate_deployment")

    if not validate_config:
        _log(log, "WARN: Validation config not available, skipping LLM health check.")
        _log(log, "Performing basic kubectl validation only...")
        return _basic_validation(val_ns, enhanced_yaml, log)

    validation_result = ""
    validation_attempts = 0
    passed = False

    try:
        _log(log, f"Deleting namespace '{val_ns}' if it exists...")
        _run_kubectl(["delete", "namespace", val_ns, "--ignore-not-found"])
        _run_kubectl(["wait", "--for=delete", f"namespace/{val_ns}", "--timeout=60s"])

        _log(log, f"Creating namespace '{val_ns}'...")
        rc, out, err = _run_kubectl(["create", "namespace", val_ns])
        if rc != 0:
            _log(log, f"  ERROR creating namespace: {err}")
            return {
                "validation_namespace": val_ns,
                "validation_passed": False,
                "validation_result": f"Failed to create namespace: {err}",
                "validation_attempts": 0,
                "progress_log": log,
                "current_phase": 2,
            }

        _log(log, f"Deploying YAML resources to '{val_ns}'...")
        rc, out, err = _run_kubectl(["apply", "-n", val_ns, "-f", "-"], stdin_data=enhanced_yaml)
        if rc != 0:
            _log(log, f"  ERROR applying YAML: {err}")
            return {
                "validation_namespace": val_ns,
                "validation_passed": False,
                "validation_result": f"kubectl apply failed: {err}",
                "validation_attempts": 0,
                "progress_log": log,
                "current_phase": 2,
            }
        _log(log, f"  Applied: {out}")

        _log(log, f"Waiting {INITIAL_WAIT_SECONDS}s for pods to start...")
        time.sleep(INITIAL_WAIT_SECONDS)

        prompt = (
            f"Check all pods in namespace '{val_ns}'. "
            "Use the MCP tools to get pod status, events, and logs if any pod is failing. "
            "If ALL pods are Running and Ready with 0 restarts, respond with the exact word "
            "VALIDATION_PASSED on its own line. If not, describe the current status of each "
            "pod and any errors you find."
        )

        for attempt in range(1, MAX_POLL_ITERATIONS + 1):
            validation_attempts = attempt
            _log(log, f"LLM health check (attempt {attempt}/{MAX_POLL_ITERATIONS})...")

            try:
                llm_response = call_responses(prompt, validate_config)
                validation_result = llm_response.strip()
                _log(log, f"  LLM ({attempt}/{MAX_POLL_ITERATIONS}): {validation_result[:200]}")

                if "VALIDATION_PASSED" in validation_result:
                    passed = True
                    _log(log, "Validation PASSED!")
                    break
            except Exception as exc:
                logger.error(f"LLM poll failed on attempt {attempt}: {exc}")
                _log(log, f"  LLM call failed: {exc}")
                validation_result = str(exc)

            if attempt < MAX_POLL_ITERATIONS:
                _log(log, f"  Waiting {POLL_SLEEP_SECONDS}s before next check...")
                time.sleep(POLL_SLEEP_SECONDS)

        if not passed:
            _log(log, f"Validation FAILED after {validation_attempts} attempts.")

    finally:
        _log(log, f"Validation namespace '{val_ns}' left intact for inspection.")

    return {
        "validation_namespace": val_ns,
        "validation_passed": passed,
        "validation_result": validation_result,
        "validation_attempts": validation_attempts,
        "progress_log": log,
        "current_phase": 2,
    }


def _basic_validation(val_ns: str, enhanced_yaml: str, log: list[str]) -> dict:
    """Fallback: just deploy, check pod status with kubectl, and clean up."""
    passed = False
    result = ""
    try:
        _run_kubectl(["delete", "namespace", val_ns, "--ignore-not-found"])
        _run_kubectl(["wait", "--for=delete", f"namespace/{val_ns}", "--timeout=60s"])

        rc, _, err = _run_kubectl(["create", "namespace", val_ns])
        if rc != 0:
            _log(log, f"  ERROR creating namespace: {err}")
            return {
                "validation_namespace": val_ns, "validation_passed": False,
                "validation_result": err, "validation_attempts": 0,
                "progress_log": log, "current_phase": 2,
            }

        _log(log, f"Deploying YAML resources to '{val_ns}'...")
        rc, out, err = _run_kubectl(["apply", "-n", val_ns, "-f", "-"], stdin_data=enhanced_yaml)
        if rc != 0:
            result = f"kubectl apply failed: {err}"
            _log(log, f"  ERROR: {result}")
            return {
                "validation_namespace": val_ns, "validation_passed": False,
                "validation_result": result, "validation_attempts": 0,
                "progress_log": log, "current_phase": 2,
            }
        _log(log, f"  Applied: {out}")

        _log(log, f"Waiting {INITIAL_WAIT_SECONDS}s for pods to start...")
        time.sleep(INITIAL_WAIT_SECONDS)

        for attempt in range(1, 6):
            _log(log, f"Checking pod status (attempt {attempt}/5)...")
            rc, out, _ = _run_kubectl(["get", "pods", "-n", val_ns, "-o", "wide"])
            _log(log, f"  {out}")
            result = out

            if "Running" in out and "0/" not in out:
                passed = True
                _log(log, "Basic validation PASSED (pods Running).")
                break
            time.sleep(POLL_SLEEP_SECONDS)

        if not passed:
            _log(log, "Basic validation FAILED.")
    finally:
        _log(log, f"Validation namespace '{val_ns}' left intact for inspection.")

    return {
        "validation_namespace": val_ns, "validation_passed": passed,
        "validation_result": result, "validation_attempts": 5,
        "progress_log": log, "current_phase": 2,
    }


# ------------------------------------------------------------------ #
#  validate_argocd — check pods in the gitops namespace after deploy   #
# ------------------------------------------------------------------ #

ARGOCD_POLL_ITERATIONS = 12
ARGOCD_POLL_SLEEP = 10
ARGOCD_INITIAL_WAIT = 15


def validate_argocd_node(state: PipelineState) -> dict:
    """Wait for ArgoCD to sync and verify the Application + pods are healthy."""
    from pipeline.graph import get_shared_context

    namespace = state["namespace"]
    chart_name = state.get("chart_name", namespace)
    target_ns = f"{namespace}-gitops"
    log = state.get("progress_log", [])[:]

    ctx = get_shared_context()
    call_responses = ctx["call_responses_api"]
    argocd_config = ctx.get("config_validate_argocd")

    _log(log, f"Validating ArgoCD deployment for app '{chart_name}' in '{target_ns}'...")
    _log(log, f"Initial wait {ARGOCD_INITIAL_WAIT}s for ArgoCD to start syncing...")
    time.sleep(ARGOCD_INITIAL_WAIT)

    if argocd_config and argocd_config.get("tools"):
        return _argocd_llm_validation(
            target_ns, chart_name, log, call_responses, argocd_config,
        )
    return _argocd_basic_validation(target_ns, log)


def _argocd_llm_validation(
    target_ns: str, chart_name: str, log: list[str], call_responses, validate_config
) -> dict:
    prompt = (
        f"Validate the ArgoCD Application '{chart_name}' and its workloads in namespace '{target_ns}'.\n\n"
        f"Step 1 — Use the ArgoCD MCP tools to check the Application sync status and health. "
        f"Report the sync status (Synced/OutOfSync) and health status (Healthy/Degraded/Progressing).\n\n"
        f"Step 2 — Use the OpenShift MCP tools to check all pods in namespace '{target_ns}'. "
        f"Get pod status, events, and logs if any pod is failing.\n\n"
        f"If the ArgoCD Application is Synced + Healthy AND all pods are Running and Ready, "
        f"respond with the exact word VALIDATION_PASSED on its own line. "
        f"Otherwise describe the current state and any errors you find."
    )

    passed = False
    result = ""
    attempts = 0

    for attempt in range(1, ARGOCD_POLL_ITERATIONS + 1):
        attempts = attempt
        _log(log, f"LLM health check on '{target_ns}' (attempt {attempt}/{ARGOCD_POLL_ITERATIONS})...")

        try:
            llm_response = call_responses(prompt, validate_config)
            result = llm_response.strip()
            _log(log, f"  LLM: {result[:200]}")

            if "VALIDATION_PASSED" in result:
                passed = True
                _log(log, f"ArgoCD deployment in '{target_ns}' is healthy!")
                break
        except Exception as exc:
            logger.error(f"LLM poll failed on attempt {attempt}: {exc}")
            _log(log, f"  LLM call failed: {exc}")
            result = str(exc)

        if attempt < ARGOCD_POLL_ITERATIONS:
            _log(log, f"  Waiting {ARGOCD_POLL_SLEEP}s...")
            time.sleep(ARGOCD_POLL_SLEEP)

    if not passed:
        _log(log, f"ArgoCD validation FAILED after {attempts} attempts.")

    return {
        "argocd_validation_result": result,
        "argocd_validation_passed": passed,
        "progress_log": log,
        "current_phase": 4,
    }


def _argocd_basic_validation(target_ns: str, log: list[str]) -> dict:
    passed = False
    result = ""

    for attempt in range(1, ARGOCD_POLL_ITERATIONS + 1):
        _log(log, f"Checking pods in '{target_ns}' (attempt {attempt}/{ARGOCD_POLL_ITERATIONS})...")
        rc, out, _ = _run_kubectl(["get", "pods", "-n", target_ns, "-o", "wide"])
        _log(log, f"  {out}")
        result = out

        if "Running" in out and "0/" not in out:
            passed = True
            _log(log, f"ArgoCD deployment in '{target_ns}' is healthy!")
            break

        if attempt < ARGOCD_POLL_ITERATIONS:
            _log(log, f"  Waiting {ARGOCD_POLL_SLEEP}s...")
            time.sleep(ARGOCD_POLL_SLEEP)

    if not passed:
        _log(log, f"ArgoCD validation FAILED after {ARGOCD_POLL_ITERATIONS} attempts.")

    return {
        "argocd_validation_result": result,
        "argocd_validation_passed": passed,
        "progress_log": log,
        "current_phase": 4,
    }
