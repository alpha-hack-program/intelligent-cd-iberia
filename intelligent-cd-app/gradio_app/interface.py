"""
Gradio interface for Intelligent CD Chatbot.

Wizard-style UI powered by LangGraph for the Intelligent CD pipeline,
plus existing Chat, MCP Test, RAG Test, and System Status tabs.
"""

import uuid

import gradio as gr
from typing import TYPE_CHECKING

from pipeline.graph import build_wizard_app, build_auto_app, set_shared_context, get_shared_context

if TYPE_CHECKING:
    from tabs.chat_tab import ChatTab
    from tabs.mcp_test_tab import MCPTestTab
    from tabs.rag_test_tab import RAGTestTab
    from tabs.system_status_tab import SystemStatusTab
    from tabs.form_tab import FormTab


THEME = gr.themes.Soft()

# ------------------------------------------------------------------ #
#  Phase definitions                                                   #
# ------------------------------------------------------------------ #

PHASE_NAMES = [
    "Resources & Best Practices",
    "Validate Deployment",
    "Helm Chart & Push",
    "ArgoCD Deploy & Validate",
]

NEXT_LABELS = {
    0: "Start Pipeline",
    1: "Next: Validate Deployment",
    2: "Next: Generate Helm Chart",
    3: "Next: Deploy & Validate ArgoCD",
    4: "Start New Pipeline",
}

# ------------------------------------------------------------------ #
#  Stepper HTML builder                                                #
# ------------------------------------------------------------------ #

def _stepper_html(active: int) -> str:
    steps = []
    for i, name in enumerate(PHASE_NAMES):
        if i < active:
            cls = "wiz-step done"
        elif i == active:
            cls = "wiz-step active"
        else:
            cls = "wiz-step"
        steps.append(
            f'<div class="{cls}">'
            f'<span class="wiz-num">{i + 1}</span> {name}'
            f'</div>'
        )
    return f'<div class="wiz-stepper">{"".join(steps)}</div>'


# ------------------------------------------------------------------ #
#  CSS                                                                 #
# ------------------------------------------------------------------ #

CSS = """
/* Full screen responsive layout */
.gradio-container {
    max-width: 100vw !important; width: 100vw !important;
    padding: 0 !important; margin: 0 !important;
}
.main-panel { width: 100% !important; max-width: 100% !important; }

/* Header */
.header-container {
    background: linear-gradient(135deg, #ff8c42 0%, #ffa726 50%, #ff7043 100%);
    color: white; padding: 20px; border-radius: 0 0 15px 15px;
    margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 100% !important;
}
.header-content { display:flex; align-items:center; justify-content:space-between; }
.header-left { display:flex; align-items:center; gap:15px; }
.logo { width:50px; height:50px; border-radius:10px; }
.header-title { font-size:2.2em; font-weight:bold; margin:0; text-shadow:1px 1px 2px rgba(0,0,0,0.3); }
.header-subtitle { font-size:1.1em; opacity:0.95; margin:5px 0 0 0; text-shadow:1px 1px 2px rgba(0,0,0,0.3); }
.header-right { display:flex; align-items:center; gap:15px; }

/* Wizard stepper */
.wiz-stepper { display:flex; gap:6px; margin-bottom:12px; }
.wiz-step {
    flex:1; text-align:center; padding:10px 6px; border-radius:6px;
    font-size:0.85em; background:#e8e8e8; color:#666; transition:all 0.3s;
}
.wiz-step .wiz-num {
    display:inline-block; width:22px; height:22px; line-height:22px;
    border-radius:50%; background:#bbb; color:#fff; font-weight:bold;
    font-size:0.8em; margin-right:4px; text-align:center;
}
.wiz-step.active { background:#667eea; color:#fff; font-weight:bold; }
.wiz-step.active .wiz-num { background:#fff; color:#667eea; }
.wiz-step.done { background:#4caf50; color:#fff; }
.wiz-step.done .wiz-num { background:#fff; color:#4caf50; }

/* Button styles */
.ai-generation-btn {
    background:#667eea !important; color:white !important; border:none !important;
    box-shadow:0 4px 15px rgba(102,126,234,0.3) !important;
}
.ai-generation-btn:hover { background:#5a6fd8 !important; transform:translateY(-2px) !important; }
.openshift-action-btn {
    background:#28a745 !important; color:white !important; border:none !important;
}

/* Config display */
.config-display {
    font-size:0.75em !important; color:#666 !important; padding:5px 10px !important;
    background-color:#f5f5f5 !important; border-radius:4px !important; border:1px solid #ddd !important;
}
.config-display p { margin:0 !important; line-height:1.4 !important; }

/* Responsive */
@media (max-width: 768px) {
    .header-title { font-size:1.8em !important; }
    .wiz-stepper { flex-direction:column; }
}
"""

