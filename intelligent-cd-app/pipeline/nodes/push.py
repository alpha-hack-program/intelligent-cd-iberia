"""Node: push_github — push Helm chart files to GitHub via PyGithub."""

from __future__ import annotations

import os
import re

from pipeline.state import PipelineState
from utils import get_logger

logger = get_logger("pipeline.push")

_SOURCE_HEADER_RE = re.compile(r"^#\s*Source:\s*[^/\s]+/(.+)$")
_CODE_FENCE_RE = re.compile(r"^```\w*\s*$")


def _parse_helm_chart_files(content: str) -> dict[str, str]:
    """Parse LLM Helm chart output into individual files by ``# Source:`` headers."""
    files: dict[str, str] = {}
    current_path: str | None = None
    lines_buf: list[str] = []

    for line in content.splitlines():
        header_match = _SOURCE_HEADER_RE.match(line.strip())
        if header_match:
            if current_path is not None:
                files[current_path] = "\n".join(lines_buf).strip()
            current_path = header_match.group(1)
            lines_buf = []
            continue
        if _CODE_FENCE_RE.match(line.strip()):
            continue
        if current_path is not None:
            lines_buf.append(line)

    if current_path is not None:
        files[current_path] = "\n".join(lines_buf).strip()
    return files


def push_github_node(state: PipelineState) -> dict:
    """Parse the Helm chart into files and push them to the GitOps repo."""
    from github import Github, GithubException

    chart_name = state.get("chart_name", state.get("namespace", "chart"))
    helm_chart = state.get("helm_chart", "")
    log = state.get("progress_log", [])[:]

    github_pat = os.getenv("GITHUB_PAT", "")
    github_repo = os.getenv("GITHUB_GITOPS_REPO", "")

    if not github_pat:
        log.append("ERROR: GITHUB_PAT environment variable is not set.")
        return {"push_errors": ["GITHUB_PAT not set"], "progress_log": log}
    if not github_repo:
        log.append("ERROR: GITHUB_GITOPS_REPO environment variable is not set.")
        return {"push_errors": ["GITHUB_GITOPS_REPO not set"], "progress_log": log}

    from pipeline.graph import live_progress

    log.append("Parsing Helm chart files...")
    live_progress("Parsing Helm chart files...")
    files = _parse_helm_chart_files(helm_chart)

    if not files:
        log.append("ERROR: Could not parse any files from the Helm chart output.")
        return {"push_errors": ["No files parsed"], "progress_log": log}

    file_list = "\n".join(f"  - {p}" for p in files)
    log.append(f"  Found {len(files)} files:\n{file_list}")

    repo_url = github_repo.rstrip("/")
    repo_slug = "/".join(repo_url.split("/")[-2:])
    if repo_slug.endswith(".git"):
        repo_slug = repo_slug[:-4]

    log.append(f"Connecting to repo '{repo_slug}'...")

    try:
        gh = Github(github_pat)
        repo = gh.get_repo(repo_slug)
    except GithubException as exc:
        logger.error(f"GitHub connection failed: {exc}")
        log.append(f"ERROR connecting to GitHub: {exc}")
        return {"push_errors": [str(exc)], "progress_log": log}

    branch = "main"
    commit_message = f"Deploy Helm chart '{chart_name}'"
    pushed: list[str] = []
    errors: list[str] = []

    for path, file_content in files.items():
        repo_path = f"{chart_name}/charts/{path}"
        msg = f"  Pushing {repo_path}..."
        log.append(msg)
        live_progress(msg)
        try:
            existing = repo.get_contents(repo_path, ref=branch)
            repo.update_file(repo_path, commit_message, file_content, existing.sha, branch=branch)
        except GithubException as exc:
            if exc.status == 404:
                repo.create_file(repo_path, commit_message, file_content, branch=branch)
            else:
                logger.error(f"Failed to push {repo_path}: {exc}")
                errors.append(f"{repo_path}: {exc}")
                continue
        pushed.append(repo_path)

    gh.close()

    if errors:
        log.append(f"Completed with {len(errors)} error(s)")
    else:
        log.append(f"Done. Pushed {len(pushed)} files to '{repo_slug}' branch '{branch}'.")

    return {"pushed_files": pushed, "push_errors": errors, "progress_log": log}
