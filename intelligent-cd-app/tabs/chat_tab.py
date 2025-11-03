"""
Chat tab functionality for Intelligent CD Chatbot.

This module handles the main chat interface with LLM using ReAct methodology.
"""

import os
import json
import ast
import random
import string
from typing import List, Dict
from llama_stack_client import LlamaStackClient
from llama_stack_client.lib.agents.react.agent import ReActAgent
from llama_stack_client.lib.agents.react.tool_parser import ReActOutput
from utils import get_logger


class ChatTab:
    """Handles chat functionality with Llama Stack LLM"""
    
    def __init__(self, client: LlamaStackClient, model: str):
        self.client = client
        self.model = model
        self.logger = get_logger("chat")
        self.max_infer_iters = int(os.getenv("CHAT_MAX_INFER_ITERS", "15"))
        
        # Load configuration from environment variables
        self.sampling_params, self.tools_json, self.model_prompt = self._load_config()

        # Initialize agent and session for the entire chat
        self.agent, self.session_id = self._initialize_agent()
    
    def _load_config(self) -> tuple[dict, list, str]:
        """Load all configuration from environment variables"""
        # Load sampling parameters
        sampling_params_str = os.getenv("CHAT_SAMPLING_PARAMS", "{}")
        sampling_params = json.loads(sampling_params_str)
        
        # Load tools
        tools_str = os.getenv("CHAT_TOOLS", "[]")
        
        # Try to parse as JSON first, fall back to Python literal
        try:
            tools = json.loads(tools_str)
        except json.JSONDecodeError:
            try:
                # Handle Python syntax with single quotes
                tools = ast.literal_eval(tools_str)
            except (ValueError, SyntaxError) as e:
                self.logger.error(f"Failed to parse CHAT_TOOLS: {e}")
                tools = []
        
        # Process tools to convert vector_db_names to vector_db_ids
        tools = self._process_tools(tools)
        
        # Load model prompt
        model_prompt = os.getenv("CHAT_PROMPT", "You are a helpful assistant.")
        
        # Debug logging
        self.logger.debug(f"CHAT_SAMPLING_PARAMS: {sampling_params}")
        self.logger.debug(f"CHAT_TOOLS: {tools}")
        self.logger.debug(f"CHAT_PROMPT: {str(model_prompt)[:200]}...")
        
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

    def _initialize_agent(self) -> tuple[ReActAgent, str]:
        """Initialize agent and session that will be reused for the entire chat"""

        formatted_prompt = self.model_prompt.format(tool_groups=self.tools_json)

        # Log agent creation details
        self.logger.info("=" * 60)
        self.logger.info("Creating Chat Tab ReActAgent")
        self.logger.info("=" * 60)
        self.logger.info(f"Model: {self.model}")
        self.logger.info(f"Toolgroups available ({len(self.tools_json)}): {self.tools_json}")
        self.logger.info(f"Max infer iters: {self.max_infer_iters}")
        self.logger.info(f"Sampling params: {self.sampling_params}")

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
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        session_name = f"OCP_Chat_Session_{random_suffix}"
        session = agent.create_session(session_name=session_name)
        
        # Handle both object with .id attribute and direct string return
        if hasattr(session, 'id'):
            session_id = session.id
        else:
            session_id = str(session)
        
        self.logger.info(f"✅ Session created: {session_id}")
        self.logger.info("=" * 60)
        return agent, session_id
    
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
    
    def chat_completion(self, message: str, chat_history: List[Dict[str, str]]) -> tuple:
        """Handle chat with LLM using Agent → Session → Turn structure"""
        from gradio import ChatMessage
        
        # Add user message to history
        chat_history.append(ChatMessage(role="user", content=message))
        
        # Get LLM response using Agent API with thinking steps
        result, thinking_steps = self._execute_agent_turn_with_thinking(message)
        
        # Add thinking steps as collapsible sections
        if thinking_steps:
            for i, step in enumerate(thinking_steps):
                chat_history.append(ChatMessage(
                    role="assistant", 
                    content=step["content"],
                    metadata={"title": step["title"]}
                ))
        
        # Add final assistant response
        chat_history.append(ChatMessage(role="assistant", content=result))
        
        return chat_history, ""
    
    def _execute_agent_turn_with_thinking(self, message: str) -> tuple[str, list]:
        """Execute agent turn and capture thinking steps for display"""
        import json
        self.logger.debug(f"Executing agent turn with thinking capture")
        
        thinking_steps = []
        
        try:
            response = self.agent.create_turn(
                messages=[
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                session_id=self.session_id,
                stream=False,  # Keep non-streaming for now
            )
            
            # Log response structure for debugging
            self.logger.info("=" * 60)
            self.logger.info("Response Structure Analysis:")
            self.logger.info("=" * 60)
            
            # Log all steps if available
            if hasattr(response, 'steps') and response.steps:
                self.logger.info(f"Number of steps: {len(response.steps)}")
                for i, step in enumerate(response.steps):
                    self.logger.debug(f"Step {i}: {step}")
            
            # Get final response content - extract only the answer part
            final_content = ""
            if hasattr(response, 'output_message') and hasattr(response.output_message, 'content'):
                try:
                    # Try to parse as JSON to extract just the answer
                    content_json = json.loads(response.output_message.content)
                    if 'answer' in content_json and content_json['answer']:
                        final_content = content_json['answer']
                    else:
                        final_content = response.output_message.content
                except json.JSONDecodeError:
                    # If not JSON, use the content as-is
                    final_content = response.output_message.content
            else:
                final_content = str(response)
            
            self.logger.info(f"Captured {len(thinking_steps)} thinking steps")
            self.logger.info(f"Final content length: {len(final_content)} characters")
            return final_content, thinking_steps
            
        except Exception as e:
            self.logger.error(f"Error in agent turn: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error: {str(e)}", []
