#!/usr/bin/env python
"""Stress a print format's pagination by growing a long text field.

Catches the failures a single happy-path render hides: content overlapping a
rule, a signature block landing near the top of the last page, a block splitting
across pages, or a 1-page doc silently becoming 2.

    ./env/bin/python paginate_test.py --bench /path/to/bench --site akos.localhost \
        --name "Instandhaltungsvertrag 0.1" --doc "Maintenance Contract:IV-2026-0017" \
        --field maintenance_contract_terms --grow 0,8,16,40 \
        --marker Unterschrift --whole Datum --whole Unterschrift
"""
import argparse
import os
import sys

PT2MM = 25.4 / 72


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--site", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--doc", required=True, help="DocType:name")
    ap.add_argument("--field", required=True, help="long text/HTML field to grow")
    ap.add_argument("--grow", default="0,8,16,40", help="comma-separated paragraph counts")
    ap.add_argument("--marker", help="word that should appear on the LAST page only")
    ap.add_argument("--whole", action="append", default=[],
                    help="words that must all land on the same (last) page")
    args = ap.parse_args()

    os.chdir(os.path.join(args.bench, "sites"))
    sys.path.insert(0, os.getcwd())
    import fitz
    import frappe

    frappe.init(site=args.site)
    frappe.connect()
    frappe.set_user("Administrator")

    from frappe.utils.jinja import render_template
    from frappe.utils.pdf import get_chrome_pdf

    doctype, docname = args.doc.split(":", 1)
    pf = frappe.get_doc("Print Format", args.name)
    base = frappe.get_doc(doctype, docname).get(args.field) or ""

    def render(text):
        d = frappe.get_doc(doctype, docname)
        d.set(args.field, text)
        body = render_template(pf.html, {"doc": d})
        html = '<div class="print-format"><style>%s</style>%s</div>' % (pf.css, body)
        return fitz.open("pdf", get_chrome_pdf("x", html, {}, None, pdf_generator="chrome"))

    for n in [int(x) for x in args.grow.split(",")]:
        extra = "".join(
            f"<p>{i+1}. Zusatzabsatz zur Pruefung der Paginierung mit etwas Text.</p>"
            for i in range(n)
        )
        text = base.replace("</div>", extra + "</div>") if "</div>" in base else base + extra
        pdf = render(text)
        last = pdf.page_count - 1
        out = [f"grow({n:3d}): pages={pdf.page_count}"]

        if args.marker:
            pages = [i + 1 for i in range(pdf.page_count) if args.marker in pdf[i].get_text()]
            ok = pages == [last + 1]
            out.append(f"{args.marker} on pages {pages} {'OK' if ok else 'FAIL'}")
        if args.whole:
            txt = pdf[last].get_text()
            missing = [w for w in args.whole if w not in txt]
            out.append("block whole=" + ("OK" if not missing else f"FAIL missing {missing}"))

        words = [w for w in pdf[last].get_text("words") if w[4].strip()]
        if words:
            out.append(f"last-page content {min(w[1] for w in words)*PT2MM:.1f}"
                       f"..{max(w[3] for w in words)*PT2MM:.1f}mm")
        print("  ".join(out))
        pdf.close()

    frappe.destroy()


if __name__ == "__main__":
    main()
