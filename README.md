# Workflow Rescue by sustAInX

An operations recovery prototype for orders interrupted between payment, stock and fulfillment. Gemini proposes the next permitted action; an independent controller enforces evidence, customer permissions, stock versions and idempotency, then verifies the result.

**All business services and customer data are synthetic.** This app does not access a bank, real inventory or a carrier. Its intended adopter is the app owner's operations team, with explicitly granted connector permissions.

## Current verified state

- Live Gemini API: **6/6 reviewed fixtures passed**, with zero safety-check failures, using `gemini-3.5-flash-lite`. See [the actual evaluation](docs/validation/evaluation-gemini.json).
- **83 Python tests and 8 JavaScript tests passed.** Desktop/mobile browser checks passed against the public application.
- Custom incident lab: change stock, payment visibility, dispatch state and explicit permissions, or import a small validated JSON incident. These are new simulations, not recorded outcomes.
- Firebase project and free Firestore database created. The server can persist and restore completed audit reports using its Google identity. Browser access to Firestore is denied by rules.
- Temporary public demo: https://federation-php-architecture-blocked.trycloudflare.com . **This stops when its Cloud Shell session ends and is not a durable evaluation deployment.**
- Durable Cloud Run hosting remains unresolved under the owner's no-paid-usage requirement. Firebase static hosting cannot run this Python backend.

## Run locally

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Open `http://localhost:8080`. A clean checkout defaults to **Rehearsal**, which makes no AI calls. Built React assets are included in `web/`.

To rebuild the interface:

```powershell
npm --prefix frontend ci
npm --prefix frontend run build
```

Use a supported Node 22.12+ or Node 24 release. The Dockerfile builds React in a Node stage and serves it from Python.

## Gemini and storage configuration

Keep credentials in an ignored server-only `.env`, never in React, a Docker image, Git, or a presentation:

```dotenv
DEFAULT_PROVIDER=gemini
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=YOUR_SERVER_SIDE_KEY
# Optional completed-audit persistence, using Google ADC:
FIRESTORE_PROJECT_ID=YOUR_FIREBASE_PROJECT_ID
```

The public demo uses the Gemini Developer API Free tier. It does not use Vertex AI. A Google API key cannot simply replace an Azure credential at an Azure endpoint; choose the Gemini adapter.

Requests are spaced at least 15 seconds apart within one server process. Rejected 429/503 requests have bounded retries; daily exhaustion stops rather than upgrading or falling back to paid providers. Google's actual quotas remain authoritative. On this account, Gemini 3.8 Flash reached its 20-request daily limit; the tested deployment intentionally selects Flash-Lite. No rotation or silent provider fallback occurs.

The server gathers the mandatory initial payment, inventory and dispatch observations in code, saving model calls for recovery choices. Gemini can inspect again when new evidence is needed. The six-fixture live run used 4, 2, 3, 1, 2 and 1 requests respectively; these are observed counts, not future guarantees.

The optional `DEMO_ACCESS_TOKEN` gates live calls. There are bounded planning steps, concurrent-run limits and an hourly process budget. **These controls are not cloud billing caps.**

See [Google setup](docs/GOOGLE-SETUP.md) and [Firebase/Firestore setup](docs/FIREBASE-SETUP.md) for current infrastructure and limitations. The old `deploy-gcp` scripts are guarded legacy Vertex/Cloud Run scripts; do not use them for this free-only deployment.

## Try an incident

1. Choose one of the six examples, or expand **Create or import an incident**.
2. Set synthetic evidence and explicit demo permissions. The order remains two Field Kits at $498; arbitrary business schemas are not supported.
3. Click **Use this incident**, review the displayed mandate, and choose **Investigate & recover**.
4. Inspect the live proposals, rejected actions, receipts and final checks. Export the actual audit.

The customer note cannot authorize another charge or override the controller. Uploaded JSON supplies synthetic incident settings, not real-world authority. Replay only reads recorded events and never starts new model calls.

| Example | Expected behavior |
|---|---|
| Changing stock | Reject stale reservation, read fresh evidence, recover using approved incoming stock. |
| Lost acknowledgement | Reconcile the existing charge and complete the order. |
| Cancellation | Refund once, cancel and release stock. |
| Payment authority unavailable | Keep payment unknown and escalate without a write. |
| Explicit substitution consent | Use the approved alternative at the original total. |
| Already dispatched | Escalate; do not invent a shipment rollback. |

## Verify

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
npm --prefix frontend test
python scripts/browser_check.py --base-url https://YOUR_APPLICATION_ORIGIN
python scripts/check-incident-lab.py --base-url https://YOUR_APPLICATION_ORIGIN
# Live evaluation consumes the selected model's quota:
python scripts/evaluate.py --provider gemini --base-url https://YOUR_APPLICATION_ORIGIN
```

`check-incident-lab.py` additionally expects Firestore to be configured. The browser suite uses rehearsal unless a live provider is explicitly requested. Model evaluation is separate from mocked provider tests. The fixed baseline shares the execution controller but stops at a stock conflict; a broader rules engine could also solve these fixtures. This is not proof of general AI superiority.

## Submission materials

[Public materials portal](https://gen-lang-client-0915819772.web.app) ? [Narrated 3:30 demonstration](https://gen-lang-client-0915819772.web.app/downloads/workflow-rescue-demo.mp4) ? [Public source](https://github.com/abhi14dodiya/workflow-rescue-sustainx)

The portal hosts the video and deck on Firebase; it does not provide the interactive backend.

- [Official-template editable PowerPoint](docs/Workflow-Rescue-Official-Pitch.pptx)
- [Official-template PDF](docs/Workflow-Rescue-Official-Pitch.pdf)
- [Submission checklist](docs/SUBMISSION.md)
- [Brief description](docs/SUBMISSION-TEXT.md)
- [3:30 narrated demonstration script](docs/DEMO-SCRIPT.md)
- [QA evidence and limitations](docs/QA.md)
- [Impact assumptions](docs/IMPACT.md)
- [Architecture](docs/ARCHITECTURE.md) and [sources](docs/SOURCES.md)

The prescribed deck, a **3-4 minute working demonstration**, accessible source repository and a prototype that remains functional throughout judging are required. Pending team details and durable hosting must be resolved before calling the submission complete. No competition submission or finalist result is implied.