# ------------------------------------------------------------------ #
#  Header HTML (shared across tabs)                                    #
# ------------------------------------------------------------------ #

HEADER_HTML = """
<div class="header-container">
    <div class="header-content">
        <div class="header-left">
            <svg class="logo" version="1.0" xmlns="http://www.w3.org/2000/svg"
                 width="50" height="50" viewBox="0 0 300 300" preserveAspectRatio="xMidYMid meet">
                <g transform="translate(0,300) scale(0.1,-0.1)" fill="currentColor" stroke="none">
                    <path d="M1470 2449 c-47 -10 -80 -53 -80 -105 0 -45 26 -88 61 -99 18 -6 19 -14 17 -138 l-3 -132 -37 -3 -38 -3 0 48 c0 43 -4 53 -34 82 -32 31 -35 38 -33 87 2 46 -2 57 -27 83 -36 38 -74 46 -120 27 -70 -29 -86 -125 -30 -177 20 -19 36 -24 79 -24 70 0 95 -22 95 -82 l0 -43 -162 0 c-108 -1 -175 -5 -200 -14 -98 -35 -168 -134 -178 -250 l-5 -69 -44 -11 c-69 -17 -85 -47 -90 -164 -5 -147 17 -194 102 -211 l32 -7 5 -80 c4 -64 11 -90 36 -134 50 -88 141 -140 247 -140 l47 0 0 -135 c0 -122 2 -137 20 -155 11 -11 29 -20 40 -20 21 0 31 8 233 193 l129 117 226 0 c125 0 244 5 264 10 62 18 128 71 162 130 25 44 32 70 36 134 l5 79 44 11 c74 18 86 45 86 186 0 141 -12 168 -86 186 l-44 11 -6 74 c-10 113 -58 187 -153 234 -47 24 -59 25 -218 25 l-168 0 0 40 c0 53 38 91 85 83 60 -10 125 46 125 107 0 38 -30 81 -67 96 -45 19 -83 11 -119 -27 -25 -26 -29 -37 -27 -83 2 -49 -1 -56 -33 -87 -30 -29 -34 -39 -34 -82 l0 -48 -37 3 -38 3 -3 132 c-2 124 -1 132 17 138 35 11 61 54 61 99 0 75 -62 122 -140 105z"/>
                    <path d="M1159 1621 c-80 -80 12 -215 114 -166 52 24 74 79 53 129 -30 71 -114 90 -167 37z"/>
                    <path d="M1702 1625 c-60 -50 -47 -142 24 -171 45 -19 78 -12 115 26 90 89 -42 226 -139 145z"/>
                    <path d="M1280 1269 c-10 -17 -6 -25 25 -54 91 -86 299 -86 390 0 31 29 35 37 25 54 -15 28 -31 26 -95 -10 -47 -26 -65 -31 -125 -31 -59 0 -78 5 -127 31 -67 37 -79 38 -93 10z"/>
                </g>
            </svg>
            <div>
                <div class="header-title">Intelligent CD Chatbot</div>
                <div class="header-subtitle">AI-Powered GitOps Deployment Assistant</div>
            </div>
        </div>
        <div class="header-right">
            <div style="text-align:right;">
                <div style="font-size:0.8em;opacity:0.7;margin-bottom:2px;">Powered by</div>
                <div style="font-size:1.2em;font-weight:bold;opacity:0.9;">Red Hat AI</div>
            </div>
        </div>
    </div>
</div>
"""


