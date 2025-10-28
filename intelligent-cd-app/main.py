"""
Intelligent CD Chatbot - Main Application

This is the main application file containing all core functionality:
- Logging configuration
- Client initialization and configuration
- Application creation and orchestration
- Environment variable management

Usage:
    python main.py
    gradio main.py

The application will start a Gradio web interface accessible at http://localhost:7860
"""

import os
import json
from typing import Tuple
from llama_stack_client import LlamaStackClient
from utils import get_logger
from tabs import ChatTab, MCPTestTab, RAGTestTab, SystemStatusTab, FormTab
from gradio_app import create_demo



# ============================================================================
# CONFIGURATION AND CLIENT INITIALIZATION
# ============================================================================

def get_extra_headers_config() -> dict:
    """Configure MCP server authentication headers and return them"""
    mcp_headers = {}
    
    # Configure ArgoCD MCP server
    argocd_url = os.getenv("ARGOCD_BASE_URL")
    argocd_token = os.getenv("ARGOCD_API_TOKEN")
    
    if argocd_url and argocd_token:
        mcp_headers["http://argocd-mcp-server:3000/sse"] = {
            "x-argocd-base-url": argocd_url,
            "x-argocd-api-token": argocd_token
        }
    
    # Configure GitHub MCP server
    github_auth_token = os.getenv("GITHUB_PAT")
    
    if github_auth_token:
        github_headers = {
            "Authorization": f"Bearer {github_auth_token}"
        }
        
        # Add optional toolsets header
        github_toolsets = os.getenv("GITHUB_MCP_SERVER_TOOLSETS")
        if github_toolsets:
            github_headers["X-MCP-Toolsets"] = github_toolsets
        
        # Add optional readonly header
        github_readonly = os.getenv("GITHUB_MCP_SERVER_READONLY")
        if github_readonly:
            github_headers["X-MCP-Readonly"] = github_readonly
        
        mcp_headers["https://api.githubcopilot.com/mcp/"] = github_headers
    
    # Return empty dict if no MCP servers are configured
    if not mcp_headers:
        return {}
    
    # Return headers with MCP configuration
    return {
        "X-LlamaStack-Provider-Data": json.dumps({
            "mcp_headers": mcp_headers
        })
    }


def initialize_client() -> Tuple[LlamaStackClient, str, str, str]:
    """Initialize Llama Stack client and return configuration
    
    Returns:
        Tuple containing:
        - LlamaStackClient instance
        - Model name
        - Vector database ID
        - Llama Stack URL
    """
    # Get logger for initialization
    logger = get_logger("main")
    
    # ALL CONFIGURATION IN ONE PLACE - including environment variable reading
    llama_stack_url = os.getenv("LLAMA_STACK_URL", "http://localhost:8321")

    extra_headers = get_extra_headers_config()
    # Pretty print the extra headers with nested JSON parsing
    if extra_headers and "X-LlamaStack-Provider-Data" in extra_headers:
        try:
            # Parse the nested JSON string
            provider_data = json.loads(extra_headers["X-LlamaStack-Provider-Data"])
            # Create a copy of extra_headers with parsed JSON
            pretty_headers = extra_headers.copy()
            pretty_headers["X-LlamaStack-Provider-Data"] = provider_data
            logger.info(f"Extra headers: {json.dumps(pretty_headers, indent=2)}")
        except json.JSONDecodeError:
            logger.info(f"Extra headers: {json.dumps(extra_headers, indent=2)}")
    else:
        logger.info(f"Extra headers: {json.dumps(extra_headers, indent=2)}")

    # Initialize client
    llama_stack_client = LlamaStackClient(
        base_url=llama_stack_url,
        default_headers=extra_headers
    )

    models = llama_stack_client.models.list()
    first_model = next(m.identifier for m in models if m.model_type == "llm")
    model = os.getenv("DEFAULT_LLM_MODEL", first_model)

    # Log configuration summary
    logger.info(f"Configuration: URL={llama_stack_url}, Model={model}")
    logger.info("✅ Llama Stack client initialized successfully")
    
    return llama_stack_client, model, llama_stack_url


# ============================================================================
# APPLICATION CREATION AND ORCHESTRATION
# ============================================================================

def create_app():
    """Create and return the complete Gradio demo application"""
    # Get logger for main application
    logger = get_logger("main")
    
    logger.info("=" * 60)
    logger.info("STARTING INTELLIGENT CD APP")
    logger.info("=" * 60)
    
    # Initialize Llama Stack client and get configuration
    client, model, llama_stack_url = initialize_client()
    
    # Initialize all tab components
    logger.info("Initializing tab components...")
    chat_tab = ChatTab(client, model=model)
    mcp_test_tab = MCPTestTab(client)
    rag_test_tab = RAGTestTab(client)
    system_status_tab = SystemStatusTab(client, llama_stack_url, model=model)
    form_tab = FormTab(client, model=model)
    
    logger.info("✅ All components initialized successfully")
    
    # Create the Gradio demo with tab instances
    logger.info("Creating Gradio interface...")
    demo = create_demo(chat_tab, mcp_test_tab, rag_test_tab, system_status_tab, form_tab)
    
    logger.info("✅ Gradio interface created successfully")
    return demo


def main():
    """Main function to launch the Intelligent CD Chatbot application"""
    logger = get_logger("main")
    
    # Create the demo application
    demo = create_app()
    
    # Launch the app
    logger.info("🚀Launching Gradio application...")
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=True,
        show_error=True
    )

if __name__ == "__main__":
    main()
