# Managed hosting and cost controls

Verified 19 October 2026. The owner authorized a $5–$10 monthly hosting target.

**Application:** https://workflow-rescue-112348114226.us-central1.run.app

**Materials and video:** https://gen-lang-client-0915819772.web.app

The application runs on Google Cloud Run and does not depend on a laptop, Cloud Shell session or temporary tunnel. Updating the existing Cloud Run service preserves its URL. Do not delete and recreate the service or change its project or region.

## Infrastructure

| Component | Configuration |
|---|---|
| Hosting project | `workflow-rescue-host-562392` (billing enabled) |
| Service and region | `workflow-rescue`, `us-central1` |
| Runtime | Node 22, first-generation Cloud Run environment |
| Resources | 0.08 vCPU, 256 MiB, Node heap limited to 128 MiB |
| Billing | Request-based; CPU boost disabled; zero minimum instances |
| Scaling | One service instance maximum; one request per instance |
| Request timeout | 900 seconds |
| Gemini | Developer API, `gemini-3.5-flash-lite`, free tier |
| Gemini and data project | `gen-lang-client-0915819772` (billing disabled) |
| Audit database | Default Firestore database in `asia-south1` |
| Runtime identity | `workflow-rescue-runtime@workflow-rescue-host-562392.iam.gserviceaccount.com` |
| Model credential | Secret Manager `workflow-rescue-gemini`, version 1; server only |

The runtime identity can use the individual Gemini secret and write/read the audit database. No service-account private key is required. Gemini is the only live model integration; the explicitly labelled rehearsal mode makes no AI calls. Business services and uploaded incident data remain synthetic.

## Spending controls

- **INR 500 monthly enforced Cloud Run spend cap**, filtered to the hosting project and Cloud Run service category. Its API state was verified as `CONFIGURED`.
- **INR 750 monthly alert budget** for the entire hosting project, with actual and forecast notifications. This is an alert, not an account-wide hard limit.
- The Cloud Run cap measures gross estimated usage before credits. Reaching it pauses new Cloud Run usage until the next month. Already-running requests and charges from other services are outside an exact total limit.
- The service scales to zero. Image cleanup retains the latest two versions; build source objects expire after seven days. Secret Manager, image storage and occasional builds may incur small charges outside the Cloud Run cap.
- Gemini and Firestore remain in the original unbilled project. No paid model fallback is configured. Free quota exhaustion can temporarily stop live AI processing.

Light demonstration traffic is expected to fit the approved $5–$10 target, often below it. This is an estimate, not a guaranteed total bill; network transfer, shared billing-account allowances, taxes and future builds affect the amount. The INR budgets are authoritative and do not track a fixed USD exchange rate.

## Verification

The deployed browser test imported a fresh JSON incident, used Gemini twice, completed recovery, and exported an audit with `persistence.saved: true`. It completed in 21.8 seconds with no browser JavaScript errors. A new Cloud Run revision then restored the same run from Firestore using the same public URL.

Supporting local records:

- `artifacts/managed-host-live-check.json`
- `artifacts/managed-host-live-audit.json`
- `artifacts/managed-host-restart-check.json`
- `artifacts/managed-host-billing-verification.json`
- `artifacts/hosting-budgets.json`
- `artifacts/managed-host-build.json`

Before deployment, 81 Python tests, 11 frontend tests and 137 Node tests passed. The extracted deployment package also passed the Node tests. The live check is additional evidence; these counts do not imply arbitrary production integrations are supported.

## Operation and updates

Use `/api/config` to check public availability and the active model. The external Google frontend returns 404 for `/healthz`; that path is not a reliable public health check for this service.

```powershell
Invoke-RestMethod 'https://workflow-rescue-112348114226.us-central1.run.app/api/config'
gcloud run services describe workflow-rescue --project=workflow-rescue-host-562392 --region=us-central1
gcloud billing projects describe gen-lang-client-0915819772 --format="value(billingEnabled)"
```

The last command must remain `False`. On the original workstation, use the trusted CA configuration described in `GOOGLE-SETUP.md` if the CLI reports a certificate error; do not disable TLS verification.

Recovery stays attached to an HTTP event stream through audit persistence, which works with request-based CPU allocation. Closing that connection cancels further recovery actions. Use the browser or an API request with `Accept: text/event-stream`. The older POST-202/polling interface is retained for compatibility but is not suitable for reliable background execution under these hosting settings.

The deliberately small service processes one request at a time. Other visitors can wait or receive a capacity response during an active recovery. Cold starts can add initial delay. Completed reports survive instance replacement; in-progress work does not resume automatically.

Prepare future releases with `python scripts/prepare-managed-deployment.py`. Its archive contains the Node runtime and current built UI, with no credentials or presentation files. Build that package's Dockerfile, then deploy the resulting image to the **same** service/project/region while retaining its secret, identity, stream support, cost controls and limits. The root Dockerfile is the separate Python development route. Avoid the retired `deploy-gcp` scripts.

## References

- [Cloud Run billing settings](https://docs.cloud.google.com/run/docs/configuring/billing-settings)
- [Cloud Run pricing](https://cloud.google.com/run/pricing)
- [Enforced billing spend caps](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Firestore quotas](https://firebase.google.com/docs/firestore/quotas)
