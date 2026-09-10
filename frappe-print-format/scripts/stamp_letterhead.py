#!/usr/bin/env python
"""Paint a full-page letterhead image behind every page of a finished PDF, and
scaffold the companion Frappe app that does it automatically for a print format.

Use this when the three-band Chrome generator splits a full-bleed letterhead
graphic at the body/footer join (visible white hairline through a corner wedge,
worse on the Linux server than locally). See reference/letterhead-stamp.md.

Two modes:

  # 1. stamp one PDF (no app) — prove the image + geometry first
  ./env/bin/python stamp_letterhead.py --stamp in.pdf --image letterhead-a4.png \
      --out stamped.pdf

  # 2. scaffold the companion app
  ./env/bin/python stamp_letterhead.py --scaffold /path/to/bench/apps \
      --app-name acme_print \
      --format "ACME Invoice=acme-invoice-a4.png" \
      --publisher "ACME GmbH" --email dev@acme.example

Only Pillow + pypdf are used for stamping (both are frappe dependencies — never
PyMuPDF, which is absent on a stock bench / Frappe Cloud).
"""
import argparse
import io
import os
import sys


# --------------------------------------------------------------------------- #
# core — this is exactly what the generated app's chrome_stamp.py runs
# --------------------------------------------------------------------------- #
def stamp_page_pdf(image_bytes: bytes, width_pt: float, height_pt: float) -> bytes:
    """One-page PDF exactly width_pt x height_pt holding the image at full bleed."""
    from PIL import Image

    im = Image.open(io.BytesIO(image_bytes))
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    dpi_x = im.width * 72.0 / width_pt
    dpi_y = im.height * 72.0 / height_pt
    buf = io.BytesIO()
    im.save(buf, format="PDF", resolution=min(dpi_x, dpi_y), dpi=(dpi_x, dpi_y))
    return buf.getvalue()


def stamp_pdf_bytes(pdf_bytes: bytes, image_bytes: bytes) -> bytes:
    """Return pdf_bytes with image_bytes placed behind every page.

    The letterhead page is the canvas; the chrome content is merged ON TOP, so
    the content page (footer XObjects, page-number clones) is only referenced,
    never rewritten — merging the other way corrupts the merged footer.
    """
    from pypdf import PdfReader, PdfWriter

    base = PdfReader(io.BytesIO(pdf_bytes))
    first = base.pages[0]
    stamp = stamp_page_pdf(
        image_bytes, float(first.mediabox.width), float(first.mediabox.height)
    )

    writer = PdfWriter()
    for page in base.pages:
        canvas = PdfReader(io.BytesIO(stamp)).pages[0]
        canvas.merge_page(page, over=True)
        writer.add_page(canvas)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# --------------------------------------------------------------------------- #
# mode 1: stamp one PDF
# --------------------------------------------------------------------------- #
def do_stamp(args):
    with open(args.stamp, "rb") as f:
        pdf = f.read()
    with open(args.image, "rb") as f:
        img = f.read()
    out = stamp_pdf_bytes(pdf, img)
    with open(args.out, "wb") as f:
        f.write(out)

    from pypdf import PdfReader

    pages = PdfReader(io.BytesIO(out)).pages
    imgs = [len(p.images) for p in pages]
    print(f"{args.out}: {len(pages)} pages, images/page = {imgs}",
          "  OK" if all(imgs) else "  <-- an unstamped page")


# --------------------------------------------------------------------------- #
# mode 2: scaffold the companion app
# --------------------------------------------------------------------------- #
_HOOKS = '''\
app_name = "{app}"
app_title = "{title}"
app_publisher = "{publisher}"
app_description = "Full-page letterhead stamp behind the {title} PDF (seam-free)."
app_email = "{email}"
app_license = "MIT"

from {app}.patch import apply as _apply_stamp_patch

_apply_stamp_patch()

before_request = ["{app}.patch.before_request"]
before_job = ["{app}.patch.before_job"]

after_install = "{app}.setup.after_install"
'''

