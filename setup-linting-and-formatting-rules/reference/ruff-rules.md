# Phamos Ruff Rules

This document describes the lint rules enforced in the phamos standard, grouped by family. Each rule includes a plain-language description and a before/after code example written in a Frappe/ERPNext context.

### Rule code structure

Every Ruff rule has a code like `F401` or `B006`. The letter prefix identifies the family, and the number identifies the specific rule within that family. Selecting a family by its prefix (for example `"F"`) enables every rule in that family. The `ignore` list disables individual rules.

Families covered: `F`, `E`, `W`, `I`, `UP`, `B`, `N`, `RUF`.

Rules disabled in the phamos config are marked **(ignored in phamos)**.

### F — Pyflakes

Flags real correctness problems with almost no stylistic opinion. This is the highest-value family in the standard.

#### F401 — unused import

An import that is never referenced in the file. Keeping unused imports creates confusion about what a module actually depends on.

```python
# before
import frappe
from frappe.utils import flt, cint   # cint is never used

def get_total(doc):
    return flt(doc.amount)

# after
import frappe
from frappe.utils import flt

def get_total(doc):
    return flt(doc.amount)

```

`F401` is configured as an unsafe fix in phamos. Ruff flags the violation but does not auto-delete the import, because in Frappe an import can register a hook or DocType even when it appears unused.

#### F402 — import shadowed by a loop variable

An imported name is reused as a loop variable, making the import inaccessible for the rest of that scope.

```python
# before
from frappe.utils import flt

for flt in amounts:   # shadows the imported flt
    process(flt)

# after
from frappe.utils import flt

for value in amounts:
    process(value)

```

#### F811 — redefinition of an unused name

The same name is defined twice and the first definition is never used before being overwritten. This commonly occurs in DocType controllers when a method is accidentally pasted twice. The first definition is silently discarded.

```python
# before
class SalesInvoice(Document):
    def validate(self):
        self.check_customer()

    def validate(self):       # silently overrides the first validate
        self.check_items()

# after
class SalesInvoice(Document):
    def validate(self):
        self.check_customer()
        self.check_items()

```

#### F821 — undefined name

A name is referenced that was never defined in the current scope. This is usually a typo that would otherwise crash at runtime.

```python
# before
def on_submit(self):
    frappe.msgprint(mesage)   # 'mesage' is undefined

# after
def on_submit(self):
    message = "Invoice submitted"
    frappe.msgprint(message)

```

#### F841 — local variable assigned but never used

A value is assigned to a local variable that is never read afterwards. This is often a sign that the variable was meant to be returned or used in a subsequent expression.

```python
# before
def calculate(self):
    total = self.amount * self.qty   # assigned, never used
    return self.amount

# after
def calculate(self):
    total = self.amount * self.qty
    return total

```

#### F632 — use of `==` to compare with a literal

Using `is` to compare against a string, bytes, or number literal is unreliable. `is` checks object identity, not value equality. Value comparisons should use `==`, and `is` should be reserved for identity checks such as `is None`.

```python
# before
if status is "Paid":

# after
if status == "Paid":

```

#### F-string and format checks (F501–F509, F522, F524)

These rules catch mismatches in string formatting, such as a `%` format string with more placeholders than arguments, or a `.format()` call referencing a missing key. They prevent runtime formatting errors.

```python
# before
msg = "Invoice %s for %s" % (invoice_name,)   # two placeholders, one argument

# after
msg = "Invoice %s for %s" % (invoice_name, customer)

```

### E — pycodestyle (errors)

PEP 8 layout and style errors. Many of these overlap with what the formatter handles automatically. The primary value comes from the correctness-adjacent checks that the formatter does not cover.

#### E402 — module import not at top of file

Imports must appear at the top of the file, before any executable code. This makes a module's dependencies immediately visible.

```python
# before
import frappe

SETTINGS = frappe.get_single("System Settings")
import json   # import after executable code

# after
import json

import frappe

SETTINGS = frappe.get_single("System Settings")

```

