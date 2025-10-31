# GitHub Operations Best Practices

## Overview

This document describes how to interact with GitHub repositories from this application using the GitHub MCP server for committing files and creating pull requests.

## GitHub MCP Server

The GitHub MCP (Model Context Protocol) server is the primary method for interacting with GitHub repositories from this application.

### Key Information

- **Purpose**: The GitHub MCP server provides tools for GitHub operations without requiring direct GitHub API credentials in the application code
- **Usage**: All GitHub interactions (commits, pull requests, file operations) should be performed through the MCP server tools
- **Authentication**: The MCP server handles authentication using configured GitHub credentials
- **Access**: The MCP server provides access to repository operations, commit creation, pull request management, and file operations

### Available Operations

The GitHub MCP server typically provides operations for:
- Committing files to repositories
- Creating and managing pull requests
- Reading repository contents and file information
- Branch management
- Repository querying and status checks

## Committing Files to GitHub

### Critical Requirement: Single Commit for All Files

**IMPORTANT**: When committing multiple files to GitHub, **ALL files must be added in a single commit**. This ensures:

- Atomic operations: All related files are committed together
- Clean history: Related changes appear as one logical unit
- Easier tracking: All files for a feature/deployment are grouped together
- Better rollback: Can revert all related changes in one operation

### Commit Process

1. **Collect All Files**: Gather all files that need to be committed (e.g., all Kubernetes manifests for a deployment)

2. **Use GitHub MCP Server**: Use the MCP server tools to commit files - do NOT use direct GitHub API calls

3. **Single Commit**: Add all files to the staging area and commit them together in one operation

4. **Verify**: Check that all files were committed successfully and verify the commit in the repository

### Example Workflow

When committing Kubernetes manifest files:

- Parse the manifest to extract individual resource YAML files
- Determine file paths based on resource metadata (e.g., `{name}-{kind}-{namespace}.yaml`)
- Commit all extracted files in a single commit operation
- Use a descriptive commit message (e.g., "Add application resources for namespace X")
- Verify all files appear in the repository after commit

## Best Practices

1. **Always Use MCP Server**: Never bypass the MCP server for GitHub operations
2. **Batch Commits**: Group related files into single commits rather than creating multiple commits
3. **Meaningful Messages**: Use descriptive commit messages that explain what was added/changed
4. **Verify After Commit**: Always verify that files were committed successfully
5. **Handle Errors**: Check for errors from MCP server operations and provide clear feedback to users

## Related Documentation

- ArgoCD applications creation best practices
- Namespace resources best practices
- Deployment configuration best practices