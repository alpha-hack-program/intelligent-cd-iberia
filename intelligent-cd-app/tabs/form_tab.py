"""
Form tab functionality for Intelligent CD Chatbot.

This module handles the form-based resource generation functionality.
"""

import os
import json
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
        tools_str = os.getenv("FORM_TOOLS", "{}")
        tools = json.loads(tools_str)
        
        # Load model prompt
        model_prompt = os.getenv("FORM_PROMPT", "You are a helpful assistant.")
        
        # Debug logging
        self.logger.debug(f"FORM_SAMPLING_PARAMS: {sampling_params}")
        self.logger.debug(f"FORM_TOOLS: {tools}")
        self.logger.debug(f"FORM_PROMPT: {str(model_prompt)[:200]}...")
        
        return sampling_params, tools, model_prompt

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


















    def apply_yaml(self, yaml_content: str) -> str:
        """Apply YAML content to OpenShift cluster"""
        self.logger.info(f"Apply YAML request received:")
        self.logger.info(f"  YAML Content Length: {len(yaml_content)} characters")

        result = f"""🔧 Apply YAML to OpenShift:

**YAML Content Length:** {len(yaml_content)} characters
**Status:** Placeholder function - not yet implemented

**Next Steps:**
- Parse and validate YAML content
- Use MCP tools to apply resources to OpenShift cluster
- Return status and applied resource information
- Handle errors and provide feedback

**YAML Content Preview:**
```yaml
{yaml_content[:500]}{'...' if len(yaml_content) > 500 else ''}
```

**Apply YAML Function Logged Successfully!** ✅"""
        
        return result

    def generate_helm(self, namespace: str, helm_chart: str, workload_type: str, supporting_resources: List[str]) -> str:
        """Generate Helm chart based on form inputs"""
        self.logger.info(f"Generate Helm request received:")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  Helm Chart: {helm_chart}")
        self.logger.info(f"  Workload Type: {workload_type}")
        self.logger.info(f"  Supporting Resources: {supporting_resources}")

        # Combine workload type and supporting resources for display
        all_resources = [workload_type] + supporting_resources if workload_type else supporting_resources

        result = f"""📦 Generate Helm Chart:

**Namespace:** {namespace}
**Helm Chart:** {helm_chart if helm_chart else 'None (will generate new chart)'}
**Workload Type:** {workload_type if workload_type else 'None'}
**Supporting Resources:** {', '.join(supporting_resources) if supporting_resources else 'None'}
**All Resources:** {', '.join(all_resources) if all_resources else 'None'}

**Status:** Placeholder function - not yet implemented

**Next Steps:**
- Generate Helm chart structure
- Create templates for selected resource types
- Generate values.yaml with namespace configuration
- Package chart and provide download/instructions

**Generate Helm Function Logged Successfully!** ✅"""
        
        return result

    def apply_helm(self, helm_chart: str, namespace: str, values: str = "") -> str:
        """Apply Helm chart to OpenShift cluster"""
        self.logger.info(f"Apply Helm request received:")
        self.logger.info(f"  Helm Chart: {helm_chart}")
        self.logger.info(f"  Namespace: {namespace}")
        self.logger.info(f"  Values: {values if values else 'None'}")

        result = f"""🚀 Apply Helm Chart to OpenShift:

**Helm Chart:** {helm_chart}
**Namespace:** {namespace}
**Values:** {values if values else 'None (using default values)'}

**Status:** Placeholder function - not yet implemented

**Next Steps:**
- Validate Helm chart and values
- Use MCP tools to install/upgrade chart in OpenShift
- Monitor deployment status
- Return installation results and status

**Apply Helm Function Logged Successfully!** ✅"""
        
        return result