#### E501 — line too long (ignored)

Flags lines exceeding the configured length (110 characters in phamos). This rule is disabled because the formatter handles line wrapping, making the linter check redundant.

#### E711 — comparison to None

Comparisons to `None` must use `is` or `is not`, not `==` or `!=`. Equality operators can behave unexpectedly with objects that override `__eq__`, whereas identity comparison is always unambiguous.

```python
# before
if self.posting_date == None:

# after
if self.posting_date is None:

```

#### E712 — comparison to True or False

Boolean values should be compared directly rather than against the literals `True` or `False`.

```python
# before
if self.is_active == True:

# after
if self.is_active:

```

#### E722 — bare except

A bare `except:` clause catches every possible exception, including system-level signals like `KeyboardInterrupt`, and makes it impossible to distinguish between different failure modes. The exception type must always be named.

```python
# before
try:
    frappe.get_doc("Sales Invoice", name)
except:
    pass

# after
try:
    frappe.get_doc("Sales Invoice", name)
except frappe.DoesNotExistError:
    pass

```

#### E741 — ambiguous variable name

The single-character names `l`, `O`, and `I` are visually indistinguishable from the digits `1` and `0` in many fonts and editors. A descriptive name must be used instead.

```python
# before
for l in items:
    process(l)

# after
for line in items:
    process(line)

```

### W — pycodestyle (warnings)

The warning tier of pycodestyle. Covers whitespace issues and a small number of correctness checks.

#### W191 — indentation contains tabs (ignored)

Normally flags tab-based indentation. Frappe indents with tabs by convention, and the phamos formatter is configured to produce tabs. This rule is disabled to avoid flagging every indented line in the codebase.

#### W291 / W293 — trailing whitespace

Trailing spaces at the end of a line or on an otherwise blank line produce noisy diffs. The formatter removes these automatically.

```python
# before
name = doc.customer_name    # trailing spaces

# after
name = doc.customer_name

```

#### W605 — invalid escape sequence

A backslash sequence inside a standard string that Python does not recognise as a valid escape will throw syntax error. This commonly occurs in regular expression patterns that should be raw strings.

```python
import re

def extract_price(text):
    # Intent: Find a dollar sign followed by one or more digits (\d+)
    # Mistake: Forgot the 'r' prefix!
    pattern = "\$\d+"
    match = re.search(pattern, text)
    if match:
        return match.group()
    return "No price found"

product_text = "The price is $125 total"
print(extract_price(product_text))
```

### I — isort

Enforces consistent import ordering and grouping across all files. This rule is fully auto-fixable and is one of the easiest wins in the standard, eliminating a persistent source of diff noise.

#### I001 — unsorted or ungrouped imports

Imports are reorganised into three sections, separated by blank lines: standard library, third-party packages, and first-party app code. Within each section, imports are sorted alphabetically.

```python
# before
from frappe.utils import flt
import frappe
from phamos.api import get_customer_for_user
import json
from frappe import _

# after
import json

import frappe
from frappe import _
from frappe.utils import flt

from phamos.api import get_customer_for_user

```

The phamos config sets `lines-after-imports = 2`, requiring two blank lines between the import block and the first statement of code.

### UP — pyupgrade

Modernises Python syntax to idiomatic equivalents available in the declared target version (Python 3.10). The rule will not suggest anything that requires a newer Python than the target.

#### UP006 — use built-in collection types for annotations

From Python 3.9 onwards, built-in types such as `list`, `dict`, and `tuple` can be used directly in annotations without importing their equivalents from `typing`.

```python
# before
from typing import List

def get_names(docs: List[str]) -> None:
    ...

# after
def get_names(docs: list[str]) -> None:
    ...

```

#### UP007 — use `X | Y` for union types

From Python 3.10 onwards, `Optional[X]` and `Union[X, Y]` can be written as `X | None` and `X | Y`.

```python
# before
from typing import Optional

def find_invoice(name: str) -> Optional[dict]:
    ...

# after
def find_invoice(name: str) -> dict | None:
    ...

```

