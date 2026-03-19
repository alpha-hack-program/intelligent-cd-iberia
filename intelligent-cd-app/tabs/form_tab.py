"""
Form tab functionality for Intelligent CD Chatbot.

This module handles the form-based resource generation functionality.
"""

import os
import re
import json
import subprocess
from typing import List, Generator
import yaml
import gradio as gr
from llama_stack_client import LlamaStackClient
from utils import get_logger


class FormTab:
    """Handles form-based resource generation functionality"""
    
    def __init__(self, client: LlamaStackClient, model: str):
        self.client = client
        self.logger = get_logger("form")
        self.model = model
        self.temperature = float(os.getenv("TEMPERATURE", "0.1"))
        self.max_infer_iters = int(os.getenv("MAX_INFER_ITERS", "30"))
        self.github_gitops_repo = os.getenv("GITHUB_GITOPS_REPO", "")

        self.logger.info("Loading step-specific configurations...")
        self.config_generate_resources = self._load_step_config("GENERATE_RESOURCES")
        self.config_apply_best_practices = self._load_step_config("APPLY_BEST_PRACTICES")
        self.config_generate_helm = self._load_step_config("GENERATE_HELM")
        self.config_push_github = self._load_step_config("PUSH_GITHUB")
        self.config_generate_argocd = self._load_step_config("GENERATE_ARGOCD")
        self.logger.info("✅ All configurations loaded successfully")

        self._resource_type_map = {
            "Deployment": ("apps/v1", "Deployment", "deployments"),
            "StatefulSet": ("apps/v1", "StatefulSet", "statefulsets"),
            "Service": ("v1", "Service", "services"),
            "Route": ("route.openshift.io/v1", "Route", "routes"),
            "ConfigMap": ("v1", "ConfigMap", "configmaps"),
        }
    
    def _load_step_config(self, step_key: str) -> dict:
        """Load step-specific tools and prompt from environment variables.
        
        Args:
            step_key: The step identifier (e.g., "GENERATE_RESOURCES", "GENERATE_HELM", etc.)
            
        Returns:
            Dictionary with keys: tools, prompt
        """
        env_prefix = f"FORM_{step_key}_"
        
        tools_str = os.getenv(f"{env_prefix}TOOLS", "[]")
        
        try:
            tools = json.loads(tools_str)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse {env_prefix}TOOLS: {e}")
            tools = []
        
        tools = self._process_tools(tools)
        
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
        
        self.logger.debug(f"{env_prefix}TOOLS: {tools}")
        self.logger.debug(f"{env_prefix}PROMPT: {str(model_prompt)[:200]}...")
        
        return {
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
            tool_copy = tool.copy()
            self.logger.info(f"Processing tool: {tool_copy}")
            
            if tool_copy.get('type') == 'file_search' and 'vector_db_names' in tool_copy:
                names = tool_copy['vector_db_names']
                if isinstance(names, list):
                    ids = [self._get_vector_store_id_by_name(name) for name in names]
                    tool_copy['vector_store_ids'] = ids
                    del tool_copy['vector_db_names']
                    self.logger.info(f"Converted vector_db_names {names} to vector_store_ids {ids}")
            
            if tool_copy.get('type') == 'mcp' and tool_copy.get('server_label') == 'github':
                github_pat = os.getenv('GITHUB_PAT', '')
                if github_pat:
                    tool_copy['authorization'] = f"Bearer {github_pat}"
                    extra_headers = {}
                    toolsets = os.getenv('GITHUB_MCP_SERVER_TOOLSETS', '')
                    if toolsets:
                        extra_headers['X-MCP-Toolsets'] = toolsets
                    readonly = os.getenv('GITHUB_MCP_SERVER_READONLY', '')
                    if readonly:
                        extra_headers['X-MCP-Readonly'] = readonly
                    if extra_headers:
                        tool_copy['headers'] = extra_headers
                    self.logger.info("Injected GitHub MCP authorization and headers")
            
            processed_tools.append(tool_copy)
        
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
            f"**Temperature:** {self.temperature}",
            f"**Max iterations:** {self.max_infer_iters}",
            f"\n**Step 1 - Generate Resources:**",
            f"  - Tools: {self.config_generate_resources['tools']}",
            f"\n**Step 2 - Generate Helm:**",
            f"  - Tools: {self.config_generate_helm['tools']}",
            f"\n**Step 3 - Generate ArgoCD:**",
            f"  - Tools: {self.config_generate_argocd['tools']}",
        ]
        
        return "  \n".join(config_lines)

    def _call_responses_api(self, user_message: str, config: dict) -> str:
        """Call the /v1/responses API directly
        
        Args:
            user_message: The user's message/prompt
            config: Configuration dict with tools and prompt
            
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
            response = self.client.responses.create(
                model=self.model,
                input=user_message,
                instructions=instructions,
                tools=tools if tools else None,
                temperature=self.temperature,
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

    # ------------------------------------------------------------------ #
    #  Pipeline Step 1 – Fetch resources directly from the cluster via oc  #
    # ------------------------------------------------------------------ #

    def _fetch_cluster_resources(
        self, namespace: str, workload_type: str, supporting_resources: List[str]
    ) -> List[dict]:
        """Fetch raw Kubernetes resources from the cluster using ``oc``/``kubectl``.

        Returns a list of individual resource dicts (the JSON representation
        returned by the Kubernetes API).
        """
        kube_cli = os.getenv("KUBE_CLI", "oc")
        types_to_fetch = [workload_type] + list(supporting_resources)
        resources: List[dict] = []

        for rtype in types_to_fetch:
            if rtype not in self._resource_type_map:
                self.logger.warning(f"Unknown resource type '{rtype}', skipping")
                continue

            # ConfigMaps are handled separately via auto-discovery to avoid
            # pulling system ConfigMaps (kube-root-ca.crt, trusted-ca-bundle, etc.)
            if rtype == "ConfigMap":
                continue

            _, _, plural = self._resource_type_map[rtype]
            cmd = [kube_cli, "get", plural, "-n", namespace, "-o", "json"]
            self.logger.info(f"Running: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.warning(
                    f"oc get {plural} failed (rc={result.returncode}): {result.stderr.strip()}"
                )
                continue

            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                self.logger.error(f"Failed to parse JSON from oc get {plural}: {exc}")
                continue

            items = data.get("items", [])
            self.logger.info(f"  Found {len(items)} {plural} in namespace '{namespace}'")
            resources.extend(items)

        # Only fetch ConfigMaps that are actually referenced by workloads.
        # A bulk fetch would pull system ConfigMaps (kube-root-ca.crt,
        # trusted-ca-bundle, odh-*, etc.) that are irrelevant and can
        # contain huge CA certificate bundles that break the LLM.
        if "ConfigMap" in types_to_fetch:
            discovered = self._discover_referenced_configmaps(resources, namespace)
            resources.extend(discovered)
            self.logger.info(
                f"  Found {len(discovered)} application ConfigMap(s) referenced by workloads"
            )

        return resources

    def _discover_referenced_configmaps(
        self, resources: List[dict], namespace: str
    ) -> List[dict]:
        """Scan workloads for configMapRef / configMapKeyRef and fetch any
        ConfigMaps that were not already retrieved."""
        existing_cm_names = {
            r["metadata"]["name"]
            for r in resources
            if r.get("kind") == "ConfigMap"
        }
        referenced_names: set = set()

        for res in resources:
            kind = res.get("kind", "")
            if kind not in ("Deployment", "StatefulSet"):
                continue
            containers = (
                res.get("spec", {})
                .get("template", {})
                .get("spec", {})
                .get("containers", [])
            )
            for container in containers:
                for env_from in container.get("envFrom", []):
                    cm_ref = env_from.get("configMapRef", {})
                    if cm_ref.get("name"):
                        referenced_names.add(cm_ref["name"])
                for env_var in container.get("env", []):
                    vf = env_var.get("valueFrom", {})
                    cm_key = vf.get("configMapKeyRef", {})
                    if cm_key.get("name"):
                        referenced_names.add(cm_key["name"])
            volumes = (
                res.get("spec", {})
                .get("template", {})
                .get("spec", {})
                .get("volumes", [])
            )
            for vol in volumes:
                cm_vol = vol.get("configMap", {})
                if cm_vol.get("name"):
                    referenced_names.add(cm_vol["name"])

        missing = referenced_names - existing_cm_names
        if not missing:
            return []

        self.logger.info(
            f"Auto-discovered {len(missing)} referenced ConfigMaps: {missing}"
        )
        kube_cli = os.getenv("KUBE_CLI", "oc")
        discovered: List[dict] = []
        for name in missing:
            cmd = [kube_cli, "get", "configmap", name, "-n", namespace, "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                try:
                    discovered.append(json.loads(result.stdout))
                except json.JSONDecodeError:
                    pass
            else:
                self.logger.warning(f"Could not fetch ConfigMap '{name}': {result.stderr.strip()}")
        return discovered

    # ------------------------------------------------------------------ #
    #  Pipeline Step 2 – Deterministic YAML cleanup in pure Python         #
    # ------------------------------------------------------------------ #

    _METADATA_KEYS_TO_REMOVE = {
        "namespace", "resourceVersion", "uid", "creationTimestamp",
        "generation", "managedFields", "selfLink", "finalizers",
        "ownerReferences",
    }

    _ANNOTATION_PATTERNS_TO_REMOVE = [
        re.compile(r"^kubectl\.kubernetes\.io/"),
        re.compile(r"^argocd\.argoproj\.io/"),
        re.compile(r"^deployment\.kubernetes\.io/"),
        re.compile(r"^kubernetes\.io/"),
        re.compile(r"^openshift\.io/"),
    ]

    def _clean_resource(self, resource: dict) -> dict:
        """Apply deterministic cleanup rules to a single resource dict.

        Removes cluster-specific metadata, status, system annotations, and
        kind-specific fields (clusterIP for Services, spec.host for Routes).
        """
        res = json.loads(json.dumps(resource))  # deep copy

        # --- metadata cleanup ---
        meta = res.get("metadata", {})
        for key in list(meta.keys()):
            if key in self._METADATA_KEYS_TO_REMOVE:
                del meta[key]

        annotations = meta.get("annotations", {})
        if annotations:
            for key in list(annotations.keys()):
                if any(p.match(key) for p in self._ANNOTATION_PATTERNS_TO_REMOVE):
                    del annotations[key]
            if not annotations:
                del meta["annotations"]

        # --- remove entire status section ---
        res.pop("status", None)

        # --- remove creationTimestamp from pod template ---
        tmpl_meta = (
            res.get("spec", {})
            .get("template", {})
            .get("metadata", {})
        )
        tmpl_meta.pop("creationTimestamp", None)

        kind = res.get("kind", "")

        # --- Service-specific ---
        if kind == "Service":
            spec = res.get("spec", {})
            spec.pop("clusterIP", None)
            spec.pop("clusterIPs", None)

        # --- Route-specific ---
        if kind == "Route":
            spec = res.get("spec", {})
            spec.pop("host", None)

        return res

    @staticmethod
    def _resource_to_yaml(resource: dict) -> str:
        """Convert a resource dict to a clean YAML string."""
        return yaml.dump(resource, default_flow_style=False, sort_keys=False).rstrip()

    # ------------------------------------------------------------------ #
    #  Pipeline Step 3 – LLM best-practices enhancement via RAG           #
    # ------------------------------------------------------------------ #

    def _apply_best_practices(self, resource_yaml: str, resource_kind: str) -> str:
        """Call the Responses API with file_search only to enhance a single
        resource with best-practice recommendations from RAG docs."""
        message = (
            f"Here is a pre-cleaned Kubernetes {resource_kind} YAML resource.\n"
            f"Apply best practices from the documentation and return ONLY the improved YAML.\n\n"
            f"{resource_yaml}"
        )
        return self._call_responses_api(message, self.config_apply_best_practices)

    # ------------------------------------------------------------------ #
    #  Orchestrator – generate_resources (generator with yield)            #
    # ------------------------------------------------------------------ #

    def generate_resources(
        self, namespace: str, helm_chart: str, workload_type: str, supporting_resources: List[str]
    ) -> Generator[str, None, None]:
        """Multi-step pipeline: fetch -> clean -> apply best practices.

        Yields progress messages so Gradio can stream updates to the UI.
        """
        self.logger.info("Step 1 - Generate Resources (multi-step pipeline):")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  Helm Chart: {helm_chart}")
        self.logger.info(f"  Workload Type: {workload_type}")
        self.logger.info(f"  Supporting Resources: {supporting_resources}")

        progress_lines: List[str] = []

        def _progress(msg: str) -> str:
            progress_lines.append(msg)
            return "\n".join(progress_lines)

        # -- Step 1: Fetch --
        yield _progress(f"Fetching resources from namespace '{namespace}'...")
        try:
            raw_resources = self._fetch_cluster_resources(namespace, workload_type, supporting_resources)
        except Exception as exc:
            yield _progress(f"ERROR fetching resources: {exc}")
            return

        kind_counts: dict[str, int] = {}
        for r in raw_resources:
            k = r.get("kind", "Unknown")
            kind_counts[k] = kind_counts.get(k, 0) + 1
        summary = ", ".join(f"{v} {k}(s)" for k, v in kind_counts.items())
        yield _progress(f"  Found: {summary}")

        if not raw_resources:
            yield _progress("No resources found. Check namespace and resource types.")
            return

        # -- Step 2: Deterministic clean --
        yield _progress("Cleaning resources (removing cluster-specific metadata)...")
        cleaned_resources: List[dict] = []
        for r in raw_resources:
            cleaned_resources.append(self._clean_resource(r))
        yield _progress(f"  Cleaned {len(cleaned_resources)} resources")

        # -- Step 3: LLM best-practices enhancement --
        total = len(cleaned_resources)
        enhanced_yamls: List[str] = []
        for idx, res in enumerate(cleaned_resources, start=1):
            kind = res.get("kind", "Unknown")
            name = res.get("metadata", {}).get("name", "unknown")
            yield _progress(f"Applying best practices to {kind} '{name}' ({idx}/{total})...")
            res_yaml = self._resource_to_yaml(res)
            try:
                enhanced = self._apply_best_practices(res_yaml, kind)
                enhanced_yamls.append(enhanced.strip())
            except Exception as exc:
                self.logger.error(f"LLM enhancement failed for {kind}/{name}: {exc}")
                yield _progress(f"  WARNING: LLM enhancement failed for {kind} '{name}', using cleaned version")
                enhanced_yamls.append(res_yaml)

        yield _progress(f"Done. {total} resources processed.\n")

        # -- Combine final output --
        final_yaml = "\n---\n".join(enhanced_yamls)
        final_output = "---\n" + final_yaml + "\n"
        self.logger.info(f"Step 1 completed. Generated {len(final_output)} characters of YAML")
        yield final_output

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
        """Step 2: Generate Helm chart from the Kubernetes resources in content_area."""
        chart_name = helm_chart if helm_chart else namespace
        self.logger.info(f"Step 2 - Generate Helm Chart:")
        self.logger.info(f"  Chart Name: {chart_name}")
        self.logger.info(f"  Resources YAML Length: {len(resources_yaml) if resources_yaml else 0} characters")

        message = (
            f"Generate a Helm chart named '{chart_name}' from these Kubernetes resources:\n\n"
            f"{resources_yaml if resources_yaml else 'No resources provided.'}"
        )

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

    # ------------------------------------------------------------------ #
    #  Helm chart content parser                                           #
    # ------------------------------------------------------------------ #

    _SOURCE_HEADER_RE = re.compile(r"^#\s*Source:\s*[^/\s]+/(.+)$")
    _CODE_FENCE_RE = re.compile(r"^```\w*\s*$")

    def _parse_helm_chart_files(self, content: str) -> dict[str, str]:
        """Parse the Helm chart text output into individual files.

        The LLM output uses ``# Source: <chart>/<path>`` headers to delimit
        each file, with optional markdown code fences wrapping the content.
        Returns a dict mapping file path to its content.
        """
        files: dict[str, str] = {}
        current_path: str | None = None
        lines_buf: list[str] = []

        for line in content.splitlines():
            header_match = self._SOURCE_HEADER_RE.match(line.strip())
            if header_match:
                if current_path is not None:
                    files[current_path] = "\n".join(lines_buf).strip()
                current_path = header_match.group(1)
                lines_buf = []
                continue

            if self._CODE_FENCE_RE.match(line.strip()):
                continue

            if current_path is not None:
                lines_buf.append(line)

        if current_path is not None:
            files[current_path] = "\n".join(lines_buf).strip()

        return files

    # ------------------------------------------------------------------ #
    #  Step 3 – Push Helm chart files to GitHub via REST API               #
    #                                                                      #
    #  [MCP-GITHUB-ALTERNATIVE] This step uses PyGithub directly because   #
    #  the deployed Llama Stack server only supports SSE transport for MCP  #
    #  tools, while GitHub Copilot MCP requires Streamable HTTP.           #
    #  When the Llama Stack image is upgraded (PR #2554, July 2025+),      #
    #  this can be replaced with a _call_responses_api() call using the    #
    #  MCP GitHub tool. See form_push_github_prompt.md for the prompt,     #
    #  and run-local.sh / values.yaml for the commented-out tool config.   #
    # ------------------------------------------------------------------ #

    def push_github(
        self, namespace: str, helm_chart: str, application_content: str
    ) -> Generator[str, None, None]:
        """Parse the Helm chart into individual files and push them to GitHub.

        Uses the GitHub REST API (PyGithub) directly instead of the LLM+MCP
        approach, since the Llama Stack MCP client does not support the
        Streamable HTTP transport required by the GitHub Copilot MCP endpoint.

        Yields progress messages so Gradio can stream updates.
        """
        from github import Github, GithubException

        chart_name = helm_chart if helm_chart else namespace
        self.logger.info("Step 3 - Push to GitHub:")
        self.logger.info(f"  Chart Name: {chart_name}")
        self.logger.info(f"  Repository URL: {self.github_gitops_repo}")
        self.logger.info(
            f"  Content Length: {len(application_content) if application_content else 0} characters"
        )

        progress_lines: list[str] = []

        def _progress(msg: str) -> str:
            progress_lines.append(msg)
            return "\n".join(progress_lines)

        # -- Validate prerequisites --
        github_pat = os.getenv("GITHUB_PAT", "")
        if not github_pat:
            yield _progress("ERROR: GITHUB_PAT environment variable is not set.")
            return
        if not self.github_gitops_repo:
            yield _progress("ERROR: GITHUB_GITOPS_REPO environment variable is not set.")
            return

        # -- Step 1: Parse the Helm chart output into individual files --
        yield _progress("Parsing Helm chart files...")
        files = self._parse_helm_chart_files(application_content)

        if not files:
            yield _progress(
                "ERROR: Could not parse any files from the Helm chart output. "
                "Make sure you have generated a Helm chart first."
            )
            return

        file_list = "\n".join(f"  - {path}" for path in files)
        yield _progress(f"  Found {len(files)} files:\n{file_list}")

        # -- Step 2: Push files via GitHub REST API --
        repo_url = self.github_gitops_repo.rstrip("/")
        repo_slug = "/".join(repo_url.split("/")[-2:])
        if repo_slug.endswith(".git"):
            repo_slug = repo_slug[:-4]

        yield _progress(f"Connecting to repo '{repo_slug}' ...")

        try:
            gh = Github(github_pat)
            repo = gh.get_repo(repo_slug)
        except GithubException as exc:
            self.logger.error(f"GitHub connection failed: {exc}")
            yield _progress(f"ERROR connecting to GitHub: {exc}")
            return

        branch = "main"
        commit_message = f"Deploy Helm chart '{chart_name}'"
        pushed_files: list[str] = []
        errors: list[str] = []

        for path, file_content in files.items():
            repo_path = f"{chart_name}/charts/{path}"
            yield _progress(f"  Pushing {repo_path} ...")
            try:
                existing = repo.get_contents(repo_path, ref=branch)
                repo.update_file(
                    repo_path, commit_message, file_content,
                    existing.sha, branch=branch,
                )
            except GithubException as exc:
                if exc.status == 404:
                    repo.create_file(
                        repo_path, commit_message, file_content,
                        branch=branch,
                    )
                else:
                    self.logger.error(f"Failed to push {repo_path}: {exc}")
                    errors.append(f"{repo_path}: {exc}")
                    continue
            pushed_files.append(repo_path)

        gh.close()

        if errors:
            error_detail = "\n".join(f"  - {e}" for e in errors)
            yield _progress(f"Completed with {len(errors)} error(s):\n{error_detail}")
        else:
            yield _progress(
                f"Done. Pushed {len(pushed_files)} files to "
                f"'{repo_slug}' branch '{branch}'."
            )

        self.logger.info(
            f"✅ Step 3 completed. Pushed {len(pushed_files)} files, "
            f"{len(errors)} errors"
        )

    # ------------------------------------------------------------------ #
    #  Step 4 – Generate ArgoCD Application and push to GitHub             #
    #                                                                      #
    #  [ARGOCD-LLM-ALTERNATIVE] This step generates the ArgoCD            #
    #  Application YAML from a Python template (no LLM needed) and        #
    #  pushes it to {chart}/gitops/ in the GitOps repo. The previous      #
    #  LLM+MCP implementation is preserved in form_generate_argocd_prompt #
    #  .md, run-local.sh, and values.yaml for future reference.           #
    # ------------------------------------------------------------------ #

    _ARGOCD_APP_TEMPLATE = """\
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: {app_name}
  namespace: openshift-gitops
