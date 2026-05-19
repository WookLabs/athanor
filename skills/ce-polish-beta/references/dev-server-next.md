<!-- Provenance:
  upstream: ce@3.8.3 references/dev-server-next.md
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

# Next.js dev-server recipe (auto-detect fallback)

Loaded when `detect-project-type.sh` returns `next` and there is no `.claude/launch.json` to consult.

## Signature

- `next.config.js`, `next.config.mjs`, `next.config.ts`, or `next.config.cjs` exists
- `package.json` contains a `next` dependency

## Start command

Standard:

```bash
npm run dev
```

Also valid (read `package.json` scripts to confirm which the project uses):

```bash
pnpm dev
yarn dev
bun run dev
```

Prefer the package manager indicated by the lockfile:
- `pnpm-lock.yaml` -> `pnpm dev`
- `yarn.lock` -> `yarn dev`
- `bun.lock` / `bun.lockb` -> `bun run dev`
- `package-lock.json` or none -> `npm run dev`

## Port

Default: `3000`. Next.js respects `-p <port>` / `--port <port>` and the `PORT` env var. Overrides follow the cascade in `references/dev-server-detection.md`.

## Turbopack

Next.js 14+ supports `--turbo` (and 15+ makes it default). If the `dev` script in `package.json` includes `--turbo`, preserve it. Turbopack changes reload behavior but not port or URL conventions.

## Stub generation

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Next dev",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "dev"],
      "port": 3000
    }
  ]
}
```

Substitute the resolved package manager (`npm` / `pnpm` / `yarn` / `bun`) and port.

## Common gotchas

- **App Router vs Pages Router:** dev-server behavior is the same; polish doesn't care. Checklist generation (Unit 5) does — pages in `app/` and `pages/` are different surfaces.
- **Monorepo roots:** in a pnpm/Turborepo monorepo, `npm run dev` at the root typically fans out to multiple packages. Users should set `cwd` in `.claude/launch.json` to the specific Next app (`cwd: "apps/web"`).
- **Env loading:** `.env.local` is loaded automatically by Next; polish does not need to export it.
