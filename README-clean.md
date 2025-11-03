# Clean up the Intelligent CD installation

If you are having issues with the Intelligent CD installation, you can clean up the installation by running the following commands depending on the step you are at:

## Clean namespaces

If you already deployed the discounts application, you can clean up the namespaces by running the following commands:

```bash
oc delete application.argoproj.io/discounts-gitops -n openshift-gitops
oc delete ns/discounts-gitops 
oc delete ns/discounts-manually-created
```

## Clean the GitOps repository

If you already committed the changes to the GitOps repository, you can clean up the repository by running the following commands:

```bash
# Remove the file from the repository
git pull
rm -rf discounts.yaml
git add .
git commit -m "🔥🔥 Remove Discounts Application from GitOps 🔥🔥"
git push
```

## Clean the Llama Stack cache

If already executed any of the steps and having issues with the Llama Stack, you can clean the cache by running the following commands:

```bash
export KUBEFLOW_ENDPOINT=$(oc get route ds-pipeline-dspa -n intelligent-cd-pipelines --template="https://{{.spec.host}}")
export BEARER_TOKEN=$(oc whoami --show-token)
oc delete llsd -n intelligent-cd llama-stack
oc delete pvc/llama-stack-pvc -n intelligent-cd
sleep 2
oc scale deployment gradio --replicas=0 -n intelligent-cd
python intelligent-cd-pipelines/clean-pipeline.py
sleep 15
./auto-install.sh
```
