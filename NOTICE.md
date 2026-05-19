# NOTICE

Athanor incorporates code from third-party open-source projects. Their
copyrights and license notices are reproduced below.

---

## compound-engineering

- **Source**: https://github.com/EveryInc/compound-engineering-plugin (v3.8.3)
- **Copyright**: (c) 2025 Kieran Klaassen / Every Inc
- **License**: MIT
- **Vendored at**: athanor v0.10.0 (2026-05-19)

### Vendored skill directories

All vendored verbatim with a T2 provenance block inserted after the YAML
frontmatter. Some skill names were not modified (CE upstream already prefixes
with `ce-`); the lone exception `lfg` was renamed `ce-lfg` for namespace
clarity, and that rename is recorded in its own provenance block. Body content
is byte-identical to upstream.

- `skills/ce-agent-native-architecture/`
- `skills/ce-agent-native-audit/`
- `skills/ce-brainstorm/`
- `skills/ce-clean-gone-branches/`
- `skills/ce-code-review/`
- `skills/ce-commit/`
- `skills/ce-commit-push-pr/`
- `skills/ce-compound/`
- `skills/ce-compound-refresh/`
- `skills/ce-debug/`
- `skills/ce-demo-reel/`
- `skills/ce-dhh-rails-style/`
- `skills/ce-doc-review/`
- `skills/ce-frontend-design/`
- `skills/ce-gemini-imagegen/`
- `skills/ce-ideate/`
- `skills/ce-lfg/` (renamed from upstream `lfg/`)
- `skills/ce-optimize/`
- `skills/ce-plan/`
- `skills/ce-polish-beta/`
- `skills/ce-product-pulse/`
- `skills/ce-proof/`
- `skills/ce-release-notes/`
- `skills/ce-report-bug/`
- `skills/ce-resolve-pr-feedback/`
- `skills/ce-riffrec-feedback-analysis/`
- `skills/ce-sessions/`
- `skills/ce-setup/`
- `skills/ce-simplify-code/`
- `skills/ce-slack-research/`
- `skills/ce-strategy/`
- `skills/ce-test-browser/`
- `skills/ce-test-xcode/`
- `skills/ce-update/`
- `skills/ce-work/`
- `skills/ce-work-beta/`
- `skills/ce-worktree/`

### Vendored sub-agents

All vendored verbatim into `agents/vendored/ce/`:

- `agents/vendored/ce/*.agent.md` — 49 sub-agent definitions used by the
  vendored CE skills above.

### License text

```
MIT License

Copyright (c) 2025 Kieran Klaassen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## superpowers

- **Source**: https://github.com/obra/superpowers (v5.1.0)
- **Copyright**: (c) 2025 Jesse Vincent
- **License**: MIT
- **Originally vendored at**: athanor v0.7.8 (`skills/verification-before-completion/`, v5.0.7)
- **Expanded at**: athanor v0.10.0 (full skill-set, v5.1.0)

### Vendored skill directories

All vendored verbatim with a T2 provenance block inserted after the YAML
frontmatter. Skill names were rewritten from upstream `<name>` to athanor
namespace-prefixed `sp-<name>` to match Claude Code's directory-to-frontmatter
naming requirement; this rename is recorded in each skill's own provenance
block. Body content is byte-identical to upstream.

- `skills/sp-brainstorming/`
- `skills/sp-dispatching-parallel-agents/`
- `skills/sp-executing-plans/`
- `skills/sp-finishing-a-development-branch/`
- `skills/sp-receiving-code-review/`
- `skills/sp-requesting-code-review/`
- `skills/sp-subagent-driven-development/`
- `skills/sp-systematic-debugging/`
- `skills/sp-test-driven-development/`
- `skills/sp-using-git-worktrees/`
- `skills/sp-using-superpowers/`
- `skills/sp-writing-plans/`
- `skills/sp-writing-skills/`
- `skills/verification-before-completion/` (vendored earlier at athanor v0.7.8;
  see that skill's provenance block for source-commit pinning)

### License text

```
MIT License

Copyright (c) 2025 Jesse Vincent

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## claude-octopus

- **Source**: https://github.com/nyldn/claude-octopus (SHA `3c260845f136cc6e3398a1d87ca5fb053a52b1d0`)
- **Copyright**: (c) 2026 nyldn
- **License**: MIT

### Vendored files

- `skills/scope-drift/SKILL.md`

### License text

```
MIT License

Copyright (c) 2026 nyldn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
