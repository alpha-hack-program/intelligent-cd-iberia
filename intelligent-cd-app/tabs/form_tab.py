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
        self.github_gitops_repo = os.getenv("GITHUB_GITOPS_REPO", "")

        # Load step-specific configurations from environment variables
        self.logger.info("Loading step-specific configurations...")
        self.config_generate_resources = self._load_step_config("GENERATE_RESOURCES")
        self.config_generate_helm = self._load_step_config("GENERATE_HELM")
        self.config_push_github = self._load_step_config("PUSH_GITHUB")
        self.config_generate_argocd = self._load_step_config("GENERATE_ARGOCD")
        
        # Initialize all agents and sessions once during initialization
        self.logger.info("Initializing all ReActAgents for form tab steps...")
        self.agent_resources, self.session_id_resources = self._initialize_agent("generate_resources", self.config_generate_resources)
        self.agent_helm, self.session_id_helm = self._initialize_agent("generate_helm", self.config_generate_helm)
        self.agent_github, self.session_id_github = self._initialize_agent("push_github", self.config_push_github)
        self.agent_argocd, self.session_id_argocd = self._initialize_agent("generate_argocd_app", self.config_generate_argocd)
        self.logger.info("✅ All ReActAgents initialized successfully")
    
    def _load_step_config(self, step_key: str) -> dict:
        """Load step-specific configuration from environment variables
        
        Args:
            step_key: The step identifier (e.g., "GENERATE_RESOURCES", "GENERATE_HELM", etc.)
            
        Returns:
            Dictionary with keys: sampling_params, tools, prompt
        """
        env_prefix = f"FORM_{step_key}_"
        
        # Load sampling parameters
        sampling_params_str = os.getenv(f"{env_prefix}SAMPLING_PARAMS", "{}")
        try:
            sampling_params = json.loads(sampling_params_str)
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse {env_prefix}SAMPLING_PARAMS: {e}, using defaults")
            sampling_params = {}
        
        # Load tools
        tools_str = os.getenv(f"{env_prefix}TOOLS", "[]")
        
        # Try to parse as JSON first, fall back to Python literal
        try:
            tools = json.loads(tools_str)
        except json.JSONDecodeError:
            try:
                # Handle Python syntax with single quotes
                tools = ast.literal_eval(tools_str)
            except (ValueError, SyntaxError) as e:
                self.logger.error(f"Failed to parse {env_prefix}TOOLS: {e}")
                tools = []
        
        # Process tools to convert vector_db_names to vector_db_ids
        tools = self._process_tools(tools)
        
        # Load model prompt
        prompt_file = os.getenv(f"{env_prefix}PROMPT_FILE", "")
        if prompt_file:
            try:
                with open(prompt_file, 'r') as f:
                    model_prompt = f.read()
            except Exception as e:
                self.logger.warning(f"Failed to read prompt file {prompt_file}: {e}, using env var or default")
                model_prompt = os.getenv(f"{env_prefix}PROMPT", "You are a helpful assistant.")
        else:
            model_prompt = os.getenv(f"{env_prefix}PROMPT", "You are a helpful assistant.")
        
        # Debug logging
        self.logger.debug(f"{env_prefix}SAMPLING_PARAMS: {sampling_params}")
        self.logger.debug(f"{env_prefix}TOOLS: {tools}")
        self.logger.debug(f"{env_prefix}PROMPT: {str(model_prompt)[:200]}...")
        
        return {
            "sampling_params": sampling_params,
            "tools": tools,
            "prompt": model_prompt
        }
    
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
                            ids = [self._get_vector_store_id_by_name(name) for name in names]
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

    def _get_vector_store_id_by_name(self, name: str) -> str:
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
            f"**Max iterations:** {self.max_infer_iters}",
            f"\n**Step 1 - Generate Resources:**",
            f"  - Tools: {self.config_generate_resources['tools']}",
            f"  - Temperature: {self.config_generate_resources['sampling_params'].get('temperature', 'default')}",
            f"\n**Step 2 - Generate Helm:**",
            f"  - Tools: {self.config_generate_helm['tools']}",
            f"  - Temperature: {self.config_generate_helm['sampling_params'].get('temperature', 'default')}",
            f"\n**Step 3 - Push GitHub:**",
            f"  - Tools: {self.config_push_github['tools']}",
            f"  - Temperature: {self.config_push_github['sampling_params'].get('temperature', 'default')}",
            f"\n**Step 4 - Generate ArgoCD:**",
            f"  - Tools: {self.config_generate_argocd['tools']}",
            f"  - Temperature: {self.config_generate_argocd['sampling_params'].get('temperature', 'default')}",
        ]
        
        return "  \n".join(config_lines)

    def _initialize_agent(self, step_name: str, config: dict, session_name: str = None) -> tuple[ReActAgent, str]:
        """Initialize agent and session for a specific step
        
        Args:
            step_name: Name of the step (e.g., "generate_resources", "generate_helm", etc.)
            config: Dictionary with keys: sampling_params, tools, prompt
            session_name: Optional custom session name. If not provided, uses step_name
            
        Returns:
            Tuple of (agent, session_id)
        """
        formatted_prompt = config["prompt"]
        sampling_params = config["sampling_params"]
        tools = config["tools"]

        # Log agent creation details
        self.logger.info("=" * 60)
        self.logger.info(f"Creating ReActAgent for step: {step_name}")
        self.logger.info("=" * 60)
        self.logger.info(f"Model: {self.model}")
        self.logger.info(f"Toolgroups available ({len(tools)}): {tools}")
        self.logger.info(f"Sampling params: {sampling_params}")
        self.logger.info(f"Max infer iters: {self.max_infer_iters}")
        self.logger.info(f"Formatted prompt: {formatted_prompt[:100]}")

        agent = ReActAgent(
            client=self.client,
            model=self.model,
            instructions=formatted_prompt,
            tools=tools,
            tool_config={"tool_choice": "auto"},  # Ensure tools are actually executed
            response_format={
                "type": "json_schema",
                "json_schema": ReActOutput.model_json_schema(),
            },
            sampling_params=sampling_params,
            max_infer_iters=self.max_infer_iters
        )
        
        self.logger.info("✅ ReActAgent created successfully")

        # Create session for the agent
        if session_name is None:
            session_name = f"{step_name}_session"
        session = agent.create_session(session_name=session_name)
        
        # Handle both object with .id attribute and direct string return
        if hasattr(session, 'id'):
            session_id = session.id
        else:
            session_id = str(session)
        
        self.logger.info(f"✅ Session created: {session_id}")
        self.logger.info("=" * 60)
        return agent, session_id
    
    def _extract_answer_content(self, response) -> str:
        """Extract answer content from agent response"""
        response_content = response.output_message.content
        final_answer = ""
        
        if response_content and isinstance(response_content, str):
            try:
                # Try to parse as JSON to extract just the answer part
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
        
        return final_answer



    
    def generate_resources(self, namespace: str, helm_chart: str, workload_type: str, supporting_resources: List[str]) -> str:
        """Step 1: Generate Kubernetes resources by taking resources from OCP and trimming unnecessary fields"""
        self.logger.info(f"Step 1 - Generate Resources:")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  Helm Chart: {helm_chart}")
        self.logger.info(f"  Workload Type: {workload_type}")
        self.logger.info(f"  Supporting Resources: {supporting_resources}")

        # Use pre-initialized agent for step 1
        message = f"Get cleaned YAML for {workload_type} and any referenced {supporting_resources} in \'{namespace}\' namespace. Remove unnecessary fields and format with '---' separators for oc apply."
        
        response = self.agent_resources.create_turn(
            messages=[{"role": "user", "content": message}],
            session_id=self.session_id_resources,
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
        
        # Extract answer content
        final_answer = self._extract_answer_content(response)
        
        self.logger.info(f"✅ Step 1 completed. Generated {len(final_answer)} characters of YAML")
        
        # Return the processed answer content
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

    def generate_helm(self, namespace: str, helm_chart: str, workload_type: str, supporting_resources: List[str], resources_yaml: str = "") -> str:
        """Step 2: Generate Helm chart by taking resources and creating a Helm chart structure"""
        self.logger.info(f"Step 2 - Generate Helm Chart:")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  Helm Chart: {helm_chart}")
        self.logger.info(f"  Workload Type: {workload_type}")
        self.logger.info(f"  Supporting Resources: {supporting_resources}")
        self.logger.info(f"  Resources YAML Length: {len(resources_yaml) if resources_yaml else 0} characters")

        # Use pre-initialized agent for step 2
        message = f"Create a Helm chart from the following Kubernetes resources: Namespace: {namespace}, Helm Chart Name: {helm_chart if helm_chart else 'generated-chart'}, Workload Type: {workload_type}, Supporting Resources: {', '.join(supporting_resources) if supporting_resources else 'None'}, Resources YAML: {resources_yaml if resources_yaml else 'No resources provided'}."
        
        response = self.agent_helm.create_turn(
            messages=[{"role": "user", "content": message}],
            session_id=self.session_id_helm,
            stream=False,
        )
        
        # Extract answer content
        helm_chart_content = self._extract_answer_content(response)
        
        self.logger.info(f"✅ Step 2 completed. Generated Helm chart ({len(helm_chart_content)} characters)")
        
        # Return the Helm chart content
        return helm_chart_content

    def apply_helm(self, helm_chart: str, namespace: str, values: str = "") -> str:
        """Apply Helm chart to OpenShift cluster"""
        self.logger.info(f"Apply Helm request received:")
        self.logger.info(f"  Helm Chart: {helm_chart}")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  Values: {values if values else 'None'}")
        return f"🚀 Apply Helm Chart to OpenShift:\n\n**Helm Chart:** {helm_chart}\n**Namespace:** {namespace}\n**Values:** {values if values else 'None (using default values)'}\n\n**Status:** Placeholder function - not yet implemented\n\n**Next Steps:**\n- Validate Helm chart and values\n- Use MCP tools to install/upgrade chart in OpenShift\n- Monitor deployment status\n- Return installation results and status\n\n**Apply Helm Function Logged Successfully!** ✅"

    def push_github(self, namespace: str, application_content: str) -> str:
        """Step 3: Push files to GitHub by creating a commit and pushing to the repository"""
        self.logger.info(f"Step 3 - Push to GitHub:")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  Application Content Length: {len(application_content) if application_content else 0} characters")
        self.logger.info(f"  Repository URL: {self.github_gitops_repo}")

        # Use pre-initialized agent for step 3
        message = f"Push the following content to the repository {self.github_gitops_repo} for the namespace {namespace} the following application content:\n{application_content}"
        
        response = self.agent_github.create_turn(
            messages=[{"role": "user", "content": message}],
            session_id=self.session_id_github,
            stream=False,
        )
        
        # Extract answer content
        push_result = self._extract_answer_content(response)
        
        self.logger.info(f"✅ Step 3 completed. Push result: {push_result[:200]}...")
        
        # Format result to show success/failure and verification info
        return push_result

    def generate_argocd_app(self, namespace: str) -> str:
        """Step 4: Generate ArgoCD Application manifest using repo, folder name, etc."""
        self.logger.info(f"Step 4 - Generate ArgoCD App:")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  Repository URL: {self.github_gitops_repo}")

        message = f"Generate an ArgoCD Application manifest with the following configuration: Repository URL: {self.github_gitops_repo}, and namespace {namespace}."
        
        response = self.agent_argocd.create_turn(
            messages=[{"role": "user", "content": message}],
            session_id=self.session_id_argocd,
            stream=False,
        )
        
        # Extract answer content
        argocd_app_content = self._extract_answer_content(response)
        
        self.logger.info(f"✅ Step 4 completed. Generated ArgoCD App manifest ({len(argocd_app_content)} characters)")
        
        # Return the ArgoCD Application manifest content
        return argocd_app_content

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


