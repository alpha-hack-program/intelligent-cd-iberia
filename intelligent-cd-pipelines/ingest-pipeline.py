from kfp import dsl
from kfp import compiler
from kfp import kubernetes
from kfp.client import Client

import os
from datetime import datetime

@dsl.component(base_image="python:3.14")
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
            "namespace-resources-best-practices.md",
            "argocd-applications-creation-best-practices.md",
            "github-operations-best-practices.md"
        ]
    }
    
    print(f"Using hardcoded configuration with {len(folders_config)} folders:")
    for folder_name, files in folders_config.items():
        print(f"  - {folder_name}: {len(files)} files - {files}")
    
    return folders_config



@dsl.component(base_image="python:3.14", packages_to_install=["llama-stack-client==0.3.5", "requests"])
def ingest_documents(folders_config: dict) -> None:
    """Processes all folders (DB IDs) using the hardcoded configuration."""
    from llama_stack_client import LlamaStackClient
    import os
    import requests
    import io
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
        
        # Initialize LlamaStack client
        client = LlamaStackClient(
            base_url=os.getenv("LLAMA_STACK_URL"),
            timeout=180.0
        )
        
        # Base URL for raw file content
        # Format: https://raw.githubusercontent.com/{project_path}/refs/heads/{branch}
        raw_base_url = f"https://raw.githubusercontent.com/{project_path}/refs/heads/{git_branch}"
        
        # Get embedding model and dimension
        print(f"\nFinding embedding model:")
        models = client.models.list()
        embedding_model_id = None
        embedding_dimension = 768  # Default for granite-embedding-125m
        
        for model in models:
            if model.model_type == "embedding":
                embedding_model_id = model.identifier
                # Get dimension from metadata or model attribute
                embedding_dimension = (
                    (model.metadata or {}).get('embedding_dimension') or
                    getattr(model, 'embedding_dimension', None) or
                    768
                )
                print(f"  Model: {embedding_model_id}, Dimension: {embedding_dimension}")
                break
        
        if not embedding_model_id:
            raise RuntimeError("No embedding model found. Please ensure an embedding model is registered in Llama Stack.")
        
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
        
        # # Delete if exists, then exit
        # if vector_store_id:
        #     print(f"Found existing vector store '{vector_store_name}' with ID: {vector_store_id}, deleting it...")
        #     client.vector_stores.delete(vector_store_id=vector_store_id)
        #     print(f"Deleted vector store '{vector_store_name}', exiting...")
        #     return
        
        # Create if doesn't exist
        if not vector_store_id:
            print(f"Vector store '{vector_store_name}' not found, creating it...")
            
            # Create the vector database
            # https://github.com/llamastack/llama-stack-client-python/blob/v0.3.5/api.md
            # The API requires a model but doesn't accept it as a direct parameter
            # Pass it via extra_body
            provider_id = "milvus"  # Use milvus provider as configured
            print(f"Using embedding model: {embedding_model_id}")
            print(f"Embedding dimension: {embedding_dimension}")
            print(f"Provider ID: {provider_id}")
            
            vector_store = client.vector_stores.create(
                name=vector_store_name,
                extra_body={
                    "embedding_model": embedding_model_id,
                    "embedding_dimension": embedding_dimension,
                    "provider_id": provider_id
                }
            )
            vector_store_id = vector_store.id
            print(f"Vector store '{vector_store_name}' created successfully with ID: {vector_store_id}")
        
        # Ingest files using vector_stores.files API
        print(f"Ingesting {len(files)} files into vector store '{vector_store_name}' (ID: {vector_store_id})")
        
        for file_name in files:
            file_path = f"{git_docs_path}/{folder_name}/{file_name}"
            raw_url = f"{raw_base_url}/{file_path}"
            
            print(f"Processing file: {file_name}")
            print(f"Raw URL: {raw_url}")
            
            # Download file from GitHub
            try:
                response = requests.get(raw_url, timeout=30)
                response.raise_for_status()
                
                # Create in-memory file-like object
                file_content = io.BytesIO(response.content)
                
                # Upload file to Llama Stack with metadata
                file_info = client.files.create(
                    file=(file_name, file_content),
                    purpose="assistants"
                )
                
                print(f"  Uploaded file '{file_name}' with ID: {file_info.id}")
                
                # Add file to vector store
                vector_store_file = client.vector_stores.files.create(
                    vector_store_id=vector_store_id,
                    file_id=file_info.id,
                    chunking_strategy={
                        "type": "static",
                        "static": {
                            "max_chunk_size_tokens": 1024,
                            "chunk_overlap_tokens": 200,
                        },
                    },
                )
                print(f"  Added file to vector store: {vector_store_file}")
                        
            except requests.RequestException as e:
                print(f"  Error downloading file '{file_name}': {e}")
                continue
            except Exception as e:
                print(f"  Error processing file '{file_name}': {e}")
                continue
        
        print(f"Successfully ingested {len(files)} files for '{vector_store_name}'")
    
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
    # Set to "false" to disable SSL verification for self-signed certificates
    ssl_verify = os.environ.get("SSL_VERIFY", "true").lower() != "false"

    # 1. Create KFP client
    print(f'Connecting to Data Science Pipelines: {kubeflow_endpoint}')
    print(f'SSL verification: {ssl_verify}')
    kfp_client = Client(
        host=kubeflow_endpoint,
        existing_token=bearer_token,
        ssl_ca_cert=None if not ssl_verify else None,
        verify_ssl=ssl_verify
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
