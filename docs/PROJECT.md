# Final project decision: Workflow Rescue

**Team: sustAInX.** Keep this exact spelling in the competition form, deck and video credits.

**Theme: Future of Work & Enterprise Productivity.**

**One-line pitch:** When a business workflow stops halfway, Workflow Rescue reconstructs what actually happened and verifies a recovery that respects the customer's instructions.

## The person and the problem

Maya, an operations engineer, must recover an interrupted customer order. Payment appears to have failed, the original reservation expired, and the customer forbids substitutions. Retrying blindly risks a duplicate action; refunding blindly may violate the customer's request to complete the order. During recovery another order consumes the remaining stock.

The prototype gives Maya an evidence trail, a bounded recovery proposal, enforceable customer permissions and independently checked outcomes. The featured recovery uses the existing payment and original items from an incoming delivery within the permitted delay.

## Fit with the published rubric

| Rubric | What we demonstrate |
|---|---|
| Technical Merit & Gen AI Implementation — 40% | Actual Gemini structured proposals; adaptive observation/replanning; controlled tools; independently verified state. The six reviewed Google-model fixtures passed; broader validation is still required. |
| Problem Alignment & Impact — 25% | A clear enterprise operations problem involving customer intent, payments and stock; an identifiable operator and measurable outcomes. Real business impact is a hypothesis, not yet a customer-validated result. |
| Innovation & Creativity — 25% | Recovery under changing evidence and natural-language constraints, with evidence beside actions. Durable workflows, retries and compensation already exist; we do not claim to invent them. |
| User Experience & Solution Design — 10% | One incident story, a coherent visual language, inspectable receipts and clear recovered/review/error outcomes. |

No published numerical qualifying cutoff or reliable finalist probability was found in the research. The rankings were selection judgments, not promised scores.

## Scope we are actually building

- Three explicitly simulated boundaries: payments, inventory and order/dispatch.
- Six reviewed incident fixtures plus a validated editable/JSON-import incident lab, with an optional stock race between observation and reservation.
- A real execution controller; the model cannot call arbitrary code, charge cards or ship orders.
- Gemini Developer API as the only live AI integration, plus clearly labelled deterministic rehearsal that makes no AI calls.
- A web interface, downloadable audit, baseline comparison, automated state/controller tests and browser checks.

## Why this project, finally

It matches the team's software and enterprise experience, uses controllable data, makes the AI's next-step decisions visible, and supports a concise, testable before/after. We can explain both what the model contributes and where code must remain in control. Scope is deliberately bounded to make a complete demonstration achievable.

The first prototype is not a production transaction-recovery platform. Real service integrations, durable distributed transactions, broader policy interpretation and real stakeholder validation remain future work.
