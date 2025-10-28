from kfp import dsl
from kfp import compiler
from kfp import kubernetes
from kfp.client import Client

import os
from datetime import datetime

@dsl.component(base_image="python:3.13")
def get_folders_config() -> dict:
    """Returns a hardcoded dictionary with folder names and their files."""
    
    # Hardcoded configuration for folders and their files
    folders_config = {
        "app-documentation": [
            "01-intro.md",
            "02-deployment-constraints.md",
            "03-network-security.md",
            "04-routing-loadbalancing.md",
            "05-storage-architecture.md",
            "06-resource-monitoring.md",
            "07-deployment-procedures.md"
        ],
        "gitops-documentation": [
            "deployment-configuration-best-practices.md",
            "namespace-resources-best-practices.md"
        ]
    }
    
    print(f"Using hardcoded configuration with {len(folders_config)} folders:")
    for folder_name, files in folders_config.items():
        print(f"  - {folder_name}: {len(files)} files - {files}")
    
    return folders_config



@dsl.component(base_image="python:3.13", packages_to_install=["llama-stack-client==0.2.23"])
def ingest_documents(folders_config: dict) -> None:
    """Processes all folders (DB IDs) using the hardcoded configuration."""
    from llama_stack_client import RAGDocument, LlamaStackClient
    import os
    from datetime import datetime
    
    # GitHub repository details
    git_repo = os.getenv("GIT_REPO", "https://github.com/alpha-hack-program/intelligent-cd-iberia.git")
    git_branch = os.getenv("GIT_BRANCH", "main")
    git_docs_path = os.getenv("GIT_DOCS_PATH", "intelligent-cd-docs")
    
    # Extract project ID from GitHub URL
    import re
    project_match = re.search(r'github\.com/([^/]+/[^/]+)\.git', git_repo)
    if not project_match:
        print(f"Error: Could not extract project path from GitHub URL: {git_repo}")
        import sys
        sys.exit(1)
    
    project_path = project_match.group(1)
    print(f"Processing {len(folders_config)} folders from configuration")
    
    # Process each folder
    for folder_name, files in folders_config.items():
        print(f"\n=== Processing folder: {folder_name} ===")
        print(f"Files to process: {files}")
        
        if not files:
            print(f"Warning: No files configured for folder '{folder_name}'!")
            continue
        
        # Base URL for raw file content
        raw_base_url = f"https://github.com/{project_path}/-/raw/{git_branch}"
        
        # Process each file
        documents = []
        for file_name in files:
            file_path = f"{git_docs_path}/{folder_name}/{file_name}"
            raw_url = f"{raw_base_url}/{file_path}"
            
            print(f"Processing file: {file_name}")
            print(f"Raw URL: {raw_url}")
            
            # Create RAG document
            doc = RAGDocument(
                document_id=f"{folder_name}/{file_name}",
                content=raw_url,
                mime_type="text/plain",
                metadata={
                    "source": git_repo,
                    "url": raw_url,
                    "title": file_name,
                    "date": datetime.now().strftime("%Y%m%d")
                },
            )
            documents.append(doc)
        
        # Initialize LlamaStack client
        client = LlamaStackClient(
            base_url=os.getenv("LLAMA_STACK_URL"),
            timeout=180.0
        )
        
        
        
        # Check if vector database exists by listing all and filtering by name
        # OpenAI does not provide mechanism to retrive by name 
        # https://platform.openai.com/docs/api-reference/vector-stores/retrieve
        # List all vector stores and find one with matching name
        print(f"\nListing all vector stores:")
        list_response = client.vector_stores.list()
        vector_store_name = folder_name
        vector_store_id = None
        for vs in list_response:
            print(f"  - ID: {vs.id}, Name: {vs.name}")
            if vs.name == vector_store_name:
                vector_store_id = vs.id
        
        # Create if doesn't exist
        if vector_store_id:
            print(f"Found existing vector store '{vector_store_name}' with ID: {vector_store_id}")
        else:
            print(f"Vector store '{vector_store_name}' not found, creating it...")
            
            # Create the vector database
            # https://github.com/llamastack/llama-stack-client-python/blob/release-0.2.22/api.md
            response = client.vector_stores.create(
                name=vector_store_name,
                embedding_model="granite-embedding-125m",
                embedding_dimension=768,
                provider_id="milvus"
            )
            # Response has 'id' attribute, not 'identifier'
            vector_store_id = response.id
            print(f"Vector store '{vector_store_name}' created successfully with ID: {vector_store_id}")
        
        # Insert the documents using the identifier
        print(f"Ingesting {len(documents)} documents into vector store '{vector_store_name}' (ID: {vector_store_id})")
        client.tool_runtime.rag_tool.insert(
            documents=documents,
            vector_db_id=vector_store_id,
            chunk_size_in_tokens=1024,
        )
        print(f"Successfully ingested documents for '{vector_store_name}'")
    
    print(f"\n=== Completed processing all {len(folders_config)} folders ===")

