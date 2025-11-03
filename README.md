# Intelligent CD

<div style="display: flex; align-items: center; margin-bottom: 1em;">
  <div style="flex: 0 0 auto; margin-right: 24px;">
    <img src="docs/images/chatbot.png" alt="Chatbot Interface" width="100" height="100"/>
  </div>
  <div style="flex: 1;">
    This project provides an application that can be deployed to an OpenShift cluster to provide a chat interface to modernize and optimize your cluster using a chat interface.
  </div>
</div>

## Features

- Chat interface to modernize and optimize your cluster based on **Gradio**.
- Use of **MCP servers** to provide tools to interact with OpenShift, ArgoCD, and GitHub.
- Use of **llama-stack** to coordinate all the AI components.
- Use of **Red Hat OpenShift AI** as the base platform for all the AI components.


## Architecture

The following diagram shows the architecture of the Intelligent CD application.

![Intelligent CD Architecture](docs/images/architecture.svg)


## Repository structure

This repository is organized as follows:

1. `ìntelligent-cd-app`: This is the Gradio application that provides the chat interface.
2. `intelligent-cd-chart`: This is the Helm chart that deploys the Intelligent CD application.
3. `intelligent-cd-docs`: Contents for the RAG on how to correctly convert the application to GitOps and documentation of a fake app that is supposed to be deployed on OpenShift manually.
4. `intelligent-cd-pipelines`: This folder contains a set of KubeFlow pipelines to run on OpenShift. As of today, these pipelines are use to ingest the contents of the `intelligent-cd-docs` folder into the RAG.


## Prerequisites

