#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' \
  'Workflow Rescue uses the Gemini Developer API and optional Firestore audit storage.' \
  'Automatic Cloud Run deployment is unavailable under the current free-tier-only requirement.' \
  'No cloud resources or billing settings were changed.' \
  'For the existing temporary Cloud Shell demo, see scripts/start-cloud-shell-demo.py and docs/GOOGLE-SETUP.md.' \
  'Firebase submission materials are published separately with scripts/deploy-submission-portal.py.' >&2
exit 2
