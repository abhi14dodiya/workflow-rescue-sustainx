# Submission checklist — sustAInX

**Project:** Workflow Rescue. **Theme:** Future of Work & Enterprise Productivity.

The submission instructions supplied by the registered team on 18 October 2026 take precedence over the earlier public FAQ summary. The team is targeting submission before midnight today; the authenticated dashboard determines the actual cutoff and timezone.

## Required deliverables

| Deliverable | Mandatory requirement | Current action |
|---|---|---|
| Pitch deck | Use the organizer's prescribed presentation template; an independently designed deck is not a substitute. | Use the prepared [official-template PPTX](Workflow-Rescue-Official-Pitch-Reviewed.pptx), based on the [official template](https://docs.google.com/presentation/d/13rg7vW43mEH6DkpuusAE6fdoEylSFz8waNpE4RLzoUg/edit), preserve its required fields, and inspect the exported PPTX. |
| Demonstration video | **3 to 4 minutes**, clearly showing working functionality. | **3:30.05 recorded and reviewed.** Actual public-app Gemini run with narration; [Public MP4](https://gen-lang-client-0915819772.web.app/downloads/workflow-rescue-demo.mp4) verified without signing in. |
| Prototype URL | Publicly accessible, deployed and working **throughout evaluation**, including its APIs. | [Cloud Run application](https://workflow-rescue-112348114226.us-central1.run.app): anonymous browser recovery and Firestore restoration after a new revision verified on 19 October 2026. |
| GitHub repository | Accessible source code and supporting materials, available throughout evaluation. | [Public repository](https://github.com/abhi14dodiya/workflow-rescue-sustainx) published; source access verified without credentials. |
| Brief description | Explain the solution and the use of **Firebase, Firestore, Cloud Run and Gemini**. | See [submission text](SUBMISSION-TEXT.md). Describe implemented integrations only. Verify the dashboard's technology requirements against actual deployment. |

The supplied instructions also say to include all technology mentioned in the submission rules. **Current implementation must therefore be checked for all four named services; mentioning an unimplemented service in the description does not meet the requirement.**

## Evidence and open gates

The earlier deployed Gemini 3.5 Flash-Lite evaluation passed all six reviewed scenarios with zero safety-check failures. The editable incident lab and JSON import passed actual browser checks. Firestore saved an app-generated report and restored it after the backend restarted. The current Gemini-only source has 81 passing Python tests and 11 frontend tests. The Node runtime also passed 137 tests. Cloud Run hosting is now live; a fresh uploaded incident completed with two real Gemini calls, and its Firestore audit restored after a new revision at the same URL. These results apply to a synthetic prototype, not production transactions.

| Gate | Evidence needed before describing it as complete |
|---|---|
| Gemini functionality | Successful fresh recovery on the deployed URL; audit reports `provider: gemini`, nonzero model calls and the observed outcome. Review all six scenarios separately. |
| Durable deployment | Stable public URL, signed-out browser verification and working backend after a new session. Cloud Shell's session-bound URL is insufficient. |
| Firebase | Completed: [Firebase materials portal](https://gen-lang-client-0915819772.web.app) and downloads verified. It is not Python backend hosting. |
| Firestore | Completed: actual UI-generated audit saved and restored after app restart. Active execution remains in memory. |
| Cloud Run | Completed: `workflow-rescue`, `us-central1`, hosting project `workflow-rescue-host-562392`. |
| Budget | $5?$10 monthly hosting target approved. INR 500 Cloud Run spend cap and INR 750 total-project alerts configured; Gemini/data project remains unbilled. See [cost scope](MANAGED-HOSTING.md). |
| Repository, video and deck | Public links/required files created and tested. |

## What the prototype does

The app owner's operations team supplies scoped authority. Gemini chooses diagnostic or recovery actions from observed payment, stock and dispatch evidence. A separate controller enforces the reviewed customer mandate, evidence references, idempotency and stock versions. Independent checks establish the final state or require operator review.

The six built-in incidents use **synthetic service data**. Each live Gemini run makes new model requests; the replay control shows the events from a completed run without making new requests. This is a bounded workflow prototype, not an installed payment processor or a production audit system. JSON import supports bounded synthetic incident settings. Real customer records and production connectors are not supported.

## Final order of work

1. Use the verified [Cloud Run application URL](https://workflow-rescue-112348114226.us-central1.run.app) in the submission; replace any expired tunnel link.
2. Add the registered team details to the prescribed-template PPTX. The video, public materials portal and source repository are prepared.
3. Add the verified durable prototype URL to the deck and submission fields; open every final link while signed out.
4. Submit through the registered team's dashboard and retain the organizer's confirmation. Prepared files are not a submitted entry.

Use only measured results from actual artifacts. Any savings example is a scenario calculation, not measured customer savings or evidence that qualification is guaranteed.