spec:
  project: default
  source:
    repoURL: {repo_url}
    targetRevision: main
    path: {chart_path}
  destination:
    server: https://kubernetes.default.svc
    namespace: {dest_namespace}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
"""

    def generate_argocd_app(
        self, namespace: str, helm_chart: str
    ) -> Generator[str, None, None]:
        """Step 4: Generate ArgoCD Application YAML and push it to GitHub."""
        from github import Github, GithubException

        chart_name = helm_chart if helm_chart else namespace
        dest_namespace = f"{namespace}-gitops"
        self.logger.info("Step 4 - Generate ArgoCD App:")
        self.logger.info(f"  Chart Name: {chart_name}")
        self.logger.info(f"  Destination Namespace: {dest_namespace}")
        self.logger.info(f"  Repository URL: {self.github_gitops_repo}")

        progress_lines: list[str] = []

        def _progress(msg: str) -> str:
            progress_lines.append(msg)
            return "\n".join(progress_lines)

        # -- Step 1: Generate the ArgoCD Application YAML --
        yield _progress("Generating ArgoCD Application manifest...")

        argocd_yaml = self._ARGOCD_APP_TEMPLATE.format(
            app_name=chart_name,
            repo_url=self.github_gitops_repo,
            chart_path=f"{chart_name}/charts",
            dest_namespace=dest_namespace,
        )

        yield _progress(f"  App name: {chart_name}")
        yield _progress(f"  Source path: {chart_name}/charts")
        yield _progress(f"  Destination namespace: {dest_namespace}")

        # -- Step 2: Push to GitHub --
        github_pat = os.getenv("GITHUB_PAT", "")
        if not github_pat:
            yield _progress("GITHUB_PAT not set — skipping push.")
            yield argocd_yaml
            return
        if not self.github_gitops_repo:
            yield _progress("GITHUB_GITOPS_REPO not set — skipping push.")
            yield argocd_yaml
            return

        repo_url = self.github_gitops_repo.rstrip("/")
        repo_slug = "/".join(repo_url.split("/")[-2:])
        if repo_slug.endswith(".git"):
            repo_slug = repo_slug[:-4]

        repo_path = f"{chart_name}/gitops/argocd-application.yaml"
        yield _progress(f"Pushing to '{repo_slug}' at {repo_path} ...")

        try:
            gh = Github(github_pat)
            repo = gh.get_repo(repo_slug)
            commit_msg = f"Deploy ArgoCD Application for '{chart_name}'"

            try:
                existing = repo.get_contents(repo_path, ref="main")
                repo.update_file(
                    repo_path, commit_msg, argocd_yaml,
                    existing.sha, branch="main",
                )
            except GithubException as exc:
                if exc.status == 404:
                    repo.create_file(
                        repo_path, commit_msg, argocd_yaml,
                        branch="main",
                    )
                else:
                    raise

            gh.close()
            yield _progress("Done. Rendering YAML...")
        except Exception as exc:
            self.logger.error(f"Push ArgoCD app to GitHub failed: {exc}")
            yield _progress(f"ERROR pushing to GitHub: {exc}")
            yield argocd_yaml
            return

        self.logger.info(
            f"✅ Step 4 completed. Pushed ArgoCD Application to {repo_path}"
        )
        yield argocd_yaml

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
