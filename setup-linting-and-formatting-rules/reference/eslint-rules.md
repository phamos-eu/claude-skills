# Phamos ESLint Rules

This document describes the base ESLint configuration adopted for phamos JavaScript development. It explains the environments, parser settings, recommended rules, Frappe-specific global variables, and the rules that are explicitly configured or disabled. This base configuration matches Frappe's own default so phamos apps stay consistent with the rest of the bench.

The configuration is based on ESLint's `eslint:recommended` ruleset with a small number of Frappe-specific adjustments that phamos inherits as-is.

Rules inherited from `eslint:recommended` are enabled automatically. Rules explicitly disabled in the configuration are marked as ignored.

#### Configuration Overview

The phamos base configuration consists of four parts.

Environment defines the JavaScript environments phamos code runs in. Parser options define how ESLint parses phamos JavaScript files. Recommended rules enables ESLint's standard rule set. Frappe globals prevents ESLint from reporting Frappe-provided identifiers used throughout phamos code as undefined.

#### `env`

```json
"env": {
    "browser": true,
    "node": true,
    "es2022": true
}

```

##### `browser`

Enables browser globals such as `window`, `document`, `localStorage`, and `setTimeout`. Required because phamos's client-side JavaScript runs in the browser as part of Frappe form scripts, list views, and custom pages.

##### `node`

Enables Node.js globals and APIs. Needed because phamos also contains JavaScript that runs in Node, such as build scripts and any future tooling.

##### `es2022`

Enables ES2022 language features and globals, so modern syntax used in phamos files is not reported as unsupported.

#### `parserOptions`

```json
"parserOptions": {
    "sourceType": "module"
}

```

`sourceType: "module"` tells ESLint that phamos files can use ES module syntax.

```js
// valid ES module syntax
import frappe from "./frappe";
import { get_status } from "./utils";

export function get_label(status) {
    return status;
}

```

#### `extends`

```json
"extends": "eslint:recommended"

```

Enables ESLint's built-in recommended rules, covering undefined variables, unused variables, unreachable code, duplicate case labels, invalid regular expressions, incorrect constructor use, constant conditions, and general syntax problems. These rules apply to all phamos JavaScript automatically, except where this base configuration overrides or disables them.

#### Enabled and Adjusted Rules

Rules where the phamos base configuration changes the default ESLint behavior, inherited directly from Frappe's own config.

##### `space-unary-ops`

```json
"space-unary-ops": ["error", { "words": true }]

```

Requires a space around unary operators that use words, such as `typeof`, `void`, and `delete`.

```js
// before
typeof(doc.name);
delete(doc.value);

// after
typeof doc.name;
delete doc.value;

```

##### `no-console`

```json
"no-console": ["warn"]

```

Reports the use of `console` methods as a warning rather than an error, since console usage is useful during phamos development and low risk to leave temporarily.

```js
// before
console.log("Invoice submitted");

// after
frappe.msgprint("Invoice submitted");

```

**Undefined variable — `no-undef`**

```js
// before
frappe.msgprint(order_total); // order_total was never declared


```

**Unreachable code — `no-unreachable`**

```js
// before
function get_status(doc) {
    return doc.status;
    console.log("this line never runs");
}

// error  Unreachable code  no-unreachable

```

**Duplicate case label — `no-duplicate-case`**

```js
// before
switch (status) {
    case "Active":
        activate();
        break;
    case "Active": // duplicate
        reactivate();
        break;
}

// error  Duplicate case label  no-duplicate-case

```

**Duplicate object keys — `no-dupe-keys`**

```js
// before
const doc = {
    name: "CUST-0001",
    name: "CUST-0002",
};

// error  Duplicate key 'name'  no-dupe-keys

```

**Constant condition — `no-constant-condition`**

```js
// before
if (true) { // always true, condition is pointless
    frappe.msgprint("This always runs");
}

// error  Unexpected constant condition  no-constant-condition

```

**Comparing to NaN — `use-isnan`**

```js
// before
if (value == NaN) {
    handle_invalid(value);
}

// error  Use the isNaN function to compare with NaN  use-isnan

```

#### Disabled Rules

Rules turned off because enforcing them would create violations against existing phamos and Frappe coding patterns.

##### `indent`

```json
"indent": "off"

```

Indentation is not checked by ESLint in phamos files. Formatting is handled separately by Prettier.

```js
function calculate_total() {
    const total = get_total();
    return total;
}

```

##### `brace-style`

```json
"brace-style": "off"

```

No particular brace placement style is enforced by ESLint in phamos code.

```js
if (status === "Active") {
    activate();
}

```

##### `no-mixed-spaces-and-tabs`

```json
"no-mixed-spaces-and-tabs": "off"

```

Code mixing spaces and tabs for indentation is not reported by ESLint, since indentation across phamos files is handled by Prettier.