#### UP008 — use `super()` without arguments

In Python 3 the arguments to `super()` are inferred automatically and must be omitted.

```python
# before
class SalesInvoice(Document):
    def validate(self):
        super(SalesInvoice, self).validate()

# after
class SalesInvoice(Document):
    def validate(self):
        super().validate()

```

#### UP015 — redundant open mode argument

The `"r"` mode is the default for `open()` and does not need to be stated explicitly.

```python
# before
with open(path, "r") as f:
    ...

# after
with open(path) as f:
    ...

```

#### UP030 / UP031 / UP032 — format string modernisation (ignored)

These rules convert `.format()` and `%`-style strings into f-strings. All three are disabled in phamos because Frappe's translation function `_()` can only extract translatable strings from literal arguments passed to `.format()` or `%`. Converting them to f-strings silently breaks translation extraction for all supported languages.

```python
# the following is intentionally left unchanged:
msg = _("Invoice {0} is overdue").format(name)

# UP032 would rewrite it to:
msg = f"Invoice {name} is overdue"   # breaks _() translation extraction

```

### B — flake8-bugbear

Flags patterns that are syntactically valid and will run without error, but are almost certainly mistakes or well-known traps. This family has a low false-positive rate and catches subtle bugs that code review frequently misses.

#### B006 — mutable default argument

A mutable object such as `[]` or `{}` used as a default argument is created once when the function is defined and is shared across all calls to that function. Mutations from one call persist into the next. The correct pattern is to default to `None` and initialise inside the function body.

```python
# before
def add_items(self, items=[]):   # the same list is reused on every call
    items.append(self.item)
    return items

# after
def add_items(self, items=None):
    items = items or []
    items.append(self.item)
    return items

```

#### B007 — unused loop variable

A loop variable that is never referenced in the loop body should be named `_` or prefixed with `_` to signal that it is intentionally unused.

```python
# before
for index, row in enumerate(self.items):
    process(row)   # index is never used

# after
for _index, row in enumerate(self.items):
    process(row)

```

#### B008 — function call in default argument

A function call used as a default argument is evaluated once at definition time, not on each call. Every invocation receives the same object produced at import time rather than a fresh value.

```python
# before
def log_entry(self, ts=frappe.utils.now()):   # now() runs once at import time

# after
def log_entry(self, ts=None):
    ts = ts or frappe.utils.now()

```

#### B012 — `return`, `break`, or `continue` inside `finally`

Control flow statements inside a `finally` block suppress any exception that is currently propagating. The exception is silently discarded, which can hide real failures.

```python
def process():
    raise ValueError("something went wrong")

def bad_version():
    result = "done"
    try:
        process()
    finally:
        return result   # the ValueError is silently swallowed here

def good_version():
    result = "done"
    try:
        process()
    finally:
        print("cleaning up...")   # cleanup runs, but does not swallow the error
    return result

# bad version — the exception disappears silently
output = bad_version()
print(output)   # prints "done" — no error, no warning, nothing
                # you have no idea process() failed

# good version — the exception surfaces properly
output = good_version()
print(output)   # raises ValueError: something went wrong
                # you can see exactly what happened
```

#### B904 — raise without `from` inside an `except` block

When raising a new exception while handling an existing one, the original exception should be chained using `from`. Without it, the original traceback is lost.

```python
# before
try:
    parse(value)
except ValueError:
    raise frappe.ValidationError("Invalid value")

# after
try:
    parse(value)
except ValueError as exc:
    raise frappe.ValidationError("Invalid value") from exc

```

### N — pep8-naming (advisory)

Enforces PEP 8 naming conventions. This family is currently advisory because some Frappe conventions do not fully align with PEP 8. It will be promoted to enforced once the ignore list has been tuned against the phamos apps.

#### N801 — class name must use PascalCase

```python
# before
class sales_invoice(Document):
    ...

# after
class SalesInvoice(Document):
    ...

```

#### N802 — function name must be snake\_case