This application is prepared to be deployed using ArgoCD on a cluster deployed using the [AI Accelerator](https://github.com/redhat-ai-services/ai-accelerator).

**First**, you need to **create an OpenShift cluster using Demo RedHat**. Please request an environment for tomorrow from our demo platform: [AWS with OpenShift Open Environment](https://catalog.demo.redhat.com/catalog?search=aws&item=babylon-catalog-prod%2Fsandboxes-gpte.sandbox-ocp.prod). Select following in the order form:
* Activity: `Brand Event`.
* Purpose: `DemoJam 2026`.
* Region: `us-east-2` (even if you are in EMEA or APAC, still choose `us-east-2`).
* OpenShift Version: `4.19`.
* Control Plane Instance Type: `m6a.4xlarge`.


<!-- **Optional**, you can delete all the failed installation pods by running the following command:
```bash
oc get pods --all-namespaces | grep -E "Error|Failed" | awk '{print "oc delete pod " $2 " -n " $1}' | bash
``` -->


**Second**, log in to the cluster and install all the components following [their documentation](https://github.com/dgpmakes/ai-accelerator/blob/main/documentation/installation.md#bootstrapping-a-cluster): 

```bash
git clone https://github.com/dgpmakes/ai-accelerator.git # This is a fork of the original repository removing the default example apps
cd ai-accelerator
./bootstrap.sh
```

**NOTE**: During the installation, you will be asked to select a bootstrap folder. Choose the overlay `3) rhoai-fast-aws-gpu`  to install the latest version of OpenShift AI with GPU support.

<!-- **NOTE**: There is a bug in the current implementation of the AI Accelerator, so the apps get stuck in a pending state waiting indefinitely for other components to be deployed. You can fix it by running the following command:
```bash
oc project openshift-gitops
argocd login --core
argocd app terminate-op openshift-gitops/openshift-ai-operator; argocd app sync openshift-gitops/openshift-ai-operator
# When the OpenShift AI operator App is synced, the other apps should be able to deploy
argocd app list | grep OutOfSync | awk '{print $1}' | xargs -I {} sh -c 'argocd app terminate-op {} && argocd app sync {}'
``` -->

**Third**, you will need to gather some variables to be used in the application. These variables are stored in the `.env` file. Prepare the following variables:

1. **MaaS Configuration**. You can retrieve them all from 
- `MODEL_NAME`: Use the following model: `llama-4-scout-17b-16e-w4a16`.
- `MODEL_API_URL`: Use the following URL: `https://llama-4-scout-17b-16e-w4a16-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443/v1`.
- `MODEL_API_TOKEN`: The API token to use to access the model. Retrieve it from MaaS UI.

2. **GitHub MCP Server Configuration**:
- `GITHUB_PAT`: The API token to use to access the GitHub repositories. Create a new personal access token with the following permissions: `Read and Write access to code, issues, and pull requests`.
- `GITHUB_MCP_SERVER_TOOLSETS`: Use the following toolsets: `"pull_requests\,repos\,issues"`. Please note that the commas are escaped for the Helm Chart template.
- `GITHUB_MCP_SERVER_READONLY`: Use the following value: `false`.
- `GITHUB_GITOPS_REPO`: You can use the following repository: `https://github.com/alpha-hack-program/intelligent-cd-iberia-gitops` or any other you have access to. If you want to use the default one, please ask for the GitHub PAT. This is the repository where the GitOps configuration for the application will be stored.


## Deploy the application

All the components can deployed using **ArgoCD**, but as there are several variables to be set, we provide a script that will set the variables and deploy the application using Helm Charts and Kustomize:

1. First, you need to create a `.env` file with the following variables:

```bash
cp .env.example .env
```

2. Ensure your python environment has the respective libraries installed:

```bash
pip install -r intelligent-cd-pipelines/requirements.txt
```

3. Adapt the values of `.env`and then run the script to deploy the application:

```bash
./auto-install.sh # This command is idempotent, so just re-execute if you want to apply new configuration or it failed.
```

4. If you need extra customization, you can modify the values.yaml from the `intelligent-cd-chart/values.yaml`

5. You can use the chat interface to modernize and optimize your cluster. This is exposed here:

```bash
oc get route gradio -n intelligent-cd --template='https://{{ .spec.host }}/?__theme=light'
```

> [!CAUTION]
> **Bug: Llamastack in several namespaces**
> There is a bug in the current implementation of the Llama Stack operator provided in OpenShift AI. With this bug, the `ClusterRoleBinding` to deploy the Llama Stack Distribution with extra privileges is only created automatically in the first namespace where a Llama Stack Distribution is deployed.
> If you already deployed the Llama Stack Distribution in a namespace, you can create the CRB manually in the other namespaces by running the following command:
> ```bash
> oc adm policy add-cluster-role-to-user system:openshift:scc:anyuid -z llama-stack-sa --rolebinding-name llama-stack-crb-$NAMESPACE -n $NAMESPACE
> ```



## Look & Feel

Your first question is probably: "OK, what how does it look like?". For that reason, I've added some screenshots of the main features of the application:

1. The most simple usage is just accessing the local Llama Stack RAG that has been loaded using the RHOAI pipeline:

![Chat using RAG](docs/images/chat-check-rag.png)

2. The chat also allows at the same time, to use the result of an MCP Server call to enhance the response:

![Chat using MCP Server](docs/images/chat-check-ocp.png)

3. As this is a really complex architecture with many moving pieces, there is a section in the application that just shows a summary of the status and configuration of all the components. This is for debugging purposes:

![System Status summary](docs/images/system-status.png)

4. Also, as the MCP Server might be available (and it is possible to list the tools), but then credentials might be wrong, I've added another Tab that allows to execute individual tools for any of the configured Llama Stack distribution. This is also for debugging purposes:

![MCP Server Test](docs/images/mcp-test-ocp.png)


5. The RAG module might fail if, for example, your LLama Stack is restarted without persistence, etc. For that reason, there is another tab just focused on retrieving results from the vector database (MilvusDB by default).

![MCP RAG Test](docs/images/rag-test-docs.png)


6. Finally, here I have an example of how to request information from ServiceNow:


![Chat using ServiceNow](docs/images/chat-check-servicenow.png)




## MCP Servers configuration


Each of these MCP Servers will need a different kind of authentication to interact with their components. In this section I try to compile all the configuration that you need for this.



### 1. OpenShift MCP Server

This MCP Server is only capable of connecting to one single cluster based on the local `kubeconfig`. For that reason, we have created a Service Account with certain permissions to access the cluster.


### 3. ArgoCD MCP Server

The ArgoCD MCP Server handles the authentication based on an API Token created against the ArgoCD Server API using the `admin` user. For that reason, in the `./auto-install.sh`, I already automated the process of retrieving the token based on the admin user and password created in OpenShift as a secret.



### 3. GitHub MCP Server

For the GitHub MCP Server, you need to create a personal access token with the following permissions. The permissions might be reduced if you want a subset of the features, but this is what I provided for a simplified experienced. Make sure that you use the new **Personal Access Token** so that you only provide these permissions against a certain number of repositories. 

**Token Details:**
- Repositories: 2 (intelligent-cd, intelligent-cd-gitops)
- Total Permissions: 14

**Required Permissions:**

| Permission | Access Level |
|------------|--------------|
| Actions | Read-only |
| Variables | Read-only |
| Administration | Read-only |
| Contents | Read-only |
| Environments | Read-only |
| Issues | Read-only |
| Merge queues | Read-only |
| Metadata | Read-only |
| Pages | Read-only |
| Pull requests | Read-only |
| Webhooks | Read-only |
| Secrets | Read-only |
| Commit statuses | Read-only |
| Workflows | Read and write |



### 4. ServiceNow MCP Server

ServiceNow allows several types of authentication, but for demo purposes we will use the `basic` authentication for user/password. For the ServiceNow MCP Server, you need to create a developer instance of the ServiceNow platform:

1. Access the [Developer portal](https://developer.servicenow.com) in ServiceNow.
2. Create a new instance and access the [Management Console](https://developer.servicenow.com/dev.do#!/manage-instance).
3. Retrieve the `Instance URL`, `Username`, and `Password` from the Management Console.
4. Add those variables to the `.env` file.


### 5. Web Search using Tavily

For the Web Search using Tavily, you need to create a new API key in the [Tavily Developer Portal](https://tavily.com/developers/api-key). Add those variables to the `.env` file.




## Customizing, adapting the components

### 1. Generate new version of Gradio


If you need to adapt the `Gradio` application and create a new version, you can do so with the following commands:

```bash
podman build -t quay.io/alopezme/intelligent-cd-gradio:latest intelligent-cd-app
podman push quay.io/alopezme/intelligent-cd-gradio:latest
```

Test the image locally:

```bash
podman run --network host quay.io/alopezme/intelligent-cd-gradio:latest
```


### 2. New version of the Helm Chart Configuration

As the `./auto-install.sh` is idempotent, change whatever and execute again.


### 3. New container image of the MCP Servers

To make sure that this repository stays clean, the `Dockerfile`s to generate the container images of the MCP servers is stored in the siblings [repository](https://github.com/alvarolop/mcp-playground).


### 4. New version of the pipeline

The pipeline might change if needed. The recommendation right now is just to delete all and recreate:

```bash
python intelligent-cd-pipelines/clean-pipeline.py
python intelligent-cd-pipelines/ingest-pipeline.py
```