##### `no-useless-escape`

```json
"no-useless-escape": "off"

```

Unnecessary escape characters are not reported. Several phamos regex patterns use defensive escaping that this rule would otherwise flag without real benefit.

```js
const pattern = /\-/;

```

##### `linebreak-style`

```json
"linebreak-style": "off"

```

No line-ending style is enforced. phamos files using either Unix (`LF`) or Windows (`CRLF`) line endings are both allowed at the ESLint level; Prettier's `endOfLine` setting normalises this instead.

##### `quotes`

```json
"quotes": ["off"]

```

Neither single nor double quotes are enforced by ESLint. Prettier's `singleQuote` setting governs quote style across phamos.

```js
const message = "Invoice submitted";
const message = 'Invoice submitted';

```

Both are allowed at the ESLint level.

##### `semi`

```json
"semi": "off"

```

Semicolons are neither required nor forbidden by ESLint. Prettier's `semi` setting governs this across phamos.

```js
const status = "Active";
const status = "Active"

```

Both styles are allowed at the ESLint level.

##### `camelcase`

```json
"camelcase": "off"

```

Identifiers are not required to use camelCase. This matters for phamos because DocType field names and Frappe conventions frequently use snake\_case.

```js
const customer_name = frm.doc.customer_name;
const posting_date = frm.doc.posting_date;

```

##### `no-unused-vars`

```json
"no-unused-vars": "off"

```

Unused variables are not reported in phamos code.

```js
const customer = frm.doc.customer;
const status = frm.doc.status;

```

Even if `customer` is never used later, ESLint does not flag it. This matters because Frappe form event handlers always receive parameters like `frm` as part of their required signature, whether or not the handler body uses them.

```
frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		// frm is required by the API
	},
	item_code(frm, cdt, cdn) {
		// cdt / cdn are part of the child-table hook even if unused
	},
});
```

##### `no-extra-boolean-cast`

```json
"no-extra-boolean-cast": ["off"]

```

Unnecessary boolean conversions are not reported. phamos code uses `!!` in places to coerce values before passing them into Frappe APIs.

```js
if (!!value) {
    process_value();
}

```

##### `no-control-regex`

```json
"no-control-regex": ["off"]

```

Control characters used inside regular expressions are not reported, allowing phamos input-sanitisation patterns that intentionally contain them.

#### Frappe Global Variables

phamos JavaScript uses many global variables and functions provided by the Frappe framework. Without declaring these, ESLint reports errors such as:

```text
'frappe' is not defined
'cur_frm' is not defined
'cint' is not defined

```

The phamos base configuration declares these as globals so ESLint recognizes them across every custom app.

```json
"globals": {
    "frappe": true,
    "cur_frm": true,
    "cint": true,
    "cstr": true,
    "flt": true
}

```

##### `frappe`

The main Frappe JavaScript API, used throughout phamos for calls, dialogs, and messaging.

```js
frappe.msgprint("Invoice submitted");

frappe.call({
    method: "frappe.client.get",
    args: {
        doctype: "Customer",
        name: "CUST-0001"
    }
});

```

##### `cur_frm`

Represents the current Frappe form. Used extensively in phamos DocType client scripts.

```js
cur_frm.set_value("status", "Active");
cur_frm.refresh_field("status");

```

##### `cur_dialog`

Represents the currently active Frappe dialog.

```js
cur_dialog.hide();

```

##### `cur_page`

Represents the current Frappe page.

```js
cur_page.page.set_title("Customers");

```

##### `__`

Frappe's translation function, used across phamos user-facing strings.

```js
const message = __("Invoice submitted successfully");

```

##### `cint`, `cstr`, and `flt`

Frappe utility functions for converting values, used throughout phamos for numeric and string coercion.

```js
const quantity = cint(value);
const customer_name = cstr(value);
const amount = flt(value);

```

#### Other Frappe and Project Globals

The phamos base configuration also declares a large number of globals used throughout the Frappe framework and its frontend ecosystem, so that phamos code referencing them is never flagged as using undefined variables.

Frappe utilities: `SetVueGlobals`, `repl`, `Class`, `locals`, `cint`, `cstr`, `cur_frm`, `cur_dialog`, `cur_page`, `cur_list`, `cur_tree`, `msg_dialog`, `is_null`, `in_list`, `has_common`, `has_words`, `validate_email`, `validate_name`, `validate_phone`, `validate_url`, `get_number_format`, `format_number`, `format_currency`, `comment_when`, `open_url_post`, `toTitle`, `lstrip`, `rstrip`, `strip`, `strip_html`, `replace_all`, `flt`, `precision`, `copy_dict`

Document and workflow constants: `CREATE`, `AMEND`, `CANCEL`

