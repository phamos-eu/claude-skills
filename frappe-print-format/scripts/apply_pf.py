#!/usr/bin/env python
"""Push HTML/CSS files into a Print Format doc (create it if missing).

Never build the HTML with a Python f-string — it eats Jinja's {{ }}. Keep the
format in real files and load them here.

    ./env/bin/python apply_pf.py --bench /path/to/bench --site akos.localhost \
        --name "Instandhaltungsvertrag 0.1" --doctype "Maintenance Contract" \
        --html pf.html --css pf.css

    # dump the current DB version back out to files
    ./env/bin/python apply_pf.py ... --dump-to /tmp/pf
"""
import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--site", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--doctype", help="required when creating a new format")
    ap.add_argument("--html")
    ap.add_argument("--css")
    ap.add_argument("--letterhead")
    ap.add_argument("--language", help="default_print_language, e.g. de")
    ap.add_argument("--pdf-generator", choices=["wkhtmltopdf", "chrome"],
                    help="v15 needs print_designer installed for 'chrome'")
    ap.add_argument("--dump-to", metavar="PREFIX", help="write <PREFIX>.html/.css and exit")
    args = ap.parse_args()

    os.chdir(os.path.join(args.bench, "sites"))
    sys.path.insert(0, os.getcwd())
    import frappe

    frappe.init(site=args.site)
    frappe.connect()
    frappe.set_user("Administrator")

    exists = frappe.db.exists("Print Format", args.name)

    if args.dump_to:
        if not exists:
            sys.exit(f"Print Format {args.name!r} does not exist")
        pf = frappe.get_doc("Print Format", args.name)
        with open(args.dump_to + ".html", "w") as f:
            f.write(pf.html or "")
        with open(args.dump_to + ".css", "w") as f:
            f.write(pf.css or "")
        print(f"dumped {args.dump_to}.html / .css")
        frappe.destroy()
        return

    if exists:
        pf = frappe.get_doc("Print Format", args.name)
    else:
        if not args.doctype:
            sys.exit("--doctype is required to create a new Print Format")
        pf = frappe.new_doc("Print Format")
        pf.name = args.name
        pf.doc_type = args.doctype
        pf.print_format_type = "Jinja"
        pf.custom_format = 1
        pf.standard = "No"
        pf.margin_top = pf.margin_bottom = pf.margin_left = pf.margin_right = 0

    if args.html:
        pf.html = open(args.html).read()
    if args.css:
        pf.css = open(args.css).read()
    if args.letterhead:
        pf.letter_head = args.letterhead
    if args.language:
        pf.default_print_language = args.language
    if args.pdf_generator and pf.meta.get_field("pdf_generator"):
        pf.pdf_generator = args.pdf_generator

    pf.save()
    frappe.db.commit()
    print(f"{'updated' if exists else 'created'} Print Format {pf.name!r}")
    frappe.destroy()


if __name__ == "__main__":
    main()
