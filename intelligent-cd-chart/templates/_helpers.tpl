{{/*
Expand the name of the chart.
*/}}
{{- define "intelligent-cd-chart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "intelligent-cd-chart.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "intelligent-cd-chart.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "intelligent-cd-chart.labels" -}}
helm.sh/chart: {{ include "intelligent-cd-chart.chart" . }}
{{ include "intelligent-cd-chart.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "intelligent-cd-chart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "intelligent-cd-chart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Gradio UI specific helpers
*/}}
{{- define "gradio-chart.name" -}}
{{- printf "%s-gradio" (include "intelligent-cd-chart.name" .) }}
{{- end }}

{{- define "gradio-chart.fullname" -}}
{{- printf "%s-gradio" (include "intelligent-cd-chart.fullname" .) }}
{{- end }}

{{- define "gradio-chart.labels" -}}
helm.sh/chart: {{ include "intelligent-cd-chart.chart" . }}
app.kubernetes.io/name: {{ include "gradio-chart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "gradio-chart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "gradio-chart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
MCP Server specific helpers - these work with the context from range iteration
*/}}
{{- define "mcp-server-chart.name" -}}
{{- printf "%s-%s" (include "intelligent-cd-chart.name" $) .name }}
{{- end }}

{{- define "mcp-server-chart.fullname" -}}
{{- printf "%s-%s" (include "intelligent-cd-chart.fullname" $) .name }}
{{- end }}

{{- define "mcp-server-chart.labels" -}}
helm.sh/chart: {{ include "intelligent-cd-chart.chart" $ }}
app.kubernetes.io/name: {{ include "mcp-server-chart.name" . }}
app.kubernetes.io/instance: {{ $.Release.Name }}
{{- if $.Chart.AppVersion }}
app.kubernetes.io/version: {{ $.Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ $.Release.Service }}
{{- end }}

{{- define "mcp-server-chart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mcp-server-chart.name" . }}
app.kubernetes.io/instance: {{ $.Release.Name }}
{{- end }}

{{/*
Kubernetes MCP Server specific helpers (for backward compatibility)
*/}}
{{- define "kubernetes-mcp-server-chart.name" -}}
{{- printf "%s-%s" (include "intelligent-cd-chart.name" $) .name }}
{{- end }}

{{- define "kubernetes-mcp-server-chart.fullname" -}}
{{- printf "%s-%s" (include "intelligent-cd-chart.fullname" $) .name }}
{{- end }}

{{- define "kubernetes-mcp-server-chart.labels" -}}
helm.sh/chart: {{ include "intelligent-cd-chart.chart" $ }}
app.kubernetes.io/name: {{ include "kubernetes-mcp-server-chart.name" . }}
app.kubernetes.io/instance: {{ $.Release.Name }}
{{- if $.Chart.AppVersion }}
app.kubernetes.io/version: {{ $.Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ $.Release.Service }}
{{- end }}

{{- define "kubernetes-mcp-server-chart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kubernetes-mcp-server-chart.name" . }}
app.kubernetes.io/instance: {{ $.Release.Name }}
{{- end }}