Form and field utilities: `refresh_many`, `refresh_field`, `toggle_field`, `get_field_obj`, `get_query_params`, `unhide_field`, `hide_field`, `set_field_options`

Browser and utility libraries: `getCookie`, `getCookies`, `get_url_arg`, `md5`, `$`, `jQuery`, `moment`, `hljs`, `Awesomplete`, `Sortable`, `Showdown`, `Taggle`, `Gantt`, `Slick`, `Webcam`, `PhotoSwipe`, `PhotoSwipeUI_Default`, `io`, `JsBarcode`, `L`, `Chart`, `DataTable`

Testing globals: `Cypress`, `cy`, `it`, `describe`, `expect`, `context`, `before`, `beforeEach`, `after`

Other Frappe globals: `posthog`, `Layout`, `web_form_settings`, `extend_cscript`, `qz`, `localforage`

Declaring these prevents ESLint from treating framework-provided identifiers used in phamos code as undefined variables.

#### Configuration

The complete phamos base configuration can be placed in the app's ESLint configuration file, `.eslintrc` or `.eslintrc.json`.

```json
{
    "env": {
        "browser": true,
        "node": true,
        "es2022": true
    },

    "parserOptions": {
        "sourceType": "module"
    },

    "extends": "eslint:recommended",

    "rules": {
        "indent": "off",
        "brace-style": "off",
        "no-mixed-spaces-and-tabs": "off",
        "no-useless-escape": "off",
        "space-unary-ops": ["error", { "words": true }],
        "linebreak-style": "off",
        "quotes": ["off"],
        "semi": "off",
        "camelcase": "off",
        "no-unused-vars": "off",
        "no-console": ["warn"],
        "no-extra-boolean-cast": ["off"],
        "no-control-regex": ["off"]
    },

    "root": true,

    "globals": {
        "frappe": true,
        "Vue": true,
        "SetVueGlobals": true,
        "__": true,
        "repl": true,
        "Class": true,
        "locals": true,
        "cint": true,
        "cstr": true,
        "cur_frm": true,
        "cur_dialog": true,
        "cur_page": true,
        "cur_list": true,
        "cur_tree": true,
        "msg_dialog": true,
        "is_null": true,
        "in_list": true,
        "has_common": true,
        "posthog": true,
        "has_words": true,
        "validate_email": true,
        "open_web_template_values_editor": true,
        "validate_name": true,
        "validate_phone": true,
        "validate_url": true,
        "get_number_format": true,
        "format_number": true,
        "format_currency": true,
        "comment_when": true,
        "open_url_post": true,
        "toTitle": true,
        "lstrip": true,
        "rstrip": true,
        "strip": true,
        "strip_html": true,
        "replace_all": true,
        "flt": true,
        "precision": true,
        "CREATE": true,
        "AMEND": true,
        "CANCEL": true,
        "copy_dict": true,
        "get_number_format_info": true,
        "strip_number_groups": true,
        "print_table": true,
        "Layout": true,
        "web_form_settings": true,
        "$c": true,
        "$a": true,
        "$i": true,
        "$bg": true,
        "$y": true,
        "$c_obj": true,
        "refresh_many": true,
        "refresh_field": true,
        "toggle_field": true,
        "get_field_obj": true,
        "get_query_params": true,
        "unhide_field": true,
        "hide_field": true,
        "set_field_options": true,
        "getCookie": true,
        "getCookies": true,
        "get_url_arg": true,
        "md5": true,
        "$": true,
        "jQuery": true,
        "moment": true,
        "hljs": true,
        "Awesomplete": true,
        "Sortable": true,
        "Showdown": true,
        "Taggle": true,
        "Gantt": true,
        "Slick": true,
        "Webcam": true,
        "PhotoSwipe": true,
        "PhotoSwipeUI_Default": true,
        "io": true,
        "JsBarcode": true,
        "L": true,
        "Chart": true,
        "DataTable": true,
        "Cypress": true,
        "cy": true,
        "it": true,
        "describe": true,
        "expect": true,
        "context": true,
        "before": true,
        "beforeEach": true,
        "after": true,
        "qz": true,
        "localforage": true,
        "extend_cscript": true
    }
}

```

`"root": true` tells ESLint to stop looking for configuration files in parent directories once this phamos configuration is found, preventing another configuration higher in the bench directory hierarchy from being applied unintentionally.

#### Setup and Usage Guide

This guide covers how to install and run ESLint on a phamos custom Frappe/ERPNext app using the base configuration above.

##### Installation

Install ESLint as a development dependency inside the app.

```bash
cd apps/<your-app>
npm install --save-dev eslint

```

or:

```bash
yarn add --dev eslint

```

Verify the installation:

```bash
npx eslint --version

```

##### Configuration File

Create the ESLint configuration file at the root of the phamos custom app. For the legacy configuration format used here, the file can be named `.eslintrc` or `.eslintrc.json`. Place the phamos base configuration shown above inside this file.

