---
name: setup-linting-and-formatting-rules
description: Autosetup (install + configure) Phamos's linting, formatting, and type-checking standard across Frappe/ERPNext custom apps. Covers a shared common setup (.editorconfig, .pre-commit-config.yaml) plus Ruff (Python), Prettier (JS/Vue), ESLint (JS), and Pyright (static type checking). This skill only installs tools and writes config — it never runs the linter/formatter/type-checker itself. Use whenever the user asks to set up, install, or configure Phamos's lint/format/type-check rules on an app, or asks "what does rule X mean" for one of these tools.
---

# Phamos lint & format setup

Applies the Phamos org-wide linting/formatting standard to a Frappe/ERPNext custom app. This
skill is built incrementally, one tool at a time. Each tool gets its own section below, its own
canonical config asset(s) in `assets/`, and its own rule-explainer reference in `reference/`.

Structural reference: the `normivo` custom app was used as the model for file layout (all config files live at the **app root**, alongside
`pyproject.toml`; `.editorconfig` and `.pre-commit-config.yaml` are shared files every tool
contributes a block to, not one file per tool).

Tools covered: **Common setup**, **Ruff**, **Prettier**, **ESLint**, **Pyright**. All four tool
rules docs have now been provided — this skill's tool coverage is complete unless the user
introduces a new tool.

## General principles (apply to every tool in this skill)

- **Scope is setup only.** This skill installs tools and writes config into the app. It never
  invokes the linter/formatter/fixer (no `ruff check`, `ruff format`, `eslint --fix`,
  `prettier --write`, type-checker runs, pre-commit runs, etc.) as part of this skill's own
  workflow. Running those commands is the user's call, made separately, whenever they choose to.
- The user has hand-defined every rule and every ignore. **Never substitute your own judgment
  for a rule choice** (e.g. don't decide E501 should be enabled because "it seems useful") —
  the documented config is the standard, full stop.
- When a tool's prose/config block and its summary table disagree, **the executable config block
  wins** — this has now been confirmed twice (Ruff: table said `E242`/omitted `B904`, config
  block had `E741`/`B904`, config won; Prettier: table said `printWidth: 100`, config block said
  `99`, config won). Don't silently rebuild canonical config from a summary table. Still flag the
  discrepancy to the user when you find one, but default to the config block.
- Never run an unsafe/aggressive autofix flag without first showing the user a preview/diff and
  getting explicit confirmation.
- Never touch config sections/files unrelated to the tool being set up (e.g. don't touch
  `[tool.poetry]` while setting up `[tool.ruff]`; don't touch the `ruff` block in
  `.pre-commit-config.yaml` while adding the `prettier` block).
- If an app's config already has a conflicting section/block for the tool being set up, show the
  diff between what's there and the canonical block and ask before overwriting. Do not silently
  clobber it.
- Install scope: always scoped to the app/bench, never global (`pip install`, `npm install -g`,
  `brew install`, etc. are all out — see each tool's install step for the specifics). This
  keeps every teammate's setup reproducible regardless of OS.

---

## Common setup (shared across all tools)

Two files are shared infrastructure — every tool section below adds its own block to these
rather than owning a separate file:

- **`.editorconfig`** — canonical content: `assets/editorconfig`. This one is tool-agnostic and
  written once, in full, the first time any tool in this skill is set up. No per-tool blocks —
  just ensure the file exists at the app root and matches the asset. If it already exists with
  different content, diff and ask before overwriting.
- **`.pre-commit-config.yaml`** — canonical full template (with every tool's hook block already
  included, for reference): `assets/pre-commit-config.yaml`. Contains a `{{APP_NAME}}`
  placeholder in a few `exclude:` regexes — substitute the app's actual top-level Python package
  directory name (e.g. `phamos`, `normivo`) before using it.
  - If `.pre-commit-config.yaml` doesn't exist yet: create it with just the top-level keys
    (`exclude`, `default_stages`, `fail_fast`, `repos:`, `ci:`) plus the generic
    `pre-commit/pre-commit-hooks` block, plus the hook block(s) for whichever tool(s) are
    currently being set up.
  - If it already exists: check whether a `repo:` block for this tool already exists (match on
    the repo URL, e.g. `astral-sh/ruff-pre-commit` for Ruff, `mirrors-prettier` for Prettier). If
    missing, append it under `repos:`, substituting `{{APP_NAME}}`. If present, diff against the
    canonical block and ask before overwriting. Never touch another tool's block.

Both files are written once per app; setting up a second tool later only adds that tool's block,
it never rewrites the other tool's block or the shared top-level keys.

---

## Ruff (Python)

Canonical config: `assets/ruff-pyproject-block.toml` — reproduce this block byte-for-byte.
Full rule-by-rule explanations and before/after examples: `reference/ruff-rules.md`.

**Known discrepancy — resolved:** `reference/ruff-rules.md` contains both a `pyproject.toml`
config block and a prose summary table near the bottom, and they disagree on the ignore list
(e.g. table says `E242` is ignored, the config block has `E741` instead; table omits `B904`
which the config block actually ignores). **`assets/ruff-pyproject-block.toml` (the executable
config block) is authoritative**, not the summary table. Treat the summary table in
`reference/ruff-rules.md` as a rough/inaccurate recap only.

### Setup workflow

1. **Find the target app.** If cwd already looks like a Frappe custom app root (has `hooks.py`
   and/or an app-name-matching inner directory), use it. Otherwise ask the user which app under
   `frappe-bench/apps/` to target.

2. **Ensure Ruff is installed — always bench-scoped, never global.** Frappe/bench keeps one
   Python virtualenv per bench at `frappe-bench/env/`, shared by every app in that bench, and
   all dev tooling belongs there. This skill is shared across the team (Mac, Linux, Windows), so
   detect the OS and use the matching venv layout:
   - **Mac / Linux / WSL2** (the normal way Frappe bench is run on Windows too — bench is not
     officially supported on native Windows): from the bench root,
     `./env/bin/pip install ruff`.
   - **Native Windows** (bench running directly on Windows, not WSL — rare, but the venv layout
     differs): from the bench root, `.\env\Scripts\pip.exe install ruff`.
   - Check `ruff --version` first; only install if missing.
   - Do **not** fall back to a global `pip install ruff` or `brew install ruff`. If the bench env
     can't be found, stop and ask the user for the bench root instead of installing globally.

3. **Write the config into the app's `pyproject.toml`** (app root, alongside `hooks.py`'s parent
   dir — see the reference repo layout above).
   - If the file doesn't exist, create it containing just the block from
     `assets/ruff-pyproject-block.toml`.
   - If it exists but has no `[tool.ruff]` / `[tool.ruff.format]` / `[tool.ruff.lint]` /
     `[tool.ruff.lint.isort]` sections, append the block at the end, preserving everything else
     (`[project]`, `[build-system]`, etc.) untouched.
   - If any of those sections already exist, diff them against the canonical block, show the
     user the diff, and ask before overwriting.

4. **Add Ruff's block to `.pre-commit-config.yaml`** per the Common setup section above (the
   `astral-sh/ruff-pre-commit` block: import-sort, lint, format hooks).

