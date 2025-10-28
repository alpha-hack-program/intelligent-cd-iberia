#!/bin/bash

set -e

ARGOCD_BASE_URL=$(oc get route openshift-gitops-server -n openshift-gitops --template='https://{{ .spec.host }}')
ARGOCD_ADMIN_USERNAME=admin
ARGOCD_ADMIN_PASSWORD=$(oc get secret openshift-gitops-cluster -n openshift-gitops --template='{{index .data "admin.password"}}' | base64 -d)
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

export CHAT_SAMPLING_PARAMS='{"temperature": 0.1, "max_tokens": 80000, "max_new_tokens": 80000, "strategy": {"type": "greedy"} }'
export CHAT_TOOLS='["mcp::servicenow", "mcp::argocd", "mcp::openshift", {"name": "builtin::rag", "args": {"vector_db_names": ["app-documentation"], "top_k": 5}}]'
export CHAT_PROMPT="$(cat ../intelligent-cd-chart/conf/app/chat_prompt.md)"

export FORM_SAMPLING_PARAMS='{"temperature": 0.1, "max_tokens": 300000, "max_new_tokens": 300000, "strategy": {"type": "greedy"} }'
export FORM_TOOLS='["mcp::openshift", {"name": "builtin::rag", "args": {"vector_db_names": ["gitops-documentation"], "top_k": 5}}]'
export FORM_PROMPT="$(cat ../intelligent-cd-chart/conf/app/form_prompt.md)"

export RAG_TEST_TAB_VECTOR_DB_NAME='app-documentation'

export FORM_MAX_INFER_ITERS=100
export CHAT_MAX_INFER_ITERS=15

LOG_LEVEL='DEBUG' gradio main.py