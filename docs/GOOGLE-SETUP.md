# Gemini, Firebase and Google Cloud setup

Updated 18 October 2026. Team: **sustAInX**. Current constraint: **free-tier services only; no paid usage**.

## Verified state

- Google Cloud CLI authentication now works. The earlier login failure was caused by local certificate trust. TLS verification remains enabled; the CLI uses `artifacts/google-cloud-trusted-ca.pem` on the original workstation.
- Project ID: `gen-lang-client-0915819772`. Project number: `56239221144`. Project billing remains **disabled**. An open billing account exists, but this work did not link it.
- The public app uses the **Gemini Developer API**, with its key stored only on the server. The current public configuration reports **`gemini-3.5-flash-lite`**; `/api/config` is authoritative after updates. Vertex AI is not used.
- The deployed Gemini report `artifacts/evaluation-gemini.json` records **6/6 expected outcomes and zero safety-check failures**. These are reviewed synthetic fixtures, not a general reliability benchmark. Earlier failed reports are retained separately.
- Firebase is enabled. One default Firestore database in `asia-south1` reports `freeTier: true`. Deployed rules deny browser database access; the server uses IAM and Application Default Credentials (ADC).
- A live Cloud Shell check **wrote, restored and deleted one synthetic Firestore test document**. Evidence: `artifacts/firestore-cloud-roundtrip.json`. Setup and unchanged billing evidence: `artifacts/firebase-free-setup.json`.
- The actual deployed UI subsequently saved a completed report, and the same report was restored by ID after an API restart. Runtime evidence: `artifacts/custom-incident-browser.json` and `artifacts/firestore-runtime-restart.json`.
- The API currently runs on a **temporary Cloud Shell VM with a TryCloudflare HTTPS tunnel**. Cloud Run has **not** been deployed. Firebase Hosting now serves the public materials portal at https://gen-lang-client-0915819772.web.app. The portal is not the interactive Python backend.

The current temporary URL and process IDs are recorded remotely in `artifacts/cloud-shell-demo.json`. A reachable temporary tunnel is not a durable competition submission link.

## Server configuration

Keep the Gemini key in the private server `.env`. Never put it in React, Git, the source ZIP, screenshots or presentation slides. The nonsecret settings for the verified configuration are:

```dotenv
GEMINI_MODEL=gemini-3.5-flash-lite
DEFAULT_PROVIDER=gemini
FIRESTORE_PROJECT_ID=gen-lang-client-0915819772
MAX_ACTIVE_RUNS=1
MAX_MODEL_CALLS_PER_HOUR=60
```

`FIRESTORE_PROJECT_ID` enables optional report persistence without enabling another model provider. Firestore uses ADC, not the Gemini API key. An authorized Cloud Shell session supplies ADC through its metadata broker. No service-account private key was created or distributed.

