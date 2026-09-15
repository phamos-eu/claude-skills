# skills

Claude Code skills for Frappe/ERPNext work.

## Skills

| Skill | What it does |
| --- | --- |
| [`frappe-print-format`](frappe-print-format/) | Build a Print Format that pixel-matches a reference PDF — extract exact mm coordinates from the source with PyMuPDF, verify every change through the real Chrome PDF pipeline. Also covers wrong margins, clipping, blank pages and bad pagination. |
| [`frappe-translations`](frappe-translations/) | Add, extract, export and debug translations in a custom app — CSV and PO/gettext files, `_()` / `__()` in Python and JS, translatable DocType fields, and the cache/build steps that make a translation actually show up. |
| [`setup-linting-and-formatting-rules`](setup-linting-and-formatting-rules/) | Autosetup (install + configure) the phamos linting/formatting/type-checking standard on a custom app — Ruff, Prettier, ESLint, Pyright, plus shared `.editorconfig` / `.pre-commit-config.yaml`. Setup only, never runs the tools. |

## Install

Clone into your personal skills directory:

```bash
git clone https://github.com/phamos-eu/claude-skills.git /tmp/skills
cp -R /tmp/skills/frappe-print-format /tmp/skills/frappe-translations /tmp/skills/setup-linting-and-formatting-rules ~/.claude/skills/
```

Or, for a single project, copy them into `<project>/.claude/skills/` instead.

Claude Code picks skills up automatically on the next session; each is invocable
by name (`/frappe-print-format`) or triggered from its `description`.

## Layout

Each skill is a directory containing a `SKILL.md` with YAML frontmatter
(`name`, `description`) plus any `scripts/` and `reference/` it needs.

```
frappe-print-format/
  SKILL.md
  reference/frappe-pdf-pipeline.md
  scripts/{apply_pf,render_pf,measure_pdf,compare,paginate_test}.py
frappe-translations/
  SKILL.md
  scripts/{csv_tools,scan_untranslated}.py
setup-linting-and-formatting-rules/
  SKILL.md
  assets/{ruff-pyproject-block.toml,eslintrc.json,pyrightconfig.json,editorconfig,pre-commit-config.yaml}
  reference/{ruff-rules,prettier-rules,eslint-rules,pyright-guide}.md
```
