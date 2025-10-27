# 🚀 Intelligent CD Web UI

A simple web interface to access Llama Stack for LLM and Agent interactions with OpenShift.

## Features

- **💬 Chat Interface**: Chat with AI assistant using Llama Stack LLM
- **🧪 MCP Testing**: Test and execute MCP tools through Llama Stack
- **🔍 System Status**: Monitor Llama Stack connectivity and health
- **☸️ OpenShift Integration**: Access Kubernetes/OpenShift resources via MCP


## Directory Structure

```
intelligent-cd-app/
├── main.py                     # 🎯 EVERYTHING HERE - The Standard Python Way
├── tabs/                       # Tab classes only
│   ├── __init__.py
│   ├── chat_tab.py            # ChatTab class
│   ├── mcp_test_tab.py        # MCPTestTab class
│   ├── rag_test_tab.py        # RAGTestTab class
│   └── system_status_tab.py   # SystemStatusTab class
└── gradio_app/                # Gradio interface only
    ├── __init__.py
    └── interface.py           # Gradio UI creation
```

## Prerequisites

- Python 3.11+
- Podman (optional)
- Llama Stack deployment running
- Port forwarding: `oc port-forward service/llama-stack-service 8321:8321 -n intelligent-cd`

## Quick Start

### Run Locally

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   gradio main.py
   ```

3. **Access the UI:**
   Open http://localhost:7860/?__theme=light



```bash
cd intelligent-cd-app
./run-local.sh
```

### Run with Podman

1. **Build the image:**
   ```bash
   podman build -t quay.io/alopezme/intelligent-cd-gradio:latest intelligent-cd-app
   ```

2. **Run the container:**
   ```bash
   podman run --network host quay.io/alopezme/intelligent-cd-gradio:latest
   ```

3. **Access the UI:**
   Open http://localhost:7860/?__theme=light

## Configuration

Set environment variables (optional):
```bash
LLAMA_STACK_URL=http://localhost:8321  # Default
DEFAULT_LLM_MODEL=llama-3-2-3b  # Default
```

## Usage

1. **Chat Tab**: Ask questions about Kubernetes, GitOps, or OpenShift
2. **MCP Test Tab**: Test and execute MCP tools for OpenShift operations
3. **System Status Tab**: Check Llama Stack connectivity and health

## Troubleshooting

- **Connection failed**: Ensure Llama Stack is running and port forwarding is active
- **MCP tools not found**: Verify MCP server is properly configured in Llama Stack
- **LLM errors**: Check if the specified model is available in your Llama Stack deployment