##### Commands

Run ESLint from the directory containing the configuration file.

##### `eslint` — inspect for violations

Scans phamos files and reports violations without modifying them.

```bash
npx eslint "**/*.js"

```

To lint a single file:

```bash
npx eslint phamos/gitlab_integration/doctype/gitlab_settings/gitlab_settings.js

```

##### `eslint --fix` — automatically fix violations

Applies safe automatic fixes. Violations without a safe fix are still reported and must be resolved manually.

```bash
npx eslint --fix "**/*.js"

```

##### Understanding ESLint Output

An error represents a violation that should normally be fixed.

```text
error  Unexpected ...

```

`space-unary-ops` is configured to report as an error.

A warning indicates a problem worth reviewing but of lower severity.

```js
console.log("Debug information");

```

This produces a warning rather than an error, since `no-console` is configured as `warn`.

##### Recommended Workflow

Run ESLint on the changed file:

```bash
npx eslint path/to/file.js

```

Review the reported violations and decide whether each represents a real problem or an expected phamos or Frappe pattern.

Apply automatic fixes where available:

```bash
npx eslint --fix path/to/file.js

```

Run ESLint again to confirm the remaining violations are resolved:

```bash
npx eslint path/to/file.js

```

##### Editor Integration

Install the official ESLint extension:

```text
dbaeumer.vscode-eslint

```

Add to `.vscode/settings.json` inside the phamos app:

```json
{
    "editor.codeActionsOnSave": {
        "source.fixAll.eslint": true
    },
    "eslint.validate": [
        "javascript"
    ]
}

```

Committing `.vscode/settings.json` to the repository lets the whole phamos team share the same editor behavior.

#### Summary

<table id="bkmrk-category-rule-status"><thead><tr><th>Category</th><th>Rule</th><th>Status</th></tr></thead><tbody><tr><td>ESLint Recommended</td><td>`eslint:recommended`</td><td>enabled</td></tr><tr><td>Formatting</td><td>`indent`</td><td>ignored</td></tr><tr><td>Formatting</td><td>`brace-style`</td><td>ignored</td></tr><tr><td>Formatting</td><td>`no-mixed-spaces-and-tabs`</td><td>ignored</td></tr><tr><td>Possible Problems</td><td>`no-useless-escape`</td><td>ignored</td></tr><tr><td>Possible Problems</td><td>`space-unary-ops`</td><td>error</td></tr><tr><td>Formatting</td><td>`linebreak-style`</td><td>ignored</td></tr><tr><td>Formatting</td><td>`quotes`</td><td>ignored</td></tr><tr><td>Formatting</td><td>`semi`</td><td>ignored</td></tr><tr><td>Naming</td><td>`camelcase`</td><td>ignored</td></tr><tr><td>Possible Problems</td><td>`no-unused-vars`</td><td>ignored</td></tr><tr><td>Possible Problems</td><td>`no-console`</td><td>warn</td></tr><tr><td>Possible Problems</td><td>`no-extra-boolean-cast`</td><td>ignored</td></tr><tr><td>Possible Problems</td><td>`no-control-regex`</td><td>ignored</td></tr><tr><td>Configuration</td><td>`root`</td><td>enabled</td></tr><tr><td>Environment</td><td>Browser</td><td>enabled</td></tr><tr><td>Environment</td><td>Node.js</td><td>enabled</td></tr><tr><td>Environment</td><td>ES2022</td><td>enabled</td></tr><tr><td>Modules</td><td>ES Modules</td><td>enabled</td></tr><tr><td>Frappe</td><td>Frappe globals</td><td>configured</td></tr></tbody></table>

#### Key Points

`eslint:recommended` provides the baseline JavaScript correctness checks for phamos.

`no-unused-vars` is disabled because Frappe form handler signatures require parameters like `frm` even when unused, and phamos follows the same convention.

`camelcase` is disabled because phamos, like the rest of Frappe, commonly uses snake\_case field names.

`semi` and `quotes` are disabled at the ESLint level because Prettier owns these formatting choices for phamos.

`indent` and `brace-style` are disabled for the same reason: Prettier formats phamos code, ESLint checks its correctness.

`no-console` is a warning rather than an error, since it is useful during phamos development.

`space-unary-ops` is explicitly enforced.

Frappe-specific globals are declared so framework-provided identifiers such as `frappe`, `cur_frm`, `flt`, `cint`, and `__` used throughout phamos are recognized by ESLint.

Browser, Node.js, and ES2022 environments are enabled to match how phamos code actually runs.

ES module syntax using `import` and `export` is supported.

This base configuration uses the legacy ESLint format. The phamos-specific additions layered on top of this base use the newer flat config format, `eslint.config.js`, covered in the separate phamos rules documentation.