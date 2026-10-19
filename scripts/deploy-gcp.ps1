param()
$ErrorActionPreference = 'Stop'
Write-Output 'Workflow Rescue uses the Gemini Developer API and optional Firestore audit storage.'
Write-Output 'Automatic Cloud Run deployment is unavailable under the current free-tier-only requirement.'
Write-Output 'No cloud resources or billing settings were changed.'
Write-Output 'For the existing temporary Cloud Shell demo, see scripts/start-cloud-shell-demo.py and docs/GOOGLE-SETUP.md.'
Write-Output 'Firebase submission materials are published separately with scripts/deploy-submission-portal.py.'
exit 2