```python
# before
def ProcessPayment(self):
    ...

# after
def process_payment(self):
    ...

```

#### N803 — argument name must be snake\_case

```python
# before
def create_entry(self, CustomerName):
    ...

# after
def create_entry(self, customer_name):
    ...

```

#### N805 — first argument of a method must be named `self`

```python
# before
class Settings(Document):
    def validate(this):
        ...

# after
class Settings(Document):
    def validate(self):
        ...

```

#### N806 — variable in a function must be snake\_case

```python
# before
def calculate(self):
    TotalAmount = 0

# after
def calculate(self):
    total_amount = 0

```

#### N815 — mixedCase variable in class scope

Flags `camelCase` class-level attributes. In Frappe, DocType field names sometimes arrive in mixed case. This rule is a candidate for the ignore list once the apps have been audited.

```python
# before
class Config(Document):
    maxRetries = 3

# after
class Config(Document):
    max_retries = 3

```

### RUF — Ruff-specific rules

Unlike every other family in the standard, `RUF` rules are not ported from an existing tool. They are written and maintained by the Ruff team and cover gaps that no other family addresses. Because they are built-in to Ruff, they are fast, well-maintained, and safe to enable across all projects. Frappe's official config includes this family, and the phamos standard follows that decision.

#### RUF001 — ambiguous Unicode character in string (ignored in phamos)

A character in a string looks like an ASCII character but is actually a different Unicode character. For example, the Greek capital letter `Η` (eta) looks identical to the Latin `H` but has a different code point. This can cause silent bugs where string comparisons fail unexpectedly.

```python
# before
print("Ηello, world!")   # "Η" is Greek eta (U+0397), not the Latin H

# after
print("Hello, world!")   # "H" is Latin capital H (U+0048)
```

This rule is disabled in phamos (`RUF001` is in the Frappe official ignore list) because Frappe apps handle multiple languages and scripts, and non-ASCII characters appearing in strings are expected and intentional.

#### RUF005 — unpack instead of concatenation

Two lists or tuples being joined with `+` can be written more clearly using unpacking with `*`. The unpacked form is faster and more idiomatic in modern Python.

```python
# before
items = base_items + [new_item]

# after
items = [*base_items, new_item]
```

#### RUF010 — use explicit conversion in f-string

When an f-string calls `str()` or `repr()` on a value, the explicit conversion flags `!s` and `!r` should be used instead. They are shorter and make the intent clearer.

```python
# before
label = f"{str(doc.name)}"
debug = f"{repr(self.value)}"

# after
label = f"{doc.name!s}"
debug = f"{self.value!r}"
```

#### RUF013 — implicit optional type annotation

When a function parameter has a default of `None`, the type annotation should explicitly include `None` (or use `Optional`). An annotation like `str` that accepts `None` as a default but does not declare it is misleading.

```python
# before
def get_customer(name: str = None):   # str does not include None
    ...

# after
def get_customer(name: str | None = None):
    ...
```

#### RUF015 — prefer next() over single-element slice

Iterating over an iterable just to get the first element by slicing is slower and less readable than using `next()`.

```python
results = [
    {"name": "INV-001", "status": "Unpaid"},
    {"name": "INV-002", "status": "Paid"},
    {"name": "INV-003", "status": "Paid"},
    {"name": "INV-004", "status": "Paid"},
    {"name": "INV-005", "status": "Paid"},
]

# before — builds entire filtered list, grabs first
first = [row for row in results if row.status == "Paid"][0]

# after — stops at the first match, never processes the rest
first = next(row for row in results if row.status == "Paid")
```

#### RUF019 — unnecessary key check before dict access

Checking whether a key exists with `if key in d` and then immediately accessing `d[key]` in the same branch is redundant. The dict access alone is sufficient, or `.get()` can be used if a default is needed.

```python
# before
if "customer" in doc_data:
    customer = doc_data["customer"]

# after
customer = doc_data.get("customer")
```

#### RUF100 — unused `# noqa` directive

