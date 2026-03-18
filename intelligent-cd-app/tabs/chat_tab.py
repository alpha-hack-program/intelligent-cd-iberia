"""
Chat tab functionality for Intelligent CD Chatbot.

This module handles the main chat interface with LLM using the /v1/responses API.
"""

import os
import json
from typing import List, Dict
from llama_stack_client import LlamaStackClient
from utils import get_logger


class ChatTab:
    """Handles chat functionality with Llama Stack LLM"""
    
    def __init__(self, client: LlamaStackClient, model: str):
        self.client = client
        self.model = model
        self.logger = get_logger("chat")
        self.temperature = float(os.getenv("TEMPERATURE", "0.1"))
        self.max_infer_iters = int(os.getenv("MAX_INFER_ITERS", "30"))
        self._previous_response_id = None
        
        self.tools, self.model_prompt = self._load_config()
    
    def _load_config(self) -> tuple[list, str]:
        """Load tools and prompt from environment variables"""
        tools_str = os.getenv("CHAT_TOOLS", "[]")
        
        try:
            tools = json.loads(tools_str)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse CHAT_TOOLS: {e}")
            tools = []
        
        tools = self._process_tools(tools)
        
        prompt_file = os.getenv("CHAT_PROMPT_FILE", "")
        if prompt_file:
            try:
                with open(prompt_file, 'r') as f:
                    model_prompt = f.read()
            except Exception as e:
                self.logger.warning(f"Failed to read prompt file {prompt_file}: {e}, using env var")
                model_prompt = os.getenv("CHAT_PROMPT", "You are a helpful assistant.")
        else:
            model_prompt = os.getenv("CHAT_PROMPT", "You are a helpful assistant.")
        
        self.logger.debug(f"CHAT_TOOLS: {tools}")
        self.logger.debug(f"CHAT_PROMPT: {str(model_prompt)[:200]}...")
        
        return tools, model_prompt
    
    def _process_tools(self, tools: list) -> list:
        """Process tools: resolve vector_db_names and inject auth headers for remote MCP servers."""
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
            vector_stores = list_response.data if hasattr(list_response, 'data') else list_response
            
            for vs in vector_stores:
                if vs.name == name:
                    self.logger.info(f"Found vector store '{name}' -> '{vs.id}'")
                    return vs.id
            
            self.logger.warning(f"Vector store '{name}' not found, using as ID")
            return name
        except Exception as e:
            self.logger.warning(f"Error looking up vector store by name '{name}': {str(e)}")
            return name
    
    def get_config_display(self) -> str:
        """Get formatted configuration for display in UI"""
        config_lines = [
            f"**Model:** {self.model}",
            f"**Tools:** {self.tools}",
            f"**Max iterations:** {self.max_infer_iters}",
            f"**Temperature:** {self.temperature}",
        ]
        
        return "  \n".join(config_lines)

    def reset_conversation(self):
        """Reset the conversation state, clearing the response chain."""
        self._previous_response_id = None
        self.logger.info("Conversation state reset (previous_response_id cleared)")

    def _call_responses_api(self, user_message: str) -> object:
        """Call the /v1/responses API and return the raw response object"""
        self.logger.info("=" * 60)
        self.logger.info("Calling /v1/responses API")
        self.logger.info("=" * 60)
        self.logger.info(f"Model: {self.model}")
        self.logger.info(f"Tools: {self.tools}")
        self.logger.info(f"Max infer iters: {self.max_infer_iters}")
        self.logger.info(f"Instructions length: {len(self.model_prompt)}")
        self.logger.info(f"Previous response ID: {self._previous_response_id}")
        self.logger.info(f"User message: {user_message[:200]}...")
        
        kwargs = dict(
            model=self.model,
            input=user_message,
            instructions=self.model_prompt,
            tools=self.tools if self.tools else None,
            temperature=self.temperature,
            include=["file_search_call.results"],
            max_infer_iters=self.max_infer_iters,
        )
        if self._previous_response_id:
            kwargs["previous_response_id"] = self._previous_response_id

        try:
            response = self.client.responses.create(**kwargs)
        except Exception as e:
            if self._previous_response_id:
                self.logger.warning(
                    f"Request with previous_response_id failed ({e}), retrying without it"
                )
                self._previous_response_id = None
                kwargs.pop("previous_response_id", None)
                response = self.client.responses.create(**kwargs)
            else:
                raise
        
        response_id = getattr(response, 'id', None)
        self.logger.info(f"Response received - status: {getattr(response, 'status', 'unknown')}")
        self.logger.info(f"Response ID: {response_id}")
        
        if response_id:
            self._previous_response_id = response_id
        
        if hasattr(response, 'output') and response.output:
            for i, item in enumerate(response.output):
                item_type = type(item).__name__
                self.logger.info(f"Output[{i}] type: {item_type}")
                if hasattr(item, 'type'):
                    self.logger.info(f"Output[{i}].type: {item.type}")
        
        return response

    def _extract_response_text(self, response) -> str:
        """Extract text content from the responses API response"""
        if hasattr(response, 'output_text') and response.output_text:
            self.logger.debug(f"Found output_text: {len(response.output_text)} chars")
            return response.output_text
        
        if hasattr(response, 'output') and response.output:
            texts = []
            for item in response.output:
                if hasattr(item, 'type') and item.type == 'message':
                    if hasattr(item, 'content') and item.content:
                        for content_item in item.content:
                            if hasattr(content_item, 'text') and content_item.text:
                                texts.append(content_item.text)
                            elif hasattr(content_item, 'type') and content_item.type == 'output_text':
                                if hasattr(content_item, 'text') and content_item.text:
                                    texts.append(content_item.text)
                elif hasattr(item, 'text') and item.text:
                    texts.append(item.text)
            
            if texts:
                result = '\n'.join(filter(None, texts))
                self.logger.debug(f"Extracted {len(texts)} text segments, total {len(result)} chars")
                return result
        
        self.logger.warning("Could not extract text from response")
        return ""

    def _extract_thinking_steps(self, response) -> list:
        """Extract tool call information as thinking steps from the response output"""
        thinking_steps = []
        
        if not hasattr(response, 'output') or not response.output:
            return thinking_steps
        
        for item in response.output:
            item_type = type(item).__name__
            
            if 'McpCall' in item_type or (hasattr(item, 'type') and item.type == 'mcp_call'):
                title = "🔧 MCP Tool Call"
                content = ""
                if hasattr(item, 'server_label'):
                    title = f"🔧 MCP: {item.server_label}"
                if hasattr(item, 'name'):
                    content += f"**Tool:** {item.name}\n"
                if hasattr(item, 'arguments'):
                    args_str = json.dumps(item.arguments, indent=2) if isinstance(item.arguments, dict) else str(item.arguments)
                    content += f"**Arguments:**\n```json\n{args_str}\n```\n"
                if hasattr(item, 'output'):
                    output_str = str(item.output)[:500]
                    content += f"**Output:**\n```\n{output_str}\n```"
                thinking_steps.append({"title": title, "content": content})
            
            elif hasattr(item, 'type') and item.type == 'file_search_call':
                title = "🔍 File Search"
                content = ""
                if hasattr(item, 'queries'):
                    content += f"**Queries:** {item.queries}\n"
                if hasattr(item, 'results') and item.results:
                    content += f"**Results:** {len(item.results)} documents found"
                thinking_steps.append({"title": title, "content": content})
        
        return thinking_steps
    
    def chat_completion(self, message: str, chat_history: List[Dict[str, str]]) -> tuple:
        """Handle chat with LLM using /v1/responses API"""
        from gradio import ChatMessage
        
        chat_history.append(ChatMessage(role="user", content=message))
        
        try:
            response = self._call_responses_api(message)
            
            thinking_steps = self._extract_thinking_steps(response)
            
            result = self._extract_response_text(response)
            if not result:
                self.logger.warning("No output_text found, using str(response)")
                result = str(response)
            
            self.logger.info(f"✅ Response extracted: {len(result)} characters")
            
        except Exception as e:
            self.logger.error(f"Error calling /v1/responses API: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            result = f"Error: {str(e)}"
            thinking_steps = []
        
        if thinking_steps:
            for step in thinking_steps:
                chat_history.append(ChatMessage(
                    role="assistant", 
                    content=step["content"],
                    metadata={"title": step["title"]}
                ))
        
        chat_history.append(ChatMessage(role="assistant", content=result))
        
        return chat_history, ""