5. **Write `.editorconfig`** per the Common setup section above, if not already present.

6. **Explaining violations.** If the user asks what a rule code means, look it up in
   `reference/ruff-rules.md` and explain it in plain language with the before/after example.

---

## Prettier (JS/Vue)

**No `.prettierrc` in this setup — deliberate user decision.** The rules doc's canonical
`.prettierrc` block (`printWidth: 99`, `useTabs: true`, etc. — see
`reference/prettier-rules.md` for the full option-by-option explanations) is kept as reference
material only. The user decided `.editorconfig` (tab width/style, line endings, charset) plus
`.pre-commit-config.yaml`'s `mirrors-prettier` hook are enough — **do not write a `.prettierrc`
file**, and don't reintroduce one on a future setup run even if it would "complete" the standard
Prettier options (`quoteProps`, `trailingComma`, `bracketSpacing`, `arrowParens`, `semi`,
`singleQuote`) that `.editorconfig` alone can't express. If the user later asks why Prettier
formatting looks inconsistent on those specific options, that's the expected tradeoff of this
choice — explain it rather than silently adding the file back.

There is no `assets/prettierrc.json` / `assets/prettierignore` file — they were removed.

### Setup workflow

1. **Find the target app** — same as Ruff step 1.

2. **Ensure Prettier is installed — always scoped to the app, never global.** Per the doc, install
   as a dev dependency inside the app (not `npm install --global`):
   ```bash
   cd apps/<app>
   yarn add --dev eslint prettier eslint-config-prettier eslint-plugin-vue vue-eslint-parser
   ```
   This is the doc's exact bundled install command — it installs Prettier together with the
   ESLint-integration packages (`eslint-config-prettier`, `eslint-plugin-vue`,
   `vue-eslint-parser`) even though ESLint's own rule config hasn't been added to this skill yet;
   don't split it into a smaller install just because ESLint's section isn't built yet.
   Node/yarn tooling is not OS-sensitive the way Python venvs are, so no Mac/Linux/Windows branch
   is needed here — `yarn add --dev` behaves the same everywhere yarn is installed.
   Verify with `npx prettier --version`.

