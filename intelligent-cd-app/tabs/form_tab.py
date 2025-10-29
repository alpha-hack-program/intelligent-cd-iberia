"""
Form tab functionality for Intelligent CD Chatbot.

This module handles the form-based resource generation functionality.
"""

import os
import json
import ast
import subprocess
from typing import List
from llama_stack_client import LlamaStackClient
from llama_stack_client.lib.agents.react.agent import ReActAgent
from llama_stack_client.lib.agents.react.tool_parser import ReActOutput
from utils import get_logger


class FormTab:
    """Handles form-based resource generation functionality"""
    
    def __init__(self, client: LlamaStackClient, model: str):
        self.client = client
        self.logger = get_logger("form")
        self.model = model
        self.max_infer_iters = int(os.getenv("FORM_MAX_INFER_ITERS", "15"))

        # Load configuration from environment variables
        self.sampling_params, self.tools_json, self.model_prompt = self._load_config()
    
    def _load_config(self) -> tuple[dict, list, str]:
        """Load all configuration from environment variables"""
        # Load sampling parameters
        sampling_params_str = os.getenv("FORM_SAMPLING_PARAMS", "{}")
        sampling_params = json.loads(sampling_params_str)
        
        # Load tools
        tools_str = os.getenv("FORM_TOOLS", "[]")
        
        # Try to parse as JSON first, fall back to Python literal
        try:
            tools = json.loads(tools_str)
        except json.JSONDecodeError:
            try:
                # Handle Python syntax with single quotes
                tools = ast.literal_eval(tools_str)
            except (ValueError, SyntaxError) as e:
                self.logger.error(f"Failed to parse FORM_TOOLS: {e}")
                tools = []
        
        # Process tools to convert vector_db_names to vector_db_ids
        tools = self._process_tools(tools)
        
        # Load model prompt
        model_prompt = os.getenv("FORM_PROMPT", "You are a helpful assistant.")
        
        # Debug logging
        self.logger.debug(f"FORM_SAMPLING_PARAMS: {sampling_params}")
        self.logger.debug(f"FORM_TOOLS: {tools}")
        self.logger.debug(f"FORM_PROMPT: {str(model_prompt)[:200]}...")
        
        return sampling_params, tools, model_prompt
    
    def _process_tools(self, tools: list) -> list:
        """Process tools to convert vector_db_names to vector_db_ids"""
        processed_tools = []
        
        for tool in tools:
            # Handle string tools (like 'mcp::servicenow')
            if isinstance(tool, str):
                processed_tools.append(tool)
                continue
            
            # Handle dict tools
            if isinstance(tool, dict):
                tool_copy = tool.copy()
                
                # Check if this tool has args with vector_db_names
                if 'args' in tool_copy and isinstance(tool_copy['args'], dict):
                    args = tool_copy['args'].copy()
                    
                    if 'vector_db_names' in args:
                        names = args['vector_db_names']
                        if isinstance(names, list):
                            # Convert names to IDs
                            ids = [self.get_vector_store_id_by_name(name) for name in names]
                            # Replace vector_db_names with vector_db_ids
                            args['vector_db_ids'] = ids
                            del args['vector_db_names']
                            self.logger.info(f"Converted vector_db_names {names} to vector_db_ids {ids}")
                        
                    tool_copy['args'] = args
                
                processed_tools.append(tool_copy)
            else:
                # Unknown type, keep as-is
                processed_tools.append(tool)
        
        return processed_tools

    def get_vector_store_id_by_name(self, name: str) -> str:
        """Get vector store ID by name"""
        try:
            list_response = self.client.vector_stores.list()
            for vs in list_response:
                if vs.name == name:
                    return vs.id
            # If not found by name, assume it might be an ID already
            return name
        except Exception as e:
            self.logger.warning(f"Error looking up vector store by name: {str(e)}")
            return name
    
    def get_config_display(self) -> str:
        """Get formatted configuration for display in UI"""
        config_lines = [
            f"**Model:** {self.model}",
            f"**Tools:** {self.tools_json}",
            f"**Max iterations:** {self.max_infer_iters}",
            f"**Temperature:** {self.sampling_params.get('temperature', 'default')}",
            f"**Top P:** {self.sampling_params.get('top_p', 'default')}",
            f"**Top K:** {self.sampling_params.get('top_k', 'default')}"
        ]
        
        return "  \n".join(config_lines)

    def _initialize_agent(self, ocp_namespace: str, helm_chart_name: str, ocp_resource_type: List[str]) -> tuple[ReActAgent, str]:
        """Initialize agent and session that will be reused for the entire chat"""

        formatted_prompt = self.model_prompt
        # formatted_prompt = self.model_prompt.format(
        #     tool_groups=self.tools_json,
        #     ocp_namespace=ocp_namespace,
        #     helm_chart_name=helm_chart_name,
        #     ocp_resource_type=ocp_resource_type
        # )

        # Log agent creation details
        self.logger.info("=" * 60)
        self.logger.info("Creating Form Tab ReActAgent")
        self.logger.info("=" * 60)
        self.logger.info(f"Model: {self.model}")
        self.logger.info(f"Toolgroups available ({len(self.tools_json)}): {self.tools_json}")
        self.logger.info(f"Sampling params: {self.sampling_params}")
        self.logger.info(f"Max infer iters: {self.max_infer_iters}")
        self.logger.info(f"Formatted prompt: {formatted_prompt[:100]}")

        agent = ReActAgent(
            client=self.client,
            model=self.model,
            instructions=formatted_prompt,
            tools=self.tools_json,
            tool_config={"tool_choice": "auto"},  # Ensure tools are actually executed
            response_format={
                "type": "json_schema",
                "json_schema": ReActOutput.model_json_schema(),
            },
            sampling_params=self.sampling_params,
            max_infer_iters=self.max_infer_iters
        )
        
        self.logger.info("✅ ReActAgent created successfully")

        # Create session for the agent
        session = agent.create_session(session_name="OCP_Chat_Session")
        
        # Handle both object with .id attribute and direct string return
        if hasattr(session, 'id'):
            session_id = session.id
        else:
            session_id = str(session)
        
        self.logger.info(f"✅ Session created: {session_id}")
        self.logger.info("=" * 60)
        return agent, session_id



    
    def generate_resources(self, namespace: str, helm_chart: str, workload_type: str, supporting_resources: List[str]) -> str:
        """Generate Kubernetes resources based on form inputs"""
        self.logger.info(f"Form submission received:")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  Helm Chart: {helm_chart}")
        self.logger.info(f"  Workload Type: {workload_type}")
        self.logger.info(f"  Supporting Resources: {supporting_resources}")

        # Combine workload type and supporting resources for backward compatibility
        resource_types = [workload_type] + supporting_resources if workload_type else supporting_resources

        # Initialize agent and session for the entire chat
        agent, session_id = self._initialize_agent(namespace, helm_chart, resource_types)

        # Execute agent turn with simple message
        message = f"Get cleaned YAML for {workload_type} and any referenced {supporting_resources} in \'{namespace}\' namespace. Format with '---' separators for oc apply."
        
        response = agent.create_turn(
            messages=[{"role": "user", "content": message}],
            session_id=session_id,
            stream=False,
        )
        
        # Log response structure for debugging
        self.logger.info("=" * 60)
        self.logger.info("Response Structure Analysis:")
        self.logger.info("=" * 60)
        self.logger.info(f"Response type: {type(response)}")
        self.logger.info(f"Response attributes: {dir(response)}")
        
        # Log all steps if available
        if hasattr(response, 'steps') and response.steps:
            self.logger.info(f"Number of steps: {len(response.steps)}")
            for i, step in enumerate(response.steps):
                self.logger.debug(f"Step {i}: {step}")
        
        # Extract answer part from the last message and fix YAML formatting
        response_content = response.output_message.content
        final_answer = ""
        
        if response_content and isinstance(response_content, str):
            try:
                # Try to parse as JSON to extract just the answer part
                import json
                content_json = json.loads(response_content)
                if 'answer' in content_json and content_json['answer']:
                    final_answer = content_json['answer']
                else:
                    # If no answer field, use the full content
                    final_answer = response_content
            except json.JSONDecodeError:
                # If not JSON, use the content as-is
                final_answer = response_content
            
            # Replace \n with actual line breaks
            final_answer = final_answer.replace('\\n', '\n')
        
        print(final_answer)
        
        # Return the processed answer content instead of the full response
        return final_answer



    def apply_yaml(self, namespace: str, yaml_content: str) -> str:
        """Apply YAML content to OpenShift cluster"""
        self.logger.info(f"Apply YAML request received:")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  YAML Content Length: {len(yaml_content)} characters")

        try:
            # Ensure namespace exists (delete and recreate if it does)
            subprocess.run(['kubectl', 'delete', 'namespace', namespace], capture_output=True)
            subprocess.run(['kubectl', 'create', 'namespace', namespace], capture_output=True)
            
            # The '-' argument tells 'kubectl apply' to read from standard input.
            process = subprocess.Popen(
                ['kubectl', 'apply', '-n', namespace, '-f', '-'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=yaml_content)

            if process.returncode == 0:
                status_message = "**Apply YAML Function Logged Successfully!** ✅"
                output = stdout
            else:
                status_message = "**Apply YAML Function Failed!** ❌"
                output = f"Error: {stderr}"
                
        except Exception as e:
            # Assuming kubectl will exist, handle any other unexpected errors
            status_message = f"An unexpected error occurred: {e}"
            output = ""

        return f"🔧 Apply YAML to OpenShift:\n\n**Namespace:** {namespace}\n**YAML Content Length:** {len(yaml_content)} characters\n\n**Output:**\n{output}\n\n**Status:** {status_message}"

    def generate_helm(self, namespace: str, helm_chart: str, workload_type: str, supporting_resources: List[str]) -> str:
        """Generate Helm chart based on form inputs"""
        self.logger.info(f"Generate Helm request received:")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  Helm Chart: {helm_chart}")
        self.logger.info(f"  Workload Type: {workload_type}")
        self.logger.info(f"  Supporting Resources: {supporting_resources}")

        # Combine workload type and supporting resources for display
        all_resources = [workload_type] + supporting_resources if workload_type else supporting_resources
        return f"📦 Generate Helm Chart:\n\n**Namespace:** {namespace}\n**Helm Chart:** {helm_chart if helm_chart else 'None (will generate new chart)'}\n**Workload Type:** {workload_type if workload_type else 'None'}\n**Supporting Resources:** {', '.join(supporting_resources) if supporting_resources else 'None'}\n**All Resources:** {', '.join(all_resources) if all_resources else 'None'}\n\n**Status:** Placeholder function - not yet implemented\n\n**Next Steps:**\n- Generate Helm chart structure\n- Create templates for selected resource types\n- Generate values.yaml with namespace configuration\n- Package chart and provide download/instructions\n\n**Generate Helm Function Logged Successfully!** ✅"

    def apply_helm(self, helm_chart: str, namespace: str, values: str = "") -> str:
        """Apply Helm chart to OpenShift cluster"""
        self.logger.info(f"Apply Helm request received:")
        self.logger.info(f"  Helm Chart: {helm_chart}")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  Values: {values if values else 'None'}")
        return f"🚀 Apply Helm Chart to OpenShift:\n\n**Helm Chart:** {helm_chart}\n**Namespace:** {namespace}\n**Values:** {values if values else 'None (using default values)'}\n\n**Status:** Placeholder function - not yet implemented\n\n**Next Steps:**\n- Validate Helm chart and values\n- Use MCP tools to install/upgrade chart in OpenShift\n- Monitor deployment status\n- Return installation results and status\n\n**Apply Helm Function Logged Successfully!** ✅"

    def push_to_github(self, namespace: str, yaml_content: str, repo_url: str = "") -> str:
        """Push generated code to GitHub repository"""
        self.logger.info(f"Push to GitHub request received:")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  YAML Content Length: {len(yaml_content)} characters")
        self.logger.info(f"  Repository URL: {repo_url if repo_url else 'None (will use default)'}")
        return f"🔄 Push code to GitHub:\n\n**Namespace:** {namespace}\n**Repository URL:** {repo_url if repo_url else 'Default repository (to be configured)'}\n**YAML Content Length:** {len(yaml_content)} characters\n\n**Status:** Placeholder function - not yet implemented\n\n**Next Steps:**\n- Authenticate with GitHub (token/config)\n- Create or update repository structure\n- Commit generated YAML/manifests\n- Push to specified branch\n- Return commit hash and repository URL\n\n**Push to GitHub Function Logged Successfully!** ✅"

    def generate_argocd_app(self, namespace: str, workload_type: str, supporting_resources: List[str], repo_url: str = "") -> str:
        """Generate ArgoCD Application manifest"""
        self.logger.info(f"Generate ArgoCD App request received:")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  Workload Type: {workload_type}")
        self.logger.info(f"  Supporting Resources: {supporting_resources}")
        self.logger.info(f"  Repository URL: {repo_url if repo_url else 'None (will use default)'}")

        # Combine workload type and supporting resources for display
        all_resources = [workload_type] + supporting_resources if workload_type else supporting_resources
        return f"📝 Generate ArgoCD App:\n\n**Namespace:** {namespace}\n**Repository URL:** {repo_url if repo_url else 'Default repository (to be configured)'}\n**Workload Type:** {workload_type if workload_type else 'None'}\n**Supporting Resources:** {', '.join(supporting_resources) if supporting_resources else 'None'}\n**All Resources:** {', '.join(all_resources) if all_resources else 'None'}\n\n**Status:** Placeholder function - not yet implemented\n\n**Next Steps:**\n- Generate ArgoCD Application manifest\n- Configure source (Git repository, Helm chart, etc.)\n- Set sync policy and automated sync options\n- Configure destination (cluster and namespace)\n- Generate Application manifest YAML\n\n**Generate ArgoCD App Function Logged Successfully!** ✅"

    def apply_argocd_app(self, namespace: str, argocd_app_content: str) -> str:
        """Apply ArgoCD Application manifest to cluster"""
        self.logger.info(f"Apply ArgoCD App request received:")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  ArgoCD App Content Length: {len(argocd_app_content)} characters")

        try:
            # This is a placeholder - will be implemented to use kubectl or ArgoCD CLI
            return f"🔧 Apply ArgoCD App to OpenShift:\n\n**Namespace:** {namespace}\n**ArgoCD App Content Length:** {len(argocd_app_content)} characters\n\n**Status:** Placeholder function - not yet implemented\n\n**Next Steps:**\n- Validate ArgoCD Application manifest\n- Use kubectl apply or ArgoCD CLI to create Application\n- Monitor ArgoCD sync status\n- Return application status and sync results\n\n**Apply ArgoCD App Function Logged Successfully!** ✅"
        except Exception as e:
            return f"🔧 Apply ArgoCD App to OpenShift:\n\n**Namespace:** {namespace}\n**ArgoCD App Content Length:** {len(argocd_app_content)} characters\n\n**Status:** Error occurred: {e}\n\n**Apply ArgoCD App Function Failed!** ❌"