A `# noqa` comment tells Ruff to ignore a specific rule on that line. If the rule no longer fires on that line (because the code was fixed or the rule was removed), the `# noqa` comment itself becomes dead code and should be removed.

```python
# before
import json   # noqa: F401   (but json is actually used below)

# after
import json
```

This is a useful maintenance rule. As code gets cleaned up over time, stale `# noqa` comments accumulate and obscure where real suppressions are still needed.


### Setup and Usage Guide

This guide covers how to configure and run Ruff on a phamos custom Frappe/ERPNext app.

#### Installation

Ruff can be installed globally or into the bench Python environment.

**Global Installation**

```bash
pip install ruff

brew install ruff

```

**Bench environment installation**

```bash
cd frappe-bench
./env/bin/pip install ruff

```

Verify the installation:

```bash
ruff --version

```

#### Configuration

Place the following configuration in the `pyproject.toml` file at the root of the custom app:

```
frappe-bench/
  apps/
    your_app/
      pyproject.toml        ← place it here
      your_app/

```

Paste the following content at the end of `pyproject.toml` file:

```toml
[tool.ruff]
target-version = "py310"
line-length = 110

[tool.ruff.format]
quote-style = "double"
indent-style = "tab"
docstring-code-format = true
exclude = [
	"*.pyi",
	"**/apps/frappe/**/*.py",
	"**/apps/erpnext/**/*.py",
]

[tool.ruff.lint]
select = [
    "F",
    "E",
    "W",
    "I",
    "UP",
    "B",
    "N",
    "RUF",
]
ignore = [
    "B017", # assertRaises(Exception) - should be more specific
    "B018", # useless expression, not assigned to anything
    "B023", # function doesn't bind loop variable - will have last iteration's value
    "B904", # raise inside except without from
    "E101", # indentation contains mixed spaces and tabs
    "E402", # module level import not at top of file
    "E501", # line too long
    "E741", # ambiguous variable name
    "F403", # can't detect undefined names from * import
    "F405", # can't detect undefined names from * import
    "F722", # syntax error in forward type annotation
    "W191", # indentation contains tabs
    "N815", # mixedCase variable in class scope - DocType field names
    "N999", # invalid module name - Frappe auto-generates some module names
    "RUF001", # string contains ambiguous unicode character
    "UP030", # Use implicit references for positional format fields (translations)
    "UP031", # Use format specifiers instead of percent format
    "UP032", # Use f-string instead of `format` call (translations)
]
typing-modules = ["frappe.types.DF"]

fixable = ["ALL"]
extend-unsafe-fixes = ["F401"] # imports may register hooks/DocTypes; don't auto-delete

[tool.ruff.lint.isort]
lines-after-imports = 2

```

All commands below must be run from inside the app directory.

#### Commands

##### `ruff check` — inspect for violations

Scans files and reports violations without making any changes. Use this to see what needs to be fixed before touching any code.

```bash
# check all files in the app
ruff check .

# check a specific file
ruff check phamos/api.py

```

To see the offending line printed underneath each violation, add `--show-source`:

```bash
ruff check phamos/api.py --show-source

```

To get a summary of how many violations exist per rule across the whole app:

```bash
ruff check . --statistics

```

---

##### `ruff check --fix` — auto-fix violations

Scans files and automatically fixes every violation that has a safe fix available. Violations that require developer judgment are reported but left unchanged.

```bash
# fix all files in the app
ruff check . --fix

# fix a specific file
ruff check phamos/api.py --fix

```

After running this, any remaining violations must be resolved manually by the developer.

##### `ruff check --unsafe-fixes` — apply hidden fixes

Some violations have a fix available but Ruff considers it unsafe, meaning it could theoretically change behaviour rather than just appearance. These are hidden by default and require an explicit flag to apply.

In the phamos config, `F401` (unused imports) is marked as an unsafe fix. Ruff will flag unused imports but will not delete them automatically, because in Frappe an import can register a hook or DocType even when it appears unused. The developer must decide whether the import is safe to remove.

