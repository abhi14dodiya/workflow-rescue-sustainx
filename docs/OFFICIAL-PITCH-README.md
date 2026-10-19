# Official pitch materials

Use **Workflow-Rescue-Official-Pitch-Reviewed.pptx**, not the older custom six-page deck.
It is populated from the organizer's actual PowerPoint template, downloaded from:

https://docs.google.com/presentation/d/13rg7vW43mEH6DkpuusAE6fdoEylSFz8waNpE4RLzoUg/export/pptx

The original remains in `AI-Builder-Cup-Official-Template.pptx`. The populated deck
preserves its cover, header, footer, required sections and closing artwork. It has
15 visible slides; the instruction-only download slide is removed. The matching PDF
also has 15 pages. The original blank branded slide contains cited sources.
All substantive slide content is editable. Speaker notes explain evidence and limits.

## Build inputs

`official-deck-status.json` controls the registered leader name, the three public
links, deployment status flags, verified local test counts and optional fresh
verification screenshot. Missing inputs remain visible. The Gemini performance
slide reads `artifacts/evaluation-gemini.json` and displays failed cases in red;
it never substitutes rehearsal or another provider's results for Gemini results.
`repo_verified` and `video_verified` distinguish proposed public URLs from files
that have actually been published and checked. `firestore_verified` means the
application runtime's persistence works, not merely that a database probe passed.

The latest user-supplied submission instructions say the video must be **3–4
minutes**. This deck applies those instructions, despite the older template's
3-minute link label. Target approximately 3:30 and show working functionality.

Do not mark Firebase, Firestore or Cloud Run verified until the respective live
deployment has been checked. The current Cloud Shell tunnel is temporary and
does not establish the required availability throughout evaluation. The supplied
free-only spending constraint remains in force.

## Regenerate the final files

Update `official-deck-status.json`, then run from the repository root:

```powershell
python scripts/make-official-deck.py --render
```

`--render` uses the installed local Microsoft PowerPoint in a background COM
instance to export an identical PDF and preview images. The PPTX generation uses
`python-pptx`; preview validation also uses Pillow, pywin32 and pypdf. No model or
paid service is called. Inspect `artifacts/official-deck-preview/contact-sheet.jpg`
and `artifacts/official-deck-validation.json` after rebuilding.

To replace the clearly labelled rehearsal screenshot, add these entries only
after capturing a real Gemini run:

```json
{
  "verification_image": "C:/absolute/path/to/actual-gemini-verification.png",
  "verification_label": "Actual deployed Gemini run; scenario and model-call count verified against its audit."
}
```

Check that all public links open while signed out, the registered leader is
correct, the outcome evidence is current, and every technology claim matches the
deployment. The existence of a deck does not mean the competition form has been
submitted.

The reviewed version replaces the initial deck: slide numbering, text fit, example consistency, screenshot readability and speaker notes were corrected. Use the Reviewed filename; earlier local copies are retained. The registered leader field and durable Cloud Run deployment remain unresolved.
