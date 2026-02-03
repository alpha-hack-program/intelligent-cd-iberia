"""
RAG Test tab functionality for Intelligent CD Chatbot.

This module handles RAG testing functionality and status reporting.
"""

import json
import os
from datetime import datetime
from llama_stack_client import LlamaStackClient
from utils import get_logger


class RAGTestTab:
    """Handles RAG testing functionality"""
    
    def __init__(self, client: LlamaStackClient):
        self.client = client
        self.logger = get_logger("rag")
        self.vector_store_name = os.getenv("RAG_TEST_TAB_VECTOR_DB_NAME", "app-documentation")

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

    def test_rag(self, query: str, database: str = None) -> str:
        """Test RAG functionality and report status in a user-friendly way"""
        
        # Use provided database name or fall back to default
        vector_store_name = database.strip() if database and database.strip() else self.vector_store_name
        
        # Convert name to ID for querying
        vector_store_id = self._get_vector_store_id_by_name(vector_store_name)

        self.logger.info(f"RAG Query:\n\n{query}")
        self.logger.info(f"Using vector store: {vector_store_name} (ID: {vector_store_id})")

        try:
            # Query documents
            result = self.client.tool_runtime.rag_tool.query(
                vector_db_ids=[vector_store_id],
                content=query,
            )
            self.logger.debug(f"RAG Result:\n\n{result}")

            # Try to format the result nicely for the user
            if isinstance(result, (dict, list)):
                formatted_result = json.dumps(result, indent=2)
            else:
                formatted_result = str(result)

            return (
                f"✅ RAG Query executed successfully!\n\n"
                f"**Database:** {vector_store_name}\n"
                f"**Query:**\n{query}\n\n"
                f"**Result:**\n```\n{formatted_result}\n```"
            )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.logger.error(f"RAG Query failed: {str(e)}\n{tb}")
            return (
                f"❌ RAG Query failed!\n\n"
                f"**Database:** {vector_store_name}\n"
                f"**Query:**\n{query}\n\n"
                f"**Error:**\n{str(e)}\n\n"
                f"**Traceback:**\n```\n{tb}\n```"
            )

    def get_available_databases(self) -> list:
        """Get list of available vector stores"""
        try:
            list_response = self.client.vector_stores.list()
            if list_response:
                db_list = []
                for vs in list_response:
                    if hasattr(vs, 'name'):
                        db_list.append(vs.name)
                    else:
                        db_list.append(str(vs))
                return db_list
            else:
                return [self.vector_store_name]  # Return default if no databases found
        except Exception as e:
            self.logger.error(f"Error listing vector stores: {str(e)}")
            return [self.vector_store_name]  # Return default on error

    def get_rag_status(self, database: str = None) -> str:
        """Get detailed RAG status information including providers, databases, and documents"""
        
        # Use provided database name or fall back to default
        vector_store_name = database.strip() if database and database.strip() else self.vector_store_name
        
        # Convert name to ID for querying
        vector_store_id = self._get_vector_store_id_by_name(vector_store_name)
        
        self.logger.info("Getting detailed RAG status information...")
        self.logger.info(f"Using vector store: {vector_store_name} (ID: {vector_store_id})")
        
        status_info = []
        status_info.append("=" * 60)
        status_info.append("📚 RAG STATUS REPORT")
        status_info.append("=" * 60)
        status_info.append(f"**Target Database:** {vector_store_name}")
        status_info.append("")
        
        try:
            # 1. List all available vector stores (with ID and Name)
            status_info.append("🗄️ **Vector Stores:**")
            try:
                list_response = self.client.vector_stores.list()
                if list_response:
                    for vs in list_response:
                        current_marker = " ✅ (Currently configured)" if vs.name == vector_store_name else ""
                        status_info.append(f"   • Name: {vs.name}{current_marker}")
                        status_info.append(f"     ID:   {vs.id}")
                else:
                    status_info.append("   • No vector stores found")
            except Exception as e:
                status_info.append(f"   ❌ Error listing vector stores: {str(e)}")
            
            status_info.append("")
            
            # 2. Get detailed information about the configured vector store
            if vector_store_id:
                status_info.append(f"🔍 **Detailed Information for '{vector_store_name}':**")
                
                # Try to get vector store info using the correct API
                try:
                    store_info = self.client.vector_stores.retrieve(vector_store_id)
                    if store_info:
                        if hasattr(store_info, '__dict__'):
                            for key, value in store_info.__dict__.items():
                                if not key.startswith('_') and value is not None:
                                    status_info.append(f"   • {key.replace('_', ' ').title()}: {value}")
                        else:
                            status_info.append(f"   • Vector Store Info: {str(store_info)}")
                    else:
                        status_info.append("   • No detailed vector store information available")
                except Exception as e:
                    status_info.append(f"   ❌ Error getting vector store info: {str(e)}")
                
                status_info.append("")
                
                # 3. Get document information using the files API
                status_info.append(f"📄 **Documents in '{vector_store_name}':**")
                try:
                    # Use the vector store files API to get file information
                    files_response = self.client.vector_stores.files.list(
                        vector_store_id=vector_store_id
                    )
                    
                    if files_response and hasattr(files_response, 'data'):
                        files = files_response.data
                        file_count = len(files)
                        
                        status_info.append(f"   • File Count: {file_count} files")
                        
                        if file_count > 0:
                            # Show file details
                            status_info.append("   • File Details:")
                            for i, file_info in enumerate(files[:10]):  # Show max 10 files
                                file_id = getattr(file_info, 'id', 'unknown')
                                status = getattr(file_info, 'status', 'unknown')
                                created_at = getattr(file_info, 'created_at', None)
                                
                                # Format creation time if available
                                if created_at:
                                    try:
                                        dt = datetime.fromtimestamp(created_at)
                                        created_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                                    except:
                                        created_str = str(created_at)
                                else:
                                    created_str = "N/A"
                                
                                status_emoji = "✅" if status == "completed" else "⏳" if status == "processing" else "❌"
                                status_info.append(f"     {i+1}. {status_emoji} File ID: {file_id[:20]}... | Status: {status} | Created: {created_str}")
                            
                            if file_count > 10:
                                status_info.append(f"     ... and {file_count - 10} more files")
                            
                            # Count files by status
                            status_counts = {}
                            for file_info in files:
                                status = getattr(file_info, 'status', 'unknown')
                                status_counts[status] = status_counts.get(status, 0) + 1
                            
                            if len(status_counts) > 1:
                                status_info.append("   • Status Summary:")
                                for status, count in status_counts.items():
                                    status_emoji = "✅" if status == "completed" else "⏳" if status == "processing" else "❌"
                                    status_info.append(f"     {status_emoji} {status}: {count}")
                        else:
                            status_info.append("   • No files found in vector store")
                    elif files_response:
                        # Handle case where response is a list directly
                        files = files_response if isinstance(files_response, list) else []
                        file_count = len(files)
                        status_info.append(f"   • File Count: {file_count} files")
                        if file_count == 0:
                            status_info.append("   • No files found in vector store")
                    else:
                        status_info.append("   • Unable to retrieve file information")
                        status_info.append("   • System is responsive to queries")
                        
                except Exception as e:
                    self.logger.warning(f"Error accessing file information via API: {str(e)}")
                    status_info.append(f"   ⚠️ Error accessing file information: {str(e)}")
                    # Fallback: indicate system is responsive
                    try:
                        test_result = self.client.tool_runtime.rag_tool.query(
                            vector_db_ids=[vector_store_id],
                            content="test",
                        )
                        if test_result:
                            status_info.append("   • System is responsive to queries")
                    except:
                        pass
                
                status_info.append("")
                
                # 4. Provider information (vector_io providers)
                status_info.append("🔧 **Provider Information (vector_io):**")
                try:
                    # List all providers and filter for vector_io type
                    providers_list = self.client.providers.list()
                    vector_io_providers = []
                    
                    for provider in providers_list:
                        # Check if provider has api attribute set to "vector_io"
                        if hasattr(provider, 'api') and provider.api == "vector_io":
                            provider_info = {
                                'id': getattr(provider, 'id', 'unknown'),
                                'name': getattr(provider, 'name', 'unknown'),
                                'api': getattr(provider, 'api', 'unknown'),
                            }
                            # Add any additional attributes
                            if hasattr(provider, '__dict__'):
                                for key, value in provider.__dict__.items():
                                    if not key.startswith('_') and key not in ['id', 'name', 'api'] and value:
                                        provider_info[key] = value
                            vector_io_providers.append(provider_info)
                    
                    if vector_io_providers:
                        status_info.append(f"   • Found {len(vector_io_providers)} vector_io provider(s):")
                        for provider in vector_io_providers:
                            status_info.append(f"     • **{provider.get('name', 'unknown')}** (ID: {provider.get('id', 'unknown')})")
                            # Show additional info if available
                            for key, value in provider.items():
                                if key not in ['id', 'name', 'api']:
                                    status_info.append(f"       - {key}: {value}")
                    else:
                        status_info.append("   • No vector_io providers found")
                        
                except Exception as e:
                    status_info.append(f"   ❌ Error getting provider info: {str(e)}")
                    self.logger.error(f"Error listing providers: {str(e)}")
                
                status_info.append("")
            
            else:
                status_info.append("❌ No vector store configured")
            
            status_info.append("")
            status_info.append("=" * 60)
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.logger.error(f"RAG Status check failed: {str(e)}\n{tb}")
            status_info.append(f"❌ Error getting RAG status: {str(e)}")
            status_info.append("")
            status_info.append("**Traceback:**")
            status_info.append(f"```\n{tb}\n```")
            status_info.append("")
            status_info.append("=" * 60)
        
        return "\n".join(status_info)
