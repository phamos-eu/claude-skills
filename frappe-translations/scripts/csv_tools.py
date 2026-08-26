#!/usr/bin/env python3
"""Work on a Frappe translation CSV (<app>/<app>/translations/<lang>.csv).

Format: source,translation[,context]. A row with a non-empty context is keyed
"source:context" at runtime, so it will NOT match a plain _("source") call.

    ./csv_tools.py validate  translations/de.csv
    ./csv_tools.py sort      translations/de.csv --write
    ./csv_tools.py merge     translations/de.csv new.csv --write
    ./csv_tools.py stats     translations/de.csv
    ./csv_tools.py to-po     translations/de.csv --lang de > locale/de.po
    ./csv_tools.py from-po   locale/de.po > translations/de.csv
"""
import argparse
import csv
import io
import re
import sys

PLACEHOLDER = re.compile(r"\{\d+\}|\{\w+\}|%[sd]")


def read_csv(path):
    """Return list of (source, translation, context, lineno)."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = []
        for lineno, row in enumerate(csv.reader(fh), 1):
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            source = row[0]
            translation = row[1] if len(row) > 1 else ""
            context = row[2] if len(row) > 2 else ""
            rows.append((source, translation, context, lineno))
        return rows


def write_csv(rows, stream):
    w = csv.writer(stream, lineterminator="\n")
    for source, translation, context, *_ in rows:
        w.writerow([source, translation, context] if context else [source, translation])


def emit(rows, path, write):
    if write:
        buf = io.StringIO()
        write_csv(rows, buf)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(buf.getvalue())
        print(f"wrote {len(rows)} rows to {path}", file=sys.stderr)
    else:
        write_csv(rows, sys.stdout)


# ------------------------------------------------------------------ validate

def cmd_validate(args):
    problems = []
    with open(args.path, "rb") as fh:
        if fh.read(3) == b"\xef\xbb\xbf":
            problems.append("file starts with a UTF-8 BOM — the first source "
                            "string will never match; save as plain UTF-8")

    rows = read_csv(args.path)
    seen = {}
    for source, translation, context, lineno in rows:
        key = (source, context)
        if key in seen:
            problems.append(f"line {lineno}: duplicate source {source!r} "
                            f"(first at line {seen[key]}) — the last one silently wins")
        seen[key] = lineno

        if not source.strip():
            problems.append(f"line {lineno}: empty source")
        if not translation.strip():
            problems.append(f"line {lineno}: {source!r} has no translation — "
                            f"drop the row instead, an empty msgstr can mask the English fallback")
            continue
        if source != source.strip():
            problems.append(f"line {lineno}: source has leading/trailing whitespace "
                            f"({source!r}) — whitespace is part of the lookup key")
        src_ph = sorted(PLACEHOLDER.findall(source))
        tr_ph = sorted(PLACEHOLDER.findall(translation))
        if src_ph != tr_ph:
            problems.append(f"line {lineno}: placeholder mismatch {src_ph} vs {tr_ph} "
                            f"in {source!r} — .format() will raise at runtime")
        if source == translation:
            problems.append(f"line {lineno}: translation identical to source ({source!r}) "
                            f"— untranslated, or an identifier that should not be here")
        if "\u00a0" in source or "\u2019" in source:
            problems.append(f"line {lineno}: source contains a non-breaking space or curly "
                            f"apostrophe — must match the code literal byte for byte")

    for p in problems:
        print(p)
    print(f"\n{len(rows)} rows, {len(problems)} problems", file=sys.stderr)
    return 1 if problems else 0


# ---------------------------------------------------------------- sort/merge

def cmd_sort(args):
    rows = read_csv(args.path)
    dedup = {}
    for source, translation, context, _ln in rows:
        dedup[(source, context)] = translation
    out = [(s, t, c) for (s, c), t in sorted(dedup.items())]
    emit(out, args.path, args.write)
    return 0


def cmd_merge(args):
    base = {(s, c): t for s, t, c, _ in read_csv(args.path)}
    added = updated = 0
    for s, t, c, _ln in read_csv(args.other):
        if not t.strip():
            continue
        key = (s, c)
        if key not in base:
            base[key] = t
            added += 1
        elif base[key] != t and args.prefer_other:
            base[key] = t
            updated += 1
    out = [(s, t, c) for (s, c), t in sorted(base.items())]
    print(f"{added} added, {updated} updated, {len(out)} total", file=sys.stderr)
    emit(out, args.path, args.write)
    return 0


def cmd_stats(args):
    rows = read_csv(args.path)
    translated = sum(1 for _s, t, _c, _ln in rows if t.strip())
    ctx = sum(1 for _s, _t, c, _ln in rows if c.strip())
    print(f"{args.path}: {len(rows)} rows, {translated} translated "
          f"({translated * 100 // max(len(rows), 1)}%), {ctx} with context")
    return 0


# -------------------------------------------------------------------- po i/o

def po_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def po_unescape(s):
    return s.replace('\\n', "\n").replace('\\"', '"').replace("\\\\", "\\")


def cmd_to_po(args):
    rows = read_csv(args.path)
    out = sys.stdout
    out.write('msgid ""\nmsgstr ""\n'
              '"MIME-Version: 1.0\\n"\n'
              '"Content-Type: text/plain; charset=UTF-8\\n"\n'
              '"Content-Transfer-Encoding: 8bit\\n"\n'
              f'"Language: {args.lang}\\n"\n\n')
    for source, translation, context, _ln in rows:
        if context:
            out.write(f'msgctxt "{po_escape(context)}"\n')
        out.write(f'msgid "{po_escape(source)}"\n')
        out.write(f'msgstr "{po_escape(translation)}"\n\n')
    return 0


def cmd_from_po(args):
    entries, cur, key = [], {}, None
    with open(args.path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            m = re.match(r'(msgctxt|msgid|msgstr) "(.*)"$', line)
            if m:
                key = m.group(1)
                cur[key] = po_unescape(m.group(2))
                continue
            m = re.match(r'"(.*)"$', line)
            if m and key:                       # continuation line
                cur[key] += po_unescape(m.group(1))
                continue
            if not line.strip():
                if cur.get("msgid") and cur.get("msgstr"):
                    entries.append((cur["msgid"], cur["msgstr"], cur.get("msgctxt", "")))
                cur, key = {}, None
    if cur.get("msgid") and cur.get("msgstr"):
        entries.append((cur["msgid"], cur["msgstr"], cur.get("msgctxt", "")))
    write_csv(sorted(entries), sys.stdout)
    print(f"{len(entries)} entries", file=sys.stderr)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate"); p.add_argument("path"); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("sort"); p.add_argument("path")
    p.add_argument("--write", action="store_true", help="edit in place (default: stdout)")
    p.set_defaults(fn=cmd_sort)
    p = sub.add_parser("merge"); p.add_argument("path"); p.add_argument("other")
    p.add_argument("--write", action="store_true")
    p.add_argument("--prefer-other", action="store_true",
                   help="let the incoming file overwrite existing translations")
    p.set_defaults(fn=cmd_merge)
    p = sub.add_parser("stats"); p.add_argument("path"); p.set_defaults(fn=cmd_stats)
    p = sub.add_parser("to-po"); p.add_argument("path")
    p.add_argument("--lang", default="en"); p.set_defaults(fn=cmd_to_po)
    p = sub.add_parser("from-po"); p.add_argument("path"); p.set_defaults(fn=cmd_from_po)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
