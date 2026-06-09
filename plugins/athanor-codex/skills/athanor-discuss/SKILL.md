---
name: athanor-discuss
description: Clarify intent or synthesize a decision using Athanor's Codex-native discuss workflow. Use for brainstorming, A vs B tradeoffs, ambiguous requirements, and requirements.md capture.
---

# Athanor Discuss

Use this when the user needs better intent, clearer requirements, or a decision
between options before planning or implementation.

## Mode Selection

Pick the mode from the user's request. If the choice is not clear, ask one
question with concrete options.

- `clarify`: the goal, user, constraints, or success criteria are unclear.
- `synthesis`: options are already visible and need comparison.

## Clarify Mode

Run a single coherent dialogue. Ask one question per turn. Do not stack several
questions into one message.

Scan for these gaps and ask only the probes that matter:

- Evidence gap: the user wants a thing, but the concrete pain or prior attempt
  is missing.
- Specificity gap: the beneficiary or context is too abstract to design for.
- Counterfactual gap: the current workaround and its cost are unclear.
- Attachment gap: the user is attached to a solution shape before the value is
  explicit.

When the scope is stable, summarize what will be built, tradeoffs, non-goals,
and remaining callouts. If the user asks for an artifact, write
`.athanor/sessions/<id>/requirements.md` with stable requirement IDs.

## Synthesis Mode

Compare options without inventing hidden requirements.

1. Restate the decision and visible options.
2. Inspect repo facts or external constraints when they materially affect the
   choice.
3. Evaluate options by value, cost, risk, reversibility, and verification.
4. Recommend one path, including when to revisit it.
5. Save a short decision note under `.athanor/sessions/<id>/decisions.md` only
   when the user asks for persistent session output.

## Codex Constraints

- Do not claim Claude Task dispatch or Claude hook enforcement.
- Use `request_user_input` only when available and when a blocking choice is
  truly needed; otherwise ask plainly.
- Keep the output actionable: requirements, decision, next plan input, or the
  next single question.
