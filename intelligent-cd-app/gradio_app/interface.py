"""
Gradio interface for Intelligent CD Chatbot.

This module contains the Gradio UI components, styling, and layout configuration.
"""

import gradio as gr
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tabs.chat_tab import ChatTab
    from tabs.mcp_test_tab import MCPTestTab
    from tabs.rag_test_tab import RAGTestTab
    from tabs.system_status_tab import SystemStatusTab
    from tabs.form_tab import FormTab


def create_demo(chat_tab: 'ChatTab', mcp_test_tab: 'MCPTestTab', rag_test_tab: 'RAGTestTab', system_status_tab: 'SystemStatusTab', form_tab: 'FormTab'):
    """Create the beautiful Gradio interface with header and chat"""
    
    with gr.Blocks(
        title="Intelligent CD Chatbot",
        # https://www.gradio.app/guides/theming-guide
        theme=gr.themes.Soft(),  # Fixed light theme - no dark mode switching
        css="""
        /* Full screen responsive layout */
        .gradio-container {
            max-width: 100vw !important;
            width: 100vw !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        
        /* Main content area - full width */
        .main-panel {
            width: 100% !important;
            max-width: 100% !important;
        }
        
        /* Header styling */
        .header-container {
            background: linear-gradient(135deg, #ff8c42 0%, #ffa726 50%, #ff7043 100%);
            color: white;
            padding: 20px;
            border-radius: 0 0 15px 15px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            width: 100% !important;
        }
        
        .header-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .logo {
            width: 50px;
            height: 50px;
            border-radius: 10px;
        }
        
        .header-title {
            font-size: 2.2em;
            font-weight: bold;
            margin: 0;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }
        
        .header-subtitle {
            font-size: 1.1em;
            opacity: 0.95;
            margin: 5px 0 0 0;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }
        
        .header-right {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        /* Chat input and buttons layout */
        .chat-input-container {
            display: flex !important;
            gap: 10px !important;
            align-items: flex-start !important;
            width: 100% !important;
        }
        
        .chat-input-field {
            flex: 1 !important;
            min-width: 0 !important;
        }
        
        .chat-buttons-column {
            display: flex !important;
            flex-direction: column !important;
            gap: 8px !important;
            flex-shrink: 0 !important;
        }
        
        /* Chat input row styling */
        .chat-input-row {
            display: flex !important;
            align-items: flex-end !important;
            gap: 10px !important;
            width: 100% !important;
        }
        

        
        /* Ensure both panels have equal heights */
        .equal-height-panels {
            display: flex !important;
            align-items: stretch !important;
        }
        
        /* Status indicator styling */
        .status-ready {
            background-color: #e8f5e8 !important;
            border-color: #4caf50 !important;
            color: #2e7d32 !important;
        }
        
        .status-loading {
            background-color: #fff3e0 !important;
            border-color: #ff9800 !important;
            color: #e65100 !important;
        }
        
        .status-error {
            background-color: #ffebee !important;
            border-color: #f44336 !important;
            color: #c62828 !important;
        }
        
        .status-success {
            background-color: #e8f5e8 !important;
            border-color: #4caf50 !important;
            color: #2e7d32 !important;
        }
        
        /* Configuration display styling - small gray text */
        .config-display {
            font-size: 0.75em !important;
            color: #666 !important;
            padding: 5px 10px !important;
            margin-top: 5px !important;
            background-color: #f5f5f5 !important;
            border-radius: 4px !important;
            border: 1px solid #ddd !important;
        }
        
        .config-display p {
            margin: 0 !important;
            line-height: 1.4 !important;
        }
        
        /* Button styling for Intelligent CD tab */
        .ai-generation-btn {
            background: #667eea !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
            transition: all 0.3s ease !important;
        }
        
        .ai-generation-btn:hover {
            background: #5a6fd8 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4) !important;
        }
        
        .openshift-action-btn {
            background: #28a745 !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3) !important;
            transition: all 0.3s ease !important;
        }
        
        .openshift-action-btn:hover {
            background: #218838 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(40, 167, 69, 0.4) !important;
        }
        
        /* GitOps button styling - full width */
        .gitops-btn {
            width: 100% !important;
            margin-top: 10px !important;
        }
        
        /* Button matrix layout */
        .button-matrix {
            display: grid !important;
            grid-template-columns: 1fr 1fr !important;
            gap: 15px !important;
            margin: 20px 0 !important;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .header-title {
                font-size: 1.8em !important;
            }
            .header-subtitle {
                font-size: 1em !important;
            }
            .button-matrix {
                grid-template-columns: 1fr !important;
                gap: 10px !important;
            }
        }
        """
    ) as demo:
        
        # Beautiful Header with Logo
        with gr.Row():
            with gr.Column(scale=1):
                gr.HTML("""
                <div class="header-container">
                    <div class="header-content">
                        <div class="header-left">
                            <svg class="logo" version="1.0" xmlns="http://www.w3.org/2000/svg" width="50" height="50" viewBox="0 0 300 300" preserveAspectRatio="xMidYMid meet">
                                <g transform="translate(0.000000,300.000000) scale(0.100000,-0.100000)" fill="currentColor" stroke="none">
                                    <path d="M1470 2449 c-47 -10 -80 -53 -80 -105 0 -45 26 -88 61 -99 18 -6 19 -14 17 -138 l-3 -132 -37 -3 -38 -3 0 48 c0 43 -4 53 -34 82 -32 31 -35 38 -33 87 2 46 -2 57 -27 83 -36 38 -74 46 -120 27 -70 -29 -86 -125 -30 -177 20 -19 36 -24 79 -24 70 0 95 -22 95 -82 l0 -43 -162 0 c-108 -1 -175 -5 -200 -14 -98 -35 -168 -134 -178 -250 l-5 -69 -44 -11 c-69 -17 -85 -47 -90 -164 -5 -147 17 -194 102 -211 l32 -7 5 -80 c4 -64 11 -90 36 -134 50 -88 141 -140 247 -140 l47 0 0 -135 c0 -122 2 -137 20 -155 11 -11 29 -20 40 -20 21 0 31 8 233 193 l129 117 226 0 c125 0 244 5 264 10 62 18 128 71 162 130 25 44 32 70 36 134 l5 79 44 11 c74 18 86 45 86 186 0 141 -12 168 -86 186 l-44 11 -6 74 c-10 113 -58 187 -153 234 -47 24 -59 25 -218 25 l-168 0 0 40 c0 53 38 91 85 83 60 -10 125 46 125 107 0 38 -30 81 -67 96 -45 19 -83 11 -119 -27 -25 -26 -29 -37 -27 -83 2 -49 -1 -56 -33 -87 -30 -29 -34 -39 -34 -82 l0 -48 -37 3 -38 3 -3 132 c-2 124 -1 132 17 138 35 11 61 54 61 99 0 75 -62 122 -140 105z m65 -79 c27 -30 7 -70 -35 -70 -42 0 -62 40 -35 70 10 11 26 20 35 20 9 0 25 -9 35 -20z m-281 -152 c16 -26 -4 -53 -40 -53 -23 0 -30 5 -32 23 -7 47 47 69 72 30z m556 8 c6 -8 10 -25 8 -38 -6 -42 -78 -32 -78 11 0 37 46 55 70 27z m-4 -376 c182 0 193 -1 225 -23 19 -12 44 -42 57 -67 21 -43 22 -54 22 -330 0 -276 -1 -287 -22 -330 -13 -25 -38 -55 -57 -67 -33 -22 -41 -23 -288 -23 l-253 0 -91 -82 c-50 -46 -109 -98 -130 -116 l-39 -34 0 96 c0 130 -6 136 -134 136 -111 0 -147 18 -183 90 -22 43 -23 54 -23 330 0 277 1 287 23 330 25 50 60 79 106 89 17 3 159 5 314 3 155 -1 368 -2 473 -2z"/>
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
                            <div style="text-align: right;">
                                <div style="font-size: 0.8em; opacity: 0.7; margin-bottom: 2px;">
                                    Powered by
                                </div>
                                <div style="font-size: 1.2em; font-weight: bold; opacity: 0.9;">
                                    Red Hat AI
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                """)
        
        # Top Right Controls - Removed for cleaner interface
        
        # Main Content Area - Two Columns
        with gr.Row():
            # Left Column - Chatbot (40%)
            with gr.Column(scale=2):
                # Tab system for different interfaces
                with gr.Tabs():
                    # Intelligent CD Form Tab
                    with gr.TabItem("📋 Intelligent CD"):
                        # Namespace input
                        namespace_input = gr.Textbox(
                            label="Namespace",
                            value="discounts",
                            placeholder="Enter namespace name",
                            interactive=True,
                            show_label=True
                        )
                        
                        # Helm Chart input (optional)
                        helm_chart_input = gr.Textbox(
                            label="Helm Chart (Optional)",
                            value="",
                            placeholder="Enter Helm chart name or repository",
                            interactive=True,
                            show_label=True
                        )
                        
                        # Workload type selector (single choice)
                        workload_type_selector = gr.Radio(
                            choices=["Deployment", "StatefulSet"],
                            label="Workload Type",
                            value="Deployment",
                            interactive=True,
                            show_label=True
                        )
                        
                        # Supporting resources selector (multiple choice, all selected by default)
                        supporting_resources_selector = gr.CheckboxGroup(
                            choices=["Service", "Route", "ConfigMap"],
                            label="Supporting Resources",
                            value=["Service", "Route", "ConfigMap"],
                            interactive=True,
                            show_label=True
                        )
                        
                        # 2x2 Button Matrix
                        with gr.Row():
                            # Top Left - Generate Resources (AI Generation - Blue/Purple theme)
                            with gr.Column(scale=3):
                                generate_btn = gr.Button(
                                    "📝 Generate Resources", 
                                    variant="primary", 
                                    size="lg",
                                    elem_classes=["ai-generation-btn"]
                                )
                            
                            # Top Right - Apply YAML (OpenShift Action - Green theme)
                            with gr.Column(scale=1):
                                apply_yaml_btn = gr.Button(
                                    "🔧 Apply YAML", 
                                    variant="secondary", 
                                    size="lg",
                                    elem_classes=["openshift-action-btn"]
                                )
                        
                        with gr.Row():
                            # Bottom Left - Generate Helm (AI Generation - Blue/Purple theme)
                            with gr.Column(scale=3):
                                generate_helm_btn = gr.Button(
                                    "📦 Generate Helm Chart", 
                                    variant="primary", 
                                    size="lg",
                                    elem_classes=["ai-generation-btn"]
                                )
                            
                            # Bottom Right - Apply Helm (OpenShift Action - Green theme)
                            with gr.Column(scale=1):
                                apply_helm_btn = gr.Button(
                                    "🚀 Apply Helm", 
                                    variant="secondary", 
                                    size="lg",
                                    elem_classes=["openshift-action-btn"]
                                )
                        
                        # Full-width GitOps button
                        with gr.Row():
                            with gr.Column(scale=1):
                                make_gitops_btn = gr.Button(
                                    "🔄 Make it GitOps", 
                                    variant="primary", 
                                    size="lg",
                                    elem_classes=["ai-generation-btn", "gitops-btn"]
                                )
                        
                        # Configuration display
                        form_config_display = gr.Markdown(
                            value=form_tab.get_config_display(),
                            elem_classes=["config-display"]
                        )
                    
                    # Chat Tab
                    with gr.TabItem("💬 Troubleshooting"):
                        # Vertical layout: Chat history (7) and input (3)
                        with gr.Column():
                            # Chat Interface - Takes most of the space (scale 7)
                            with gr.Column(scale=7):
                                from gradio import ChatMessage
                                history = [ChatMessage(role="assistant", content="Hello, how can I help you?")]
                                
                                chatbot = gr.Chatbot(history,
                                    label="💬 Chat with AI Assistant",
                                    show_label=False,
                                    avatar_images=["assets/chatbot.png", "assets/chatbot.png"],
                                    allow_file_downloads=True,
                                    type="messages",
                                    layout="panel"
                                )
                            
                            # Chat Input - Takes less space (scale 3)
                            with gr.Column(scale=3):
                                with gr.Row():
                                    with gr.Column(scale=6):
                                        msg = gr.Textbox(
                                            label="Message",
                                            show_label=False,
                                            placeholder="Ask me about Kubernetes, GitOps, or OpenShift deployments...",
                                            value="Using the resources_list tool from the MCP Server for OpenShift, list the pods in the namespace intelligent-cd and show the name, container image and status of each pod.",
                                            lines=2,
                                            max_lines=3
                                        )
                                    with gr.Column(scale=2):
                                        send_btn = gr.Button("Send", variant="primary", size="md", scale=1)
                                        save_btn = gr.Button("Save", variant="primary", size="md", scale=1)
                                
                                # Configuration display below text input
                                config_display = gr.Markdown(
                                    value=chat_tab.get_config_display(),
                                    elem_classes=["config-display"]
                                )
                    
                    # MCP Test Tab
                    with gr.TabItem("🤖 MCP Test"):
                        # Status Bar - Simple textbox with status styling
                        status_indicator = gr.Textbox(
                            label="Status",
                            value="✅ Ready to test MCP server",
                            interactive=False,
                            show_label=False,
                            elem_classes=["status-ready"]
                        )
                        
                        # Toolgroup Selector with Refresh Button
                        with gr.Row():
                            refresh_toolgroups_btn = gr.Button("🔄ToolGroups", variant="secondary", size="md", scale=1)
                            refresh_methods_btn = gr.Button("🔄Methods", variant="secondary", size="md", scale=1)

                        toolgroup_selector = gr.Dropdown(
                            choices=["Select a toolgroup..."],
                            label="Select Toolgroup",
                            value="Select a toolgroup...",
                            interactive=True
                        )

                        method_selector = gr.Dropdown(
                            choices=["Select a method..."],
                            label="Select Method",
                            value="Select a method...",
                            interactive=True
                        )

                        
                        # Parameters Section
                        with gr.Group():
                            # gr.Markdown("**Parameters:**")
                            params_input = gr.Textbox(
                                label="Parameters (JSON)",
                                placeholder='{"namespace": "default"}',
                                lines=3,
                                value='{}'
                            )
                        
                        # Execute Button
                        execute_btn = gr.Button("Execute Method", variant="primary", size="lg")
                    
                    # RAG Test Tab
                    with gr.TabItem("📚 RAG Test"):
                        # Preconfigured textbox
                        rag_input = gr.Textbox(
                            label="RAG Query",
                            value="Based on the documents stored in the RAG, please, tell me which teams and emails I need to contact to approve that my system is not stateless and I also need a route",
                            lines=4,
                            max_lines=6,
                            interactive=True,
                            show_label=True
                        )
                        
                        # Database dropdown with refresh button
                        with gr.Row():
                            rag_database_input = gr.Dropdown(
                                choices=["Loading databases..."],
                                label="Database Name",
                                value="",
                                interactive=True,
                                show_label=True,
                                allow_custom_value=True
                            )
                        
                        # Send button
                        rag_send_btn = gr.Button("Send Query", variant="primary", size="lg")
                        
                        # RAG Status button
                        rag_status_btn = gr.Button("RAG Status", variant="secondary", size="lg")
                        
                        # Note for user
                        gr.Markdown("Use the textbox above to modify your RAG query, then click Send to process it. Use RAG Status to view detailed RAG configuration information. Select a database from the dropdown or leave empty for default. Use the 🔄 button to refresh the database list.")
                    
                    # System Status Tab
                    with gr.TabItem("🔍 System Status"):
                        # Check Status Button
                        system_status_btn = gr.Button("Check System Status", variant="primary", size="lg")
                        
                        # Note for user
                        gr.Markdown("Click the button above to view detailed system information in the right panel.")
            
            # Right Column - Code Canvas (60%)
            with gr.Column(scale=3):
                # Dynamic content area for System Status, MCP Test results, and other content
                content_area = gr.Textbox(
                    label="📝 Code Canvas & Saved Responses",
                    placeholder="Click a button above to see results here, chat with the AI to generate deployment manifests, or use the Save button to move the last chat response here for better clarity...",
                    lines=20,
                    max_lines=50,
                    interactive=True,
                    show_copy_button=True,
                    show_label=True
                )
        

        
        # Event handlers
        
        # Intelligent CD Form Tab functionality
        generate_btn.click(
            fn=form_tab.generate_resources,
            inputs=[namespace_input, helm_chart_input, workload_type_selector, supporting_resources_selector],
            outputs=content_area
        )
        
        # Apply YAML button functionality
        apply_yaml_btn.click(
            fn=form_tab.apply_yaml,
            inputs=[namespace_input, content_area],
            outputs=content_area
        )
        
        # Generate Helm button functionality
        generate_helm_btn.click(
            fn=form_tab.generate_helm,
            inputs=[namespace_input, helm_chart_input, workload_type_selector, supporting_resources_selector],
            outputs=content_area
        )
        
        # Apply Helm button functionality - show alert
        apply_helm_btn.click(
            fn=lambda: "🚀 Button 'Apply Helm' clicked",
            outputs=content_area
        )
        
        # Make it GitOps button functionality - show alert
        make_gitops_btn.click(
            fn=lambda: "🔄 Button 'Make it GitOps' clicked",
            outputs=content_area
        )
        
        # Refresh Toolgroups Button (next to dropdown)
        refresh_toolgroups_btn.click(
            fn=mcp_test_tab.list_toolgroups,
            outputs=[toolgroup_selector]
        )
        
        # Refresh Methods Button
        refresh_methods_btn.click(
            fn=mcp_test_tab.get_toolgroup_methods,
            inputs=[toolgroup_selector],
            outputs=[status_indicator, method_selector]
        )
        
        execute_btn.click(
            fn=lambda toolgroup, method, params: f"🧪 MCP Method Execution: {method}\n\n{mcp_test_tab.execute_tool(toolgroup, method, params)}",
            inputs=[toolgroup_selector, method_selector, params_input],
            outputs=content_area
        )
        
        # System Status Tab functionality
        system_status_btn.click(
            fn=lambda: f"{system_status_tab.get_system_status()}",
            outputs=content_area
        )
        
        # RAG Test Tab functionality
        rag_send_btn.click(
            fn=rag_test_tab.test_rag,
            inputs=[rag_input, rag_database_input],
            outputs=content_area
        )
        
        # RAG Status button functionality
        rag_status_btn.click(
            fn=rag_test_tab.get_rag_status,
            inputs=[rag_database_input],
            outputs=content_area
        )
        
        # Function to populate database dropdown
        def populate_database_dropdown():
            """Populate the database dropdown with available databases"""
            try:
                databases = rag_test_tab.get_available_databases()
                return gr.Dropdown(choices=databases, value="")
            except Exception as e:
                return gr.Dropdown(choices=["Error loading databases"], value="")
        
        # Populate database dropdown on startup
        demo.load(
            fn=populate_database_dropdown,
            outputs=[rag_database_input]
        )
        
        # Chat functionality - both Enter key and Send button
        msg.submit(
            fn=chat_tab.chat_completion,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg]
        )
        
        send_btn.click(
            fn=chat_tab.chat_completion,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg]
        )
        
        # Save button functionality - moves last chat answer to right panel
        save_btn.click(
            fn=lambda chat_history: f"💾 SAVED CHAT RESPONSE:\n\n{chat_history[-1]['content'] if chat_history and len(chat_history) > 0 else 'No chat history available'}",
            inputs=[chatbot],
            outputs=[content_area]
        )
        
        # Add JavaScript to handle Enter key behavior properly
        demo.load(
            fn=None,
            js="""
            function() {
                // Wait for the page to load and find the textarea
                setTimeout(function() {
                    const textarea = document.querySelector('textarea[placeholder*="Ask me about Kubernetes"]');
                    if (textarea) {
                        textarea.addEventListener('keydown', function(e) {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                // Find and click the send button
                                const sendBtn = document.querySelector('button:has-text("Send")');
                                if (sendBtn) {
                                    sendBtn.click();
                                }
                            }
                        });
                        console.log('Enter key handler attached to chat textarea');
                    } else {
                        console.log('Chat textarea not found');
                    }
                }, 1000);
            }
            """
        )
        

    
    return demo
