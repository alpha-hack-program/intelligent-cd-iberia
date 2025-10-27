from kfp.client import Client
import os

def clean_pipeline_components():
    """Remove all pipeline components in reverse order."""
    
    # Get connection details
    kubeflow_endpoint = os.environ["KUBEFLOW_ENDPOINT"]
    bearer_token = os.environ["BEARER_TOKEN"]
    
    # Create KFP client
    print(f'Connecting to Data Science Pipelines: {kubeflow_endpoint}')
    kfp_client = Client(
        host=kubeflow_endpoint,
        existing_token=bearer_token
    )
    
    # 1. Delete runs from experiment
    print("Deleting pipeline runs...")
    experiments = kfp_client.list_experiments()
    if experiments and hasattr(experiments, "experiments"):
        for exp in experiments.experiments:
            if exp.display_name == "ingest-experiment":
                runs = kfp_client.list_runs(experiment_id=exp.experiment_id)
                if runs and hasattr(runs, "runs"):
                    for run in runs.runs:
                        print(f"Deleting run: {run.display_name} (ID: {run.run_id})")
                        kfp_client.delete_run(run_id=run.run_id)
    
    # 2. Delete experiment
    print("Deleting experiment...")
    experiments = kfp_client.list_experiments()
    if experiments and hasattr(experiments, "experiments"):
        for exp in experiments.experiments:
            if exp.display_name == "ingest-experiment":
                print(f"Deleting experiment: {exp.display_name} (ID: {exp.experiment_id})")
                kfp_client.delete_experiment(experiment_id=exp.experiment_id)
    
    # 3. Delete pipeline versions and pipeline
    print("Deleting pipeline...")
    pipelines = kfp_client.list_pipelines()
    if pipelines and hasattr(pipelines, "pipelines"):
        for pipeline in pipelines.pipelines:
            if pipeline.display_name == "ingest-pipeline":
                # Delete all pipeline versions first
                versions = kfp_client.list_pipeline_versions(pipeline_id=pipeline.pipeline_id)
                if versions and hasattr(versions, "pipeline_versions"):
                    for version in versions.pipeline_versions:
                        print(f"Deleting pipeline version: {version.pipeline_version_id}")
                        kfp_client.delete_pipeline_version(
                            pipeline_id=pipeline.pipeline_id, 
                            pipeline_version_id=version.pipeline_version_id)
                
                # Delete the pipeline itself
                print(f"Deleting pipeline: {pipeline.display_name} (ID: {pipeline.pipeline_id})")
                kfp_client.delete_pipeline(pipeline_id=pipeline.pipeline_id)
    
    # 4. Clean up local files
    print("Cleaning up local files...")
    if os.path.exists("ingest-pipeline.yaml"):
        os.remove("ingest-pipeline.yaml")
        print("Deleted ingest-pipeline.yaml")
    
    print("Pipeline cleanup completed!")

if __name__ == "__main__":
    clean_pipeline_components()
