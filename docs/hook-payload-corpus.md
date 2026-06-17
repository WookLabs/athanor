# Hook Payload Corpus

This corpus gives athanor a replayable hook-payload evidence base before any
evidence-only behavior is promoted to strict enforcement.

## Fixture Provenance

Fixtures live in `tests/fixtures/hooks/index.json`.

- `synthetic`: hand-authored payloads that exercise the current contract. These
  are useful regression locks, but they do not prove Claude Code live payload
  shape.
- `live-redacted`: sanitized captures from a real Claude Code hook invocation.
  These are required before changing `tool_response_available` or similar
  capability fields from expected to confirmed.
- `summary-only`: shape metadata without raw payload fields. Use this only when
  a raw fixture would be unsafe to commit.

The corpus includes synthetic contract fixtures, live-redacted Claude Code
2.1.177 captures for Stop, PreToolUse, and PostToolUse, and a Claude Code
2.1.178 live-redacted targeted pytest PostToolUse capture. The synthetic
fixtures cover Stop transcript-path parsing, PreToolUse kernel blocking,
PostToolUse pytest evidence, and PostToolUse Freeze D2 file-change
observations. The live fixtures prove the installed Claude Code payload shape
for the core hook events and the targeted pytest evidence path, including the
current boundary that targeted pytest PostToolUse output has stdout/stderr but
no direct exit-code field.

## Opt-In Live Capture

`scripts/hooks/hook_payload_capture.py` is a log-only capture harness for
reviewing live Stop, PreToolUse, PostToolUse, FileChanged, SessionStart,
UserPromptSubmit, PreCompact, PermissionRequest, PostToolUseFailure, and
SubagentStop payload shapes. It is not registered in repo `hooks/hooks.json`;
use it only by copying the printed settings snippet into user-global Claude
settings for a short manual capture session.

Print the snippet with:

```bash
python scripts/hooks/hook_payload_capture.py --print-settings-snippet
```

When installed manually, the harness writes raw payloads plus redacted
shape-only summaries under `.athanor/spikes/hook-payloads`. The summary records
keys, scalar types, string lengths, and short hashes, but not raw prompt,
tool-input, token, or private URL strings. Remove the temporary user-global
settings entry after capture, then manually review the raw payload before
importing it into this corpus.

## Redaction Rules

Do not commit raw secrets, host-local absolute paths, user names, private image
URLs, or private key material. Prefer project-relative paths and placeholder
values. A fixture that came from a live run must be reviewed and reduced before
being marked `live-redacted`.

## Live Import

After a manual review of a captured hook payload, import it with:

```bash
python scripts/gates/import_hook_fixture.py \
  --fixture-root tests/fixtures/hooks \
  --id live-posttool-pytest-example \
  --event PostToolUse \
  --payload .athanor/spikes/raw-posttool-payload.json \
  --expected-json .athanor/spikes/raw-posttool-expected.json
```

The importer recursively redacts home-directory paths, Claude project slugs,
obvious API tokens, private GitHub image URLs, and private-key blocks from both
`--payload` and `--expected-json`, then appends a `source_level: live-redacted`
fixture to the index. This is not a substitute for manual review: the reviewer
must still inspect the generated fixture, confirm the expected evidence subset
is minimal, add capture provenance when committing the fixture, and run the
replay gate before committing it.

Replayable events are imported with `replayable: true`: Stop, PreToolUse, and
PostToolUse. Cataloged `capture-only` events such as SessionStart,
UserPromptSubmit, PreCompact, PermissionRequest, PostToolUseFailure,
SubagentStop, and FileChanged may also be imported after manual review, but the
importer marks them `replayable: false`. This lets the corpus retain
live-redacted shape evidence without pretending a replay handler or runtime
policy hook exists.

Do not fabricate live capture-only fixtures. A `live-redacted` fixture must
come from an opt-in capture session, be manually reduced, and keep
`redaction.review_required: true` plus the applied rules before it is committed.

## Replay

Run:

```bash
python scripts/gates/replay_hook_fixtures.py --fixture-root tests/fixtures/hooks --json
```

The replay gate creates a temporary athanor project/session, materializes any
transcript placeholder into a temp JSONL transcript, invokes the real hook
scripts, and checks exit codes plus JSONL evidence records.

Replay also enforces corpus safety before invoking hooks: fixtures containing
obvious API tokens, host-local home paths, Claude project slugs, private GitHub
image URLs, or private key blocks fail the gate. `live-redacted` fixtures must
include redaction metadata with `review_required: true` and a `rules` list, so a
manually edited fixture cannot silently bypass provenance review.

Capture-only fixtures are safety-validated before replay decisions. If a safe
fixture is marked `replayable: false` and its event is still cataloged as
`capture-only`, replay reports it as `skipped` with an explicit capture-only
reason. Unsafe capture-only fixtures still fail the gate.

## Strict Deferral

The corpus does not change runtime policy. PostToolUse missing evidence remains
a concern, not a strict failure, unless a project opts into `hooks.evidence.mode:
"strict"`. The committed live-redacted fixtures satisfy the payload-shape
precondition for the installed Claude Code 2.1.177 core hook events and the
Claude Code 2.1.178 targeted pytest PostToolUse evidence path. The sniffer
records whether an exit code came directly from the payload or was inferred
from clear pytest output summaries. Changing the default from `warn` to
`strict` still requires a separate release-policy decision for new and existing
installs.
