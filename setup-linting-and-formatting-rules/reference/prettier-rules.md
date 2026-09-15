# Phamos Prettier Rules

This document describes the Prettier formatting options enforced in the phamos standard. Each option includes a description and a before/after code example written in a Frappe/ERPNext context.

Prettier options do not have code identifiers. Each option is referred to by its exact name as it appears in `.prettierrc`.

Prettier owns all formatting decisions. ESLint is configured with `eslint-config-prettier` (via `extends: ["prettier"]`) to disable every ESLint formatting rule that would conflict with Prettier.

### Options

#### `printWidth`

**Value: `99`**

The soft line length limit. Prettier wraps lines that exceed this value at natural breaking points such as function arguments, object properties, and array items. It will exceed the limit when no clean break is possible.

```js
// before — this line is 130 characters, exceeds printWidth: 99
frappe.call({ method: "phamos.phamos.doctype.charge_point.accounting_receipt.get_status", args: { charge_point: frm.doc.name } });

// after — Prettier breaks the object onto multiple lines
frappe.call({
	method: "phamos.phamos.doctype.charge_point.accounting_receipt.get_status", // 76 chars w/ tab indent — fits under 99
	args: { charge_point: frm.doc.name },
});
```

#### `useTabs`

**Value: `true`**

Uses tab characters for indentation instead of spaces. Frappe's JavaScript codebase uses tabs throughout, and this setting keeps custom app files consistent with upstream Frappe files.

```js
// before
frappe.ui.form.on("Payment Entry", {
  onload(frm) { // space indentation
    frm.set_query("party", () => {
      return { filters: { disabled: 0 } };
  });
 },
});

// after
frappe.ui.form.on("Payment Entry", {
	onload(frm) { // tab indentation, consistent with Frappe
		frm.set_query("party", () => {
			return { filters: { disabled: 0 } };
		});
	},
});

```

#### `tabWidth`

**Value: `4`**

Controls how wide a tab character is displayed in editors that respect `.prettierrc`. When `useTabs` is `true`, this is a display hint only and does not change the indentation character. One tab equals 4 space/column.

```js
// before
frappe.ui.form.on("Sales Invoice", {
  refresh(frm) { // 2-space indentation
    frm.add_custom_button(__("Preview"), () => {
      preview_invoice(frm);
    });
  },
});

// after
frappe.ui.form.on("Sales Invoice", {
	refresh(frm) { // tab character, displayed at 4-space width
		frm.add_custom_button(__("Preview"), () => {
			preview_invoice(frm);
		});
	},
});

```

#### `semi`

**Value: `true`**

Adds a semicolon at the end of every statement. Without semicolons, JavaScript's Automatic Semicolon Insertion (ASI) can silently change the meaning of code, particularly on lines beginning with `[`, `(`, or a template literal.

```js
// before
const filters = { docstatus: 1 } // no semicolons, ASI risk
const result = await frappe.db.get_list("Sales Invoice", { filters })
frappe.msgprint(result.length + " invoices found")

// after
const filters = { docstatus: 1 };
const result = await frappe.db.get_list("Sales Invoice", { filters });
frappe.msgprint(result.length + " invoices found");

```

#### `singleQuote`

**Value: `false`**

Uses double quotes for strings. This is consistent with JSON syntax, HTML attribute values, and Frappe's own JavaScript style. Single quotes are used only when the string itself contains a double quote.

```js
// before
frappe.call({
    method: 'erpnext.accounts.doctype.payment_entry.payment_entry.get_outstanding', // single quotes
    args: { 'voucher_type': 'Sales Invoice' },
});

// after
frappe.call({
    method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_outstanding", // double quotes
    args: { voucher_type: "Sales Invoice" },
});

```

#### `quoteProps`

**Value: `"as-needed"`**

Quotes object property keys only when syntactically required, such as when the key contains a hyphen, starts with a digit, or is a reserved word. Unnecessary quotes on valid identifiers are removed.

```js
// before
const config = {
    "name": "becharged",       // unnecessary quotes on a plain identifier
    "charge_point": frm.doc.name,
    "max-power": 22,           // hyphen requires quotes
    "status": "Available",
};

// after
const config = {
    name: "becharged",
    charge_point: frm.doc.name,
    "max-power": 22,           // hyphen requires quotes, kept
    status: "Available",
};

```

