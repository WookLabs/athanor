# UserPromptSubmit Spike Harness

This is an opt-in live payload spike for `UserPromptSubmit`. Athanor does not
register `UserPromptSubmit` in repo `hooks/hooks.json`, and this harness does
not replace the current static dedup mechanism.

## Generate Settings Snippet

Run:

```powershell
python scripts/hooks/user_prompt_submit_spike.py --print-settings-snippet
```

Copy the printed `UserPromptSubmit` entry into user-global Claude settings only
for the spike session. The script writes local evidence under `.athanor/spikes`.

## Capture

After installing the snippet manually, submit one ordinary prompt in Claude Code.
The hook writes two local files:

- `.athanor/spikes/ups-payload-<timestamp>-<hash>.json`
- `.athanor/spikes/ups-payload-<timestamp>-<hash>.summary.json`

The raw JSON is ignored local state and must not be committed.

## Redacted Summary

Redacted summary files are safe to inspect because they omit original prompt
text.

The committed evidence, if needed later, should come from the redacted summary.
It records only payload shape: top-level keys, nested object keys, value types,
string lengths, and short hashes. It must not include prompt text.

## Cleanup

Remove the `UserPromptSubmit` entry from user-global Claude settings after the
spike. Keep raw payloads local unless a future review explicitly approves a
sanitized fixture.

## Promotion Criteria

Only after a live capture confirms the payload shape should Athanor design
runtime prompt injection or static-dedup replacement. Until then,
`capability_probe.py` must continue reporting `UserPromptSubmit.supported =
false`.