# ------------------------------------------------------------------ #
#  Helper: determine which phase we're in after graph stream ends      #
# ------------------------------------------------------------------ #

def _detect_phase(graph_app, config) -> int:
    """Inspect the graph checkpoint to determine the current pipeline phase."""
    snap = graph_app.get_state(config)
    nxt = snap.next if snap else ()
    if not nxt:
        return 4
    if "validate_deployment" in nxt:
        return 1
    if "generate_helm" in nxt:
        return 2
    if "generate_argocd" in nxt:
        return 3
    return 4


def _phase_outputs(final_state: dict, new_phase: int):
    """Extract content_area and changes_panel text from pipeline state."""
    if new_phase == 1:
        content = final_state.get("enhanced_yaml", "")
        changes_list = final_state.get("changes_applied", [])
        changes = "\n".join(changes_list) if changes_list else "No changes detected."
    elif new_phase == 2:
        content = final_state.get("validation_result", "")
        if final_state.get("validation_passed"):
            changes = "Validation PASSED — all pods healthy."
        else:
            changes = "Validation FAILED — see output for details."
    elif new_phase == 3:
        content = final_state.get("helm_chart", "")
        pushed = final_state.get("pushed_files", [])
        errs = final_state.get("push_errors", [])
        changes = "Pushed files:\n" + "\n".join(f"  - {f}" for f in pushed)
        if errs:
            changes += "\n\nErrors:\n" + "\n".join(f"  - {e}" for e in errs)
    elif new_phase == 4:
        content = final_state.get("argocd_yaml", "")
        ok = final_state.get("argocd_deployed", False)
        parts = []
        parts.append("ArgoCD Application deployed." if ok else "ArgoCD deployment FAILED.")
        if final_state.get("argocd_validation_passed"):
            parts.append("GitOps validation PASSED — application is running healthy.")
        elif final_state.get("argocd_validation_result"):
            parts.append("GitOps validation FAILED — see output for details.")
        changes = "\n".join(parts)
    else:
        content, changes = "", ""
    return content, changes


# ------------------------------------------------------------------ #
#  Main interface builder                                              #
# ------------------------------------------------------------------ #

