# Containerization & Local Execution Guide

This guide explains how to build, run, and test the **Evacuation Readiness ADK Agent** locally using Docker and Docker Compose.

---

## 1. Prerequisites (GCP Authentication)

Because the agent queries BigQuery (`evacuation_readiness`) and calls Gemini via Vertex AI, the container needs Google Cloud credentials.

Run this once on your local machine to generate Application Default Credentials (ADC):
```bash
gcloud auth application-default login
```
*(This creates `~/.config/gcloud/application_default_credentials.json`, which Docker Compose automatically mounts into the container).*

---

## 2. Quickstart with Docker Compose (Recommended)

1. **Verify your `.env` settings**:
   Ensure `.env` matches your GCP project:
   ```bash
   GOOGLE_CLOUD_PROJECT=qwiklabs-gcp-03-82491e646971
   GOOGLE_CLOUD_LOCATION=us-central1
   BIGQUERY_DATASET=evacuation_readiness
   ADK_MODEL=gemini-3.6-flash
   GOOGLE_GENAI_USE_VERTEXAI=True
   ```

2. **Start the container**:
   ```bash
   docker compose up --build
   ```

3. **Open the Agent Web UI**:
   Navigate to [http://localhost:8080](http://localhost:8080) in your browser.

4. **Stop the container**:
   ```bash
   docker compose down
   ```

---

## 3. Running with Standard Docker CLI

### Step A: Build the Image
```bash
docker build -t a4i-evacuation-agent .
```

### Step B: Run the Container

**Option 1: Using your local `gcloud` credentials (Mac / Linux / WSL)**
```bash
docker run -d \
  --name evacuation-agent \
  -p 8080:8080 \
  --env-file .env \
  -v ${HOME}/.config/gcloud:/root/.config/gcloud:ro \
  a4i-evacuation-agent
```

**Option 2: Using a Service Account Key file (`key.json`)**
```bash
docker run -d \
  --name evacuation-agent \
  -p 8080:8080 \
  --env-file .env \
  -v $(pwd)/key.json:/app/credentials.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  a4i-evacuation-agent
```

### Step C: View Container Logs
```bash
docker logs -f evacuation-agent
```

---

## 4. Testing the Running Agent

### Option 1: Via Web Browser
Open [http://localhost:8080](http://localhost:8080) and use the interactive ADK chat interface.

### Option 2: Via REST API / curl
```bash
curl -X POST http://localhost:8080/api/run \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the nearest wheelchair accessible shelter to Brickell Miami?"}'
```

---

## 5. Deploying Image to Google Cloud Run

To deploy your container directly to Google Cloud Run for production:
```bash
# 1. Build and push to Google Artifact Registry
gcloud builds submit --tag gcr.io/qwiklabs-gcp-03-82491e646971/evacuation-agent

# 2. Deploy to Cloud Run
gcloud run deploy evacuation-agent \
  --image gcr.io/qwiklabs-gcp-03-82491e646971/evacuation-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=qwiklabs-gcp-03-82491e646971,ADK_MODEL=gemini-3.6-flash
```
