---
name: frappe-translations
description: Add, extract, export and debug translations in a Frappe/ERPNext custom app — CSV and PO/gettext files under the app, `_()` / `__()` in Python and JS, translatable DocType fields, and the cache/build steps that make a translation actually show up. Use whenever the user asks to translate an app or site, add a language (German, French, Amharic, …), export/import translation files, wire up `_()` or `__()`, fix a string that stays English after translating, or set up a translation workflow for a custom app such as suncycle.
---

# Frappe translations in a custom app

House standard: **translations live in files inside the app repo**, not only in
the site database. A translation that exists only in the Translation doctype is
invisible to git and dies with the site. Everything below serves that rule.

## Workflow

1. **Find the bench, the app and the Frappe version.** Translation storage
   changed between major versions, so read it from the source instead of
   assuming — see *Which format does this app use?* below.
2. **Make the strings extractable first.** Wrap user-facing text in `_()`
   (Python) / `__()` (JS) with **literal** arguments. Run
   `scripts/scan_untranslated.py <app_path>` — it reports unwrapped
   `frappe.throw` / `msgprint` messages and, more importantly, the
   *silently-broken* wrappings (f-strings, concatenation, JS template literals)
   that extraction skips.
3. **Generate the message catalog** from the source (`bench generate-pot-file`
   for PO apps, `bench get-untranslated` for CSV apps). Never hand-write the
   source column — a typo there means the string never matches at runtime.
4. **Fill in translations**, then validate with
   `scripts/csv_tools.py validate <file>`: it catches the failures that produce
   a silently-untranslated string — duplicate sources, mismatched `{0}` / `%s`
   placeholders, stray whitespace, a BOM, wrong column count.
5. **Load and verify.** `bench --site <site> clear-cache`, then `bench build`
   if any JS-side string changed (gotcha 4). Verify in the UI **and** from the
   API, not just by re-reading the file.
6. **Commit the translation file to the app repo** — that is what makes the
   translation deploy to the next site.

## Which format does this app use?

Do not guess from the Frappe version number; grep the installed frappe:

```bash
grep -rn "translations\|locale\|\.po\b" apps/frappe/frappe/translate.py | head -40
ls apps/<app>/<app>/translations apps/<app>/<app>/locale 2>/dev/null
```

- **`<app>/<app>/translations/<lang>.csv`** — the classic format. Two columns
  `source,translation`, optionally a third context column. Still read by v15 for
  backward compatibility, and the format the house standard was written against.
- **`<app>/<app>/locale/main.pot` + `locale/<lang>.po`** — gettext, introduced
  in v15. If the app has a `locale/` directory, use it; a CSV added alongside is
  at best a second source of truth and at worst dead weight.

Language codes are the ones in the Language doctype (`fr`, `de`, `es`,
`pt-BR`, `am`) — the file name must match exactly, `fr_FR.csv` will not load.

### CSV apps

```bash
bench --site <site> get-untranslated <lang> /tmp/untranslated.txt --app <app>
# translate, then:
bench --site <site> update-translations <lang> /tmp/untranslated.txt /tmp/translated.txt --app <app>
bench --site <site> clear-cache
```

`update-translations` writes `apps/<app>/<app>/translations/<lang>.csv`. You can
also write the CSV directly — that is normal — but keep it sorted and unique
(`scripts/csv_tools.py sort`), or merges turn into conflict soup.

### PO apps

```bash
bench generate-pot-file --app <app>          # source strings → locale/main.pot
bench update-po-files --app <app>            # merge new strings into every locale/<lang>.po
bench migrate-csv-to-po --app <app> --locale <lang>   # one-time, if a CSV exists
bench compile-po-to-mo --app <app>           # only if your version ships .mo
```

Edit the `.po` with any PO editor; `msgid` is the source, `msgstr` the
translation, `msgctxt` the context. Leave `#, fuzzy` entries unresolved at your
peril — some loaders drop them.

## Writing translatable code

```python
frappe.throw(_("Meter {0} has no active contract").format(meter.name))
_("Open", context="Task Status")        # disambiguates a short word
```

```js
frappe.msgprint(__("Meter {0} has no active contract", [meter.name]));
__("Open", null, "Task Status");        // (msg, replacements, context)
```

The argument must be a **literal**. Extraction is a static parse of the source,
so anything computed is invisible to it:

