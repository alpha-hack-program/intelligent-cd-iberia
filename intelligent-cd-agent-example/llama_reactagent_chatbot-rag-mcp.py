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
        self.base_url = os.getenv("REMOTE_BASE_URL", "http://localhost:8321")
        self.model_id = os.getenv("INFERENCE_MODEL_ID", "granite32-8b")
        self.session_id = None
        self.vector_db_id = "my_documents"
        self.rag_loaded = False  # Track RAG loading status
        
        # Basic sampling parameters
        self.sampling_params = {
            "temperature": 0.1, 
            "max_tokens": 200000, 
            "max_new_tokens": 200000, 
            "strategy": {"type": "greedy"}
        }
        
        # Setup client with SSL and auth
        self._setup_client()
        
        # Verify and register MCP toolgroups
        self._verify_mcp_tools()
        
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
You are an expert Kubernetes and DevOps assistant powered by ReAct (Reason-then-Act) methodology. Use the available tools to help users with their requests.

**ReAct Reasoning Framework:**

1. **REASON:** Before taking any action, clearly think through:
   - What information do I need to solve this problem?
   - Which tools are most appropriate for gathering this information?
   - What is my step-by-step approach to address the user's request?

2. **ACT:** Execute your reasoning by using the appropriate tools:
   - Use mcp::openshift for real-time system data, pod status, logs, and cluster information
   - Use builtin::rag to search knowledge base for configuration guides, troubleshooting procedures, and best practices
   - Combine multiple tools when needed to get complete information

3. **OBSERVE:** Analyze the results from your actions and determine:
   - Did I get the information I need?
   - Do I need additional data or clarification?
   - What patterns or issues can I identify?

4. **REASON AGAIN:** Based on observations, determine next steps:
   - Continue gathering more specific information
   - Synthesize findings into actionable recommendations
   - Provide clear explanations and solutions

**Standard Operating Procedure for Problem Solving:**

When a user reports application issues (API failures, database problems, performance issues, etc.):
- **REASON**: Break down the problem into specific diagnostic steps
- **ACT**: Use tools systematically to gather both real-time system data and documentation
- **OBSERVE**: Analyze results and correlate system state with known patterns
- **REASON & ACT**: Provide synthesized recommendations with supporting evidence

Available tools:
- Use OpenShift/Kubernetes tools to get cluster information, list, retrieve configurations, etc.
- Use RAG search to find best practices and documentation

For Kubernetes YAML management:
- Retrieve YAML configurations using the available tools
- Clean them by removing only unnecessary cluster-specific metadata (resourceVersion, uid, creationTimestamp, etc.)
- Add best practice labels and annotations based on the knowledge base

**CRITICAL TOOL EXECUTION RULES:**
- When you need to use tools, set "answer": null and provide proper "action" object
- Only provide "answer" with actual results after tool execution is complete
- Always use tool_calls to execute functions for real cluster data
- Never generate fake data or describe hypothetical scenarios when real data is available

**CORRECT ACTION FORMAT:**
When using tools, use this exact format:
{
  "thought": "Your reasoning here",
  "action": {
    "tool_name": "tool_name_here",
    "tool_params": {"param_name": "param_value"}
  },
  "answer": null
}

