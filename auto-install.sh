#!/bin/bash
set -e

echo "🚀 Starting Intelligent CD deployment..."

#####################################
# Step 1: Retrieve environment variables
#####################################

echo -e "\n📋 Step 1: Setting up environment variables..."

if [ -f .env ]; then
  source .env
else
  echo "❌ .env file not found! Please create and define required environment variables in a .env file before running this script."
  exit 1
fi

echo "✅ Environment variables configured"

#####################################
# Step 2: Calculate variables
#####################################

echo -e "\n🔐 Step 2: Retrieving ArgoCD API token..."

ARGOCD_BASE_URL=$(oc get route openshift-gitops-server -n openshift-gitops --template='https://{{ .spec.host }}')
ARGOCD_ADMIN_USERNAME=admin
ARGOCD_ADMIN_PASSWORD=$(oc get secret openshift-gitops-cluster -n openshift-gitops --template='{{index .data "admin.password"}}' | base64 -d)
ARGOCD_API_TOKEN=$(curl -k -s $ARGOCD_BASE_URL/api/v1/session \
  -H 'Content-Type:application/json' \
  -d '{"username":"'"$ARGOCD_ADMIN_USERNAME"'","password":"'"$ARGOCD_ADMIN_PASSWORD"'"}' | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')

echo "✅ ArgoCD API token retrieved successfully"

#####################################
# Step 3: Print environment variables
#####################################

echo -e "\n📊 Step 3: Environment Variables Summary:"
echo ""
echo "🤖 OLS Configuration:"
echo "  Model: $MODEL_NAME"
echo "  URL: $MODEL_API_URL"
echo "  Token: ${MODEL_API_TOKEN:0:10}..."
echo ""
echo "🚀 ArgoCD Configuration:"
echo "  Base URL: $ARGOCD_BASE_URL"
echo "  Username: $ARGOCD_ADMIN_USERNAME"
echo "  Password: ${ARGOCD_ADMIN_PASSWORD:0:10}..."
echo "  API Token: ${ARGOCD_API_TOKEN:0:10}..."
echo ""
echo "🔧 ServiceNow MCP Server Configuration:"
echo "  Instance URL: $SERVICENOW_INSTANCE_URL"
echo "  Auth Type: $SERVICENOW_AUTH_TYPE"
echo "  Username: $SERVICENOW_USERNAME"
echo "  Password: ${SERVICENOW_PASSWORD:0:3}..."
echo "  Tool Package: ${SERVICENOW_MCP_TOOL_PACKAGE}"
echo ""
echo "🔧 GitHub MCP Server Configuration:"
echo "  Auth Token: ${GITHUB_MCP_SERVER_AUTH_TOKEN:0:10}..."
echo "  Toolsets: $GITHUB_MCP_SERVER_TOOLSETS"
echo "  Readonly: $GITHUB_MCP_SERVER_READONLY"
echo ""
echo " Web Search using Tavily"
echo "🔧 Tavily API Token: $TAVILY_SEARCH_API_KEY"
echo ""

#####################################
# Step 4: Create the MinIO storage
#####################################

echo -e "\n📡 Step 4: Creating MinIO storage..."
cat minio.yaml | \
  CLUSTER_DOMAIN=$(oc get dns.config/cluster -o jsonpath='{.spec.baseDomain}') \
  envsubst | oc apply -f -
sleep 5

echo "Waiting for MinIO pods to be ready..."

while [[ $(oc get pods -l app=minio -n minio -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}') != "True" ]]; do 
    echo -n "⏳" && sleep 1
done

echo "✅ MinIO pods are ready!"


#####################################
# Step 5: Create the Distributed Tracing Deployment
#####################################

echo -e "\n📡 Step 5: Configuring Distributed Tracing Stack..."
oc apply -f ocp-dist-tracing-operators.yaml

# 1. Wait for OpenTelemetry Operator
echo -n "⏳ Waiting for OpenTelemetry Operator to be ready..."
while [[ $(oc get csv -n openshift-opentelemetry-operator -l operators.coreos.com/opentelemetry-product.openshift-opentelemetry-operator -o 'jsonpath={..status.phase}' 2>/dev/null) != "Succeeded" ]]; do
    echo -n "⏳" && sleep 3
done
echo -e " [OK]"

# 2. Wait for Cluster Observability Operator
echo -n "⏳ Waiting for Cluster Observability Operator to be ready..."
while [[ $(oc get csv -n openshift-operators -l operators.coreos.com/cluster-observability-operator.openshift-operators -o 'jsonpath={..status.phase}' 2>/dev/null) != "Succeeded" ]]; do
    echo -n "⏳" && sleep 3
done
echo -e " [OK]"

# 3. Wait for Tempo Operator
echo -n "⏳ Waiting for Tempo Operator to be ready..."
while [[ $(oc get csv -n openshift-tempo-operator -l operators.coreos.com/tempo-product.openshift-tempo-operator -o 'jsonpath={..status.phase}' 2>/dev/null) != "Succeeded" ]]; do
    echo -n "⏳" && sleep 3
done
echo -e " [OK]"

echo "✅ Operators deployed successfully!"

echo "Configuring operators..."


oc apply -f ocp-dist-tracing-config.yaml


echo "✅ Distributed Tracing Stack configured successfully!"

#####################################
# Step 6: Apply the Helm Chart
#####################################

echo -e "\n🚀 Step 6: Deploying Intelligent CD application..."

# Option 1: Helm template
helm template intelligent-cd-chart \
--set inference.model="$MODEL_NAME" \
--set inference.url="$MODEL_API_URL" \
--set inference.apiToken="$MODEL_API_TOKEN" \
--set gradioUI.config.argocd.base_url="$ARGOCD_BASE_URL" \
--set gradioUI.config.argocd.api_token="$ARGOCD_API_TOKEN" \
--set gradioUI.config.github.auth_token="$GITHUB_MCP_SERVER_AUTH_TOKEN" \
--set gradioUI.config.github.toolsets='$GITHUB_MCP_SERVER_TOOLSETS' \
--set gradioUI.config.github.readonly="$GITHUB_MCP_SERVER_READONLY" \
--set mcpServers.servicenowMcp.env.SERVICENOW_INSTANCE_URL="$SERVICENOW_INSTANCE_URL" \
--set mcpServers.servicenowMcp.env.SERVICENOW_AUTH_TYPE="$SERVICENOW_AUTH_TYPE" \
--set mcpServers.servicenowMcp.env.SERVICENOW_USERNAME="$SERVICENOW_USERNAME" \
--set mcpServers.servicenowMcp.env.SERVICENOW_PASSWORD="$SERVICENOW_PASSWORD" \
--set mcpServers.servicenowMcp.env.MCP_TOOL_PACKAGE="$SERVICENOW_MCP_TOOL_PACKAGE" \
--set llamaStack.websearch.tavilyApiKey="$TAVILY_SEARCH_API_KEY" \
--set RAG.git_token="$GITLAB_PAT" \
| oc apply -f -

# # Option 2: ArgoCD Application
# cat application-intelligent-cd.yaml | \
#   CLUSTER_DOMAIN=$(oc get dns.config/cluster -o jsonpath='{.spec.baseDomain}') \
#   LLS_ENDPOINT="http://llama-stack-service.intelligent-cd.svc.cluster.local:8321" \
#   MODEL_NAME="$MODEL_NAME" \
#   MODEL_API_URL="$MODEL_API_URL" \
#   MODEL_API_TOKEN="$MODEL_API_TOKEN" \
#   ARGOCD_BASE_URL="$ARGOCD_BASE_URL" \
#   ARGOCD_API_TOKEN="$ARGOCD_API_TOKEN" \
#   GITHUB_MCP_SERVER_AUTH_TOKEN="$GITHUB_MCP_SERVER_AUTH_TOKEN" \
#   GITHUB_MCP_SERVER_TOOLSETS="$GITHUB_MCP_SERVER_TOOLSETS" \
#   GITHUB_MCP_SERVER_READONLY="$GITHUB_MCP_SERVER_READONLY" \
#   SERVICENOW_INSTANCE_URL="$SERVICENOW_INSTANCE_URL" \
#   SERVICENOW_AUTH_TYPE="$SERVICENOW_AUTH_TYPE" \
#   SERVICENOW_USERNAME="$SERVICENOW_USERNAME" \
#   SERVICENOW_PASSWORD="$SERVICENOW_PASSWORD" \
#   SERVICENOW_MCP_TOOL_PACKAGE="$SERVICENOW_MCP_TOOL_PACKAGE" \
#   TAVILY_SEARCH_API_KEY="$TAVILY_SEARCH_API_KEY" \
#   GITLAB_PAT="$GITLAB_PAT" \
#   envsubst | oc apply -f -

echo "✅ Helm template applied successfully"


#####################################
# Step 7: Wait for pods to be ready
#####################################

echo -e "\n⏳ Step 7: Waiting for Intelligent CD pods to be ready..."

while [[ $(oc get pods -l app=llama-stack -n intelligent-cd -o 'jsonpath={..status.conditions[?(@.type=="Ready")].status}') != "True" ]]; do 
    echo -n "⏳" && sleep 1
done

echo "✅ All pods are ready!"


#####################################
# Step 8: Deploy the LLS Playground
#####################################

echo -e "\n🗄️ Step 8: Deploying the LLS Playground..."

cat lls-playground.yaml | \
  CLUSTER_DOMAIN=$(oc get dns.config/cluster -o jsonpath='{.spec.baseDomain}') \
  LLS_ENDPOINT="http://llama-stack-service.intelligent-cd.svc.cluster.local:8321" \
  envsubst | oc apply -f -

#####################################
# Step 9: Wait for route to be created
#####################################

echo -e "\n⏳ Step 9: Waiting for ds-pipeline-dspa route to be created..."

# Wait for the route to be created
while ! oc get route ds-pipeline-dspa -n intelligent-cd-pipelines &>/dev/null; do 
    echo -n "⏳" && sleep 1
done

# Wait for the route to have a host
until [[ $(oc get route ds-pipeline-dspa -n intelligent-cd-pipelines -o jsonpath='{.spec.host}' 2>/dev/null) ]]; do
    echo -n "⏳" && sleep 1
done

echo "✅ ds-pipeline-dspa route is ready!"

#####################################
# Step 10: Run the pipeline
#####################################

echo -e "\n🗄️ Step 10: Populating the vector database..."

export KUBEFLOW_ENDPOINT=$(oc get route ds-pipeline-dspa -n intelligent-cd-pipelines --template="https://{{.spec.host}}")
export BEARER_TOKEN=$(oc whoami --show-token)
python intelligent-cd-pipelines/ingest-pipeline.py

#####################################
# Step 11: Deploy Discounts App
#####################################

echo -e "\n🛍️ Step 11: Deploying Discounts Application..."

# Create the discounts namespace if it doesn't exist
oc create namespace discounts --dry-run=client -o yaml | oc apply -f -

# Deploy the discounts app
oc apply -f components/discounts-app/discounts-app.yaml

echo "✅ Discounts application deployed successfully!"

echo -e "\n🎉 Installation Complete!"
echo "✨ Intelligent CD has been successfully deployed and configured!"