#### `trailingComma`

**Value: `"es5"`**

Adds a trailing comma after the last item in multi-line objects, arrays, and destructuring patterns, wherever valid in ES5. Trailing commas are not added to function parameters, where they require ES2017 support.

Trailing commas produce cleaner diffs: adding or removing an item changes only one line instead of also touching the line above it.

```js
// before
const fields = [
    "name",
    "status",
    "charge_point_id"  // no trailing comma, adding a new item changes this line too
];

// after
const fields = [
    "name",
    "status",
    "charge_point_id", // trailing comma, adding a new item only touches the new line
];

```

```js
Without trailing comma:

diff
const fields = [
    "name",
    "status",
-   "charge_point_id"
+   "charge_point_id",
+   "location"
];

Two lines flagged as changed.

With trailing comma:

diff
const fields = [
    "name",
    "status",
    "charge_point_id",
+   "location",
];

Only the actual addition line flagged as changed
```

#### `bracketSpacing`

**Value: `true`**

Prints spaces between the braces and content of inline object literals.

```js
// before
frappe.db.get_value("Charge Point", {name: frm.doc.charge_point}, "status"); // no spaces inside braces

// after
frappe.db.get_value("Charge Point", { name: frm.doc.charge_point }, "status"); // spaces inside braces

```

#### `arrowParens`

**Value: `"always"`**

Always wraps arrow function parameters in parentheses, even when there is only one. This keeps the syntax consistent across all arrow functions and makes adding a second parameter easier.

```js
// before
frappe.call({
    callback: r => { // single parameter, no parens
        const doc = r.message;
        update_form(doc);
    },
});

// after
frappe.call({
    callback: (r) => { // parens always present
        const doc = r.message;
        update_form(doc);
    },
});

```

#### `endOfLine`

**Value: `"lf"`**

Enforces Unix-style line endings (`\n`) on all files. Mixed line endings produce noisy diffs and cause issues when files move between operating systems. Frappe apps run on Linux servers, so LF is the correct standard.

### Setup and Usage Guide

This guide covers how to configure and run Prettier on a custom Frappe/ERPNext app.

#### Installation

Install Prettier as a development dependency inside the app, not globally. This ensures every developer on the team uses the same version.

**Global Installation**

```
npm install --global eslint prettier eslint-config-prettier eslint-plugin-vue vue-eslint-parser
```

**Bench environment installation**

Install Prettier and the ESLint integration as development dependencies inside the app. This ensures every developer on the team uses the same version.

```
cd apps/<your-app>
yarn add --dev eslint prettier eslint-config-prettier eslint-plugin-vue vue-eslint-parser
```

- `eslint` — the linter
- `prettier` — the formatter
- `eslint-config-prettier` — disables conflicting ESLint formatting rules
- `eslint-plugin-vue` — ESLint rules for `.vue` files
- `vue-eslint-parser` — parser that lets ESLint understand Vue single-file component syntax

**Verify the installation:**

```bash
npx prettier --version
```

#### Configuration

Create a file named `.prettierrc` at the root of the custom app:

```bash
touch .prettierrc
```

Paste the following content:

```json
{
    "printWidth": 99,
    "useTabs": true,
    "tabWidth": 4,
    "semi": true,
    "singleQuote": false,
    "quoteProps": "as-needed",
    "trailingComma": "es5",
    "bracketSpacing": true,
    "arrowParens": "always",
    "endOfLine": "lf"
}

```

Create a `.prettierignore` file at the same root level to exclude files that should not be formatted:

```
# Build outputs
public/dist/

# Minified files
**/*.min.js

# Generated TypeScript declarations
**/*.d.ts

# Dependencies
node_modules/

```

Add `"prettier"` as the last item in `extends` inside `.eslintrc.cjs`. It must be last so it overrides all other formatting-related ESLint rules:

```js
extends: ["eslint:recommended", "prettier"],

```

#### Production-Level Setup

Combines `.editorconfig` and pre-commit into one enforced pipeline. Nothing is optional or editor-dependent.

##### 1. `.editorconfig`

```json
# Root editor config file
root = true

# Common settings
[*]
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
charset = utf-8

# python, js indentation settings
[{*.py,*.js,*.vue,*.css,*.scss,*.html}]
indent_style = tab
indent_size = 4
max_line_length = 99

# JSON files - mostly doctype schema files
[{*.json}]
insert_final_newline = false
indent_style = space
indent_size = 2

```

