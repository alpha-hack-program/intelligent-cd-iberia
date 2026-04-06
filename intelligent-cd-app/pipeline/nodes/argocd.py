"""Nodes: generate_argocd — Python template, deploy_argocd — kubectl apply."""

from __future__ import annotations

import os
import subprocess

from pipeline.state import PipelineState
from utils import get_logger

logger = get_logger("pipeline.argocd")


def _log(log: list[str], msg: str) -> None:
    from pipeline.graph import live_progress
    log.append(msg)
    live_progress(msg)

_ARGOCD_APP_TEMPLATE = """\
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: {app_name}
  namespace: openshift-gitops
spec:
  project: default
  source:
    repoURL: {repo_url}
    targetRevision: main
    path: {chart_path}
  destination:
    server: https://kubernetes.default.svc
    namespace: {dest_namespace}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
"""


def generate_argocd_node(state: PipelineState) -> dict:
    """Generate ArgoCD Application YAML and push it to the GitOps repo."""
    from github import Github, GithubException

    chart_name = state.get("chart_name", state.get("namespace", "chart"))
    namespace = state["namespace"]
    dest_namespace = f"{namespace}-gitops"
    github_repo = os.getenv("GITHUB_GITOPS_REPO", "")
    log = state.get("progress_log", [])[:]

    _log(log, "═══ Step 4: Deploy with ArgoCD ═══")
    _log(log, "Generating ArgoCD Application manifest...")

    argocd_yaml = _ARGOCD_APP_TEMPLATE.format(
        app_name=chart_name,
        repo_url=github_repo,
        chart_path=f"{chart_name}/charts",
        dest_namespace=dest_namespace,
    )

    _log(log, f"  App name: {chart_name}")
    _log(log, f"  Source path: {chart_name}/charts")
    _log(log, f"  Destination namespace: {dest_namespace}")

    github_pat = os.getenv("GITHUB_PAT", "")
    if not github_pat or not github_repo:
        _log(log, "GitHub credentials not set — skipping push.")
        return {"argocd_yaml": argocd_yaml, "progress_log": log}

    repo_url = github_repo.rstrip("/")
    repo_slug = "/".join(repo_url.split("/")[-2:])
    if repo_slug.endswith(".git"):
        repo_slug = repo_slug[:-4]

    repo_path = f"{chart_name}/gitops/argocd-application.yaml"
    _log(log, f"Pushing to '{repo_slug}' at {repo_path}...")

    try:
        gh = Github(github_pat)
        repo = gh.get_repo(repo_slug)
        commit_msg = f"Deploy ArgoCD Application for '{chart_name}'"
        try:
            existing = repo.get_contents(repo_path, ref="main")
            repo.update_file(repo_path, commit_msg, argocd_yaml, existing.sha, branch="main")
        except GithubException as exc:
            if exc.status == 404:
                repo.create_file(repo_path, commit_msg, argocd_yaml, branch="main")
            else:
                raise
        gh.close()
        _log(log, "  ArgoCD manifest pushed to GitHub.")
    except Exception as exc:
        logger.error(f"Push ArgoCD app to GitHub failed: {exc}")
        _log(log, f"ERROR pushing to GitHub: {exc}")

    return {"argocd_yaml": argocd_yaml, "progress_log": log}


def deploy_argocd_node(state: PipelineState) -> dict:
    """Apply the ArgoCD Application manifest to the cluster."""
    argocd_yaml = state.get("argocd_yaml", "")
    namespace = state["namespace"]
    dest_namespace = f"{namespace}-gitops"
    log = state.get("progress_log", [])[:]

    if not argocd_yaml:
        _log(log, "ERROR: No ArgoCD YAML to apply.")
        return {"argocd_deployed": False, "progress_log": log}

    kube_cli = os.getenv("KUBE_CLI", "oc")

    _log(log, f"Deleting namespace '{dest_namespace}' if it exists...")
    subprocess.run(
        [kube_cli, "delete", "namespace", dest_namespace, "--ignore-not-found"],
        capture_output=True, text=True,
    )
    subprocess.run(
        [kube_cli, "wait", "--for=delete", f"namespace/{dest_namespace}", "--timeout=60s"],
        capture_output=True, text=True,
    )

    _log(log, "Applying ArgoCD Application to cluster...")

    try:
        process = subprocess.Popen(
            [kube_cli, "apply", "-f", "-"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate(input=argocd_yaml)

        if process.returncode == 0:
            _log(log, f"  Applied successfully: {stdout.strip()}")
            return {"argocd_deployed": True, "progress_log": log, "current_phase": 4}
        else:
            _log(log, f"  Apply failed: {stderr.strip()}")
            return {"argocd_deployed": False, "error": stderr.strip(), "progress_log": log}
    except Exception as exc:
        _log(log, f"  Exception: {exc}")
        return {"argocd_deployed": False, "error": str(exc), "progress_log": log}