_PATCH = '''\
"""Wrap get_chrome_pdf to stamp a full-page letterhead behind every page."""

import frappe

_FLAG = "_{app}_stamped"


def apply():
    import frappe.utils.pdf as pdf_mod

    if getattr(pdf_mod.get_chrome_pdf, _FLAG, False):
        return
    _orig = pdf_mod.get_chrome_pdf

    def get_chrome_pdf(print_format, html, options, output, pdf_generator=None):
        result = _orig(print_format, html, options, output, pdf_generator=pdf_generator)
        if not result or pdf_generator != "chrome":
            return result

        from {app}.chrome_stamp import resolve_stamp, stamp_pdf_bytes

        image = resolve_stamp(print_format)
        if not image:
            return result
        try:
            if isinstance(result, (bytes, bytearray)):
                return stamp_pdf_bytes(bytes(result), image)

            import io

            from pypdf import PdfReader, PdfWriter

            buf = io.BytesIO()
            result.write(buf)
            stamped = stamp_pdf_bytes(buf.getvalue(), image)
            fresh = PdfWriter()
            fresh.append_pages_from_reader(PdfReader(io.BytesIO(stamped)))
            return fresh
        except Exception:
            frappe.log_error(title="{app}: letterhead stamp failed")
            return result

    get_chrome_pdf.__dict__[_FLAG] = True
    pdf_mod.get_chrome_pdf = get_chrome_pdf


def before_request(*args, **kwargs):
    apply()


def before_job(*args, **kwargs):
    apply()
'''

_CHROME_STAMP = '''\
"""Place a full-page letterhead image behind every page of a finished PDF.

Pillow + pypdf only (both frappe dependencies) — no PyMuPDF.
"""

import io
import os

import frappe

_STATIONERY_DIR = os.path.join(os.path.dirname(__file__), "stationery")

# print format name -> stamp image basename (a public File named exactly this,
# with a copy in stationery/ as a fallback)
STAMPS = {stamps!r}


def resolve_stamp(print_format) -> bytes | None:
    name = getattr(print_format, "name", None)
    if not name and isinstance(print_format, str):
        name = print_format
    basename = STAMPS.get(name or "")
    if not basename:
        return None

    if frappe.db.get_value("File", {{"file_name": basename, "is_private": 0}}, "name"):
        try:
            path = frappe.utils.get_files_path(basename, is_private=False)
            if os.path.exists(path):
                return open(path, "rb").read()
            return frappe.get_doc("File", {{"file_name": basename, "is_private": 0}}).get_content()
        except Exception:
            frappe.log_error(title="{app}: could not read stamp File")

    pkg = os.path.join(_STATIONERY_DIR, basename)
    if os.path.exists(pkg):
        return open(pkg, "rb").read()
    return None


def _stamp_page_pdf(image_bytes, width_pt, height_pt):
    from PIL import Image

    im = Image.open(io.BytesIO(image_bytes))
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    dpi_x = im.width * 72.0 / width_pt
    dpi_y = im.height * 72.0 / height_pt
    buf = io.BytesIO()
    im.save(buf, format="PDF", resolution=min(dpi_x, dpi_y), dpi=(dpi_x, dpi_y))
    return buf.getvalue()


def stamp_pdf_bytes(pdf_bytes, image_bytes):
    from pypdf import PdfReader, PdfWriter

    base = PdfReader(io.BytesIO(pdf_bytes))
    first = base.pages[0]
    stamp = _stamp_page_pdf(image_bytes, float(first.mediabox.width), float(first.mediabox.height))

    writer = PdfWriter()
    for page in base.pages:
        canvas = PdfReader(io.BytesIO(stamp)).pages[0]
        canvas.merge_page(page, over=True)
        writer.add_page(canvas)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
'''

_SETUP = '''\
import frappe

# print formats that must stay on the stock chrome generator for the wrapper to
# fire (the stamp replaces their letterhead graphics)
_FORMATS = {formats!r}


def after_install():
    for name in _FORMATS:
        if frappe.db.exists("Print Format", name):
            if frappe.db.get_value("Print Format", name, "pdf_generator") != "chrome":
                frappe.db.set_value("Print Format", name, "pdf_generator", "chrome")
    frappe.clear_cache(doctype="Print Format")
'''

_PYPROJECT = '''\
[project]
name = "{app}"
authors = [
    {{ name = "{publisher}", email = "{email}" }},
]
description = "Full-page letterhead stamp behind the {title} PDF."
requires-python = ">=3.10"
readme = "README.md"
dynamic = ["version"]
dependencies = []

[build-system]
requires = ["flit_core >=3.4,<5"]
build-backend = "flit_core.buildapi"

[tool.bench.frappe-dependencies]
frappe = ">=16.0.0,<17.0.0"

[tool.flit.module]
name = "{app}"
'''

