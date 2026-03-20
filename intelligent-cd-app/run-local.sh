#!/bin/bash

set -e

source ../.env

# Detect ArgoCD route name (try both possible names)
ARGOCD_ROUTE_NAME=""
ARGOCD_NAMESPACE="openshift-gitops"

if oc get route argocd-server -n $ARGOCD_NAMESPACE &>/dev/null; then
  ARGOCD_ROUTE_NAME="argocd-server"
elif oc get route openshift-gitops-server -n $ARGOCD_NAMESPACE &>/dev/null; then
  ARGOCD_ROUTE_NAME="openshift-gitops-server"
else
  echo "❌ Error: Could not find ArgoCD route. Tried 'argocd-server' and 'openshift-gitops-server' in namespace $ARGOCD_NAMESPACE"
  exit 1
fi

ARGOCD_BASE_URL=$(oc get route $ARGOCD_ROUTE_NAME -n $ARGOCD_NAMESPACE --template='https://{{ .spec.host }}')
echo "ARGOCD_BASE_URL: $ARGOCD_BASE_URL"
ARGOCD_ADMIN_USERNAME=admin

if oc get secret argocd-cluster -n $ARGOCD_NAMESPACE &>/dev/null; then
  ARGOCD_SECRET_NAME="argocd-cluster"
elif oc get secret openshift-gitops-cluster -n $ARGOCD_NAMESPACE &>/dev/null; then
  ARGOCD_SECRET_NAME="openshift-gitops-cluster"
else
  echo "❌ Error: Could not find ArgoCD secret. Tried 'argocd-cluster' and 'openshift-gitops-cluster' in namespace $ARGOCD_NAMESPACE"
  exit 1
fi

