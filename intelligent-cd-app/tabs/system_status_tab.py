"""
System Status tab functionality for Intelligent CD Chatbot.

This module handles system status monitoring and health checks.
"""

import os
from llama_stack_client import LlamaStackClient
from utils import get_logger


class SystemStatusTab:
    """Handles system status functionality"""
    
    def __init__(self, client: LlamaStackClient, llama_stack_url: str, model: str):
        self.client = client
        self.llama_stack_url = llama_stack_url
        self.model = model
        self.vector_store_name = os.getenv("RAG_TEST_TAB_VECTOR_DB_NAME", "app-documentation")
        self.logger = get_logger("system")  
    
    def get_gradio_status(self) -> str:
        """Get Gradio application status"""
        return "✅ Gradio Application: Running and accessible"
    
    def get_llama_stack_status(self) -> list[str]:
        """Get Llama Stack server health and version information"""
        llama_stack_status = []
        llama_stack_status.append("🚀 Llama Stack Server:")
        llama_stack_status.append(f"   • URL: {self.llama_stack_url}")
        
        try:
            # Get version information
            version_info = self.client.inspect.version()
            llama_stack_status.append(f"   • Version: ✅ {version_info.version}")
            
            # Get health information
            health_info = self.client.inspect.health()
            llama_stack_status.append(f"   • Health: ✅ {health_info.status}")
            
        except Exception as e:
            llama_stack_status.append("   • Status: ❌ Failed to connect to Llama Stack server")
            llama_stack_status.append(f"   • Error: {str(e)}")
        
        return llama_stack_status
    
    def get_llm_status(self) -> list[str]:
        """Get LLM service status and test connectivity"""
        llm_status = []
        llm_status.append("🤖 LLM Service (Inference):")
        
        # Test LLM connectivity with a direct chat.completions.create request
        try:
            test_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Hello, this is a test message."}
                ],
                temperature=0.7,
                max_tokens=100,
                stream=False,
            )
            llm_status.append("   • Status: ✅ LLM service responding")
            llm_status.append(f"   • Model: {self.model}")
        except Exception as e:
            llm_status.append("   • Status: ❌ LLM service not responding")
            llm_status.append(f"   • Error: {str(e)}")
            test_response = None
        
        # Extract response content for length calculation
        if hasattr(test_response, 'messages') and test_response.messages:
            last_message = test_response.messages[-1]
            response_content = getattr(last_message, 'content', str(last_message))
        else:
            response_content = str(test_response)
        
        llm_status.append(f"   • Response: ✅ Received {len(response_content)} characters")
        
        return llm_status
    
    def get_rag_status(self) -> list[str]:
        """Get RAG server status and vector database availability"""
        rag_status = []
        rag_status.append("📚 RAG Server:")
        
        # Check 1: Test connection by calling list()
        try:
            list_response = self.client.vector_stores.list()
            rag_status.append("   • Connection: ✅ RAG backend responding")
        except Exception as e:
            rag_status.append("   • Connection: ❌ Failed to connect to RAG backend")
            rag_status.append(f"   • Error: {str(e)}")
            return rag_status
        
        # Check 2: Check if self.vector_store_name is included in the list by name
        vector_store_found = False
        for vs in list_response:
            if vs.name == self.vector_store_name:
                vector_store_found = True
                break
        
        if vector_store_found:
            rag_status.append(f"   • Target DB: ✅ Vector Store '{self.vector_store_name}' found in list")
        else:
            rag_status.append(f"   • Target DB: ❌ Vector Store '{self.vector_store_name}' not found in list")
        
        # Check 3: Show all vector stores with ID and Name
        vector_stores_list = list(list_response) if list_response else []
        if vector_stores_list:
            rag_status.append(f"   • Available DBs: Found {len(vector_stores_list)} vector database(s)")
            rag_status.append("   • DB Details:")
            for vs in vector_stores_list:
                rag_status.append(f"      - Name: {vs.name}")
                rag_status.append(f"        ID:   {vs.id}")
        else:
            rag_status.append("   • Available DBs: No vector databases found")

        return rag_status
    
    def get_mcp_status(self) -> list[str]:
        """Get MCP server status and tool information"""
        mcp_status = []
        mcp_status.append("☸️ MCP Server:")
        
        # Test MCP connection directly
        self.logger.debug("Testing MCP connection directly...")
        try:
            # Test if we can list tools
            tools = self.client.tools.list()
            self.logger.info(f"MCP tools.list() returned: {len(tools)} tools")
            
            # Test if we can invoke a simple tool
            if tools:
                first_tool = tools[0]
                self.logger.debug(f"First tool: {first_tool}")
                if hasattr(first_tool, 'name'):
                    self.logger.debug(f"First tool name: {first_tool.name}")
        except Exception as e:
            self.logger.error(f"MCP test failed: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # List tools to check MCP server connectivity
        tools = self.client.tools.list()
        
        # Extract unique toolgroup IDs
        toolgroups = list(set(tool.toolgroup_id for tool in tools))
        mcp_status.append("   • Status: ✅ MCP server responding")
        mcp_status.append(f"   • Toolgroups: ✅ Found {len(toolgroups)} toolgroup(s)")
        
        # List all toolgroup identifiers as a simple list
        if toolgroups:
            mcp_status.append("   • Toolgroup IDs:")
            for toolgroup_id in toolgroups:
                mcp_status.append(f"      - {toolgroup_id}")
        
        return mcp_status
    
    def get_system_status(self) -> str:
        """Get comprehensive system status by combining all component statuses"""
        
        # Combine all status information
        full_status = "\n".join([
            "=" * 60,
            "🔍 SYSTEM STATUS REPORT",
            "=" * 60,
            "",
            self.get_gradio_status(),
            "",
            "\n".join(self.get_llama_stack_status()),
            "",
            "\n".join(self.get_llm_status()),
            "",
            "\n".join(self.get_rag_status()),
            "",
            "\n".join(self.get_mcp_status()),
            "",
            "=" * 60
        ])
        
        return full_status
