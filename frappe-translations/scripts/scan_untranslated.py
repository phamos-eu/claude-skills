#!/usr/bin/env python3
"""Find strings a Frappe app will never translate.

Two classes of finding, both worth fixing:

  MISSING  a user-facing string passed to throw/msgprint/title with no _() / __()
  BROKEN   a _() / __() call whose argument is not a plain literal (f-string,
           concatenation, %-format, JS template literal). These look translated
           in review but the extractor cannot read them and the runtime key
           never matches.

    ./scan_untranslated.py /path/to/apps/suncycle
    ./scan_untranslated.py apps/suncycle --only broken --json
"""
import argparse
import ast
import json
import os
import re
import sys

# calls whose first argument is shown to a user
PY_USER_FACING = {
    "throw", "msgprint", "frappe.throw", "frappe.msgprint",
    "frappe.throw_permission_error", "PermissionError",
}
JS_USER_FACING = ("frappe.throw", "frappe.msgprint", "frappe.show_alert",
                  "frappe.confirm", "frappe.warn")

SKIP_DIRS = {".git", "node_modules", "__pycache__", "dist", "build",
             ".venv", "env", "public/dist", "translations", "locale"}


class Finding:
    def __init__(self, path, line, kind, code, message):
        self.path, self.line, self.kind = path, line, kind
        self.code, self.message = code, message

    def as_dict(self):
        return dict(file=self.path, line=self.line, kind=self.kind,
                    code=self.code, message=self.message)

    def __str__(self):
        return f"{self.path}:{self.line}: {self.kind} [{self.code}] {self.message}"


# --------------------------------------------------------------------- python

def dotted(node):
    """Best-effort dotted name of a call target."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def is_translate_call(node):
    return isinstance(node, ast.Call) and dotted(node.func) in ("_", "frappe._")


def literal_arg_problem(arg):
    """Return a reason string if this _() argument is not statically extractable."""
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return None
    if isinstance(arg, ast.JoinedStr):
        return "f-string inside _() — the extractor sees the template, the runtime sees the interpolated text"
    if isinstance(arg, ast.BinOp):
        if isinstance(arg.op, ast.Mod):
            return "%-formatting inside _() — translate first, format after: _(\"...{0}\").format(x)"
        if isinstance(arg.op, ast.Add):
            return "string concatenation inside _() — pass one literal with {0} placeholders"
        return "computed expression inside _()"
    if isinstance(arg, ast.Call):
        if dotted(arg.func).endswith(".format"):
            return "_() applied to an already-formatted string — move .format() outside _()"
        return "computed expression inside _()"
    if isinstance(arg, (ast.Name, ast.Attribute, ast.Subscript)):
        return "variable inside _() — nothing to extract; translate where the value is defined"
    return "non-literal argument to _()"


def scan_python(path, src):
    out = []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [Finding(path, e.lineno or 0, "SKIP", "parse-error", str(e))]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = dotted(node.func)

        if is_translate_call(node) and node.args:
            problem = literal_arg_problem(node.args[0])
            if problem:
                out.append(Finding(path, node.lineno, "BROKEN", "non-literal", problem))
            continue

        if name in PY_USER_FACING and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value.strip():
                    out.append(Finding(path, node.lineno, "MISSING", "unwrapped",
                                       f"{name}(): {arg.value[:60]!r} is not wrapped in _()"))
            elif isinstance(arg, ast.JoinedStr):
                out.append(Finding(path, node.lineno, "MISSING", "unwrapped-fstring",
                                   f"{name}(): f-string message, not translatable"))
        # title=/label=/description= keywords carrying a bare literal
        for kw in node.keywords:
            if kw.arg in ("title", "label", "description") and \
                    isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str) \
                    and kw.value.value.strip():
                out.append(Finding(path, node.lineno, "MISSING", "unwrapped-kwarg",
                                   f"{name}({kw.arg}=): {kw.value.value[:40]!r} is not wrapped in _()"))
    return out


# ------------------------------------------------------------------------- js

JS_TRANSLATE_TEMPLATE = re.compile(r"__\(\s*`")
JS_TRANSLATE_CONCAT = re.compile(r"""__\(\s*(["'][^"']*["']\s*\+|\w+\s*[,)])""")
JS_CALL = re.compile(r"(" + "|".join(re.escape(c) for c in JS_USER_FACING) + r")\s*\(\s*(.)")


def scan_js(path, src):
    out = []
    for i, line in enumerate(src.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        if JS_TRANSLATE_TEMPLATE.search(line):
            out.append(Finding(path, i, "BROKEN", "template-literal",
                               "__(`...`) — template literals are skipped by the extractor; "
                               'use __("... {0}", [x])'))
        m = JS_TRANSLATE_CONCAT.search(line)
        if m and not JS_TRANSLATE_TEMPLATE.search(line):
            out.append(Finding(path, i, "BROKEN", "non-literal",
                               "__() argument is not a plain string literal"))
        for call, first in JS_CALL.findall(line):
            if first in "\"'":
                out.append(Finding(path, i, "MISSING", "unwrapped",
                                   f"{call}(): literal message is not wrapped in __()"))
    return out


# ----------------------------------------------------------------------- main

def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if fn.endswith((".py", ".js")) and not fn.endswith((".min.js", ".bundle.js")):
                yield os.path.join(dirpath, fn)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="app root, e.g. apps/suncycle")
    ap.add_argument("--only", choices=["missing", "broken"],
                    help="restrict to one class of finding")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    findings = []
    for path in walk(args.path):
        try:
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        rel = os.path.relpath(path, args.path)
        findings += scan_python(rel, src) if path.endswith(".py") else scan_js(rel, src)

    if args.only:
        findings = [f for f in findings if f.kind == args.only.upper()]

    if args.json:
        json.dump([f.as_dict() for f in findings], sys.stdout, indent=2)
        print()
    else:
        for f in sorted(findings, key=lambda f: (f.kind, f.path, f.line)):
            print(f)
        broken = sum(1 for f in findings if f.kind == "BROKEN")
        missing = sum(1 for f in findings if f.kind == "MISSING")
        print(f"\n{broken} broken, {missing} missing "
              f"({len(findings)} findings). Fix BROKEN first — those read as "
              f"translated but never are.", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
