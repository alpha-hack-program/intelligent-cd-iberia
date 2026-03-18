#!/bin/bash
# Script to delete all vector stores and files from Llama Stack
# Usage: ./clean-all.sh [LLAMA_STACK_URL]
# Example: ./clean-all.sh http://localhost:8321

set -e

# Get Llama Stack URL from argument or environment variable
LLAMA_STACK_URL="${1:-${LLAMA_STACK_URL:-http://localhost:8321}}"

echo "🧹 Cleaning all vector stores and files from Llama Stack at: ${LLAMA_STACK_URL}"
echo ""

# Function to check if jq is installed
check_jq() {
    if ! command -v jq &> /dev/null; then
        echo "❌ Error: jq is not installed. Please install it first."
        echo "   On Fedora/RHEL: sudo dnf install jq"
        echo "   On Ubuntu/Debian: sudo apt-get install jq"
        echo "   On macOS: brew install jq"
        exit 1
    fi
}

# Check dependencies
check_jq

# Delete all vector stores
echo "📦 Deleting all vector stores..."
VECTOR_STORES=$(curl -s -X GET "${LLAMA_STACK_URL}/v1/vector_stores" \
    -H "Content-Type: application/json" | jq -r '.data[]?.id // empty')

if [ -z "$VECTOR_STORES" ]; then
    echo "   ℹ️  No vector stores found"
else
    COUNT=0
    while IFS= read -r vs_id; do
        if [ -n "$vs_id" ]; then
            echo "   🗑️  Deleting vector store: $vs_id"
            curl -s -X DELETE "${LLAMA_STACK_URL}/v1/vector_stores/${vs_id}" \
                -H "Content-Type: application/json" > /dev/null
            COUNT=$((COUNT + 1))
        fi
    done <<< "$VECTOR_STORES"
    echo "   ✅ Deleted ${COUNT} vector store(s)"
fi

echo ""

# Delete all files
echo "📄 Deleting all files..."
FILES=$(curl -s -X GET "${LLAMA_STACK_URL}/v1/files" \
    -H "Content-Type: application/json" | jq -r '.data[]?.id // empty')

if [ -z "$FILES" ]; then
    echo "   ℹ️  No files found"
else
    COUNT=0
    while IFS= read -r file_id; do
        if [ -n "$file_id" ]; then
            echo "   🗑️  Deleting file: $file_id"
            curl -s -X DELETE "${LLAMA_STACK_URL}/v1/files/${file_id}" \
                -H "Content-Type: application/json" > /dev/null
            COUNT=$((COUNT + 1))
        fi
    done <<< "$FILES"
    echo "   ✅ Deleted ${COUNT} file(s)"
fi

echo ""
echo "✨ Cleanup complete!"
