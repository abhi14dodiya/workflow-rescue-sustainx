# Prototype QA - 18 October 2026

## Verified results

| Area | Result | Evidence |
|---|---|---|
| Python controller, API, provider and persistence checks | PASS: 83 tests | `python -m pytest -q`; includes quota pacing, bounded retry, daily exhaustion, custom input validation and audit-save completion. |
| Recorded-state projection | PASS: 8 tests | `npm --prefix frontend test`; future evidence isolation and final-state correctness. |
| Live Gemini evaluation | PASS: 6/6 reviewed fixtures, zero safety-check failures | `docs/validation/evaluation-gemini.json`; actual Gemini 3.5 Flash-Lite calls through public deployment. |
| Desktop/mobile browser flow | PASS | `docs/validation/browser-validation.json`; 320px and 390px layouts, Home reload, history race, keyboard controls, reduced motion, no-WebGL fallback and audit download. |
| Production interface build | PASS | React/Vite built with local fonts and separate Three.js chunk. |
| Free Firebase/Firestore infrastructure | PASS | `docs/validation/firebase-free-setup.json`; billing disabled, free default database, deny-client rules. |
| Firebase materials portal | PASS | Public page, PPTX, PDF and narrated MP4 returned HTTP 200; billing remains disabled. This is static materials hosting. |
| Firestore server access | PASS in Cloud Shell probe | `docs/validation/firestore-cloud-roundtrip.json`; write/read comparison and deletion of the exact synthetic probe. |
| Custom incident runtime and restart persistence | PASS | `docs/validation/custom-incident-browser.json` and `firestore-runtime-restart.json`; actual UI import, changed recovery outcome, saved audit restored after backend restart. |
| Public source repository | PASS | Public GitHub repository, README and API source returned HTTP 200 without credentials; published commit matched the reviewed local tree. |
| Official deck | Organizer template used | `Workflow-Rescue-Official-Pitch.pptx` and `.pdf`; registered names still need confirmation. |
| Narrated video | PASS: 210.05 seconds | `docs/validation/video-qa.json` and `video-manifest.json`; actual public-app Gemini recording, offline Microsoft Zira narration, complete decode and visual/audio review. |
| Durable Cloud Run deployment | NOT COMPLETE | Cloud Shell is temporary; Firebase static hosting cannot execute the Python backend. |

## What the Gemini result means

The controller gathers payment, inventory and dispatch observations before the first model request. Gemini then selects recovery actions, obtains new inventory evidence after the injected stock conflict and proposes permitted changes. The six run call counts were 4, 2, 3, 1, 2 and 1. Unknown payment and already-dispatched cases correctly ended in review, not forced recovery.

These are six reviewed synthetic fixtures, not a held-out benchmark. The fixed workflow shares the same guarded tools and stops at a stock conflict; a richer rules engine could also solve the examples. No general accuracy, production reliability or AI-superiority claim follows from 6/6.

The earlier Gemini 3.8 Flash attempt failed: first 1/6, then daily quota exhaustion. Google returned a per-model free-tier limit of 20 requests/day. Those failures were not re-labelled as successes. The deployment intentionally changed to the listed free Gemini 3.5 Flash-Lite model and reduced unnecessary model calls. There is no silent provider fallback, quota increase or paid upgrade.

## Corrections found during QA

- Initial mandatory evidence reads consumed scarce model quota; code now gathers those three reads before asking Gemini to select recovery.
- Rejected model requests could terminate recovery immediately; bounded 429/503 retries and process-wide spacing now respect quota. Daily or long reset windows stop cleanly.
- A newly edited incident could be started before validation completed; the start controls now wait for the applied permissions.
- A terminal run could appear ready while Firestore saving still occupied the active slot; the UI now shows Saving audit until that attempt finishes.
- Cloud Shell authorization expired after the database probe. Google session authorization must be renewed; database existence alone does not establish runtime persistence.

## Boundaries and remaining requirements

All business services and customer data are simulated. JSON import changes a bounded two-kit, $498 incident; it cannot introduce a charge tool or authorize real transactions. Completed Firestore reports are inspectable, not a certified immutable audit log. Active execution and model-call budgets remain process-local.

The current public backend is session-bound Cloud Shell hosting. A permanent Firebase materials page does not make that backend durable. The user's rules require all APIs to remain functional throughout evaluation; Cloud Run, registered team details and final dashboard submission remain open until separately verified.

The illustrative impact calculation is a staffing-capacity hypothesis, not measured savings. No billion-dollar savings or finalist qualification is claimed.
