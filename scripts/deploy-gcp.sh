#!/usr/bin/env bash
# Run from Google Cloud Shell after uploading/extracting the source package.
set -euo pipefail
if [[ "${WORKFLOW_RESCUE_ALLOW_BILLABLE_HOSTING:-}" != 'true' ]]; then
  echo 'Deployment stopped: this legacy Vertex/Cloud Run route can incur charges and is outside the current free-tier-only policy. No cloud resources were changed.' >&2
  exit 2
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."

project_reference="${1:-56239221144}"
region="${2:-asia-south1}"
model="${3:-gemini-3.8-flash}"
project_id="$(gcloud projects describe "$project_reference" --format='value(projectId)' --quiet)"
[[ "$project_id" =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]] || { echo 'Could not resolve a valid project ID.' >&2; exit 1; }
printf 'Deploying workflow-rescue to %s in %s\n' "$project_id" "$region"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com aiplatform.googleapis.com iam.googleapis.com --project="$project_id" --quiet

service_account="workflow-rescue-run@${project_id}.iam.gserviceaccount.com"
existing="$(gcloud iam service-accounts list --project="$project_id" --filter="email=$service_account" --format='value(email)')"
if [[ -z "$existing" ]]; then
  gcloud iam service-accounts create workflow-rescue-run --display-name='Workflow Rescue runtime' --project="$project_id" --quiet
fi
gcloud projects add-iam-policy-binding "$project_id" --member="serviceAccount:$service_account" --role=roles/aiplatform.user --condition=None --quiet --format=none

# Explicit build identity avoids relying on a default account with missing permissions.
build_account="workflow-rescue-build@${project_id}.iam.gserviceaccount.com"
existing_build="$(gcloud iam service-accounts list --project="$project_id" --filter="email=$build_account" --format='value(email)')"
if [[ -z "$existing_build" ]]; then
  gcloud iam service-accounts create workflow-rescue-build --display-name='Workflow Rescue build' --project="$project_id" --quiet
fi
gcloud projects add-iam-policy-binding "$project_id" --member="serviceAccount:$build_account" --role=roles/run.builder --condition=None --quiet --format=none

# Single process/instance: demo state is ephemeral. Background work needs allocated CPU.
gcloud run deploy workflow-rescue --source=. --project="$project_id" --region="$region" \
  --service-account="$service_account" --allow-unauthenticated --port=8080 \
  --build-service-account="projects/$project_id/serviceAccounts/$build_account" \
  --memory=512Mi --cpu=1 --min-instances=0 --max-instances=1 --concurrency=20 \
  --timeout=900 --no-cpu-throttling \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$project_id,GOOGLE_CLOUD_LOCATION=global,VERTEX_MODEL=$model,DEFAULT_PROVIDER=vertex,MAX_ACTIVE_RUNS=2,MAX_MODEL_CALLS_PER_HOUR=120" --quiet
service_url="$(gcloud run services describe workflow-rescue --project="$project_id" --region="$region" --format='value(status.url)')"
curl --fail --silent --show-error "$service_url/healthz"
printf '\nApplication URL: %s\n' "$service_url"
printf 'Test connection, then complete and export a live Gemini recovery. Deployment alone does not validate AI.\n'
