# Submission checklist — sustAInX

**Project:** Workflow Rescue. **Theme:** Future of Work & Enterprise Productivity.

The submission instructions supplied by the registered team on 18 October 2026 take precedence over the earlier public FAQ summary. The team is targeting submission before midnight today; the authenticated dashboard determines the actual cutoff and timezone.

## Required deliverables

| Deliverable | Mandatory requirement | Current action |
|---|---|---|
| Pitch deck | Use the organizer's prescribed presentation template; an independently designed deck is not a substitute. | Use the prepared [official-template PPTX](Workflow-Rescue-Official-Pitch.pptx), based on the [official template](https://docs.google.com/presentation/d/13rg7vW43mEH6DkpuusAE6fdoEylSFz8waNpE4RLzoUg/edit), preserve its required fields, and inspect the exported PPTX. |
| Demonstration video | **3 to 4 minutes**, clearly showing working functionality. | Target **3:30**. Record the actual deployed Gemini application; review the output and upload it to a publicly accessible video/file host. |
| Prototype URL | Publicly accessible, deployed and working **throughout evaluation**, including its APIs. | A temporary Cloud Shell tunnel is a development preview and cannot satisfy this availability requirement. Validate the durable hosting URL before submission. |
| GitHub repository | Accessible source code and supporting materials, available throughout evaluation. | Publish the reviewed source, then open the repository while signed out. A ZIP alone does not meet this requirement. |
| Brief description | Explain the solution and the use of **Firebase, Firestore, Cloud Run and Gemini**. | See [submission text](SUBMISSION-TEXT.md). Describe implemented integrations only. Verify the dashboard's technology requirements against actual deployment. |

The supplied instructions also say to include all technology mentioned in the submission rules. **Current implementation must therefore be checked for all four named services; mentioning an unimplemented service in the description does not meet the requirement.**

## Evidence and open gates

The deployed Gemini 3.5 Flash-Lite evaluation passed all six reviewed scenarios with zero safety-check failures. The editable incident lab and JSON import passed actual browser checks. Firestore saved an app-generated report and restored it after the backend restarted. There are 83 passing Python tests and 8 JavaScript tests. These results apply to a synthetic prototype, not production transactions.

| Gate | Evidence needed before describing it as complete |
|---|---|
| Gemini functionality | Successful fresh recovery on the deployed URL; audit reports `provider: gemini`, nonzero model calls and the observed outcome. Review all six scenarios separately. |
| Durable deployment | Stable public URL, signed-out browser verification and working backend after a new session. Cloud Shell's session-bound URL is insufficient. |
| Firebase | Firebase project configured; static materials portal is being finalized. It is not Python backend hosting. |
| Firestore | Completed: actual UI-generated audit saved and restored after app restart. Active execution remains in memory. |
| Cloud Run | Deployed service and revision; the current preview runs in Cloud Shell. |
| Budget | User permits free-tier resources only. Do not assume trial credits, paid Vertex AI, or uncapped billable hosting are permitted. |
| Repository, video and deck | Public links/required files created and tested. |

## What the prototype does

The app owner's operations team supplies scoped authority. Gemini chooses diagnostic or recovery actions from observed payment, stock and dispatch evidence. A separate controller enforces the reviewed customer mandate, evidence references, idempotency and stock versions. Independent checks establish the final state or require operator review.

The six built-in incidents use **synthetic service data**. Each live Gemini run makes new model requests; the replay control shows the events from a completed run without making new requests. This is a bounded workflow prototype, not an installed payment processor or a production audit system. JSON import supports bounded synthetic incident settings. Real customer records and production connectors are not supported.

## Final order of work

1. Finish deployment and live Gemini checks; resolve any mandatory technology gaps.
2. Inspect the prescribed-template PPTX and make its claims match the final application.
3. Publish the source repository and verify public access without an account.
4. Record the **3:30** deployed demonstration using [DEMO-SCRIPT.md](DEMO-SCRIPT.md), inspect its audio/video, then upload it.
5. Add the final prototype, repository and video URLs to the deck and submission fields. Open every URL while signed out.
6. Submit through the registered team's dashboard and retain the organizer's confirmation. Prepared files are not a submitted entry.

Use only measured results from actual artifacts. Any savings example is a scenario calculation, not measured customer savings or evidence that qualification is guaranteed.
