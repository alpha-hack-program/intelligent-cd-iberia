"""
Form tab functionality for Intelligent CD Chatbot.

This module handles the form-based resource generation functionality.
"""

import os
import json
import ast
import subprocess
from typing import List
import gradio as gr
from llama_stack_client import LlamaStackClient
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
        self.logger.info("✅ All configurations loaded successfully")
    
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
        
        # Process tools to convert vector_db_names to vector_store_ids
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
        """Process tools to convert vector_db_names to vector_store_ids for file_search tools.
        
        Supports the /v1/responses API tool formats:
        - MCP tools: {"type": "mcp", "server_label": "...", "server_url": "..."}
        - File search: {"type": "file_search", "vector_store_ids": [...]}
        """
        processed_tools = []
        
        for tool in tools:
            # Handle dict tools
            if isinstance(tool, dict):
                tool_copy = tool.copy()
                self.logger.info(f"Processing tool: {tool_copy}")
                
                # Handle file_search tools with vector_db_names (convert to vector_store_ids)
                if tool_copy.get('type') == 'file_search' and 'vector_db_names' in tool_copy:
                    names = tool_copy['vector_db_names']
                    if isinstance(names, list):
                        # Convert names to IDs
                        ids = [self._get_vector_store_id_by_name(name) for name in names]
                        tool_copy['vector_store_ids'] = ids
                        del tool_copy['vector_db_names']
                        self.logger.info(f"Converted vector_db_names {names} to vector_store_ids {ids}")
                
                processed_tools.append(tool_copy)
            elif isinstance(tool, str):
                # Legacy string format - log warning and skip
                self.logger.warning(f"Skipping legacy string tool format '{tool}'. Use dict format for /v1/responses API.")
            else:
                # Unknown type, keep as-is
                processed_tools.append(tool)
        
        return processed_tools

    def _get_vector_store_id_by_name(self, name: str) -> str:
        """Get vector store ID by name"""
        try:
            list_response = self.client.vector_stores.list()
            # Access the data attribute which contains the list of VectorStore objects
            vector_stores = list_response.data if hasattr(list_response, 'data') else list_response
            
            for vs in vector_stores:
                if vs.name == name:
                    self.logger.info(f"Found vector store '{name}' -> '{vs.id}'")
                    return vs.id
            
            # If not found by name, assume it might be an ID already
            self.logger.warning(f"Vector store '{name}' not found, using as ID")
            return name
        except Exception as e:
            self.logger.warning(f"Error looking up vector store by name '{name}': {str(e)}")
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
            # f"\n**Step 3 - Push GitHub:**",
            # f"  - Tools: {self.config_push_github['tools']}",
            # f"  - Temperature: {self.config_push_github['sampling_params'].get('temperature', 'default')}",
            f"\n**Step 3 - Generate ArgoCD:**",
            f"  - Tools: {self.config_generate_argocd['tools']}",
            f"  - Temperature: {self.config_generate_argocd['sampling_params'].get('temperature', 'default')}",
        ]
        
        return "  \n".join(config_lines)

    def _call_responses_api(self, user_message: str, config: dict) -> str:
        """Call the /v1/responses API directly
        
        Args:
            user_message: The user's message/prompt
            config: Configuration dict with tools, prompt, and sampling_params
            
        Returns:
            The response text content
        """
        tools = config["tools"]
        instructions = config["prompt"]
        
        self.logger.info("=" * 60)
        self.logger.info("Calling /v1/responses API")
        self.logger.info("=" * 60)
        self.logger.info(f"Model: {self.model}")
        self.logger.info(f"Tools: {tools}")
        self.logger.info(f"Max infer iters: {self.max_infer_iters}")
        self.logger.info(f"Instructions length: {len(instructions)}")
        self.logger.info(f"User message: {user_message[:200]}...")
        
        try:
            
            # Call the responses API directly (non-streaming)
            response = self.client.responses.create(
                model=self.model,
                input=user_message,
                instructions=instructions,
                tools=tools if tools else None,
                include=["file_search_call.results"],
                max_infer_iters=self.max_infer_iters
            )
            
            self.logger.info(f"Response received - status: {getattr(response, 'status', 'unknown')}")
            self.logger.info(f"Response ID: {getattr(response, 'id', 'unknown')}")
            
            # Log output structure for debugging
            if hasattr(response, 'output') and response.output:
                for i, item in enumerate(response.output):
                    item_type = type(item).__name__
                    self.logger.info(f"Output[{i}] type: {item_type}")
                    if hasattr(item, 'type'):
                        self.logger.info(f"Output[{i}].type: {item.type}")
            
            # Extract the output text - try output_text first (like chatbot.py example)
            output_text = getattr(response, "output_text", None)
            
            if not output_text:
                # Fallback to manual extraction
                output_text = self._extract_response_text(response)
            
            if not output_text:
                # Last resort - convert response to string
                self.logger.warning("No output_text found, using str(response)")
                output_text = str(response)
            
            self.logger.info(f"✅ Response extracted: {len(output_text)} characters")
            return output_text
            
        except Exception as e:
            self.logger.error(f"Error calling /v1/responses API: {str(e)}")
            raise

    def _extract_response_text(self, response) -> str:
        """Extract text content from the responses API response
        
        Args:
            response: The response object from client.responses.create()
            
        Returns:
            The extracted text content
        """
        # First check for output_text property (llama-stack convenience property)
        if hasattr(response, 'output_text') and response.output_text:
            self.logger.debug(f"Found output_text: {len(response.output_text)} chars")
            return response.output_text
        
        # Check for text property in response.text
        if hasattr(response, 'text') and response.text:
            if hasattr(response.text, 'format'):
                self.logger.debug(f"Found response.text with format")
        
        # Parse the output array
        if hasattr(response, 'output') and response.output:
            texts = []
            for item in response.output:
                item_type = type(item).__name__
                
                # Look for message type outputs with content
                if hasattr(item, 'type') and item.type == 'message':
                    if hasattr(item, 'content') and item.content:
                        for content_item in item.content:
                            if hasattr(content_item, 'text') and content_item.text:
                                texts.append(content_item.text)
                            elif hasattr(content_item, 'type') and content_item.type == 'output_text':
                                if hasattr(content_item, 'text') and content_item.text:
                                    texts.append(content_item.text)
                
                # Direct text attribute
                elif hasattr(item, 'text') and item.text:
                    texts.append(item.text)
                
                # MCP call results might have output
                elif 'McpCall' in item_type and hasattr(item, 'output'):
                    self.logger.debug(f"Found MCP call output")
            
            if texts:
                result = '\n'.join(filter(None, texts))
                self.logger.debug(f"Extracted {len(texts)} text segments, total {len(result)} chars")
                return result
        
        # Fallback
        self.logger.warning(f"Could not extract text from response")
        return ""

    def generate_resources(self, namespace: str, helm_chart: str, workload_type: str, supporting_resources: List[str]) -> str:
        """Step 1: Generate Kubernetes resources by taking resources from OCP and trimming unnecessary fields"""
        self.logger.info(f"Step 1 - Generate Resources:")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  Helm Chart: {helm_chart}")
        self.logger.info(f"  Workload Type: {workload_type}")
        self.logger.info(f"  Supporting Resources: {supporting_resources}")

        # Ask for docs first (triggers file_search), then resources (triggers MCP)
        message = f"First check GitOps best practices in the documentation, then show {workload_type} in {namespace} namespace as clean YAML."
        
        final_answer = self._call_responses_api(message, self.config_generate_resources)
        
        self.logger.info(f"✅ Step 1 completed. Generated {len(final_answer)} characters of YAML")
        return final_answer

    def apply_yaml(self, namespace: str, yaml_content: str) -> str:
        """Apply YAML content to OpenShift cluster"""
        self.logger.info(f"Apply YAML request received:")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  YAML Content Length: {len(yaml_content)} characters")

        try:
            new_namespace = namespace+"-manually-created"
            # Ensure namespace exists (delete and recreate if it does)
            subprocess.run(['kubectl', 'create', 'namespace', new_namespace], capture_output=True)
            
            # The '-' argument tells 'kubectl apply' to read from standard input.
            process = subprocess.Popen(
                ['kubectl', 'apply', '-n', new_namespace, '-f', '-'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=yaml_content)

            if process.returncode == 0:
                # Show success info message
                info_message = f"✅ Apply YAML Function Logged Successfully!\n\n**Namespace:** {new_namespace}\n**YAML Content Length:** {len(yaml_content)} characters\n\n**Output:**\n{stdout}"
                gr.Info(info_message)
            else:
                # Show error info message
                info_message = f"❌ Apply YAML Function Failed!\n\n**Namespace:** {new_namespace}\n**YAML Content Length:** {len(yaml_content)} characters\n\n**Error:**\n{stderr}"
                gr.Info(info_message)
                
        except Exception as e:
            # Show exception info message
            new_namespace = namespace+"-manually-created"
            info_message = f"⚠️ An unexpected error occurred: {e}\n\n**Namespace:** {new_namespace}\n**YAML Content Length:** {len(yaml_content)} characters"
            gr.Info(info_message)

        # Return empty string to leave the right panel intact
        return ""

    def generate_helm(self, namespace: str, helm_chart: str, workload_type: str, supporting_resources: List[str], resources_yaml: str = "") -> str:
        """Step 2: Generate Helm chart by taking resources and creating a Helm chart structure"""
        self.logger.info(f"Step 2 - Generate Helm Chart:")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  Helm Chart: {helm_chart}")
        self.logger.info(f"  Workload Type: {workload_type}")
        self.logger.info(f"  Supporting Resources: {supporting_resources}")
        self.logger.info(f"  Resources YAML Length: {len(resources_yaml) if resources_yaml else 0} characters")

        message = f"Create a Helm chart from the following Kubernetes resources: Namespace: {namespace}, Helm Chart Name: {helm_chart if helm_chart else 'generated-chart'}, Workload Type: {workload_type}, Supporting Resources: {', '.join(supporting_resources) if supporting_resources else 'None'}, Resources YAML: {resources_yaml if resources_yaml else 'No resources provided'}."
        
        helm_chart_content = self._call_responses_api(message, self.config_generate_helm)
        
        self.logger.info(f"✅ Step 2 completed. Generated Helm chart ({len(helm_chart_content)} characters)")
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

        message = f"You are given this Kubernetes manifest file. It describes different Kubernetes resources. Commit the respective YAML to GitHub.\n\nrepo {self.github_gitops_repo}.\n\nbranch: main\n\ncommit message: \"☕🧰 Make it GitOps! ☕🧰\"\n\nFile information:\n\n- path: It will be just one file named {namespace}.yaml with the content of that YAML: \n\n\n{application_content}"
        
        push_result = self._call_responses_api(message, self.config_push_github)
        
        self.logger.info(f"✅ Step 3 completed. Push result: {push_result[:200]}...")
        return push_result

    def generate_argocd_app(self, namespace: str) -> str:
        """Step 4: Generate ArgoCD Application manifest using repo, folder name, etc."""
        new_namespace = namespace+"-gitops"
        self.logger.info(f"Step 4 - Generate ArgoCD App:")
        self.logger.info(f"  Namespace: {new_namespace}")
        self.logger.info(f"  Repository URL: {self.github_gitops_repo}")

        message = f"Generate an ArgoCD Application manifest with the following configuration: Repository URL: {self.github_gitops_repo}, and namespace {new_namespace}. This special time, the YAMLs are in the root folder of the repository, not in a subfolder."
        
        argocd_app_content = self._call_responses_api(message, self.config_generate_argocd)
        
        self.logger.info(f"✅ Step 4 completed. Generated ArgoCD App manifest ({len(argocd_app_content)} characters)")
        return argocd_app_content

    def apply_argocd_app(self, argocd_app_content: str) -> str:
        """Apply ArgoCD Application manifest to cluster"""
        self.logger.info(f"Apply ArgoCD App request received:")
        self.logger.info(f"  ArgoCD App Content Length: {len(argocd_app_content)} characters")

        try:
            # Apply ArgoCD Application manifest using kubectl
            # The '-' argument tells 'kubectl apply' to read from standard input.
            process = subprocess.Popen(
                ['kubectl', 'apply', '-f', '-'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=argocd_app_content)

            if process.returncode == 0:
                status_message = "**Apply ArgoCD App Function Logged Successfully!** ✅"
                output = stdout
            else:
                status_message = "**Apply ArgoCD App Function Failed!** ❌"
                output = f"Error: {stderr}"
                
        except Exception as e:
            # Handle any unexpected errors
            status_message = f"An unexpected error occurred: {e}"
            output = ""

        return f"🔧 Apply ArgoCD App to OpenShift:\n\n**ArgoCD App Content Length:** {len(argocd_app_content)} characters\n\n**Output:**\n{output}\n\n**Status:** {status_message}"
