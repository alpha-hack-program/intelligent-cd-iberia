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

# Chat tab configuration
export CHAT_SAMPLING_PARAMS='{"temperature": 0.1, "max_tokens": 300000, "max_new_tokens": 300000, "strategy": {"type": "greedy"} }'
export CHAT_TOOLS='["mcp::openshift", "mcp::github", {"name": "builtin::rag", "args": {"vector_db_names": ["app-documentation"], "top_k": 5}}]'
export CHAT_PROMPT="$(cat ../intelligent-cd-chart/conf/app/chat_prompt.md)"
export CHAT_MAX_INFER_ITERS=30

# Step 1: Generate Resources
export FORM_GENERATE_RESOURCES_SAMPLING_PARAMS='{"temperature": 0.1, "max_tokens": 300000, "max_new_tokens": 300000, "strategy": {"type": "greedy"} }'
export FORM_GENERATE_RESOURCES_TOOLS='["mcp::openshift", {"name": "builtin::rag", "args": {"vector_db_names": ["gitops-documentation"], "top_k": 5}}]'
export FORM_GENERATE_RESOURCES_PROMPT="$(cat ../intelligent-cd-chart/conf/app/form_generate_resources_prompt.md 2>/dev/null || cat ../intelligent-cd-chart/conf/app/form_prompt.md)"

# Step 2: Generate Helm
export FORM_GENERATE_HELM_SAMPLING_PARAMS='{"temperature": 0.1, "max_tokens": 300000, "max_new_tokens": 300000, "strategy": {"type": "greedy"} }'
export FORM_GENERATE_HELM_TOOLS='[{"name": "builtin::rag", "args": {"vector_db_names": ["gitops-documentation"], "top_k": 5}}]'
export FORM_GENERATE_HELM_PROMPT="$(cat ../intelligent-cd-chart/conf/app/form_generate_helm_prompt.md 2>/dev/null || cat ../intelligent-cd-chart/conf/app/form_prompt.md)"

# Step 3: Push GitHub
export FORM_PUSH_GITHUB_SAMPLING_PARAMS='{"temperature": 0.1, "max_tokens": 300000, "max_new_tokens": 300000, "strategy": {"type": "greedy"} }'
export FORM_PUSH_GITHUB_TOOLS='["mcp::github"]'
export FORM_PUSH_GITHUB_PROMPT="$(cat ../intelligent-cd-chart/conf/app/form_push_github_prompt.md 2>/dev/null || cat ../intelligent-cd-chart/conf/app/form_prompt.md)"

# Step 4: Generate ArgoCD
export FORM_GENERATE_ARGOCD_SAMPLING_PARAMS='{"temperature": 0.1, "max_tokens": 300000, "max_new_tokens": 300000, "strategy": {"type": "greedy"} }'
export FORM_GENERATE_ARGOCD_TOOLS='["mcp::openshift", {"name": "builtin::rag", "args": {"vector_db_names": ["gitops-documentation"], "top_k": 5}}]'
export FORM_GENERATE_ARGOCD_PROMPT="$(cat ../intelligent-cd-chart/conf/app/form_generate_argocd_prompt.md 2>/dev/null || cat ../intelligent-cd-chart/conf/app/form_prompt.md)"

# Global form configuration
export FORM_MAX_INFER_ITERS=50

# RAG test tab configuration
export RAG_TEST_TAB_VECTOR_DB_NAME='app-documentation'

# GitHub MCP Server Configuration
export GITHUB_PAT=$GITHUB_PAT
# Options: https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md#remote-mcp-toolsets
export GITHUB_MCP_SERVER_TOOLSETS=$(echo "$GITHUB_MCP_SERVER_TOOLSETS" | sed 's/\\//g')
export GITHUB_MCP_SERVER_READONLY=$GITHUB_MCP_SERVER_READONLY

export GITHUB_GITOPS_REPO=$GITHUB_GITOPS_REPO
LOG_LEVEL='DEBUG' gradio main.py