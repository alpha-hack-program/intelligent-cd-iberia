#!/usr/bin/env python3
"""
Llama Stack Agent Chatbot - Simplified Version
"""

import os
import ssl
import httpx
import logging
from dotenv import load_dotenv
from llama_stack_client import LlamaStackClient, RAGDocument
from llama_stack_client.lib.agents.react.agent import ReActAgent
from llama_stack_client.lib.agents.react.tool_parser import ReActOutput

# Suppress httpx INFO logs
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv()

class LlamaStackChatbot:
    def __init__(self):
        import time
        self.base_url = os.getenv("REMOTE_BASE_URL", "http://localhost:8321")
        self.model_id = os.getenv("INFERENCE_MODEL_ID", "granite32-8b")
        self.session_id = None
        self.vector_db_id = "my_documents"  # Dynamic ID to ensure fresh documents
        self.rag_loaded = False  # Track RAG loading status
        
        # Basic sampling parameters
        self.sampling_params = {
            "temperature": 0.1, 
            "max_tokens": 300000, 
            "max_new_tokens": 300000, 
            "strategy": {"type": "greedy"}
        }
        
        # Agent configuration to handle complex multi-resource queries
        self.agent_config = {
            "max_infer_iters": 100,  # Increase max iterations for complex queries
            "enable_session_persistence": True
        }
        
        # Setup client with SSL and auth
        self._setup_client()
        
        # Verify and register MCP toolgroups
        self._verify_mcp_tools()
        
        # Delete existing RAG chunks before loading new ones
        self._delete_existing_rag_chunks()
        
        # Load Kubernetes best practices documentation into RAG
        self.load_kubernetes_best_practices_documents()
        
        # Setup agent with all available tools
        # Configure RAG tool with vector DB IDs
        available_tools = [
            "mcp::openshift",
            {
                "name": "builtin::rag",
                "args": {
                    "vector_db_ids": [self.vector_db_id],
                    "top_k": 5
                }
            }
        ]
        
        instructions = """
You are an expert OpenShift/Kubernetes assistant specialized in managing application resources. You focus specifically on four core resource types: Deployment, ConfigMap, Service, and Route.

**Your Primary Mission:**
Focus exclusively on retrieving and managing these resource types in the specified namespace:
- Deployments: Application workload definitions
- ConfigMaps: Configuration data storage
- Services: Network service definitions  
- Routes: External access configuration (OpenShift-specific)

**Available MCP Operations (ONLY use these two):**
- resources_list: List resources of a specific type in the target namespace
- resources_get: Get detailed YAML configuration of specific resources

**ReAct Reasoning Framework:**

1. **REASON:** Before taking any action, clearly think through:
   - Which of the 4 target resource types (deployment, configmap, service, route) does the user need?
   - Do I need to list resources first or get a specific resource directly?
   - What namespace did the user specify in their query? Extract and use that namespace
   - ALWAYS use knowledge_search to get YAML cleaning best practices from BOTH "namespace-resources-best-practices" AND "deployment-configuration-best-practices" documents

2. **ACT:** Execute your reasoning using ONLY the allowed MCP operations:
   - Use mcp::openshift resources_list to list deployments, configmaps, services, or routes in the target namespace
   - Use mcp::openshift resources_get to retrieve specific resource YAML configurations
   - MANDATORY: Use builtin::rag to search BOTH documents: "namespace-resources-best-practices" AND "deployment-configuration-best-practices"

3. **OBSERVE:** Analyze the results from your actions and determine:
   - Did I get the resource information I need?
   - Are there any configuration issues or improvements needed?
   - What cleanup or optimization can be applied based on best practices?

4. **REASON AGAIN:** Based on observations, determine next steps:
   - If user requests multiple resource types, you MUST process ALL of them before providing final answer
   - CRITICAL: When you get a deployment YAML, immediately scan for ConfigMap references in envFrom/configMapRef and ALWAYS retrieve those ConfigMaps
   - CRITICAL: When you get a deployment YAML, immediately scan for Service references with the same selector labels and ALWAYS retrieve those ConfigMaps
   - MANDATORY: Health checks (liveness, readiness) - MUST BE ADDED IF MISSING BASE ON RAG DOCUMENT
   - MANDATORY: Resource requests and limits - MUST BE ADDED IF MISSING BASE ON RAG DOCUMENT
   - MANDATORY: delete the namespace from the YAML
   - Apply YAML cleaning best practices to remove cluster-specific metadata, unwanted annotations, and status sections
   - Remove kubectl.kubernetes.io/last-applied-configuration and argocd.argoproj.io/* annotations
   - Remove entire status section from all resources
   - For Deployments: 
     * *MANDATORY*: Preserve spec.template.metadata.labels (critical for pod selection by the service)
     * *MANDATORY*: Preserve spec.selector.matchLabels (critical for pod selection by the service)
   - For Services: 
     * ALWAYS include Services referenced by deployment labels in the final answer
     * MANDATORY: Remove clusterIP, clusterIPs (cluster-specific, auto-assigned)
   - For Routes: 
     * MANDATORY: Remove spec.host (cluster-specific, auto-generated by OpenShift)
     * ALWAYS include Routes referenced by service name in the final answer
     * Remove spec.host (cluster-specific, auto-generated by OpenShift)
   - Format final answer as standard Kubernetes YAML with '---' separators between resources
   - ALWAYS include ConfigMaps referenced by deployments in the final answer
   - **MANDATORY FINAL STEP**: Before providing the final answer, validate and correct the YAML:
     * Remove quotes from resource values (memory: 256Mi not memory: "256Mi")
     * Remove quotes from port numbers (port: 8080 not port: "8080")
     * Ensure proper YAML syntax and Kubernetes resource format
     * Validate that all required fields are present
   - Only provide final answer after processing ALL requested resource types AND their referenced ConfigMaps AND validating the YAML

**Resource-Specific Focus Areas:**

DEPLOYMENTS:
- *MANDATORY*: Container specifications and resource requirements can not be changed and keep as is
- *MANDATORY*: Health checks (liveness, readiness) - MUST BE ADDED IF MISSING BASE ON RAG DOCUMENT
- *MANDATORY*: Resource requests and limits - MUST BE ADDED IF MISSING BASE ON RAG DOCUMENT



CONFIGMAPS:
- Configuration data organization
- Proper key-value structure
- Integration with deployments via environment variables or volume mounts

SERVICES:
- Service type selection (ClusterIP, NodePort, LoadBalancer)
- Port configurations and target port mappings
- *MANDATORY*: Selector labels matching deployment pods

ROUTES (OpenShift-specific):
- External hostname configuration
- TLS/SSL termination settings
- Backend service connections
- Path-based routing rules

**CRITICAL OPERATIONAL CONSTRAINTS:**
- ALWAYS extract and use the namespace specified by the user in their query
- ONLY use resources_list and resources_get MCP operations
- NEVER use other MCP operations like logs, exec, delete, create, etc.
- Focus exclusively on the 4 target resource types: deployment, configmap, service, route

**MULTI-RESOURCE PROCESSING REQUIREMENTS:**
When user requests multiple resource types (e.g., "deployments, services, routes, configmaps"):
1. **MANDATORY**: Process ALL requested resource types - never skip any
2. **Systematic approach**: List each resource type, then get YAML for found resources
3. **ConfigMap intelligence**: When processing deployments, automatically identify and retrieve ConfigMaps referenced in envFrom/configMapRef
4. **Complete processing**: Get YAML for all deployments, services, routes found
5. **Focus on application resources**: For ConfigMaps, prioritize app-specific ones over system ones
6. **Final answer only after ALL types processed**: Never provide partial results

**CORRECT ACTION FORMAT:**
When using tools, use this exact format:
{
  "thought": "Your reasoning about which resource type and operation is needed. If processing multiple types, indicate which type you're currently working on and which ones remain.",
  "action": {
    "tool_name": "resources_list" or "resources_get",
    "tool_params": [
      {
        "name": "apiVersion",
        "value": "apps/v1" (for Deployment) or "v1" (for Service/ConfigMap) or "route.openshift.io/v1" (for Route)
      },
      {
        "name": "kind", 
        "value": "Deployment" or "Service" or "ConfigMap" or "Route"
      },
      {
        "name": "namespace",
        "value": "namespace-from-user-query"
      },
      {
        "name": "name",
        "value": "specific-resource-name" (only for resources_get)
      }
    ]
  },
  "answer": null
}

For RAG knowledge search (MANDATORY - search BOTH documents):
{
  "thought": "I need to get best practices for YAML cleaning and deployment configuration",
  "action": {
    "tool_name": "knowledge_search",
    "tool_params": [
      {
        "name": "query",
        "value": "namespace-resources-best-practices deployment-configuration-best-practices"
      }
    ]
  },
  "answer": null
}

**FINAL ANSWER FORMAT:**
When providing final results (ONLY after ALL requested resources have been processed AND YAML validated):
{
  "thought": "Summary of what was accomplished with ALL the target resources that were requested. CRITICAL: I have removed spec.host from Routes and clusterIP/clusterIPs from Services in the cleaned YAMLs. MANDATORY: I have validated and corrected the YAML format, ensuring resource values like memory and CPU are not quoted, and port numbers are numeric.",
  "action": null,
  "answer": "Provide cleaned and VALIDATED YAMLs in standard Kubernetes format with '---' separators between each resource, ready for 'oc apply -f' command. MANDATORY: Routes must NOT have spec.host field. Services must NOT have clusterIP or clusterIPs fields. Resource values (memory, CPU) and port numbers must NOT be quoted."
}

"""   
        self.agent = ReActAgent(
            client=self.client,
            model=self.model_id,
            instructions=instructions,
            tools=available_tools,
            tool_config={"tool_choice": "auto"},  # Ensure tools are actually executed
            response_format={
                "type": "json_schema",
                "json_schema": ReActOutput.model_json_schema(),
            },
            sampling_params=self.sampling_params,
            max_infer_iters=self.agent_config["max_infer_iters"]  # Pass max iterations config
        )
    
    def _setup_client(self):
        """Setup client with essential SSL and auth configuration"""
        # Get essential config
        skip_ssl_verify = os.getenv("SKIP_SSL_VERIFY", "False").lower() == "true"
        timeout = int(os.getenv("LLAMA_STACK_TIMEOUT", "30"))
        
        # Prepare client config
        client_kwargs = {
            "base_url": self.base_url,
            "timeout": timeout
        }
        
        # Handle SSL if needed
        if skip_ssl_verify:
            http_client = httpx.Client(verify=False, timeout=timeout)
            client_kwargs["http_client"] = http_client
      
        
        self.client = LlamaStackClient(**client_kwargs)
    
    def _verify_mcp_tools(self):
        """Verify that MCP toolgroups are registered and working"""
        print("🔍 Verifying MCP toolgroups...")
        
        try:
            # List registered toolgroups
            registered_toolgroups = {tg.identifier for tg in self.client.toolgroups.list()}
            print(f"🔗 Registered toolgroups: {registered_toolgroups}")
            
            # List MCP OpenShift tools specifically (avoid general tools.list() due to TaskGroup issues)
            try:
                openshift_tools = self.client.tools.list(toolgroup_id="mcp::openshift")
                print(f"🛠️  OpenShift MCP tools available: {len(openshift_tools)}")
            except Exception as e:
                print(f"❌ Error listing MCP tools: {e}")
                openshift_tools = []
            
            # Also try to list RAG tools
            try:
                rag_tools = self.client.tools.list(toolgroup_id="builtin::rag")
                print(f"📚 RAG tools available: {len(rag_tools)}")
            except Exception as e:
                print(f"❌ Error listing RAG tools: {e}")
                rag_tools = []
            
            if openshift_tools:
                print(f"✅ OpenShift MCP tools found: {len(openshift_tools)}")
                for tool in openshift_tools:
                    print(f"   - {tool.identifier}")
            else:
                print(f"❌ No OpenShift MCP tools found!")
                print(f"🔧 Available toolgroups: {registered_toolgroups}")
                
        except Exception as e:
            print(f"❌ Error verifying MCP tools: {e}")
            print(f"🔧 This could indicate MCP server connection issues")
    
    def _delete_existing_rag_chunks(self):
        """Delete existing RAG chunks from the vector database"""
        print(f"🗑️  Deleting existing RAG chunks from vector database: {self.vector_db_id}")
        
        try:
            # Try to get the vector database to check if it exists
            try:
                db_info = self.client.vector_dbs.retrieve(vector_db_id=self.vector_db_id)
                print(f"📋 Found existing vector database: {self.vector_db_id}")
                
                # Try to delete the entire vector database
                try:
                    if hasattr(self.client.vector_dbs, 'unregister'):
                        self.client.vector_dbs.unregister(vector_db_id=self.vector_db_id)
                        print(f"✅ Vector database '{self.vector_db_id}' deleted successfully")
                    elif hasattr(self.client.vector_dbs, 'delete'):
                        self.client.vector_dbs.delete(vector_db_id=self.vector_db_id)
                        print(f"✅ Vector database '{self.vector_db_id}' deleted successfully")
                    else:
                        print(f"⚠️  No delete method found, trying to clear content...")
                        self._clear_vector_database_content()
                        
                except Exception as delete_e:
                    print(f"⚠️  Could not delete vector database, trying to clear content: {delete_e}")
                    self._clear_vector_database_content()
                    
            except Exception as retrieve_e:
                print(f"📋 Vector database '{self.vector_db_id}' does not exist yet: {retrieve_e}")
                # Database doesn't exist, nothing to delete
                
        except Exception as e:
            print(f"❌ Error during RAG chunk deletion: {e}")
            print(f"🔄 Continuing with fresh vector database creation...")
    
    def _clear_vector_database_content(self):
        """Try to clear the content of the vector database without deleting it"""
        try:
            if hasattr(self.client, 'tool_runtime') and hasattr(self.client.tool_runtime, 'rag_tool'):
                rag_tool = self.client.tool_runtime.rag_tool
                
                # Try different methods to clear content
                if hasattr(rag_tool, 'clear'):
                    rag_tool.clear(vector_db_id=self.vector_db_id)
                    print(f"✅ Vector database content cleared successfully")
                elif hasattr(rag_tool, 'delete_all'):
                    rag_tool.delete_all(vector_db_id=self.vector_db_id)
                    print(f"✅ Vector database content deleted successfully")
                elif hasattr(rag_tool, 'drop'):
                    rag_tool.drop(vector_db_id=self.vector_db_id)
                    print(f"✅ Vector database content dropped successfully")
                else:
                    print(f"⚠️  No content clearing method found in RAG tool")
            else:
                print(f"⚠️  RAG tool not available for content clearing")
                
        except Exception as e:
            print(f"⚠️  Error clearing vector database content: {e}")
    
    def load_kubernetes_best_practices_documents(self):
        """Load Kubernetes YAML management best practices documentation into RAG"""
        print("📚 Loading Kubernetes YAML management best practices documentation...")
        
        # Using dynamic vector DB ID to ensure fresh documents each time
        print(f"📋 Using fresh vector database: {self.vector_db_id}")
        
        # First, ensure the vector database exists
        try:
            # Try to get the vector database to check if it exists
            self.client.vector_dbs.retrieve(vector_db_id=self.vector_db_id)
            print(f"✅ Vector database '{self.vector_db_id}' already exists")
        except Exception as e:
            print(f"📋 Vector database '{self.vector_db_id}' does not exist, creating it...")
            print(f"   Error: {e}")
            
            try:
                # Create the vector database
                self.client.vector_dbs.register(
                    vector_db_id=self.vector_db_id,
                    embedding_model="granite-embedding-125m",
                    embedding_dimension=768,
                    provider_id="milvus"
                )
                print(f"✅ Vector database '{self.vector_db_id}' created successfully")
            except Exception as create_e:
                print(f"❌ Failed to create vector database: {create_e}")
                self.rag_loaded = False
                return
        
        documents = [
            RAGDocument(
                document_id="namespace-resources-best-practices",
                content="""
                KUBERNETES/OPENSHIFT NAMESPACE - RESOURCE MANAGEMENT BEST PRACTICES
                
                TARGET RESOURCE TYPES (FOCUS ONLY ON THESE 4):
                1. Deployments - Application workload definitions
                2. ConfigMaps - Configuration data storage
                3. Services - Network service definitions
                4. Routes - External access configuration (OpenShift-specific)
                
                YAML CLEANING AND SANITIZATION FOR APPLICATION RESOURCES:
                
                METADATA TO REMOVE WHEN CLEANING YAMLS:
                - namespace: Target namespace (use the namespace specified by user)
                - resourceVersion: Cluster-specific version identifier
                - uid: Unique identifier assigned by Kubernetes
                - creationTimestamp: When the resource was created
                - generation: Internal versioning counter
                - managedFields: Field management information
                - selfLink: Deprecated API link
                - finalizers: (usually safe to remove for redeployment)
                - ownerReferences: (remove if creating standalone resources)
                
                SECTIONS TO COMPLETELY REMOVE:
                - status: ENTIRE status section must be removed (runtime information)
                - spec.template.metadata.creationTimestamp: Remove from pod templates
                
                ANNOTATIONS TO REMOVE WHEN CLEANING YAMLS:
                - kubectl.kubernetes.io/last-applied-configuration: Auto-generated kubectl annotation
                - argocd.argoproj.io/*: All ArgoCD-specific annotations (sync-wave, tracking-id, etc.)
                - deployment.kubernetes.io/revision: Deployment revision number
                - Any other system-generated annotations that start with kubernetes.io/ or openshift.io/
                
                METADATA TO PRESERVE:
                - name: Resource name
                - namespace: Target namespace (use the namespace specified by user)
                - labels: Custom labels and selectors
                - annotations: Custom annotations (except system-generated ones)
                
                ESSENTIAL LABELS TO ADD FOR APPLICATION RESOURCES:
                - app.kubernetes.io/name: application-name (or specific component name)
                - app.kubernetes.io/instance: application-instance
                - app.kubernetes.io/version: Application version
                - app.kubernetes.io/component: api|frontend|database|cache
                - app.kubernetes.io/part-of: application-system
                - app.kubernetes.io/managed-by: openshift
                
                DEPLOYMENT-SPECIFIC CLEANING:
                - Remove spec.template.metadata.creationTimestamp
                - Remove spec.template.metadata.labels that are system-generated
                - *MANDATORY*: Preserve spec.selector.matchLabels (critical for pod selection)
                - *MANDATORY*: Preserve spec.template.spec.containers configuration
                
                CONFIGMAP-SPECIFIC CLEANING:
                - Preserve all data and binaryData sections
                - Clean only metadata section
                - Ensure proper key naming conventions
                - When processing deployments, automatically identify ConfigMaps referenced in:
                  * spec.template.spec.containers[].envFrom[].configMapRef.name
                  * spec.template.spec.volumes[].configMap.name
                - Always retrieve and clean ConfigMaps that are referenced by deployments
                
                SERVICE-SPECIFIC CLEANING:
                - Preserve spec.selector (critical for pod targeting)
                - Preserve spec.ports configuration
                - Remove spec.clusterIP and spec.clusterIPs (auto-assigned)
                - Keep spec.type if explicitly set
                - Remove entire status section (including loadBalancer status)
                
                ROUTE-SPECIFIC CLEANING (OpenShift):
                - Remove spec.host (cluster-specific hostname, auto-generated by OpenShift)
                - Preserve spec.to.name (backend service reference)
                - Remove entire status section (including status.ingress)
                - Preserve spec.tls configuration if present
                - Remove system-generated annotations like openshift.io/host.generated
                
                YAML OUTPUT FORMAT REQUIREMENTS:
                - Use standard Kubernetes multi-document YAML format
                - Separate each resource with '---' on its own line
                - Start with '---' before the first resource
                - End with '---' after the last resource
                - This format allows direct use with 'oc apply -f filename.yaml'
                - Example format:
                  ---
                  apiVersion: apps/v1
                  kind: Deployment
                  ...
                  ---
                  apiVersion: v1
                  kind: Service
                  ...
                  ---
                
                """,
                mime_type="text/plain",
                metadata={"topic": "kubernetes-namespace", "type": "best-practices", "category": "resource-management"}
            ),
            RAGDocument(
                document_id="deployment-configuration-best-practices",
                content="""
                KUBERNETES/OPENSHIFT - DEPLOYMENT CONFIGURATION BEST PRACTICES
                
                DEPLOYMENT RESOURCE SPECIFICATIONS FOR APPLICATIONS:
                
                RESOURCE REQUESTS AND LIMITS:
                - Always specify resource requests and limits for applications
                - CPU requests: Start with 100m (0.1 CPU core) for microservices
                - Memory requests: Start with 256Mi for applications
                - CPU limits: Set 2-3x higher than requests for burstability
                - Memory limits: Set 1.5-2x higher than requests
                
                MANDATORY DEPLOYMENT RESOURCE CONFIGURATION TO ADD IF MISSING:
                resources:
                  requests:
                    memory: 256Mi
                    cpu: 250m
                  limits:
                    memory: 512Mi
                    cpu: 500m
                
                HEALTH CHECKS FOR APPLICATION SERVICES:
                
                MANDATORY LIVENESS PROBE TO ADD IF MISSING:
                livenessProbe:
                  failureThreshold: 3
                  httpGet:
                    path: /q/health/live
                    port: 8080
                    scheme: HTTP
                  initialDelaySeconds: 0
                  periodSeconds: 30
                  successThreshold: 1
                  timeoutSeconds: 10
                
                MANDATORY READINESS PROBE TO ADD IF MISSING:
                readinessProbe:
                  failureThreshold: 3
                  httpGet:
                    path: /q/health/ready
                    port: 8080
                    scheme: HTTP
                  initialDelaySeconds: 0
                  periodSeconds: 30
                  successThreshold: 1
                  timeoutSeconds: 10

                CONFIGMAP INTEGRATION PATTERNS:
                - Use environment variables from ConfigMaps for application configuration
                - Mount ConfigMaps as volumes for complex configuration files
                - Separate configuration by environment (dev, staging, prod)
                
                EXAMPLE CONFIGMAP USAGE IN DEPLOYMENT:
                env:
                - name: APP_CONFIG_VALUE
                  valueFrom:
                    configMapKeyRef:
                      name: app-config
                      key: config-value
                - name: DATABASE_URL
                  valueFrom:
                    configMapKeyRef:
                      name: app-config
                      key: database-url
                
                """,
                mime_type="text/plain",
                metadata={"topic": "kubernetes-namespace", "type": "best-practices", "category": "deployment-configuration"}
            )
        ]
        
        try: 
            # Check if RAG tool is available
            if not hasattr(self.client, 'tool_runtime') or not hasattr(self.client.tool_runtime, 'rag_tool'):
                raise Exception("RAG tool is not available in the client. Check if RAG is properly configured in the server.")
            
            # Insert documents into the vector database
            result = self.client.tool_runtime.rag_tool.insert(
                documents=documents,
                vector_db_id=self.vector_db_id,
                chunk_size_in_tokens=1024,
            )
            print(f"✅ Kubernetes best practices documents loaded successfully. Vector DB ID: {self.vector_db_id}")
            

            
            # Verify documents were inserted by inspecting RAG tool
            try:
                print(f"🔍 Inspecting RAG tool to find correct query method...")
                rag_tool = self.client.tool_runtime.rag_tool
                
                # Try with correct parameters
                query_result = None
                try:
                    query_result = rag_tool.query(
                        content="Kubernetes YAML best practices",
                        vector_db_ids=[self.vector_db_id]
                    )
                    print(f"✅ RAG query with correct parameters worked!")
                except Exception as correct_e:
                    print(f"❌ Correct parameters query failed: {correct_e}")
                
                if query_result is not None:
                    print(f"🔍 RAG verification query successful. Found results.")
                    self.rag_loaded = True
                else:
                    print(f"⚠️  All RAG query attempts failed, but documents were inserted successfully")
                    print(f"✅ Marking RAG as loaded since document insertion succeeded")
                    self.rag_loaded = True
                    
            except Exception as verify_e:
                print(f"⚠️  RAG inspection failed: {verify_e}")
                print(f"✅ Marking RAG as loaded since document insertion succeeded")
                self.rag_loaded = True
                
        except Exception as e:
            print(f"❌ Error loading RAG documents: {e}")
            print(f"📋 Details: {type(e).__name__}: {str(e)}")
            self.rag_loaded = False
            # Continue without RAG functionality
    
    def create_session(self):
        """Create a new agent session"""
        self.session_id = self.agent.create_session("chatbot-session")
    
    def chat(self, message: str):
        """Send a message to the agent and get response"""
        try:
            if not self.session_id:
                self.create_session()
            
            print(f"\n🧠 ReActAgent Processing: '{message}'")
            print(f"📊 RAG Status: {'✅ Loaded' if self.rag_loaded else '❌ Not loaded'}")
            print(f"🛠️  Available tools: mcp::openshift, builtin::rag")
            print(f"🔄 Using ReAct methodology: Reason → Act → Observe → Reason...")
            print("=" * 60)
            
            response = self.agent.create_turn(
                messages=[{"role": "user", "content": message}],
                session_id=self.session_id,
                stream=False
            )
            
            # Print detailed response information
            print("\n📋 AGENT RESPONSE:")
            print("=" * 50)
            
            # Check if tools were used
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"🔧 Tools used: {[tool.tool_name for tool in response.tool_calls]}")
                for tool_call in response.tool_calls:
                    print(f"   - {tool_call.tool_name}: {tool_call.arguments}")
            else:
                print("🔧 No tools were used in this response")
                
            # Additional debugging for tool calls
            if hasattr(response, 'steps'):
                print(f"🔄 Response has {len(response.steps)} steps")
                for i, step in enumerate(response.steps):
                    print(f"   Step {i+1}: {type(step)} - {getattr(step, 'step_type', 'unknown')}")
                    if hasattr(step, 'tool_calls') and step.tool_calls:
                        for tool_call in step.tool_calls:
                            print(f"      Tool: {tool_call.tool_name}")
            
            print(response)
            print(f"\n💬 Response:")
            
            # Fix YAML formatting by replacing \n with actual line breaks
            response_content = response.output_message.content
            
            if response_content and isinstance(response_content, str):
                response_content = response_content.replace('\\n', '\n')
            print(response_content)
            
            # Update the response object with the processed content
            if hasattr(response, 'output_message'):
                response.output_message.content = response_content
            
            return response
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print(f"❌ Error type: {type(e).__name__}")
            
            
            import traceback
            traceback.print_exc()
            return None
    
def main():
    """Main function to run a single query"""
    try:
        chatbot = LlamaStackChatbot()
        chatbot.create_session()
        
        print(f"\n{'='*60}")
        print("🧪 Namespace Resource Test")
        print('='*60)
        complex_query = "Get cleaned YAML for deployment and any referenced configmaps, service and route in 'discounts' namespace. Format with '---' separators for oc apply."
        chatbot.chat(complex_query)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()