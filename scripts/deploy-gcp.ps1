param(
    [string]$ProjectReference = '56239221144',
    [string]$Region = 'asia-south1',
    [string]$Model = 'gemini-3.8-flash',
    [switch]$AllowBillableHosting
)
$ErrorActionPreference = 'Stop'
if (-not $AllowBillableHosting) { throw 'Deployment stopped: this legacy Vertex/Cloud Run route can incur charges and is outside the current free-tier-only policy. No cloud resources were changed.' }
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

# gcloud auth login is required. No credential files are built into the image.
$ProjectId = (gcloud projects describe $ProjectReference --format='value(projectId)' --quiet)
if ($LASTEXITCODE -ne 0 -or -not $ProjectId) { throw 'Sign in with gcloud auth login, then verify access to the selected project.' }
$ProjectId = $ProjectId.Trim()
if ($ProjectId -notmatch '^[a-z][a-z0-9-]{4,28}[a-z0-9]$') { throw 'The resolved project ID is invalid.' }
Write-Output "Deploying workflow-rescue to project $ProjectId in $Region"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com aiplatform.googleapis.com iam.googleapis.com --project=$ProjectId --quiet
if ($LASTEXITCODE -ne 0) { throw 'Could not enable required Google Cloud APIs. Check billing and permissions.' }

$ServiceAccount = "workflow-rescue-run@$ProjectId.iam.gserviceaccount.com"
$Existing = gcloud iam service-accounts list --project=$ProjectId --filter="email=$ServiceAccount" --format='value(email)'
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect service accounts.' }
if (-not $Existing) {
    gcloud iam service-accounts create workflow-rescue-run --display-name='Workflow Rescue runtime' --project=$ProjectId --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the runtime service identity.' }
}
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$ServiceAccount" --role='roles/aiplatform.user' --condition=None --quiet --format='none'
if ($LASTEXITCODE -ne 0) { throw 'Could not grant Vertex AI access to the runtime identity.' }

# Use an explicit build identity instead of assuming the default has build permissions.
$BuildServiceAccount = "workflow-rescue-build@$ProjectId.iam.gserviceaccount.com"
$ExistingBuild = gcloud iam service-accounts list --project=$ProjectId --filter="email=$BuildServiceAccount" --format='value(email)'
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect build service accounts.' }
if (-not $ExistingBuild) {
    gcloud iam service-accounts create workflow-rescue-build --display-name='Workflow Rescue build' --project=$ProjectId --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the build service identity.' }
}
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$BuildServiceAccount" --role='roles/run.builder' --condition=None --quiet --format='none'
if ($LASTEXITCODE -ne 0) { throw 'Could not grant the build role to the build identity.' }

# Single instance and process are intentional: this prototype stores runs in memory.
# CPU must remain allocated because model runs continue between polling requests.
gcloud run deploy workflow-rescue --source=. --project=$ProjectId --region=$Region --service-account=$ServiceAccount --build-service-account="projects/$ProjectId/serviceAccounts/$BuildServiceAccount" --allow-unauthenticated --port=8080 --memory=512Mi --cpu=1 --min-instances=0 --max-instances=1 --concurrency=20 --timeout=900 --no-cpu-throttling --set-env-vars="GOOGLE_CLOUD_PROJECT=$ProjectId,GOOGLE_CLOUD_LOCATION=global,VERTEX_MODEL=$Model,DEFAULT_PROVIDER=vertex,MAX_ACTIVE_RUNS=2,MAX_MODEL_CALLS_PER_HOUR=120" --quiet
if ($LASTEXITCODE -ne 0) { throw 'Cloud Run deployment failed. Read the gcloud error; no deployment success is assumed.' }
$ServiceUrl = gcloud run services describe workflow-rescue --project=$ProjectId --region=$Region --format='value(status.url)'
if ($LASTEXITCODE -ne 0) { throw 'Deployed service URL could not be retrieved.' }
$ServiceUrl = $ServiceUrl.Trim()
Invoke-RestMethod -Uri "$ServiceUrl/healthz" | ConvertTo-Json
Write-Output "Application URL: $ServiceUrl"
Write-Output 'Select Gemini on Vertex AI, test the connection, then complete and export a live recovery run.'

