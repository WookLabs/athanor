<!-- Provenance:
  upstream: compound-engineering/ce-brainstorm SKILL.md §Phase 1.2-1.3
            (specifically "Product Pressure Test" Standard-tier lenses
            and "Collaborative Dialogue" rigor-probe rules)
  source-commit: compound-engineering@3.8.2 skills/ce-brainstorm/SKILL.md
                 §Phase 1.2-1.3 (vendored at athanor v0.9.0 release time;
                 verified still present at compound-engineering@3.8.3 during
                 v0.10.0 absorption). SHA pin not available from plugin-cache
                 distribution; version-tag fallback per CLAUDE.md §"Concept Absorption
                 Surface" drift policy (v0.10.1 correction; vendor manifest detail: docs/archive/concept-absorption-surface.md).
  license: MIT (Copyright (c) 2025 Every Inc / compound-engineering authors)
  modifications:
    - Vendored verbatim conceptual content from ce-brainstorm Phase 1.2-1.3
    - Korean prose adapted to athanor's bilingual project voice
    - Athanor-specific framing: "leader" instead of "agent", `/athanor:discuss`
      pipeline references instead of generic ce-brainstorm
    - Plus stop-phrase guard (athanor-local v0.9.0 addition; not present in
      compound-engineering ce-brainstorm)
  t0-t1-disproof:
    Why not T0/T1? compound-engineering is shipped as a Claude Code plugin
    (T3 marketplace listing) per docs/DEPENDENCIES.md §Marketplace Status.
    T0 (install companion) is unavailable for athanor's per-skill reference
    files. T1 (require dependency) is reserved pending Claude Code plugin-spec
    `requires` field support. Therefore T2 (vendor) is the only feasible tier.
-->

# Clarify-mode gap probes (vendored from ce-brainstorm Phase 1.2-1.3)

> This reference is read by `skills/discuss/SKILL.md` §"Step 2-clarify.1"
> (Internal gap-scan) and §"Step 2-clarify.2" (Dialogue protocol). Both
> the lens definitions and the probe templates live here so the SKILL.md
> body stays focused on the workflow.

## When to scan for gaps

Before asking any clarify-mode question, the leader silently runs an
**internal scan** over the user's opening prompt — agent-internal analysis,
NOT a user-facing checklist. Read the opening, note which gaps actually
exist, and raise only those as questions during the dialogue. A fuzzy
opening may earn three or four probes; a concrete, well-framed opening
may earn zero because no scope-appropriate gaps were found.

## The four lenses (ce-brainstorm Standard tier)

### Evidence gap

**When it fires:** the opening asserts a want/need but doesn't point to
anything someone has already done — time spent, money paid, workarounds
built — that would make the want observable. The user might say "we need
better notification handling" with no signal anyone has actually been
frustrated by current notification handling.

**Example open-ended probe:** *"What's the most concrete thing someone's
already done about this — paid for it, built a workaround, quit a tool
over it?"*

### Specificity gap

**When it fires:** the opening describes the beneficiary at a level of
abstraction where the leader couldn't design without silently inventing
who they are and what changes for them. The user might say "developers
need a better debugging experience" — which developers? doing what kind
of debugging?

**Example open-ended probe:** *"Can you name a specific person or narrow
segment you've actually watched hit this — or are you reasoning from
intuition? Either is fine, but the answer changes what we design for."*

### Counterfactual gap

**When it fires:** the opening doesn't make visible what users do today
when this problem arises, nor what changes if nothing ships. The user
might say "we should add a calendar integration" with no signal about
how teams handle scheduling today.

**Example open-ended probe:** *"What's the current workaround when this
problem comes up, even if it's messy — and what does that workaround
cost the user?"*

### Attachment gap

**When it fires:** the opening treats a particular solution shape as
the thing being built, rather than the value that shape is supposed to
deliver, and hasn't been examined against smaller forms that might
deliver the same value. The user might say "we need a new Settings
dashboard" without examining whether a single inline preference toggle
would do the job.

**Example open-ended probe:** *"Before we move to shapes or approaches —
what's the smallest version that would still prove the bet right, and
what's deliberately excluded from that smallest version?"*

**Attachment is the final rigor probe before scoping synthesis when the
attachment gap is present.** Fire it regardless of whether a specific
shape has emerged through narrowing; its job is to pressure-test the
user's implicit framing before the doc inherits it.

## Probe form rules (Interaction Rule 5 in ce-brainstorm)

Rigor probes are **open-ended**, NOT 4-option menus. The reason: an option
menu signals which kinds of evidence count and lets the user pick rather
than produce. Open-ended questions force the user to produce real
observation or surface their uncertainty — which is exactly the rigor
the probe is meant to extract.

Narrowing questions later in the dialogue can and should use
`AskUserQuestion` blocking menus (4 options or fewer, single-select for
direction, multi-select only for compatible sets). The line is:
- **Rigor probe** → open-ended
- **Narrowing decision** → blocking menu

## One question per turn (ce-brainstorm Interaction Rule 1)

Even when sub-questions feel related, fire only one per leader turn.
Stacking ("And also, what about X? And could you tell me Y? And by the
way, Z?") produces diluted answers because the user picks the most
convenient sub-question and ignores the rest. The leader keeps state
across turns and asks the next sub-question on the next turn.

## Stop-phrase guard (athanor-local v0.9.0 addition)

The leader's own dialog turns must NEVER use the early-stop phrases.
Stop-phrase whitelist: see `docs/stop-phrase-whitelist.md`.

These phrases were originally designed to detect workers (Researchers /
Devil's Advocate / Critic) giving up mid-task; in clarify mode, the
leader itself drives the dialog, so emitting them would short-circuit
the gap probes and silently degrade clarify into a single-pass restate.
The leader keeps progressing through scope-appropriate probes until
the integration check and scoping synthesis both pass. Users themselves
can still end the session at any turn; the guard applies only to the
leader's wording.

## Integration check (pre-exit, before scoping synthesis)

Before exiting the gap-probe phase, mentally combine what the user has
said so far and surface any non-obvious consequences the dialogue
hasn't probed. If user-stated X plus user-stated Y plus the
leader's-default-Z produces a downstream effect the user is unlikely
to have tracked through one-question-at-a-time dialogue ("if mute lives
on the rule AND we don't warn on delete, then rule-delete silently
loses pause state"), fire one open-ended probe NOW. One probe per
genuine combination effect.

Phase 2.5's scoping synthesis call-outs are a safety net for residuals
(silent agent inferences, late-cycle scope bets) — NOT a punt list for
consequences the leader could have asked about during dialogue.

## Exit condition

Continue the gap-probe phase until BOTH:

1. Every scope-appropriate gap from the internal scan has been probed.
2. The integration check has surfaced no remaining un-probed consequences.

OR the user explicitly states they want to proceed despite an outstanding
probe — in which case record the un-asked probe as an explicit assumption
in the requirements doc rather than skipping it silently.

Then fire the scoping synthesis (`skills/discuss/SKILL.md` §Step 2-clarify.4)
and wait for user confirmation before writing requirements.md.