def create_demo(
    chat_tab: 'ChatTab',
    mcp_test_tab: 'MCPTestTab',
    rag_test_tab: 'RAGTestTab',
    system_status_tab: 'SystemStatusTab',
    form_tab: 'FormTab',
):
    wizard_app = build_wizard_app()
    auto_app = build_auto_app()

    def _ctx():
        set_shared_context({
            "call_responses_api": form_tab._call_responses_api,
            "config_apply_best_practices": form_tab.config_apply_best_practices,
            "config_generate_helm": form_tab.config_generate_helm,
            "config_validate_deployment": form_tab.config_validate_deployment,
            "config_validate_argocd": form_tab.config_validate_argocd,
        })

    # ============================================================== #
    #  Wizard handlers                                                 #
    # ============================================================== #

    # ------------------------------------------------------------ #
    #  Real-time progress: run graph in a thread, poll live_progress #
    # ------------------------------------------------------------ #

    import threading
    import time as _time

    _POLL_INTERVAL = 0.5  # seconds between UI refreshes

    def _make_running_yield(progress_text, pipe_st, cur_phase):
        return (
            gr.update(),                                    # stepper
            progress_text,                                  # progress_log
            gr.update(),                                    # content_area
            gr.update(),                                    # changes_panel
            gr.update(interactive=False),                   # next_btn
            gr.update(interactive=False),                   # run_all_btn
            gr.update(visible=False),                       # retry_btn
            gr.update(visible=False),                       # abort_btn
            pipe_st,                                        # pipeline_state
            cur_phase,                                      # current_phase
        )

    def _run_graph_in_thread(graph_app, stream_arg, config, live_buf):
        """Run graph.stream() in a background thread, return result holder."""
        holder = {"last_state": {}, "error": None, "done": False}

        def _worker():
            try:
                for sv in graph_app.stream(stream_arg, config, stream_mode="values"):
                    holder["last_state"] = sv
                    # Merge node progress into live_buf so the UI picks it up
                    for line in sv.get("progress_log", []):
                        if line not in live_buf:
                            live_buf.append(line)
            except Exception as exc:
                holder["error"] = exc
            finally:
                holder["done"] = True

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return t, holder

    def _poll_until_done(thread, holder, live_buf, pipe_st, cur_phase):
        """Yield UI updates while the graph thread is running."""
        prev_len = 0
        while not holder["done"]:
            _time.sleep(_POLL_INTERVAL)
            cur_len = len(live_buf)
            if cur_len != prev_len:
                prev_len = cur_len
                yield _make_running_yield("\n".join(live_buf), pipe_st, cur_phase)
        thread.join()
        # Final flush
        if len(live_buf) != prev_len:
            yield _make_running_yield("\n".join(live_buf), pipe_st, cur_phase)

    def handle_next(pipe_st, cur_phase, ns, chart, wtype, sres):
        chart_name = chart if chart else ns

        # --- Reset ---
        if cur_phase >= 4:
            yield (
                _stepper_html(0), "", "", gr.update(value="", visible=False),
                gr.update(value=NEXT_LABELS[0], interactive=True, visible=True),
                gr.update(interactive=True),
                gr.update(visible=False), gr.update(visible=False),
                {}, 0,
            )
            return

        # --- Prepare shared live buffer ---
        live_buf: list[str] = []
        _ctx()
        set_shared_context({**get_shared_context(), "live_progress": live_buf})

        # --- Start or resume ---
        if cur_phase == 0:
            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}
            stream_arg = {
                "namespace": ns,
                "chart_name": chart_name,
                "workload_type": wtype,
                "supporting_resources": sres,
                "progress_log": [],
                "current_phase": 0,
            }
        else:
            thread_id = pipe_st.get("thread_id", str(uuid.uuid4()))
            config = {"configurable": {"thread_id": thread_id}}
            stream_arg = None

        new_pipe_st = {"thread_id": config["configurable"]["thread_id"]}
        yield _make_running_yield("Running...", new_pipe_st, cur_phase)

        thread, holder = _run_graph_in_thread(wizard_app, stream_arg, config, live_buf)
        yield from _poll_until_done(thread, holder, live_buf, new_pipe_st, cur_phase)

        if holder["error"]:
            yield (
                gr.update(), f"ERROR: {holder['error']}", gr.update(), gr.update(),
                gr.update(value=NEXT_LABELS.get(cur_phase, "Next"), interactive=True, visible=True),
                gr.update(interactive=(cur_phase == 0)),
                gr.update(visible=False), gr.update(visible=False),
                new_pipe_st, cur_phase,
            )
            return

        # --- Phase complete ---
        last_state = holder["last_state"]
        new_phase = _detect_phase(wizard_app, config)
        content, changes = _phase_outputs(last_state, new_phase)
        progress = last_state.get("progress_log", [])
        validation_failed = (
            new_phase == 2 and last_state.get("validation_passed") is False
        )

        yield (
            _stepper_html(new_phase),
            "\n".join(progress),
            content,
            gr.update(value=changes, visible=True),
            gr.update(
                value=NEXT_LABELS.get(new_phase, "Next"),
                interactive=not validation_failed,
                visible=not validation_failed,
            ),
            gr.update(interactive=(new_phase >= 4)),
            gr.update(visible=validation_failed),
            gr.update(visible=validation_failed),
            new_pipe_st,
            new_phase,
        )

    def handle_run_all(pipe_st, cur_phase, ns, chart, wtype, sres):
        chart_name = chart if chart else ns
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        live_buf: list[str] = []
        _ctx()
        set_shared_context({**get_shared_context(), "live_progress": live_buf})

        stream_arg = {
            "namespace": ns,
            "chart_name": chart_name,
            "workload_type": wtype,
            "supporting_resources": sres,
            "progress_log": [],
            "current_phase": 0,
        }
        new_pipe_st = {"thread_id": thread_id}

        yield _make_running_yield("Running full pipeline...", new_pipe_st, 0)

        thread, holder = _run_graph_in_thread(auto_app, stream_arg, config, live_buf)
        yield from _poll_until_done(thread, holder, live_buf, new_pipe_st, 0)

        if holder["error"]:
            yield (
                gr.update(), f"ERROR: {holder['error']}", gr.update(), gr.update(),
                gr.update(value="Start Pipeline", interactive=True, visible=True),
                gr.update(interactive=True),
                gr.update(visible=False), gr.update(visible=False),
                {}, 0,
            )
            return

        last_state = holder["last_state"]
        content, changes = _phase_outputs(last_state, 4)
        progress = last_state.get("progress_log", [])

        yield (
            _stepper_html(4),
            "\n".join(progress),
            content,
            gr.update(value=changes, visible=True),
            gr.update(value="Start New Pipeline", interactive=True, visible=True),
            gr.update(interactive=True),
            gr.update(visible=False), gr.update(visible=False),
            new_pipe_st, 4,
        )

    def handle_retry(pipe_st, cur_phase):
        thread_id = pipe_st.get("thread_id")
        if not thread_id:
            return
        config = {"configurable": {"thread_id": thread_id}}

        live_buf: list[str] = []
        _ctx()
        set_shared_context({**get_shared_context(), "live_progress": live_buf})

        wizard_app.update_state(
            config,
            {
                "validation_passed": None,
                "validation_result": "",
                "validation_attempts": 0,
                "progress_log": [],
            },
            as_node="apply_best_practices",
        )

        new_pipe_st = {"thread_id": thread_id}
        yield _make_running_yield("Retrying validation...", new_pipe_st, cur_phase)

        thread, holder = _run_graph_in_thread(wizard_app, None, config, live_buf)
        yield from _poll_until_done(thread, holder, live_buf, new_pipe_st, cur_phase)

        if holder["error"]:
            yield (
                gr.update(), f"ERROR during retry: {holder['error']}", gr.update(), gr.update(),
                gr.update(visible=False), gr.update(interactive=False),
                gr.update(visible=True), gr.update(visible=True),
                new_pipe_st, cur_phase,
            )
            return

        last_state = holder["last_state"]
        new_phase = _detect_phase(wizard_app, config)
        content, changes = _phase_outputs(last_state, new_phase)
        progress = last_state.get("progress_log", [])
        validation_failed = (
            new_phase == 2 and last_state.get("validation_passed") is False
        )

        yield (
            _stepper_html(new_phase),
            "\n".join(progress),
            content,
            gr.update(value=changes, visible=True),
            gr.update(
                value=NEXT_LABELS.get(new_phase, "Next"),
                interactive=not validation_failed,
                visible=not validation_failed,
            ),
            gr.update(interactive=False),
            gr.update(visible=validation_failed),
            gr.update(visible=validation_failed),
            new_pipe_st, new_phase,
        )

    def handle_abort(pipe_st, cur_phase):
        """Abort the pipeline and reset to Phase 0."""
        return (
            _stepper_html(0),
            "Pipeline aborted.",
            "",
            gr.update(value="", visible=False),
            gr.update(value="Start Pipeline", interactive=True, visible=True),
            gr.update(interactive=True),
            gr.update(visible=False), gr.update(visible=False),
            {}, 0,
        )

    # ============================================================== #
    #  Gradio layout                                                   #
    # ============================================================== #

    with gr.Blocks(title="Intelligent CD Chatbot") as demo:

        # Header
        with gr.Row():
            with gr.Column(scale=1):
                gr.HTML(HEADER_HTML)

        with gr.Row():
            # ---- Left column ----
            with gr.Column(scale=2):
                with gr.Tabs():

                    # ============== Intelligent CD Wizard ============== #
                    with gr.TabItem("📋 Intelligent CD"):
                        stepper = gr.HTML(value=_stepper_html(0))

                        namespace_input = gr.Textbox(
                            label="Namespace", value="discounts",
                            placeholder="Enter namespace name", interactive=True,
                        )
                        helm_chart_input = gr.Textbox(
                            label="Helm Chart (Optional)", value="",
                            placeholder="Enter Helm chart name", interactive=True,
                            visible=False,
                        )
                        workload_type_selector = gr.Radio(
                            choices=["Deployment", "StatefulSet"],
                            label="Workload Type", value="Deployment", interactive=True,
                            visible=False,
                        )
                        supporting_resources_selector = gr.CheckboxGroup(
                            choices=["Service", "Route", "ConfigMap"],
                            label="Supporting Resources",
                            value=["Service", "Route", "ConfigMap"], interactive=True,
                            visible=False,
                        )

                        with gr.Row():
                            next_btn = gr.Button(
                                "Start Pipeline", variant="primary", size="lg",
                                elem_classes=["ai-generation-btn"],
                            )
                            run_all_btn = gr.Button(
                                "Run All", variant="secondary", size="lg",
                            )
                        with gr.Row():
                            retry_btn = gr.Button(
                                "Retry Validation", variant="stop", size="sm",
                                visible=False,
                            )
                            abort_btn = gr.Button(
                                "Abort Pipeline", variant="stop", size="sm",
                                visible=False,
                            )

                        progress_log = gr.Textbox(
                            label="Progress", lines=12, max_lines=30,
                            interactive=False, show_label=True,
                        )
                        changes_panel = gr.Textbox(
                            label="Changes Applied", lines=8, max_lines=20,
                            interactive=False, visible=False,
                        )

                        pipeline_state = gr.State(value={})
                        current_phase = gr.State(value=0)

                        form_config_display = gr.Markdown(
                            value=form_tab.get_config_display(),
                            elem_classes=["config-display"],
                        )

                    # ============== Chat Tab ============== #
                    with gr.TabItem("💬 Troubleshooting"):
                        with gr.Column():
                            with gr.Column(scale=7):
                                from gradio import ChatMessage
                                history = [ChatMessage(role="assistant", content="Hello, how can I help you?")]
                                chatbot = gr.Chatbot(
                                    history, label="Chat",
                                    show_label=False,
                                    avatar_images=["assets/chatbot.png", "assets/chatbot.png"],
                                    allow_file_downloads=True, layout="panel",
                                )
                            with gr.Column(scale=3):
                                with gr.Row():
                                    with gr.Column(scale=6):
                                        msg = gr.Textbox(
                                            label="Message", show_label=False,
                                            placeholder="Ask me about Kubernetes, GitOps, or OpenShift deployments...",
                                            value="Using the resources_list tool from the MCP Server for OpenShift, list the pods in the namespace intelligent-cd and show the name, container image and status of each pod.",
                                            lines=2, max_lines=3,
                                        )
                                    with gr.Column(scale=2):
                                        send_btn = gr.Button("Send", variant="primary", size="md", scale=1)
                                        save_btn = gr.Button("Save", variant="primary", size="md", scale=1)
                                        clear_btn = gr.Button("Clear", variant="secondary", size="md", scale=1)
                                config_display = gr.Markdown(
                                    value=chat_tab.get_config_display(),
                                    elem_classes=["config-display"],
                                )

                    # ============== MCP Test Tab ============== #
                    with gr.TabItem("🤖 MCP Test"):
                        status_indicator = gr.Textbox(
                            label="Status", value="Ready to test MCP server",
                            interactive=False, show_label=False,
                        )
                        with gr.Row():
                            refresh_toolgroups_btn = gr.Button("ToolGroups", variant="secondary", size="md", scale=1)
                            refresh_methods_btn = gr.Button("Methods", variant="secondary", size="md", scale=1)
                        toolgroup_selector = gr.Dropdown(
                            choices=["Select a toolgroup..."], label="Select Toolgroup",
                            value="Select a toolgroup...", interactive=True,
                        )
                        method_selector = gr.Dropdown(
                            choices=["Select a method..."], label="Select Method",
                            value="Select a method...", interactive=True,
                        )
                        with gr.Group():
                            params_input = gr.Textbox(
                                label="Parameters (JSON)",
                                placeholder='{"namespace": "default"}', lines=3, value='{}',
                            )
                        execute_btn = gr.Button("Execute Method", variant="primary", size="lg")

                    # ============== RAG Test Tab ============== #
                    with gr.TabItem("📚 RAG Test"):
                        rag_input = gr.Textbox(
                            label="RAG Query",
                            value="Based on the documents stored in the RAG, please, tell me which teams and emails I need to contact to approve that my system is not stateless and I also need a route",
                            lines=4, max_lines=6, interactive=True,
                        )
                        with gr.Row():
                            rag_database_input = gr.Dropdown(
                                choices=["Loading databases..."], label="Database Name",
                                value="", interactive=True, allow_custom_value=True,
                            )
                        rag_send_btn = gr.Button("Send Query", variant="primary", size="lg")
                        rag_status_btn = gr.Button("RAG Status", variant="secondary", size="lg")
                        gr.Markdown("Modify the RAG query above, then click Send. Use RAG Status for configuration details.")

                    # ============== System Status Tab ============== #
                    with gr.TabItem("🔍 System Status"):
                        system_status_btn = gr.Button("Check System Status", variant="primary", size="lg")
                        gr.Markdown("Click the button above to view system information in the right panel.")

            # ---- Right column ---- #
            with gr.Column(scale=3):
                content_area = gr.Textbox(
                    label="Code Canvas & Output",
                    placeholder="Pipeline output will appear here...",
                    lines=20, max_lines=50, interactive=True,
                    show_label=True,
                )

        # ============================================================== #
        #  Event wiring                                                    #
        # ============================================================== #

        _wizard_outputs = [
            stepper, progress_log, content_area, changes_panel,
            next_btn, run_all_btn, retry_btn, abort_btn,
            pipeline_state, current_phase,
        ]
        _wizard_inputs = [
            pipeline_state, current_phase,
            namespace_input, helm_chart_input,
            workload_type_selector, supporting_resources_selector,
        ]

        next_btn.click(fn=handle_next, inputs=_wizard_inputs, outputs=_wizard_outputs)
        run_all_btn.click(fn=handle_run_all, inputs=_wizard_inputs, outputs=_wizard_outputs)
        retry_btn.click(
            fn=handle_retry,
            inputs=[pipeline_state, current_phase],
            outputs=_wizard_outputs,
        )
        abort_btn.click(
            fn=handle_abort,
            inputs=[pipeline_state, current_phase],
            outputs=_wizard_outputs,
        )

        # ---- Chat ---- #
        msg.submit(fn=chat_tab.chat_completion, inputs=[msg, chatbot], outputs=[chatbot, msg])
        send_btn.click(fn=chat_tab.chat_completion, inputs=[msg, chatbot], outputs=[chatbot, msg])
        save_btn.click(
            fn=lambda hist: f"SAVED:\n\n{hist[-1]['content'] if hist else 'No history'}",
            inputs=[chatbot], outputs=[content_area],
        )

        def clear_chat():
            from gradio import ChatMessage
            chat_tab.reset_conversation()
            return [ChatMessage(role="assistant", content="Hello, how can I help you?")], ""

        clear_btn.click(fn=clear_chat, outputs=[chatbot, msg])

        # ---- MCP Test ---- #
        refresh_toolgroups_btn.click(fn=mcp_test_tab.list_toolgroups, outputs=[toolgroup_selector])
        refresh_methods_btn.click(
            fn=mcp_test_tab.get_toolgroup_methods,
            inputs=[toolgroup_selector], outputs=[status_indicator, method_selector],
        )
        execute_btn.click(
            fn=lambda tg, m, p: f"MCP: {m}\n\n{mcp_test_tab.execute_tool(tg, m, p)}",
            inputs=[toolgroup_selector, method_selector, params_input], outputs=content_area,
        )

        # ---- RAG Test ---- #
        rag_send_btn.click(fn=rag_test_tab.test_rag, inputs=[rag_input, rag_database_input], outputs=content_area)
        rag_status_btn.click(fn=rag_test_tab.get_rag_status, inputs=[rag_database_input], outputs=content_area)

        def populate_database_dropdown():
            try:
                databases = rag_test_tab.get_available_databases()
                return gr.Dropdown(choices=databases, value="")
            except Exception:
                return gr.Dropdown(choices=["Error loading databases"], value="")

        demo.load(fn=populate_database_dropdown, outputs=[rag_database_input])

        # ---- System Status ---- #
        system_status_btn.click(fn=lambda: system_status_tab.get_system_status(), outputs=content_area)

    return demo