_README = '''\
# {title}

Wraps `frappe.utils.pdf.get_chrome_pdf` and paints a full-page letterhead image
behind every page of these print formats:

{format_list}

The formats stay on the stock `pdf_generator = "chrome"`; strip every letterhead
`background-image` from their CSS and force the page transparent
(`html, body, .print-format, .print-format .wrapper {{ background: transparent !important }}`).

## Install

```bash
bench get-app <this repo or path>
bench --site <site> install-app {app}
bench restart
```

Then upload each stamp PNG as a **public File** named exactly as in
`STAMPS` (e.g. `/files/<basename>.png`). A copy in `{app}/stationery/` is a dev
fallback.

## Frappe Cloud

Push to a Git repo, add it in the Bench group (Apps -> Add App), deploy, add to
site, then upload the stamp Files from the site Console.
'''


def do_scaffold(args):
    app = args.app_name
    if not app.replace("_", "").isalnum():
        sys.exit("--app-name must be a valid python identifier (snake_case)")
    title = args.title or app.replace("_", " ").title()
    stamps = {}
    for pair in args.format:
        if "=" not in pair:
            sys.exit(f"--format expects 'Print Format Name=basename.png', got {pair!r}")
        k, v = pair.split("=", 1)
        stamps[k.strip()] = v.strip()
    if not stamps:
        sys.exit("at least one --format is required")

    root = os.path.join(args.scaffold, app)
    pkg = os.path.join(root, app)
    if os.path.exists(root):
        sys.exit(f"{root} already exists")
    os.makedirs(os.path.join(pkg, app))          # inner module dir (modules.txt)
    os.makedirs(os.path.join(pkg, "stationery"))

    fmt = dict(app=app, title=title, publisher=args.publisher, email=args.email,
               stamps=stamps, formats=list(stamps))
    files = {
        os.path.join(root, "pyproject.toml"): _PYPROJECT.format(**fmt),
        os.path.join(root, "README.md"): _README.format(
            format_list="\n".join(f"- `{k}`  ->  `{v}`" for k, v in stamps.items()),
            **fmt),
        os.path.join(root, ".gitignore"): "__pycache__/\n*.pyc\n.DS_Store\n",
        os.path.join(pkg, "__init__.py"): '__version__ = "0.1.0"\n',
        os.path.join(pkg, "hooks.py"): _HOOKS.format(**fmt),
        os.path.join(pkg, "patch.py"): _PATCH.format(**fmt),
        os.path.join(pkg, "chrome_stamp.py"): _CHROME_STAMP.format(**fmt),
        os.path.join(pkg, "setup.py"): _SETUP.format(**fmt),
        os.path.join(pkg, "modules.txt"): title + "\n",
        os.path.join(pkg, "patches.txt"): "",
        os.path.join(pkg, app, "__init__.py"): "",
        os.path.join(pkg, "stationery", ".gitkeep"): "",
    }
    for path, content in files.items():
        with open(path, "w") as f:
            f.write(content)

    print(f"scaffolded {root}")
    print("next:")
    print(f"  1. put the A4 letterhead PNG(s) in {pkg}/stationery/  (and upload as public Files)")
    print(f"  2. cd {root} && git init && git add -A && git commit -m 'first commit'")
    print(f"  3. bench get-app {root} && bench --site <site> install-app {app}")
    print("  4. strip letterhead background-images from the print format CSS; make it transparent")


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stamp", help="PDF to stamp (mode 1)")
    ap.add_argument("--image", help="A4 letterhead PNG (mode 1)")
    ap.add_argument("--out", default="stamped.pdf", help="output PDF (mode 1)")

    ap.add_argument("--scaffold", help="apps/ dir to write the companion app into (mode 2)")
    ap.add_argument("--app-name", help="snake_case app name, e.g. acme_print")
    ap.add_argument("--title", help="human title (default: from app name)")
    ap.add_argument("--format", action="append", default=[],
                    help="'Print Format Name=basename.png' (repeatable)")
    ap.add_argument("--publisher", default="")
    ap.add_argument("--email", default="")

    args = ap.parse_args()
    if args.stamp:
        if not args.image:
            ap.error("--stamp needs --image")
        do_stamp(args)
    elif args.scaffold:
        if not args.app_name:
            ap.error("--scaffold needs --app-name")
        do_scaffold(args)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