3. **Add Prettier's block to `.pre-commit-config.yaml`** per the Common setup section above (the
   `pre-commit/mirrors-prettier` block, `{{APP_NAME}}` substituted).

4. **Write `.editorconfig`** per the Common setup section above, if not already present (likely
   already done if Ruff was set up first on this app).

5. **`.eslintrc` `extends` ordering.** The doc requires `"prettier"` to be the *last* entry in
   `extends` inside `.eslintrc`/`.eslintrc.cjs`, so it overrides other formatting-related ESLint
   rules. If `.eslintrc` already exists in the app, check this and fix the ordering if it's
   wrong or missing, but do **not** build out the rest of `.eslintrc`'s rules here — that's the
   ESLint section's job.

6. **Explaining options.** If the user asks what a Prettier option does (even though it isn't
   being written to a config file), look it up in `reference/prettier-rules.md` and explain it
   in plain language with the before/after example. Note: Prettier options aren't referred to by
   rule codes (unlike Ruff) — always use the exact option name as it appears in the doc.

---

## ESLint (JS)

Canonical config: `assets/eslintrc.json` — target filename `.eslintrc` (or `.eslintrc.json`) at
the app root. Full rule-by-rule explanations: `reference/eslint-rules.md`. No discrepancy found
between this doc's config block and its summary table — they agree, so no authoritative-source
call was needed here (unlike Ruff and Prettier).

This base config matches Frappe's own default (`extends: "eslint:recommended"` plus the same
disabled formatting rules and Frappe globals) so phamos apps stay consistent with the rest of the
bench — this is confirmed by the reference repo's `.eslintrc` matching the doc almost exactly.

### Setup workflow

1. **Find the target app** — same as Ruff step 1.

