"""LangGraph StateGraph definition for the CD pipeline.

Provides two compiled graphs:
  - ``build_wizard_app()`` — pauses after each phase for user review
  - ``build_auto_app()``   — runs end-to-end without interrupts

Nodes that need LLM access (best_practices, helm, validate) pull their
callables from a thread-local shared context set before each graph run.
"""

from __future__ import annotations

import threading
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from pipeline.state import PipelineState
from pipeline.nodes.fetch import fetch_resources_node
from pipeline.nodes.clean import clean_resources_node
from pipeline.nodes.best_practices import apply_best_practices_node
from pipeline.nodes.validate import validate_deployment_node, validate_argocd_node
from pipeline.nodes.helm import generate_helm_node
from pipeline.nodes.push import push_github_node
from pipeline.nodes.argocd import generate_argocd_node, deploy_argocd_node

# ------------------------------------------------------------------ #
#  Shared context — holds callables that can't be serialised in state  #
# ------------------------------------------------------------------ #

_shared_ctx: dict[str, Any] = {}
_ctx_lock = threading.Lock()


def set_shared_context(ctx: dict[str, Any]) -> None:
    """Store LLM callables and configs accessible from any thread."""
    global _shared_ctx
    with _ctx_lock:
        _shared_ctx = ctx


def get_shared_context() -> dict[str, Any]:
    with _ctx_lock:
        return _shared_ctx


def live_progress(msg: str) -> None:
    """Append a progress message that the UI can read in real-time.

    The ``live_progress`` list in the shared context is a plain Python list
    shared between the graph thread and the Gradio generator thread.
    ``list.append`` is atomic under the GIL, so no lock is needed.
    """
    ctx = get_shared_context()
    buf = ctx.get("live_progress")
    if buf is not None:
        buf.append(msg)


# ------------------------------------------------------------------ #
#  Graph construction                                                  #
# ------------------------------------------------------------------ #

def _build_graph() -> StateGraph:
    g = StateGraph(PipelineState)

    g.add_node("fetch_resources", fetch_resources_node)
    g.add_node("clean_resources", clean_resources_node)
    g.add_node("apply_best_practices", apply_best_practices_node)
    g.add_node("validate_deployment", validate_deployment_node)
    g.add_node("generate_helm", generate_helm_node)
    g.add_node("push_github", push_github_node)
    g.add_node("generate_argocd", generate_argocd_node)
    g.add_node("deploy_argocd", deploy_argocd_node)
    g.add_node("validate_argocd", validate_argocd_node)

    g.set_entry_point("fetch_resources")
    g.add_edge("fetch_resources", "clean_resources")
    g.add_edge("clean_resources", "apply_best_practices")
    g.add_edge("apply_best_practices", "validate_deployment")
    g.add_edge("validate_deployment", "generate_helm")
    g.add_edge("generate_helm", "push_github")
    g.add_edge("push_github", "generate_argocd")
    g.add_edge("generate_argocd", "deploy_argocd")
    g.add_edge("deploy_argocd", "validate_argocd")
    g.add_edge("validate_argocd", END)

    return g


def build_wizard_app():
    """Compile the graph with interrupt_after points for the wizard UI."""
    return _build_graph().compile(
        checkpointer=MemorySaver(),
        interrupt_after=["apply_best_practices", "validate_deployment", "push_github"],
    )


def build_auto_app():
    """Compile the graph without interrupts for autonomous mode."""
    return _build_graph().compile(checkpointer=MemorySaver())