#### 2. Pre-commit Enforcement

Prettier runs as a pre-commit hook (`.pre-commit-config.yaml`), scoped to JavaScript, Vue, and SCSS files while excluding generated or vendored paths:

```yaml
- repo: https://github.com/pre-commit/mirrors-prettier
  rev: v2.7.1
  hooks:
    - id: prettier
      types_or: [javascript, vue, scss]
      exclude: |
        (?x)^(
          phamos/public/dist/.*|
          .*node_modules.*|
          .*boilerplate.*|
          phamos/templates/includes/.*|
          phamos/public/js/lib/.*
        )$

```

No separate `.prettierignore` is needed. The `exclude` pattern above keeps all exclusions in one place.

#### Commands

All commands below must be run from inside the app directory, where `.prettierrc` is located.

##### `prettier --check` — inspect for formatting violations

Checks all matching files and reports which ones are not correctly formatted, without making any changes.

```bash
npx prettier --check "**/*.js"

```

To check a single file:

```bash
npx prettier --check frappe/public/js/frappe/form/form.js

```

The output lists every file that would be changed if `--write` were run. Files that are already correctly formatted are not listed.

##### `prettier --write` — format files in place

Reformats all matching files to conform to the `.prettierrc` configuration. This modifies files on disk. It only changes how code looks, never what it does.

```bash
npx prettier --write "**/*.js"

```

To format a single file:

```bash
npx prettier --write public/js/charge_point.js

```

##### Difference between `prettier --write` and `eslint --fix`

These two commands do different things and are not interchangeable.

`prettier --write` addresses code appearance: quote style, indentation, whitespace, trailing commas, line breaks. It never changes what the code does.

`eslint --fix` addresses lint violations: unused variables, outdated syntax, import ordering, bug patterns. It changes what the code says at a structural level.

##### Recommended order of operations

Run the commands in this order when cleaning up a file or the whole app:

```bash
# 1. Fix lint violations first
npx eslint --fix "**/*.js"

# 2. Format the result
npx prettier --write "**/*.js"

```

Prettier runs last because the ESLint `--fix` pass can introduce minor formatting inconsistencies, which Prettier then cleans up.

#### Editor Integration

Prettier works best when it formats files automatically on save. The following settings apply to VS Code and Cursor.

**Install the Prettier extension:**

```
ext install esbenp.prettier-vscode

```

**Add to `.vscode/settings.json` inside the app:**

```json
{
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true,
    "[javascript]": {
        "editor.defaultFormatter": "esbenp.prettier-vscode"
    }
}

```

Committing `.vscode/settings.json` to the repository ensures all team members share the same editor behaviour without individual configuration.

### Summary

<table id="bkmrk-option-value-reason-"><thead><tr><th>Option</th><th>Value</th><th>Reason</th></tr></thead><tbody><tr><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">printWidth</span>`</td><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">100</span>`</td><td>Avoids unnecessary wrapping on modern screens</td></tr><tr><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">tabWidth</span>`</td><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">4</span>`</td><td>Display width for tab characters</td></tr><tr><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">useTabs</span>`</td><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">true</span>`</td><td>Consistent with Frappe's JavaScript convention</td></tr><tr><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">semi</span>`</td><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">true</span>`</td><td>Prevents ASI-related bugs</td></tr><tr><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">singleQuote</span>`</td><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">false</span>`</td><td>Consistent with JSON, HTML attributes, and Frappe style</td></tr><tr><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">quoteProps</span>`</td><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">"as-needed"</span>`</td><td>Quotes only where syntactically required</td></tr><tr><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">trailingComma</span>`</td><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">"es5"</span>`</td><td>Cleaner diffs; valid in ES5</td></tr><tr><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">bracketSpacing</span>`</td><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">true</span>`</td><td>Readable inline object literals</td></tr><tr><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">arrowParens</span>`</td><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">"always"</span>`</td><td>Consistent arrow function syntax</td></tr><tr><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">endOfLine</span>`</td><td>`<span style="font-family: -apple-system, system-ui, Segoe UI, Oxygen, Ubuntu, Roboto, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif;">"lf"</span>`</td><td>Consistent with Linux server targets</td></tr></tbody></table>