| broken | why | fix |
| --- | --- | --- |
| `_(f"Hello {name}")` | extractor stores `Hello {name}`; at runtime the string is already interpolated and matches nothing | `_("Hello {0}").format(name)` |
| `_("Total: " + label)` | not a literal | `_("Total: {0}").format(label)` |
| `_("Found %s rows" % n)` | translates the *already formatted* string | `_("Found {0} rows").format(n)` |
| ``__(`Hello ${name}`)`` | template literal, skipped by the JS extractor | `__("Hello {0}", [name])` |
| `_(status)` | variable — nothing to extract | translate at the definition site |

Always translate **after** formatting the sentence, never per fragment: languages
reorder clauses, and a translator handed `"Total: "` alone has no context.

## DocType and field labels

- DocType `label`, DocField `label`, `description` and Select `options` are
  translated automatically at render time — put the **English label exactly as
  it appears in the JSON** into the translation file. No code change needed.
- The DocField property for translating *stored data* is **`translatable`**
  (checkbox on Data/Select fields), not `translate`. Setting it means the value
  users typed gets passed through `_()` when displayed — appropriate for a
  fixed vocabulary (statuses, types), wrong for free text and names.
- Custom Fields created through the UI live in the site DB, but their labels
  still translate through the app's file — add the label to the CSV/PO.
- Report column labels, Workspace links, Notification subjects and Print Format
  static text all translate the same way: source string in, translation out.

## The gotchas that cost the most time

1. **Translations are cached per site and per language.** Nothing you edit in a
   file shows up until `bench --site <site> clear-cache`. If it still does not,
   `bench restart` (or restart `bench start`) — the in-process
   `frappe.local.lang_full_dict` survives a cache clear inside a running worker.
2. **The site database wins over your file.** A row in the **Translation**
   doctype overrides the app file for that source string, so a colleague's
   quick UI fix will make your correct file edit look broken. Check
   `frappe.get_all("Translation", filters={"source_text": "..."})` before
   debugging further, and migrate any keeper into the app file.
3. **The user's language is not the site's language.** `_()` resolves against
   `frappe.local.lang`, which comes from User → Language, falling back to
   System Settings. Testing as Administrator with no language set will show
   English no matter how right the file is. Force it in a bench console with
   `frappe.local.lang = "de"` before calling `_()`.
4. **JS translations are baked at build time.** Strings used in the desk/portal
   bundles are shipped through `bench build`; a CSV edit alone leaves the
   browser on the old text. Clear cache, `bench build`, then hard-reload.
5. **Whitespace and punctuation are part of the key.** `"Save "` ≠ `"Save"`,
   and a trailing period, a curly apostrophe or a non-breaking space makes the
   lookup miss. `csv_tools.py validate` flags these.
6. **The third CSV column is context, and it changes the key.** With a context
   value the entry is keyed `source:context`, so a 3-column row will never
   match a plain `_("source")` call. Only add context where the code passes one.
7. **`_()` in a print format only translates when the caller sets the print
   language** — `frappe.get_print` from a script does not, the desk PDF button
   does. Wrap scripted renders in `frappe.translate.print_language(lang)`.
8. **Server-side `_()` at import time is evaluated once**, before any user
   language exists — module-level constants, default arguments and
   `dict` literals at module scope all freeze to English. Translate inside the
   function.
9. **Never translate identifiers.** Doctype names, fieldnames, workflow state
   names and link values are keys; translating them breaks queries. Only labels
   and messages get `_()`.
10. **`bench update-translations` overwrites the file it targets.** Work on a
    copy or commit first — it does not merge with what you hand-edited.

## Verifying

Verify a specific string end-to-end rather than trusting the file:

```bash
bench --site <site> console
```
```python
frappe.local.lang = "de"
frappe.clear_cache()
from frappe import _
_("Meter {0} has no active contract")            # → the German string
frappe.translate.get_all_translations("de").get("Save")
```

For the JS side, load the site with `?lang=de` and check a string that lives in
a bundle, not just one rendered server-side — those two paths fail separately.

## Scripts

Stdlib only; run with any python3 (no bench env needed).

| script | purpose |
| --- | --- |
| `scripts/scan_untranslated.py` | Walk an app for user-facing strings that are unwrapped, plus `_()`/`__()` calls whose argument is not a literal (f-string, concat, `%`, template literal) and so never extract. |
| `scripts/csv_tools.py` | `validate` / `sort` / `merge` / `stats` a Frappe translation CSV, and `to-po` / `from-po` to move between the two formats. |
