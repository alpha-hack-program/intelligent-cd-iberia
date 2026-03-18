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
        
        try:
            test_response = self.client.with_options(
                max_retries=0, timeout=15.0
            ).chat.completions.create(
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
            
            if test_response.choices:
                choice = test_response.choices[0]
                response_content = getattr(choice, 'message', None)
                if response_content and hasattr(response_content, 'content'):
                    response_content = response_content.content or ""
                else:
                    response_content = getattr(choice, 'text', "") or ""
                llm_status.append(f"   • Response: ✅ Received {len(response_content)} characters")
            else:
                llm_status.append("   • Response: ⚠️ No choices in response")
        except Exception as e:
            llm_status.append("   • Status: ❌ LLM service not responding")
            llm_status.append(f"   • Error: {str(e)}")
        
        return llm_status
    
    def get_rag_status(self) -> list[str]:
        """Get RAG server status and vector database availability"""
        rag_status = []
        rag_status.append("📚 RAG Server:")
        
        try:
            list_response = self.client.vector_stores.list()
            vector_stores_list = list(list_response)
            rag_status.append("   • Connection: ✅ RAG backend responding")
        except Exception as e:
            rag_status.append("   • Connection: ❌ Failed to connect to RAG backend")
            rag_status.append(f"   • Error: {str(e)}")
            return rag_status
        
        vector_store_found = any(vs.name == self.vector_store_name for vs in vector_stores_list)
        
        if vector_store_found:
            rag_status.append(f"   • Target DB: ✅ Vector Store '{self.vector_store_name}' found in list")
        else:
            rag_status.append(f"   • Target DB: ❌ Vector Store '{self.vector_store_name}' not found in list")
        
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
        
        try:
            tools = self.client.tools.list()
            self.logger.info(f"MCP tools.list() returned: {len(tools)} tools")
            
            toolgroups = list(set(
                tool.toolgroup_id for tool in tools if tool.toolgroup_id
            ))
            mcp_status.append("   • Status: ✅ MCP server responding")
            mcp_status.append(f"   • Toolgroups: ✅ Found {len(toolgroups)} toolgroup(s)")
            
            if toolgroups:
                mcp_status.append("   • Toolgroup IDs:")
                for toolgroup_id in toolgroups:
                    mcp_status.append(f"      - {toolgroup_id}")
        except Exception as e:
            self.logger.error(f"MCP test failed: {str(e)}")
            mcp_status.append("   • Status: ❌ MCP server not responding")
            mcp_status.append(f"   • Error: {str(e)}")
        
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
