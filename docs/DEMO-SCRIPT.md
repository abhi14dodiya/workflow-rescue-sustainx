# Workflow Rescue — 3:30 deployed demonstration

**Team: sustAInX.** The registered team's supplied rule is **3–4 minutes**; this replaces the earlier under-three-minute draft.

Record a fresh **Gemini** run from the deployed app. Leave the provider and synthetic-services labels visible. Do not call rehearsal footage live AI, or describe Cloud Shell as Cloud Run. The script below assumes the featured stock-race recovery has actually succeeded. If it fails, fix or re-record; do not narrate success over failed evidence.

| Time | Actual screen action | Message |
|---|---|---|
| 0:00–0:22 | Home, branded recovery core, click a service | Enterprise workflows can stop between payment, stock and order systems. The operations team needs a justified next action. |
| 0:22–0:50 | Workspace; import a custom JSON incident and select Gemini; show the customer note and permissions | Existing payment, exact item, no extra charge, limited delivery delay. Service data is synthetic; Gemini calls are live. |
| 0:50–2:05 | Click **Investigate & recover** once; show new events and provider | The controller gathers mandatory evidence. Gemini chooses recovery actions and can request fresh observations. Changing stock invalidates a stale reservation. New observations support a different permitted recovery. Show the actual outcome. |
| 2:05–2:37 | Actual blocked event, inventory evidence, final independent checks | Separate proposing, enforcing and verifying. Show why the stock conflict mattered and which checks passed. |
| 2:37–3:05 | Export actual audit; open History; identify missing-evidence scenario | An operator can inspect evidence, actions and model calls. Unknown payment and post-dispatch cancellation require review. Do not claim a second case ran if it was only selected. |
| 3:05–3:30 | How it works, then Home | Explain actual Gemini integration and the owner-authorized operating model. End with the team and product name. |

## Truthful presentation rules

- Use one complete working flow; it proves more than a fast slideshow of unexecuted scenarios.
- A run is live when the application makes fresh model calls. **Replay recovery** is recorded run evidence, with no new model calls. Explain that distinction if replay appears.
- The selected fixtures make the demo reproducible. They do not establish broad real-world accuracy. There is no production payment mutation or independent authority over a customer's bank.
- If waiting time is compressed, keep a visible label stating that fact and retain the uncut recording/audit. Preserve the app's actual model latency and elapsed time.
- Do not claim Firebase, Firestore or Cloud Run merely because they appear in an architecture plan. Update the narration only after the services are integrated and verified.
- The exported audit is inspectable trace evidence, not a certified, immutable compliance record.

## Free local narrated recording

The helper uses the installed Windows **Microsoft Zira** voice, Playwright with Microsoft Edge, and locally installed FFmpeg. It makes no paid TTS calls. It creates local MP4/WAV/SRT files; it does not upload the video or submit the competition form.

```powershell
# Generates narration and a recording manifest, without calling Gemini.
python scripts/voice-demo.py prepare

# Run only after deployment validation is finished and the app is free.
# This starts ONE new live Gemini run, which consumes free API quota.
python scripts/voice-demo.py record --base-url https://YOUR-VERIFIED-APP-URL --confirm-free-gemini

# Render the recorded footage and narration into a 3:30 MP4.
python scripts/voice-demo.py render
```

Output: `artifacts/video/workflow-rescue-demo.mp4`, transcript/captions and the actual run audit. Review the whole video with sound, check its duration, ensure the selected deployment remains functional throughout judging, then publish the video link.