@dsl.pipeline(name="intelligent-cd-ingest-pipeline")
def pipeline():
    """Main pipeline that processes multiple DB IDs using hardcoded configuration."""
    
    # Step 1: Get folders configuration
    folders_config_task = get_folders_config()
    
    # Step 2: Process all folders using the configuration
    ingest_documents_task = ingest_documents(folders_config=folders_config_task.output)
    
    # Add secrets for the process task
    kubernetes.use_secret_as_env(
        ingest_documents_task,
        secret_name='ingestion-secret',
        secret_key_to_env={
            'LLAMA_STACK_URL': 'LLAMA_STACK_URL',
            'GIT_REPO': 'GIT_REPO',
            'GIT_BRANCH': 'GIT_BRANCH',
            'GIT_DOCS_PATH': 'GIT_DOCS_PATH'
        })

# Helper function to get or create pipeline
def get_or_create_pipeline(client, pipeline_name, package_path):
    """Get existing pipeline or create new one."""
    existing_pipelines = client.list_pipelines()
    
    # Check if pipelines list exists and has items
    if existing_pipelines and hasattr(existing_pipelines, "pipelines") and existing_pipelines.pipelines:
        for pipeline in existing_pipelines.pipelines:
            if pipeline.display_name == pipeline_name:
                print(f"Pipeline '{pipeline_name}' already exists with ID: {pipeline.pipeline_id}")
                return pipeline
    
    # Pipeline doesn't exist, create it
    print(f"Pipeline '{pipeline_name}' not found, uploading new pipeline...")
    pipeline_obj = client.upload_pipeline(
        pipeline_package_path=package_path,
        pipeline_name=pipeline_name
    )
    print(f"Pipeline uploaded successfully with ID: {pipeline_obj.pipeline_id}")
    return pipeline_obj

# Helper function to get or create experiment
def get_or_create_experiment(client, experiment_name, description):
    """Get existing experiment or create new one."""
    existing_experiments = client.list_experiments()
    
    # Check if experiments list exists and has items
    if existing_experiments and hasattr(existing_experiments, "experiments"):
        for exp in existing_experiments.experiments:
            if exp.display_name == experiment_name:
                print(f"Experiment '{experiment_name}' already exists with ID: {exp.experiment_id}")
                return exp
    
    # Experiment doesn't exist, create it
    print(f"Experiment '{experiment_name}' not found, creating new experiment...")
    experiment = client.create_experiment(
        name=experiment_name,
        description=description
    )
    print(f"Experiment created successfully with ID: {experiment.experiment_id}")
    return experiment

# Helper function to execute pipeline (always executes)
def execute_pipeline(client, experiment, pipeline_obj, run_name):
    """Execute pipeline run."""
    print("Starting pipeline execution...")
    
    # First, retrieve the first version of the pipeline
    pipeline_versions = client.list_pipeline_versions(pipeline_id=pipeline_obj.pipeline_id)
    if pipeline_versions and hasattr(pipeline_versions, "pipeline_versions") and pipeline_versions.pipeline_versions:
        # Just get the first version from the array
        version_id = pipeline_versions.pipeline_versions[0].pipeline_version_id
        print(f"Using pipeline version: {version_id}")
    else:
        raise RuntimeError("No versions found for the pipeline to execute.")
    
    # Then, run the pipeline with the retrieved version
    run_result = client.run_pipeline(
        experiment_id=experiment.experiment_id,
        job_name=run_name,
        pipeline_id=pipeline_obj.pipeline_id,
        version_id=version_id
    )
    print(f"Pipeline execution started with run ID: {run_result.run_id}")
    return run_result

if __name__ == "__main__":
    # SVC: https://ds-pipeline-dspa.{namespace}.svc:8443
    # Route: https://ds-pipeline-dspa-rhoai-playground.apps.$CLUSTER_DOMAIN
    kubeflow_endpoint = os.environ["KUBEFLOW_ENDPOINT"]
    bearer_token = os.environ["BEARER_TOKEN"]

    # 1. Create KFP client
    print(f'Connecting to Data Science Pipelines: {kubeflow_endpoint}')
    kfp_client = Client(
        host=kubeflow_endpoint,
        existing_token=bearer_token
    )

    # 2. Create pipeline object
    pipeline_package = compiler.Compiler().compile(
        pipeline_func=pipeline,
        package_path="ingest-pipeline.yaml"
    )

    # 3. Get or create pipeline
    pipeline_obj = get_or_create_pipeline(kfp_client, "ingest-pipeline", "ingest-pipeline.yaml")
    print(f"Pipeline ready with ID: {pipeline_obj.pipeline_id}")

    # 4. Get or create experiment
    experiment = get_or_create_experiment(
        kfp_client, 
        "ingest-experiment", 
        "Runs our pipeline to ingest documents into the vector database"
    )
    print(f"Experiment ready with ID: {experiment.experiment_id}")

    # 5. Execute pipeline
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"ingest-execution-{timestamp}"
    run_result = execute_pipeline(kfp_client, experiment, pipeline_obj, run_name) 
