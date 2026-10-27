#!/usr/bin/env bash
# Script to launch the ADK Web UI for the Evacuation Readiness Agent
set -euo pipefail

export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-qwiklabs-gcp-03-82491e646971}"
export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
export GOOGLE_GENAI_USE_VERTEXAI="${GOOGLE_GENAI_USE_VERTEXAI:-True}"
export ADK_MODEL="${ADK_MODEL:-gemini-3.6-flash}"

echo "Starting ADK Web Server for Evacuation Readiness Agent..."
echo "Project: $GOOGLE_CLOUD_PROJECT"
echo "Model:   $ADK_MODEL"

adk web agent
