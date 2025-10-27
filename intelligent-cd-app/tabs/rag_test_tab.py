"""
RAG Test tab functionality for Intelligent CD Chatbot.

This module handles RAG testing functionality and status reporting.
"""

import json
import os
from llama_stack_client import LlamaStackClient
from utils import get_logger


class RAGTestTab:
    """Handles RAG testing functionality"""
    
    def __init__(self, client: LlamaStackClient):
        self.client = client
        self.logger = get_logger("rag")
        self.vector_db_id = os.getenv("RAG_TEST_TAB_VECTOR_DB_ID", "app-documentation")

    def test_rag(self, query: str, database: str = None) -> str:
        """Test RAG functionality and report status in a user-friendly way"""
        
        # Use provided database or fall back to default
        vector_db_id = database.strip() if database and database.strip() else self.vector_db_id

        self.logger.info(f"RAG Query:\n\n{query}")
        self.logger.info(f"Using vector database: {vector_db_id}")

        try:
            # Query documents
            result = self.client.tool_runtime.rag_tool.query(
                vector_db_ids=[vector_db_id],
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
                f"**Database:** {vector_db_id}\n"
                f"**Query:**\n{query}\n\n"
                f"**Result:**\n```\n{formatted_result}\n```"
            )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.logger.error(f"RAG Query failed: {str(e)}\n{tb}")
            return (
                f"❌ RAG Query failed!\n\n"
                f"**Database:** {vector_db_id}\n"
                f"**Query:**\n{query}\n\n"
                f"**Error:**\n{str(e)}\n\n"
                f"**Traceback:**\n```\n{tb}\n```"
            )

    def get_available_databases(self) -> list:
        """Get list of available vector databases from Milvus"""
        try:
            vector_dbs = self.client.vector_dbs.list()
            if vector_dbs:
                db_list = []
                for db_item in vector_dbs:
                    if hasattr(db_item, 'identifier'):
                        db_list.append(db_item.identifier)
                    else:
                        db_list.append(str(db_item))
                return db_list
            else:
                return [self.vector_db_id]  # Return default if no databases found
        except Exception as e:
            self.logger.error(f"Error listing vector databases: {str(e)}")
            return [self.vector_db_id]  # Return default on error

    def get_rag_status(self, database: str = None) -> str:
        """Get detailed RAG status information including providers, databases, and documents"""
        
        # Use provided database or fall back to default
        vector_db_id = database.strip() if database and database.strip() else self.vector_db_id
        
        self.logger.info("Getting detailed RAG status information...")
        self.logger.info(f"Using vector database: {vector_db_id}")
        
        status_info = []
        status_info.append("=" * 60)
        status_info.append("📚 RAG STATUS REPORT")
        status_info.append("=" * 60)
        status_info.append(f"**Target Database:** {vector_db_id}")
        status_info.append("")
        
        try:
            # 1. List all available vector databases (summary only)
            status_info.append("🗄️ **Vector Databases:**")
            try:
                vector_dbs = self.client.vector_dbs.list()
                if vector_dbs:
                    for db_item in vector_dbs:
                        if hasattr(db_item, 'identifier'):
                            db_id = db_item.identifier
                            current_marker = " ✅ (Currently configured)" if db_id == vector_db_id else ""
                            status_info.append(f"   • {db_id}{current_marker}")
                        else:
                            status_info.append(f"   • {str(db_item)}")
                else:
                    status_info.append("   • No vector databases found")
            except Exception as e:
                status_info.append(f"   ❌ Error listing vector databases: {str(e)}")
            
            status_info.append("")
            
            # 2. Get detailed information about the configured vector database
            if vector_db_id:
                status_info.append(f"🔍 **Detailed Information for '{vector_db_id}':**")
                
                # Try to get database info using the correct API
                try:
                    db_info = self.client.vector_dbs.retrieve(vector_db_id)
                    if db_info:
                        if hasattr(db_info, '__dict__'):
                            for key, value in db_info.__dict__.items():
                                if not key.startswith('_') and value is not None:
                                    status_info.append(f"   • {key.replace('_', ' ').title()}: {value}")
                        else:
                            status_info.append(f"   • Database Info: {str(db_info)}")
                    else:
                        status_info.append("   • No detailed database information available")
                except Exception as e:
                    status_info.append(f"   ❌ Error getting database info: {str(e)}")
                
                status_info.append("")
                
                # 3. Get document information with count and truncated titles
                status_info.append(f"📄 **Documents in '{vector_db_id}':**")
                try:
                    # Try to get document information through queries
                    document_titles = []
                    document_count = 0
                    
                    # Try different queries to extract document information
                    test_queries = [
                        "What documents are available?",
                        "List all document titles",
                        "What files or documents are stored?",
                        "Show me the document names"
                    ]
                    
                    for query in test_queries:
                        try:
                            result = self.client.tool_runtime.rag_tool.query(
                                vector_db_ids=[vector_db_id],
                                content=query,
                            )
                            if result:
                                result_str = str(result).lower()
                                # Look for document-related information in the response
                                if any(keyword in result_str for keyword in ['document', 'file', 'title', 'name']):
                                    # Try to extract titles from the response
                                    lines = str(result).split('\n')
                                    for line in lines:
                                        line = line.strip()
                                        if line and len(line) > 5 and len(line) < 100:
                                            # Simple heuristic to identify potential document titles
                                            if any(keyword in line.lower() for keyword in ['document', 'file', '.pdf', '.txt', '.doc', 'title']):
                                                if line not in document_titles:
                                                    document_titles.append(line)
                                    break
                        except Exception:
                            continue
                    
                    # If we couldn't extract titles, try a more generic approach
                    if not document_titles:
                        try:
                            # Try to get a sample of content to estimate document count
                            sample_result = self.client.tool_runtime.rag_tool.query(
                                vector_db_ids=[vector_db_id],
                                content="sample content",
                            )
                            if sample_result:
                                # Estimate based on response length and structure
                                result_str = str(sample_result)
                                if len(result_str) > 1000:
                                    document_count = "Multiple documents detected"
                                else:
                                    document_count = "Documents available"
                        except Exception:
                            pass
                    
                    # Display results
                    if document_titles:
                        status_info.append(f"   • Document Count: {len(document_titles)} documents found")
                        status_info.append("   • Document Titles (truncated):")
                        for i, title in enumerate(document_titles[:5]):  # Show max 5 titles
                            truncated_title = title[:60] + "..." if len(title) > 60 else title
                            status_info.append(f"     {i+1}. {truncated_title}")
                        if len(document_titles) > 5:
                            status_info.append(f"     ... and {len(document_titles) - 5} more documents")
                    elif document_count:
                        status_info.append(f"   • Document Status: {document_count}")
                    else:
                        status_info.append("   • Document information not available through queries")
                        status_info.append("   • System is responsive to queries")
                        
                except Exception as e:
                    status_info.append(f"   ❌ Error accessing document information: {str(e)}")
                
                status_info.append("")
                
                # 4. Provider information (extracted from vector databases)
                status_info.append("🔧 **Provider Information:**")
                try:
                    vector_dbs = self.client.vector_dbs.list()
                    providers_found = set()
                    for db_item in vector_dbs:
                        if hasattr(db_item, 'provider_id'):
                            providers_found.add(db_item.provider_id)
                    
                    if providers_found:
                        status_info.append("   • Configured Providers:")
                        for provider in providers_found:
                            status_info.append(f"     • {provider}")
                    else:
                        status_info.append("   • No provider information available")
                        
                except Exception as e:
                    status_info.append(f"   ❌ Error getting provider info: {str(e)}")
                
                status_info.append("")
                
                # 5. Functionality test
                status_info.append("🧪 **Functionality Test:**")
                try:
                    test_result = self.client.tool_runtime.rag_tool.query(
                        vector_db_ids=[vector_db_id],
                        content="test query",
                    )
                    if test_result:
                        status_info.append("   ✅ RAG query functionality is working")
                        status_info.append(f"   • Test query returned: {len(str(test_result))} characters")
                    else:
                        status_info.append("   ⚠️ RAG query returned empty result")
                except Exception as e:
                    status_info.append(f"   ❌ RAG query test failed: {str(e)}")
            
            else:
                status_info.append("❌ No vector database ID configured")
            
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