The user confirmed the Gemini project is on its **Free** API tier. Recheck [AI Studio Projects](https://aistudio.google.com/projects) before changing accounts or billing. Linking a billing account can change Gemini API usage to paid pricing; do not do it under the current constraint.

## Temporary Cloud Shell launch and restart

The source archive excludes `.env`. Restore the source and provide the key separately in that private file; do not paste it into shell history. In the Cloud Shell app directory:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
chmod 600 .env
USER_CONFIRMED_GEMINI_FREE_TIER=1 .venv/bin/python scripts/start-cloud-shell-demo.py
```

Cloud Shell session authorization is separate from the local CLI login. If Firestore reports `ADC_UNAVAILABLE`, authorize the existing session from the authenticated local terminal:

```powershell
gcloud cloud-shell ssh --authorize-session --command=true
```

This sends current OAuth credentials through Google's supported Cloud Shell authorization flow. An expired session was observed to break both ADC and the remote Google CLI; reauthorizing restored both. No key file or token was printed or exported. The server refreshes ADC when persisting a report, so reauthorization can restore storage without restarting the API.

The launcher checks a real structured Gemini response before publishing, removes alternate provider configuration, verifies the official tunnel binary's release digest, and records its own process IDs. It creates no Cloud Run, Cloud Build, registry or paid model resources.

Do not rerun the launcher while the old app/tunnel pair is active unless a separate demo is intended. A fresh tunnel can produce a different URL. In the current working session, this operational helper verifies the stored PID belongs to this directory and Uvicorn application before restarting only the API, preserving the tunnel:

```bash
.venv/bin/python artifacts/restart-demo-app.py
```

The helper is an ignored session artifact, not a public-source dependency. If absent on a fresh checkout, use the launcher for a new session. Never kill a guessed PID or unrelated process. Restart only when no recovery is active; export important reports first.

Cloud Shell documents approximately **40 minutes** for noninteractive idle sessions, **12 hours** per session and a default **50 hours/week** quota. The API and tunnel stop when the session ends. Do not fabricate keepalive activity to extend the service. Firestore data persists independently; the public API does not.

## Verify the public application

Open the URL signed out. In Workspace, select **Gemini API**, test its connection, run a recovery, inspect the evidence and final checks, and export the audit. The report must identify `gemini`, the actual model and nonzero model calls. Rehearsal and replay do not prove live AI connectivity.

Run these sequentially because the public demo permits one active run:

```powershell
python scripts/evaluate.py --provider gemini --base-url https://CURRENT-PUBLIC-URL
python scripts/browser_check.py --live-provider gemini --base-url https://CURRENT-PUBLIC-URL
```

Replace the example URL. Unknown-payment and already-dispatched cases should end in human review. Gemini requests are paced within the free tier; eligible transient quota errors use bounded retries. Daily quota exhaustion requires quota reset, not repeated retries, alternate credentials or a paid fallback. A model switch must be deliberate and retested.

## Firebase and Firestore

`app/audit_store.py` saves reports under opaque run IDs and restores them after they leave memory. Save failures return a sanitized status and local JSON export remains available. This is ordinary persistence, not an immutable or certified audit trail. Use synthetic data only.

Free Firestore allowance: one database/project, 1 GiB stored data, 50,000 reads/day, 20,000 writes/day, 20,000 deletes/day and 10 GiB/month outbound transfer. Paid backup, restore, clone and point-in-time recovery features were not enabled.

`scripts/configure-free-firebase.py` checks billing is disabled and the existing default database reports `freeTier: true` before adding Firebase metadata and publishing deny-client rules. Setup has already completed; rerunning is unnecessary unless restoring configuration. It does not create a database or deploy a frontend.

`firebase.json`, `.firebaserc`, `firestore.rules` and `firestore.indexes.json` contain the source configuration. `scripts/prepare-firebase-hosting.py` assembles frontend files only after a durable backend and API routing are verified. A static Firebase site cannot execute FastAPI. Spark excludes Cloud Run and Cloud Functions; Hosting rewrites cannot proxy an arbitrary external tunnel. See [FIREBASE-SETUP.md](FIREBASE-SETUP.md) for the integration contract.

## Durable deployment blocker

The submission requires availability throughout evaluation and mentions **Firebase, Firestore, Cloud Run and Gemini**. The temporary demo does not satisfy the durable Cloud Run requirement.

**AI Studio Starter Tier** is the documented no-billing Cloud Run route: eligible accounts can publish up to two apps. Google says active or prior paid Cloud billing can make an account ineligible. The current account has billing history, so eligibility cannot be assumed. An existing eligible teammate account can check the actual **Publish → Get Started → Publish App** offer in AI Studio.

AI Studio supports GitHub import but documents a Node.js backend runtime. Importing this existing Python Dockerfile unchanged through Starter Tier has not been verified. A successful source import or preview is not proof of deployment.

Ordinary Cloud Run needs a billing-enabled project. Free allowances, zero minimum instances, maximum-instance limits, model-call limits and budget alerts do **not** guarantee zero charges. No billing link, Cloud Run service, Cloud Build job or registry was created by this free setup.

`scripts/deploy-gcp.ps1` and `scripts/deploy-gcp.sh` are guarded legacy files, not the current Gemini API route. **Do not bypass their guards under the free-only instruction.** A future standard deployment needs server-side Gemini secret configuration, Firestore IAM and tested request lifetime handling. The current API starts asynchronous work after HTTP 202; request-based CPU can stop that work when requests finish. A tested long-lived request or another supported execution design is needed before selecting request-based billing.

## Read-only project checks

```powershell
gcloud auth list
gcloud projects describe 56239221144 --format="value(projectId)"
gcloud billing projects describe gen-lang-client-0915819772 --format="value(billingEnabled)"
gcloud firestore databases describe --database="(default)" --project=gen-lang-client-0915819772 --format="yaml(name,locationId,freeTier)"
```

Expected billing: `False`. Expected database: `(default)`, `asia-south1`, `freeTier: true`. If the local CLI again reports a certificate error, repair trusted CA configuration while preserving TLS verification.

## Common errors

| Result | Meaning and response |
|---|---|
| Local HTML `GATEWAY_403` | A non-JSON network denial; it does not prove the key invalid. Cloud Shell has reached Gemini successfully. |
| Google JSON 403 | Check API/key restrictions and account/model eligibility. It is different from the local HTML denial. |
| 429 rate limit | Respect pacing/retry delay. A daily free-quota limit needs quota reset; no paid fallback is configured. |
| 404 model | Confirm the exact model is available to this free-tier project. |
| `INCOMPLETE_MODEL_OUTPUT` | No complete allowed action was returned. No action from that response executes. |
| `ADC_UNAVAILABLE` | Firestore's server identity cannot authenticate. Check ADC/IAM; do not use the Gemini API key for Firestore. |
| Firestore save failure | Mark persistence unavailable and export locally; do not claim a successful save. |
| Firebase quota-project error | The management REST request needs `x-goog-user-project`. The prepared script sets it; this does not link billing. |
| Cloud Run billing precondition | The project is unbilled. Stop; the current instruction does not authorize billing linkage. |

## Official sources

- [AI Studio deployment and eligibility](https://ai.google.dev/gemini-api/docs/aistudio-deploying)
- [Google Cloud Starter Tier](https://docs.cloud.google.com/docs/starter-tier)
- [AI Studio runtime and GitHub import](https://ai.google.dev/gemini-api/docs/aistudio-build-mode)
- [Firebase plans and Spark restrictions](https://firebase.google.com/docs/projects/billing/firebase-pricing-plans)
- [Firestore free quota](https://firebase.google.com/docs/firestore/quotas)
- [Gemini billing through Firebase AI Logic](https://firebase.google.com/docs/ai-logic/pricing)
- [Cloud Shell limits](https://docs.cloud.google.com/shell/docs/quotas-limits)
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output)
- [Cloud Run billing settings](https://docs.cloud.google.com/run/docs/configuring/billing-settings)
