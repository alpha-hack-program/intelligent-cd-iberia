"""
MCP Test tab functionality for Intelligent CD Chatbot.

This module handles MCP server testing functionality with Llama Stack.
"""

import json
import gradio as gr
from llama_stack_client import LlamaStackClient
from utils import get_logger


class MCPTestTab:
    """Handles MCP testing functionality with Llama Stack"""
    
    def __init__(self, client: LlamaStackClient):
        self.client = client
        self.logger = get_logger("mcp")
    
    def list_toolgroups(self) -> gr.update:
        """List available MCP toolgroups through Llama Stack"""
        self.logger.debug("Attempting to list MCP toolgroups through Llama Stack...")
        
        # Use the shared client to get tools (which contain toolgroups)
        tools = self.client.tools.list()
        
        # Extract unique toolgroup IDs from tools
        toolgroups = list(set(tool.toolgroup_id for tool in tools))
        self.logger.info(f"Found {len(toolgroups)} toolgroups: {toolgroups}")
        
        return gr.update(choices=toolgroups, value=None)
    
    def get_toolgroup_methods(self, toolgroup_name: str) -> tuple[str, gr.update]:
        """Get methods for a specific toolgroup through Llama Stack"""
        if not toolgroup_name:
            return (
                "❌ Please select a toolgroup first",
                gr.update(choices=[], value=None)
            )
        
        self.logger.debug(f"Getting methods for toolgroup: {toolgroup_name}")
        
        # Use the shared client to get tools for the specific toolgroup
        tools = self.client.tools.list()
        
        # Filter tools by toolgroup and extract individual tools
        methods = []
        for tool in tools:
            if hasattr(tool, 'toolgroup_id') and tool.toolgroup_id == toolgroup_name:
                # Check if this tool has individual tools/methods
                if hasattr(tool, 'tools') and tool.tools:
                    # Tool contains individual methods
                    for individual_tool in tool.tools:
                        method_name = getattr(individual_tool, 'name', getattr(individual_tool, 'identifier', 'Unknown'))
                        methods.append(method_name)
                else:
                    # This is a direct tool
                    method_name = getattr(tool, 'name', getattr(tool, 'identifier', 'Unknown'))
                    methods.append(method_name)
        
        self.logger.info(f"Found {len(methods)} methods: {methods}")
        
        # Update status to success
        status_text = f"✅ Found {len(methods)} methods in toolgroup '{toolgroup_name}'"
        
        return status_text, gr.update(choices=methods, value=None)
    
    def execute_tool(self, toolgroup_name: str, method_name: str, params_json: str) -> str:
        """Execute an MCP tool through Llama Stack using toolgroup and method"""
        if not toolgroup_name:
            return "❌ Please select a toolgroup first"
        
        if not method_name:
            return "❌ Please select a method first"
        
        try:
            # Parse parameters
            try:
                params = json.loads(params_json) if params_json.strip() else {}
            except json.JSONDecodeError:
                return "❌ Invalid JSON parameters. Please check your input."
            
            # Execute tool through Llama Stack using tool_runtime

            result = self.client.tool_runtime.invoke_tool(
                tool_name=method_name,
                kwargs=params,
            )
            
            if result:
                self.logger.debug(f"Result: {result}")
                # Extract the actual result data from ToolInvocationResult
                try:
                    # Handle ToolInvocationResult structure
                    if hasattr(result, 'content') and result.content:
                        # Extract text from TextContentItem objects
                        if isinstance(result.content, list):
                            text_parts = []
                            for item in result.content:
                                if hasattr(item, 'text'):
                                    text_parts.append(item.text)
                                else:
                                    text_parts.append(str(item))
                            result_data = '\n'.join(text_parts)
                        else:
                            result_data = str(result.content)
                    elif hasattr(result, 'text'):
                        result_data = result.text
                    elif hasattr(result, 'data'):
                        result_data = result.data
                    else:
                        # Fallback: convert to string representation
                        result_data = str(result)
                    
                    # Try to format as JSON if it's a dict/list, otherwise use string
                    if isinstance(result_data, (dict, list)):
                        formatted_result = json.dumps(result_data, indent=2)
                    else:
                        formatted_result = str(result_data)
                        
                    return f"✅ Method '{method_name}' from toolgroup '{toolgroup_name}' executed successfully:\n\n```\n{formatted_result}\n```"
                except Exception as format_error:
                    # If JSON formatting fails, return as string
                    return f"✅ Method '{method_name}' from toolgroup '{toolgroup_name}' executed successfully:\n\n```\n{str(result)}\n```"
            else:
                return f"❌ Method '{method_name}' from toolgroup '{toolgroup_name}' failed: No result returned"
                
        except Exception as e:
            return f"❌ Error executing method '{method_name}' from toolgroup '{toolgroup_name}': {str(e)}"