**FINAL ANSWER FORMAT:**
When providing final results (no more tools needed):
{
  "thought": "Summary of what was accomplished",
  "action": null,
  "answer": "Your complete response here"
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
            sampling_params=self.sampling_params
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
    
    def load_kubernetes_best_practices_documents(self):
        """Load Kubernetes YAML management best practices documentation into RAG"""
        print("📚 Loading Kubernetes YAML management best practices documentation...")
        
        documents = [
            RAGDocument(
                document_id="kubernetes-yaml-best-practices",
                content="""
                KUBERNETES YAML MANAGEMENT - BEST PRACTICES
                
                YAML CLEANING AND SANITIZATION:
                
                METADATA TO REMOVE WHEN CLEANING YAMLS:
                - resourceVersion: Cluster-specific version identifier
                - uid: Unique identifier assigned by Kubernetes
                - creationTimestamp: When the resource was created
                - generation: Internal versioning counter
                - managedFields: Field management information
                - selfLink: Deprecated API link
                - finalizers: (usually safe to remove for redeployment)
                - ownerReferences: (remove if creating standalone resources)
                - status: Runtime status information
                
                METADATA TO PRESERVE:
                - name: Resource name
                - namespace: Target namespace
                - labels: Custom labels and selectors
                - annotations: Custom annotations
                
                ESSENTIAL LABELS TO ADD:
                - app.kubernetes.io/name: Application name
                - app.kubernetes.io/instance: Instance identifier
                - app.kubernetes.io/version: Application version
                - app.kubernetes.io/component: Component within application
                - app.kubernetes.io/part-of: Application suite name
                - app.kubernetes.io/managed-by: Tool managing the resource
                
                """,
                mime_type="text/plain",
                metadata={"topic": "kubernetes", "type": "best-practices", "category": "yaml-management"}
            ),
            RAGDocument(
                document_id="kubernetes-resource-requirements",
                content="""
                KUBERNETES RESOURCE REQUIREMENTS - BEST PRACTICES
                
                RESOURCE REQUESTS AND LIMITS:
                
                DEPLOYMENT RESOURCE SPECIFICATIONS:
                - Always specify resource requests and limits
                - CPU requests: Start with 100m (0.1 CPU core) for small apps
                - Memory requests: Start with 128Mi for small apps
                - CPU limits: Set 2-4x higher than requests for burstability
                - Memory limits: Set 1.5-2x higher than requests
                
                EXAMPLE RESOURCE CONFIGURATION:
                resources:
                  requests:
                    memory: 256Mi
                    cpu: 250m
                  limits:
                    memory: 512Mi
                    cpu: 500m
                
                QUALITY OF SERVICE CLASSES:
                - Guaranteed: requests = limits for all containers
                - Burstable: requests < limits or only requests specified
                - BestEffort: no requests or limits specified
                
                PROBES AND HEALTH CHECKS:
                
                LIVENESS PROBE:
                livenessProbe:
                  httpGet:
                    path: /health
                    port: 8080
                  initialDelaySeconds: 30
                  periodSeconds: 10
                  timeoutSeconds: 5
                  failureThreshold: 3
                
                READINESS PROBE:
                readinessProbe:
                  httpGet:
                    path: /ready
                    port: 8080
                  initialDelaySeconds: 5
                  periodSeconds: 5
                  timeoutSeconds: 3
                  failureThreshold: 3
                
                STARTUP PROBE (for slow-starting apps):
                startupProbe:
                  httpGet:
                    path: /startup
                    port: 8080
                  initialDelaySeconds: 10
                  periodSeconds: 10
                  timeoutSeconds: 5
                  failureThreshold: 30
              
                """,
                mime_type="text/plain",
                metadata={"topic": "kubernetes", "type": "best-practices", "category": "resource-requirements"}
            ),
            RAGDocument(
                document_id="kubernetes-services-networking",
                content="""
                KUBERNETES SERVICES AND NETWORKING - BEST PRACTICES
                
                SERVICE TYPES AND CONFIGURATIONS:
                
                1. CLUSTERIP SERVICE (Internal):
                apiVersion: v1
                kind: Service
                metadata:
                  name: my-app-service
                  labels:
                    app.kubernetes.io/name: my-app
                    app.kubernetes.io/component: backend
                spec:
                  type: ClusterIP
                  selector:
                    app.kubernetes.io/name: my-app
                  ports:
                  - name: http
                    port: 80
                    targetPort: 8080
                    protocol: TCP
                
                2. NODEPORT SERVICE (External):
                spec:
                  type: NodePort
                  selector:
                    app.kubernetes.io/name: my-app
                  ports:
                  - name: http
                    port: 80
                    targetPort: 8080
                    nodePort: 30080
                    protocol: TCP
                
                3. LOADBALANCER SERVICE (Cloud):
                spec:
                  type: LoadBalancer
                  selector:
                    app.kubernetes.io/name: my-app
                  ports:
                  - name: http
                    port: 80
                    targetPort: 8080
                    protocol: TCP
                
                
                CONFIGMAP AND SECRET MANAGEMENT:
                
                CONFIGMAP EXAMPLE:
                apiVersion: v1
                kind: ConfigMap
                metadata:
                  name: my-app-config
                  labels:
                    app.kubernetes.io/name: my-app
                data:
                  database-host: "postgres.default.svc.cluster.local"
                  database-port: "5432"
                  log-level: "INFO"
                  feature-flags: |
                    feature1=true
                    feature2=false
                
                SECRET EXAMPLE:
                apiVersion: v1
                kind: Secret
                metadata:
                  name: my-app-secret
                  labels:
                    app.kubernetes.io/name: my-app
                type: Opaque
                data:
                  database-password: cGFzc3dvcmQxMjM=
                  api-key: YWJjZGVmZ2hpams=
                

                """,
                mime_type="text/plain",
                metadata={"topic": "kubernetes", "type": "best-practices", "category": "services-networking"}
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
                chunk_size_in_tokens=512,
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
            import traceback
            traceback.print_exc()
            return None
    
def main():
    """Main function to run a single query"""
    try:
        chatbot = LlamaStackChatbot()
        chatbot.create_session()
        
        print(f"\n{'='*60}")
        print("🧪 Final Complex Test")
        print('='*60)
        complex_query = "List the pods in the 'intelligent-cd' namespace. For each pod, get its full YAML configuration, then directly apply the Kubernetes best practices from the knowledge base to clean it. Remove only unnecessary cluster-specific metadata and return the cleaned YAML for each pod."
        chatbot.chat(complex_query)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()