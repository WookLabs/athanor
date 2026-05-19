<!-- Provenance:
  upstream: ce@3.8.3 references/dev-server-rails.md
  source-commit: vendored at athanor v0.10.0 release time from ce@3.8.3
  upstream-url: https://github.com/EveryInc/compound-engineering-plugin
  license: MIT (Copyright (c) 2025 Kieran Klaassen / Every Inc)
  modifications: none — verbatim copy under T2 vendoring pattern; provenance block inserted after frontmatter only
  t0-t1-disproof:
    Why not T0/T1? ce is shipped as a Claude Code plugin (T3 marketplace
    listing). T0 (install companion) is unavailable for per-skill reference files.
    T1 (require dependency) is reserved pending Claude Code plugin-spec `requires`
    field support. T2 (vendor) is the only feasible tier today.
-->

# Rails dev-server recipe (auto-detect fallback)

Loaded when `detect-project-type.sh` returns `rails` and there is no `.claude/launch.json` to consult.

## Signature

- `bin/dev` exists and is executable
- `Gemfile` exists

## Start command

```bash
bin/dev
```

`bin/dev` is the Rails 7+ convention for "start everything" (web + assets watcher + optional workers). It is a one-liner script that invokes `foreman start -f Procfile.dev` under the hood, so `Procfile.dev` is the canonical place to read the *actual* command if `bin/dev` is missing or non-executable.

## Port

Default: `3000`. Overrides follow the cascade in `references/dev-server-detection.md`:
1. `Procfile.dev` `web:` line may contain `-p <n>`
2. `config/puma.rb` may bind to a non-default port
3. `.env` / `.env.development` `PORT=<n>`
4. `AGENTS.md` / `CLAUDE.md` project instructions

## Stub generation for `.claude/launch.json`

When the user accepts "Save this as `.claude/launch.json`?", emit the Rails stub from `launch-json-schema.md`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Rails dev",
      "runtimeExecutable": "bin/dev",
      "runtimeArgs": [],
      "port": 3000
    }
  ]
}
```

If the cascade resolved a non-3000 port, substitute it in the stub's `port` field before writing.

## Common gotchas

- **Bundler path:** some machines require `bundle exec bin/dev`. If `bin/dev` fails with a load-path error, fall back to `bundle exec bin/dev`.
- **Foreman vs overmind:** `Procfile` vs `Procfile.dev` often both exist. Rails' `bin/dev` resolves to `Procfile.dev`; if the project uses `overmind` explicitly, prefer `overmind start -f Procfile.dev` (see `dev-server-procfile.md`).
- **SSL dev server:** `rails s` with `--ssl` changes the URL scheme. Polish's reachability probe uses `http://`; users with SSL dev servers should set `port` explicitly in `.claude/launch.json` and note the scheme in the checklist.
