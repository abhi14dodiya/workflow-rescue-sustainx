# Implementation and research references

These sources informed scope and design. The application does not claim to reproduce their results.

Official competition pages and Google design/model references were rechecked on **18 October 2026**. The logged-in submission dashboard remains uninspected; its exact cutoff and final field requirements need the registered team.

- Official themes/rubric: https://aibuildercup.com/themes.html
- Official submission FAQ: https://aibuildercup.com/Faqs.html
- Official timeline: https://aibuildercup.com/
- Gemini structured output: https://ai.google.dev/gemini-api/docs/structured-output
- Gemini available models: https://ai.google.dev/gemini-api/docs/models
- Gemini model lifecycle: https://ai.google.dev/gemini-api/docs/deprecations
- Google Cloud Gemini 3.8 Flash: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash
- Vertex inference: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference
- OpenAI structured output (temporary development adapter): https://developers.openai.com/api/docs/guides/structured-outputs
- Temporal compensation and durable workflows: https://temporal.io/blog/compensating-actions-part-of-a-complete-breakfast-with-sagas
- Stripe webhook delivery and duplicate handling: https://docs.stripe.com/webhooks
- Stripe idempotent requests: https://docs.stripe.com/api/idempotent_requests
- ToolSandbox, stateful tool-use evaluation: https://arxiv.org/abs/2408.04682
- CaMeL, separating model decisions from control/authorization: https://arxiv.org/abs/2503.18813
- Handover presentation reference: https://www.youtube.com/watch?v=k5ECYUIr2Ag
- Google Material foundations: https://m3.material.io/foundations
- Google expressive design research: https://design.google/library/expressive-material-design-google-research
- Linear's product homepage (visual hierarchy reference): https://linear.app/

The UI pass uses clearly labelled navigation, primary-action emphasis, larger touch targets, readable hierarchy, consistent rounded groups and optional motion. Cyan distinguishes the history transition; violet connects the recovery and explanation sections. These are selective design principles, not a copy of Google's brand or a claim of affiliation. Google's usability study statistics are not results for this prototype.

Handover inspired a coherent single-person story, visible intelligent interaction and evidence beside decisions. Workflow Rescue uses its own problem, implementation, text and visual design. Prior research artifacts in the user's Documents folder contain the broader source register and research QA.
