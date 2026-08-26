#!/usr/bin/env python
"""Render a Print Format against a real doc through the SAME path as the PDF button.

Reports page count, where each marker word landed, and the lowest content on the
page — the numbers you actually verify against. Optionally saves page PNGs.

    ./env/bin/python render_pf.py --bench /path/to/bench --site akos.localhost \
        --name "Instandhaltungsvertrag 0.1" --doc "Maintenance Contract:IV-2026-0013" \
        --out /tmp/out --dpi 120 --find Unterschrift --find Datum
"""
import argparse
import os
import sys

PT2MM = 25.4 / 72


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--site", required=True)
    ap.add_argument("--name", required=True, help="Print Format name")
    ap.add_argument("--doc", required=True, help="DocType:name")
    ap.add_argument("--out", default="/tmp/pf_render", help="output prefix")
    ap.add_argument("--dpi", type=int, default=0, help="save page PNGs at this dpi")
    ap.add_argument("--find", action="append", default=[], help="report y of this word")
    ap.add_argument("--generator", default="chrome", choices=["chrome", "wkhtmltopdf"])
    ap.add_argument("--language", help="print language, as the desk PDF button passes it")
    args = ap.parse_args()

    os.chdir(os.path.join(args.bench, "sites"))
    sys.path.insert(0, os.getcwd())
    import fitz
    import frappe

    frappe.init(site=args.site)
    frappe.connect()
    frappe.set_user("Administrator")

    doctype, docname = args.doc.split(":", 1)

    # the exact path the desk PDF button takes, on both v15 and v16
    frappe.form_dict.pdf_generator = args.generator
    from frappe.translate import print_language

    with print_language(args.language or frappe.local.lang):
        raw = frappe.get_print(
            doctype, docname, args.name, as_pdf=True, pdf_generator=args.generator
        )

    pdf_path = args.out + ".pdf"
    with open(pdf_path, "wb") as f:
        f.write(raw)
    pdf = fitz.open("pdf", raw)
    print(f"{args.name} / {args.doc}: {pdf.page_count} page(s) -> {pdf_path}")

    for i, page in enumerate(pdf):
        words = [w for w in page.get_text("words") if w[4].strip()]
        r = page.rect
        print(
            f"  page {i+1}: {r.width*PT2MM:.1f}x{r.height*PT2MM:.1f}mm  "
            f"words={len(words)}  "
            f"content top={min(w[1] for w in words)*PT2MM:.1f}mm "
            f"bottom={max(w[3] for w in words)*PT2MM:.1f}mm"
            if words
            else f"  page {i+1}: EMPTY"
        )
        for needle in args.find:
            hits = [w for w in words if w[4] == needle]
            for w in hits:
                print(f"    {needle!r}: top={w[1]*PT2MM:.2f}mm left={w[0]*PT2MM:.2f}mm")
        if args.dpi:
            png = f"{args.out}_p{i+1}.png"
            page.get_pixmap(dpi=args.dpi).save(png)
            print(f"    saved {png}")

    frappe.destroy()


if __name__ == "__main__":
    main()