```bash
# preview what the unsafe fixes would change, without applying them
ruff check phamos/api.py --unsafe-fixes

# apply both safe and unsafe fixes
ruff check phamos/api.py --fix --unsafe-fixes

```

Always review the changes produced by `--unsafe-fixes` before committing, particularly for `__init__.py` files and files that import Frappe hooks.

##### `ruff format` — format code appearance

Reformats code to match the style defined in `ruff.toml`. This pass only changes how code looks, never what it does. It handles quote style, indentation, trailing whitespace, blank lines, and line wrapping.

```bash
# format all files in the app
ruff format .

# format a specific file
ruff format phamos/api.py

```

##### Difference between `check --fix` and `format`

These two commands do different things and are not interchangeable.

`ruff check --fix` addresses **lint violations**: unused imports, outdated syntax, bug patterns, import ordering. It changes what the code says at a structural level.

`ruff format` addresses **code appearance**: quote style, indentation, whitespace, line breaks. It never changes what the code does, only how it looks.

##### Recommended order of operations

Run the commands in this order when cleaning up a file or the whole app:

```bash
ruff check . --fix     # resolve lint violations first
ruff format .          # then clean up appearance

```

Format runs last because the `--fix` pass can introduce minor formatting inconsistencies when rewriting code, which `format` then cleans up in a single pass.

## Summary

<table id="bkmrk-family-status-ignore" style="width: 61.6667%; height: 307px;"><thead><tr style="height: 29.7969px;"><th style="width: 37.147%; height: 29.7969px;">Family</th><th style="width: 27.8433%; height: 29.7969px;">Status</th><th style="width: 35.0097%; height: 29.7969px;">Ignored rules</th></tr></thead><tbody><tr style="height: 35.3984px;"><td style="width: 37.147%; height: 35.3984px;">F — Pyflakes</td><td style="width: 27.8433%; height: 35.3984px;">Enforced</td><td style="width: 35.0097%; height: 35.3984px;">none</td></tr><tr style="height: 29.7969px;"><td style="width: 37.147%; height: 29.7969px;">E — pycodestyle errors</td><td style="width: 27.8433%; height: 29.7969px;">Enforced</td><td style="width: 35.0097%; height: 29.7969px;">E501, E242</td></tr><tr style="height: 29.7969px;"><td style="width: 37.147%; height: 29.7969px;">W — pycodestyle warnings</td><td style="width: 27.8433%; height: 29.7969px;">Enforced</td><td style="width: 35.0097%; height: 29.7969px;">W191</td></tr><tr style="height: 29.7969px;"><td style="width: 37.147%; height: 29.7969px;">I — isort</td><td style="width: 27.8433%; height: 29.7969px;">Enforced, auto-fix</td><td style="width: 35.0097%; height: 29.7969px;">none</td></tr><tr style="height: 29.7969px;"><td style="width: 37.147%; height: 29.7969px;">UP — pyupgrade</td><td style="width: 27.8433%; height: 29.7969px;">Enforced</td><td style="width: 35.0097%; height: 29.7969px;">UP030, UP031, UP032</td></tr><tr style="height: 29.7969px;"><td style="width: 37.147%; height: 29.7969px;">B — flake8-bugbear</td><td style="width: 27.8433%; height: 29.7969px;">Enforced</td><td style="width: 35.0097%; height: 29.7969px;">B023</td></tr><tr style="height: 29.7969px;"><td style="width: 37.147%; height: 29.7969px;">N — pep8-naming</td><td style="width: 27.8433%; height: 29.7969px;">Advisory</td><td style="width: 35.0097%; height: 29.7969px;">candidates: N815, N999</td></tr><tr style="height: 29.7969px;"><td style="width: 37.147%; height: 29.7969px;">RUF — Ruff-specific rules</td><td style="width: 27.8433%; height: 29.7969px;">Enforced</td><td style="width: 35.0097%; height: 29.7969px;">RUF001</td></tr></tbody></table>