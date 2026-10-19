# Optional Node.js deployment runtime

This is a compatibility port for hosts that accept Node.js but cannot run the primary Python application. It serves the same compiled React UI and performs fresh recovery executions. It is **not a deployment confirmation**, and does not establish Cloud Run Starter eligibility.

From this directory, with Node.js 22 or later:

```text
npm test
npm start
```

For a self-contained upload, copy `starter/` into a new directory and copy the repository's `web/` directory into that directory as `web/`. The entry point is `server.mjs`; `npm start` honors the host's `PORT`. No npm packages or Python runtime are required. Do not copy `.env`, credentials, or private artifacts.

Set these values through the host's server secrets/environment interface:

```text
GEMINI_API_KEY=<set privately in the host, never in source>
GEMINI_MODEL=gemini-3.5-flash-lite
DEFAULT_PROVIDER=gemini
FIRESTORE_PROJECT_ID=<project with the existing Firestore database>
MAX_ACTIVE_RUNS=2
MAX_MODEL_CALLS_PER_HOUR=120
```

The deployment identity must have permission to access the Firestore audit collection. This adapter uses Google's metadata service for identity and does not accept a service-account key. Leaving `FIRESTORE_PROJECT_ID` unset keeps exportable in-memory reports and accurately reports persistence as disabled. It does not silently claim Firestore succeeded.

The browser now uses an HTTP event stream for the whole recovery and audit save. This keeps the request active on hosts that allocate CPU only during requests. Closing the stream cancels further recovery actions. Completed audits can be retrieved through Firestore after an instance restart. The legacy polling API remains for older clients; configure one instance for those clients. Verify the actual host's request timeout and Firestore permissions before publishing the final link.

The Node runtime exposes Gemini and explicitly labeled non-AI rehearsal only. Gemini is its only model integration; it never falls back after a Gemini failure. Free-tier eligibility and quota belong to the configured Google account; this code cannot guarantee an account's pricing tier.

## Equivalence evidence

`export-parity.py` generates deterministic reference traces from the primary Python implementation, without calling a model. `runtime.test.mjs` compares full normalized event streams, state and independent verification checks for all six scenarios, 48 varied custom incidents, both planners, and adversarial controller guards. It also checks fresh Gemini structured-output transport with an HTTP mock and the browser-facing API. Timestamp and elapsed-time fields are the only normalized fields.

Regenerate reference data from the repository root after changes to the Python domain:

```text
python starter/export-parity.py
node --test starter/runtime.test.mjs
```

`contracts.json` contains the Python scenario definitions, public scenario views, typed-action schema, default incident and planner system instruction. It contains no credential or completed run. `parity-fixtures.json` contains deterministic test evidence only and is never read by the running application.
