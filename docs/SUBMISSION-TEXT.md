# Submission text — review against the final deployment

**Team:** sustAInX  
**Solution:** Workflow Rescue  
**Theme:** Future of Work & Enterprise Productivity

## Brief solution description

Workflow Rescue helps an app owner's operations team resolve interrupted business workflows while preserving customer instructions. When payment, inventory and order records disagree, Gemini reads available evidence and proposes a recovery. A separate controller checks permissions, evidence, idempotency and inventory versions before executing the permitted step. Independent checks then verify the business state or flag a case for human review. The prototype includes six synthetic order incidents plus a custom editor and JSON import. Users can change stock, payment visibility and explicit permissions, run fresh Gemini recovery, inspect the evidence trail and export the saved audit.

## Technology description — current verified scope

**Gemini:** The controller gathers mandatory service evidence; Gemini 3.5 Flash-Lite selects recovery actions and requests fresh evidence when conditions change. Credentials stay on the server. All six reviewed fixtures passed the live model evaluation; these are demonstrations, not a general accuracy benchmark.

**Firebase:** A Firebase project is configured. A static Hosting portal is prepared to distribute the deck, video and source links; its public deployment is being finalized. The materials portal is separate from the working backend.

**Firestore:** Completed recovery reports are saved by the backend using its Google identity. A report created through the actual interface was restored after the app restarted. Browser access is denied by Firestore rules; active workflow execution remains process-local.

**Cloud Run:** The current public preview uses a Google Cloud Shell VM with a temporary HTTPS tunnel. It is not Cloud Run and does not meet the evaluation-period availability requirement. Replace only after a durable Cloud Run service is verified.

**Do not paste the incomplete technology section as a claim of compliance.** The user's supplied rules name all four services. Resolve those implementation/deployment gaps first; if unresolved, report them truthfully.

## Problem and value, in two sentences

A successful payment can coexist with a failed order, expired stock reservation or changed customer request, leaving operations teams to reconcile conflicting systems. Workflow Rescue gathers evidence, proposes only permitted recovery steps and verifies the resulting state, so the operator can resolve supported cases and identify those that need human intervention.

## Innovation and scope

The distinctive behavior is adapting after a recovery proposal becomes invalid: a stale stock snapshot is rejected, fresh evidence is requested, and the next action must still preserve the customer's mandate. Separate execution guards and state checks keep a fluent AI explanation from being mistaken for a completed recovery.

The current examples are simulated; no production integrations, measured customer savings or broad benchmark accuracy are claimed. A rules engine can also solve these fixtures. Any benefit from AI across a wider incident population needs additional measurement.

## Submission fields

| Field | Final value |
|---|---|
| Deployed prototype | **Pending durable verified URL** |
| GitHub repository | https://github.com/abhi14dodiya/workflow-rescue-sustainx (source publication being finalized) |
| Demonstration video | **Pending public 3–4-minute video URL** |
| Prescribed-template deck | [Official-template PPTX](Workflow-Rescue-Official-Pitch.pptx); registered names still required |

Replace every pending value before submission and test all links while signed out.