ARGOCD_ADMIN_PASSWORD=$(oc get secret $ARGOCD_SECRET_NAME -n $ARGOCD_NAMESPACE --template='{{index .data "admin.password"}}' | base64 -d)
echo "ARGOCD_ADMIN_PASSWORD: $ARGOCD_ADMIN_PASSWORD"
ARGOCD_API_TOKEN=$(curl -k -s $ARGOCD_BASE_URL/api/v1/session \
  -H 'Content-Type:application/json' \
  -d '{"username":"'"$ARGOCD_ADMIN_USERNAME"'","password":"'"$ARGOCD_ADMIN_PASSWORD"'"}' | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')

# # Test if the params are working directly to the ArgoCD API
# curl -sk $ARGOCD_BASE_URL/api/v1/applications -H "Authorization: Bearer $ARGOCD_API_TOKEN" | jq '.items[].metadata.name' 

echo "Print variables:"
echo "ARGOCD_BASE_URL: $ARGOCD_BASE_URL"
echo "ARGOCD_ADMIN_USERNAME: $ARGOCD_ADMIN_USERNAME"
echo "ARGOCD_ADMIN_PASSWORD: ${ARGOCD_ADMIN_PASSWORD:0:10}..."
echo "ARGOCD_API_TOKEN: ${ARGOCD_API_TOKEN:0:10}..."

export ARGOCD_BASE_URL=$ARGOCD_BASE_URL
export ARGOCD_API_TOKEN=$ARGOCD_API_TOKEN

export LLAMA_STACK_URL=${LLAMA_STACK_URL:-http://localhost:8321}
export DEFAULT_LLM_MODEL=${DEFAULT_LLM_MODEL:-vllm-inference/llama-4-scout-17b-16e-w4a16}
echo "LLAMA_STACK_URL: $LLAMA_STACK_URL"
echo "DEFAULT_LLM_MODEL: $DEFAULT_LLM_MODEL"

# Shared LLM settings
export TEMPERATURE=0.1
export MAX_INFER_ITERS=30

# Chat tab
#export CHAT_TOOLS='[{"type":"mcp","server_label":"openshift","server_url":"http://ocp-mcp-server.intelligent-cd.svc.cluster.local:8080/sse"},{"type":"mcp","server_label":"argocd","server_url":"http://mcp-for-argocd.intelligent-cd.svc.cluster.local:3000/sse"},{"type":"mcp","server_label":"github","server_url":"https://api.githubcopilot.com/mcp/"},{"type":"file_search","vector_db_names":["app-documentation"]}]'
export CHAT_TOOLS='[{"type":"mcp","server_label":"openshift","server_url":"http://ocp-mcp-server.intelligent-cd.svc.cluster.local:8080/sse"},{"type":"mcp","server_label":"argocd","server_url":"http://mcp-for-argocd.intelligent-cd.svc.cluster.local:3000/sse"},{"type":"file_search","vector_db_names":["app-documentation"]}]'
export CHAT_PROMPT="$(cat ../intelligent-cd-chart/conf/app/chat_prompt.md)"

# Form tab - Step 1: Generate Resources (fetch done via oc, no LLM tools needed)
export FORM_GENERATE_RESOURCES_TOOLS='[]'
export FORM_GENERATE_RESOURCES_PROMPT=""

# Form tab - Step 1b: Apply Best Practices (LLM + RAG only, no MCP)
export FORM_APPLY_BEST_PRACTICES_TOOLS='[{"type": "file_search", "vector_db_names": ["gitops-documentation"]}]'
export FORM_APPLY_BEST_PRACTICES_PROMPT="$(cat ../intelligent-cd-chart/conf/app/form_apply_best_practices_prompt.md)"

# Form tab - Step 2: Generate Helm
export FORM_GENERATE_HELM_TOOLS='[{"type": "file_search", "vector_db_names": ["gitops-documentation"]}]'
export FORM_GENERATE_HELM_PROMPT="$(cat ../intelligent-cd-chart/conf/app/form_generate_helm_prompt.md 2>/dev/null || cat ../intelligent-cd-chart/conf/app/form_prompt.md)"

# Form tab - Step 3: Push GitHub
# Currently uses PyGithub directly (no LLM/MCP needed).
# [MCP-GITHUB-ALTERNATIVE] Uncomment the lines below if the Llama Stack server
# is upgraded to support Streamable HTTP transport for MCP tools, then remove
# the PyGithub implementation in form_tab.py push_github().
#export FORM_PUSH_GITHUB_TOOLS='[{"type": "mcp", "server_label": "github", "server_url": "https://api.githubcopilot.com/mcp/"}]'
#export FORM_PUSH_GITHUB_PROMPT="$(cat ../intelligent-cd-chart/conf/app/form_push_github_prompt.md 2>/dev/null || cat ../intelligent-cd-chart/conf/app/form_prompt.md)"
export FORM_PUSH_GITHUB_TOOLS='[]'
export FORM_PUSH_GITHUB_PROMPT=""

# Form tab - Step 4: Generate ArgoCD (uses Python template + PyGithub, no LLM/MCP needed)
# [ARGOCD-LLM-ALTERNATIVE] Uncomment the lines below to use LLM+MCP instead
# of the Python template in form_tab.py generate_argocd_app().
#export FORM_GENERATE_ARGOCD_TOOLS='[{"type": "mcp", "server_label": "openshift", "server_url": "http://ocp-mcp-server.intelligent-cd.svc.cluster.local:8080/sse"}, {"type": "mcp", "server_label": "argocd", "server_url": "http://mcp-for-argocd.intelligent-cd.svc.cluster.local:3000/sse"}, {"type": "file_search", "vector_db_names": ["gitops-documentation"]}]'
#export FORM_GENERATE_ARGOCD_PROMPT="$(cat ../intelligent-cd-chart/conf/app/form_generate_argocd_prompt.md 2>/dev/null || cat ../intelligent-cd-chart/conf/app/form_prompt.md)"
export FORM_GENERATE_ARGOCD_TOOLS='[]'
export FORM_GENERATE_ARGOCD_PROMPT=""

# Form tab - Validate Deployment (LLM + MCP OpenShift for intelligent health checks)
export FORM_VALIDATE_DEPLOYMENT_TOOLS='[{"type":"mcp","server_label":"openshift","server_url":"http://ocp-mcp-server.intelligent-cd.svc.cluster.local:8080/sse"}]'
export FORM_VALIDATE_DEPLOYMENT_PROMPT="You are a Kubernetes deployment validator. Use the MCP tools to check pod health, events, and logs. Diagnose any issues you find."

# Form tab - Validate ArgoCD (LLM + MCP OpenShift + ArgoCD for full gitops health validation)
export FORM_VALIDATE_ARGOCD_TOOLS='[{"type":"mcp","server_label":"openshift","server_url":"http://ocp-mcp-server.intelligent-cd.svc.cluster.local:8080/sse"},{"type":"mcp","server_label":"argocd","server_url":"http://mcp-for-argocd.intelligent-cd.svc.cluster.local:3000/sse"}]'
export FORM_VALIDATE_ARGOCD_PROMPT="You are a GitOps deployment validator. Use both the ArgoCD and OpenShift MCP tools to verify the deployment is healthy."

# RAG test tab configuration
export RAG_TEST_TAB_VECTOR_DB_NAME='app-documentation'

# GitHub MCP Server Configuration
export GITHUB_PAT=$GITHUB_PAT
# Options: https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md#remote-mcp-toolsets
export GITHUB_MCP_SERVER_TOOLSETS=$(echo "$GITHUB_MCP_SERVER_TOOLSETS" | sed 's/\\//g')
export GITHUB_MCP_SERVER_READONLY=$GITHUB_MCP_SERVER_READONLY

export GITHUB_GITOPS_REPO=$GITHUB_GITOPS_REPO
LOG_LEVEL='DEBUG' python main.py