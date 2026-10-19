# Firebase and Firestore setup

The project `gen-lang-client-0915819772` now has Firebase enabled and one **free default Firestore database** in `asia-south1`. Its billing account remains unlinked. The database API returned `freeTier: true`; point-in-time recovery is disabled. Live setup evidence is in `artifacts/firebase-free-setup.json`.

Runtime persistence was also verified through the actual public UI: a completed recovery report was saved, the API process was restarted, and the same report was restored by its run ID with `saved` and `restored` both true. Evidence: `artifacts/custom-incident-browser.json` and `artifacts/firestore-runtime-restart.json`. The separate direct write/read/delete probe is in `artifacts/firestore-cloud-roundtrip.json`.

## What the application uses

`app/audit_store.py` stores a completed synthetic recovery report in the `workflow_rescue_audits` collection. A report can then be restored by its opaque run ID after the API process restarts. This is useful persistence, not an immutable or certified audit ledger.

Set this server environment variable:

```text
FIRESTORE_PROJECT_ID=gen-lang-client-0915819772
```

The module uses Google Application Default Credentials and the Firestore REST API. A Cloud Run deployment should use its attached service account with an appropriate Firestore data role. An authorized Cloud Shell session supplies ADC through its metadata broker. If that session authorization expires, use `gcloud cloud-shell ssh --authorize-session --command=true` from the authenticated local terminal; this was verified to restore ADC without exporting keys. No service-account private key or Gemini API key is needed for Firestore. `FIRESTORE_PROJECT_ID` is separate from model configuration; persistence uses a Google identity while Gemini uses its own server-only API key.

The deployed `firestore.rules` deny all browser reads and writes. The API accesses reports using server IAM. Reports are retrievable through the application by their unguessable run IDs; do not upload real customer data into this public prototype.

If storage is unavailable, `save_audit` returns a sanitized failure and recovery can continue. Local JSON export remains available. Free-tier quota exhaustion must be reported honestly; it is not silently described as a successful save.

## Integration contract

```python
from app.audit_store import configured, save_audit, load_audit, AuditStoreError

record["persistence"] = await save_audit(record)
# When the run is no longer in the in-memory RUNS mapping:
restored_record = await load_audit(identifier)  # dict or None; sanitized exception on outage
```

`save_audit` returns `{"saved": True, "backend": "firestore"}` on a confirmed write. Disabled storage returns `{"saved": False, "backend": "disabled"}`. A failed write includes a stable error `code`, without credentials or raw provider text.

The Firestore free quota is 1 GiB stored data, 50,000 reads/day, 20,000 writes/day, 20,000 deletes/day and 10 GiB/month outbound transfer. This project has no billing enabled, so exceeding free allowance does not authorize paid usage.

## Hosting status and limits

The Firebase project now serves the [public submission materials portal](https://gen-lang-client-0915819772.web.app). The page, PPTX, PDF and narrated video were verified without authentication, with billing still disabled. **The interactive Python backend is not hosted on Firebase.** `firebase.json` and `scripts/prepare-firebase-hosting.py` prepare the assets only after a working backend and routing are verified. The current React frontend requires same-origin `/api` endpoints; a static Firebase site alone cannot execute the FastAPI server.

The application now runs on the Node runtime in the separate billing-enabled project `workflow-rescue-host-562392`, following the owner's $5?$10 monthly hosting authorization. Its Cloud Run runtime identity has `roles/datastore.user` on the original data project. `starter/audit-store.mjs` implements the same audit persistence contract through the metadata service and Firestore REST API.

The original Firebase/Gemini project remains unbilled. [Managed hosting](MANAGED-HOSTING.md) records the stable application URL, spending controls and successful live Gemini / post-revision Firestore restoration checks. The temporary Cloud Shell tunnels are retired.

## Sources

- [Firestore free quota](https://firebase.google.com/docs/firestore/quotas)
- [Firebase pricing plans and Spark restrictions](https://firebase.google.com/docs/projects/billing/firebase-pricing-plans)
- [AI Studio deployment and Starter eligibility](https://ai.google.dev/gemini-api/docs/aistudio-deploying)
- [Google Cloud Starter Tier](https://docs.cloud.google.com/docs/starter-tier)
- [AI Studio web runtime](https://ai.google.dev/gemini-api/docs/aistudio-build-mode)

Updated 19 October 2026. Preserve the original project's unbilled status when updating the separate Cloud Run deployment.