2. **Ensure ESLint is installed — always scoped to the app, never global.**
   - If Prettier has already been set up on this app, ESLint is likely already installed as part
     of Prettier's bundled install command (`yarn add --dev eslint prettier
     eslint-config-prettier eslint-plugin-vue vue-eslint-parser`) — check `npx eslint --version`
     first before installing anything.
   - If not yet installed, run from the app directory:
     ```bash
     yarn add --dev eslint
     ```
     (or `npm install --save-dev eslint` if the app uses npm instead of yarn — check which lock
     file, `yarn.lock` or `package-lock.json`, is already present; don't introduce the other one).
   - No OS branching needed here, same reasoning as Prettier.

3. **Write `.eslintrc`** at the app root from `assets/eslintrc.json`, byte-for-byte, *unless* the
   file already exists because Prettier's setup already touched it:
   - If `.eslintrc` doesn't exist yet: create it with the full canonical content as-is (`extends`
     is the plain string `"eslint:recommended"` at this point — no Prettier integration yet).
   - If `.eslintrc` already exists (e.g. Prettier's step 6 already adjusted `extends`), diff the
     `env` / `parserOptions` / `rules` / `root` / `globals` keys against the canonical asset and
     merge in anything missing, but **leave `extends` alone** if it's already in the
     `["eslint:recommended", "prettier"]` array form — that's Prettier's concern, not this
     section's. Only set `extends` to the plain-string canonical form if the file is being
     created fresh here.
   - Either way, if content conflicts (not just "missing"), diff and ask before overwriting.

4. **Add ESLint's block to `.pre-commit-config.yaml`** per the Common setup section above (the
   `pre-commit/mirrors-eslint` block, `{{APP_NAME}}` substituted). This block is already present
   in `assets/pre-commit-config.yaml` (previously marked "not yet built" — it's built now).

5. **Write `.editorconfig`** per the Common setup section above, if not already present.

6. **Editor integration is optional, not part of default setup.** The doc's `.vscode/settings.json`
   snippet (`editor.codeActionsOnSave` / `eslint.validate`) is an editor convenience, not a lint
   rule — the reference repo (`normivo-develop`) doesn't actually have it wired up yet even
   though Ruff's own `.vscode/settings.json` entry is present there. Only add it if the user
   explicitly asks for editor-on-save integration; don't bundle it into a default setup run.

7. **Explaining violations.** If the user asks what a rule means, look it up in
   `reference/eslint-rules.md` and explain it in plain language with the before/after example.

---

## Pyright (static type checking)

Unlike the other three tools, Pyright runs in **advisory mode** — it surfaces type errors in the
editor and can be run manually, but it does not block commits or fail CI. There's no
`.pre-commit-config.yaml` hook for it in this skill for that reason (the reference repo doesn't
have one either).

**No single canonical config in the source doc** — `reference/pyright-guide.md`'s own
`pyrightconfig.json` example (`include`, `exclude`, `pythonVersion: "3.11"`,
`typeCheckingMode: "basic"`, `reportMissingImports: false`, `reportMissingModuleSource: false`)
is missing the settings actually required to make Pyright work inside a real bench —
`venvPath`/`venv` (so Pyright resolves the bench's virtualenv instead of erroring on every
`import frappe`) and `extraPaths` (so it can see sibling apps like `frappe`/`erpnext`). Those are
present in `normivo-develop`'s real `pyrightconfig.json` but its file is missing the doc's
advisory settings. **`assets/pyrightconfig.json` is the merge of both**, confirmed with the user:
- `pythonVersion` is set to `"3.10"`, not the doc's `"3.11"`, to stay consistent with Ruff's
  `target-version = "py310"` elsewhere in this same skill.
- `reportAttributeAccessIssue: false` (from `normivo-develop`, not in the doc) is kept — without
  it, Pyright over-reports on Frappe's dynamic attribute patterns.
- `include` uses a `{{APP_NAME}}` placeholder, same convention as `.pre-commit-config.yaml` —
  substitute the app's actual top-level Python package directory name.

Topics 1–10 in `reference/pyright-guide.md` (the `export_python_type_annotations` hook, `cast()`
usage, `TYPE_CHECKING` guards, avoiding AI-generated `getattr()` workarounds, etc.) are **coding
guidance, not enforceable config** — nothing to write into a config file for these beyond the
`hooks.py` flag in step 3 below. Use them only to explain *why* when the user asks about a
specific pattern, the same as the rule-explainer references for the other tools.

### Setup workflow

1. **Find the target app** — same as Ruff step 1.

2. **Ensure Pyright is installed — always scoped, never global.** The doc offers a Python-based
   install (`pip install pyright`) and a Node-based one (`npm install -g pyright`); per this
   skill's install-scope rule, neither should run as shown (bare `pip install` is global, and
   `npm install -g` is explicitly global). Use the scoped equivalent of whichever variant fits
   the app's existing tooling:
   - Python-based, bench-scoped (preferred, consistent with Ruff): from the bench root,
     `./env/bin/pip install pyright` (Mac/Linux/WSL2) or `.\env\Scripts\pip.exe install pyright`
     (native Windows).
   - Node-based, app-scoped (only if the team prefers the npm version for faster updates): from
     the app directory, `yarn add --dev pyright`.
   Check `pyright --version` (or `npx pyright --version` for the Node install) before installing.

3. **Set the `export_python_type_annotations` hook.** Open the app's `hooks.py` and ensure it
   contains:
   ```python
   export_python_type_annotations = True
   ```
   Add it if missing; don't touch other hooks. This is required — without it, Pyright reports
   `Unknown` for every Doctype field access, making the rest of the setup close to useless.

4. **Write `pyrightconfig.json`** at the app root from `assets/pyrightconfig.json`, substituting
   `{{APP_NAME}}` with the app's actual package directory name. If the file already exists with
   different content, diff and ask before overwriting — don't silently merge over an existing
   `extraPaths` list a developer may have customized for their own bench layout.

5. **No `.pre-commit-config.yaml` block and no `.editorconfig` change** for this tool — Pyright
   is advisory-only, not part of the enforced pre-commit pipeline (see note above).

6. **Explaining guidance.** If the user asks about a Pyright pattern (`cast()`, `TYPE_CHECKING`,
   why a field shows `Unknown`, etc.), look it up in `reference/pyright-guide.md` by topic
   number and explain it with the before/after example from that doc.

---

### Out of scope (do not do this as part of setup, for any tool above)

This skill stops once config is written and tools are installed. It does **not**:
- run `ruff check`, `ruff check --fix`, `ruff format`, `prettier --check`, `prettier --write`,
  `eslint --fix`, `pyright`, or `pre-commit run`,
- report violation/formatting-diff/type-error counts or statistics,
- apply fixes to the user's code.

If the user wants to actually lint/format their code, that's a separate, explicit request — not
something to chain onto a setup run. When setup is done, tell the user the config is in place and
that running the tools (or `pre-commit run --all-files`) is theirs to do whenever they're ready.
For Ruff specifically, mention `F401` is an unsafe fix (Frappe hook/DocType registration) — don't
run `--unsafe-fixes` for them.

### Verification

After setup, confirm tools are installed and config is present, without running any lint/format
or type check:
```bash
ruff --version
npx prettier --version
npx eslint --version
pyright --version
```
and visually confirm the written config files match their canonical assets
(`assets/ruff-pyproject-block.toml`, `assets/eslintrc.json`, `assets/pyrightconfig.json`,
`assets/editorconfig`, `assets/pre-commit-config.yaml` with `{{APP_NAME}}` correctly
substituted — deliberately no `.prettierrc`), and confirm `export_python_type_annotations = True`
is present in `hooks.py`.
