---
name: frappe-print-format
description: Build a Frappe/ERPNext Print Format that pixel-matches a reference PDF, by extracting exact mm coordinates from the source with PyMuPDF and verifying every change through the real Chrome PDF pipeline. Use whenever the user asks to create, clone, or fix a print format / PDF layout for a Frappe site (invoice, contract, quotation, letterhead), especially when they supply a sample PDF to match, or when a print format renders with wrong margins, clipping, blank pages, bad pagination, or a full-bleed letterhead graphic that shows a hairline / seam at a corner (often fine locally, broken on the Linux/Frappe-Cloud server).
---

# Frappe print formats, measured against a reference PDF

Build the format as an **absolutely-positioned A4 canvas** whose every coordinate
comes from measuring the reference PDF — not from eyeballing a preview. Then
verify each change through the **same code path the PDF button uses**, never the
browser preview alone.

## Workflow

1. **Locate the bench and site.** Need the bench root (has `env/`, `sites/`,
   `apps/`) and the site name. Install the measurement libs into the bench env
   once: `./env/bin/pip install pymupdf pillow`.
2. **Measure the reference PDF** — `scripts/measure_pdf.py`. Dumps every text
   line, ruling line, rect and image with x/y in both pt and mm. Text top =
   `y0` of the line bbox; font size stays in pt. This output is the spec.
3. **Draft the format** as HTML + CSS (see Layout below), keep both in files in
   the scratchpad, and push them into the DB with `scripts/apply_pf.py`.
4. **Verify** with `scripts/render_pf.py` (renders through
   `frappe.utils.pdf.get_chrome_pdf`) and `scripts/compare.py` (per-word mm
   shift vs. the original + pixel diff). Iterate until the shift is ~0.
5. **Test pagination** before declaring done: render the same format against a
   short doc, a typical doc, and an artificially grown doc (duplicate the long
   text field) and assert page count, that nothing overlaps a rule, and that
   footer/signature blocks land where intended.

Work one section at a time when converting static text to dynamic fields, and
re-verify after each — that cadence catches a broken Jinja expression while it's
still the only change.

## Layout that works

- Single `.sheet` div, `210mm × 296mm` (296, not 297 — 297 rounds onto a second
  page), `position: relative`, `@page { size: A4; margin: 0 }`.
- Every element `position: absolute` with `top`/`left` in mm from the measured
  values. Put **all** coordinates in the CSS field as named classes
  (`.sender-name`, `.rule-1`, `.party-*`) — no inline styles, so moving an
  element is a one-line CSS edit.
- Semantic wrappers (`<header>`, `<section>`) are non-positioned and contain
  only absolute children, so they collapse to 0 height and never shift anything.
- Content that must grow (line-item tables, terms, notes) goes in a **flowing**
  region after the fixed zone — normal flow, `position: static` — so it
  paginates instead of overlapping. Give the fixed zone
  `display: flow-root` (see gotcha 2) and an explicit `height` in mm.
- `break-inside: avoid` on paragraphs, cost bands and signature blocks.

Read `reference/frappe-pdf-pipeline.md` before touching margins, headers or
footers — the Chrome generator's rules are unintuitive and most layout bugs
trace back to them.

## Know your generator first

`frappe.get_print(..., as_pdf=True, pdf_generator=...)` is the path the desk PDF
button takes on both versions, but what sits behind it differs:

- **v16 core** ships the chrome generator (`frappe/utils/pdf_generator/`).
- **v15 core is wkhtmltopdf only.** The chrome generator comes from the
  **print_designer** app, which registers the `pdf_generator` hook and adds a
  `pdf_generator` field on Print Format — set it to `chrome`. If the app is not
  installed on the site, you are targeting 2012-era WebKit: no flexbox, weak
  page-break control. Check `frappe.get_installed_apps()` before designing.
- print_designer's generator renders **three separate PDFs — header band, body
  band, footer band — and stacks them**. See `reference/frappe-pdf-pipeline.md`;
  it changes what `position: fixed` can reach and what the sheet measures.

## Escape hatch: stamp the letterhead as one image (only for a body↔footer seam)

**This is not the default.** Build the format in HTML/CSS as above; keep
letterhead graphics as `background-image` on `#header-html`, `.print-format`, or
a `position: fixed` body layer. Reach for the stamp **only** when a full-bleed
graphic (corner wedge, framed border, side bar) must touch the page edge on
*every* page and therefore gets **split at the body↔footer PDF-merge join** —
leaving a white hairline that is quantised against the band heights, so it looks
clean on macOS and breaks on the Linux / Frappe-Cloud server, and sweeping the
band heights (per `reference/frappe-pdf-pipeline.md`) only narrows it.

If the graphic lives entirely within one band (header-only logo, footer-only
bar), or the doc is always one page, or the seam closes with band-height
tuning — do none of this.

When it does apply: stop drawing that graphic in HTML and **stamp the whole
letterhead as one full-page image behind every finished page**, via a small
companion app that wraps `get_chrome_pdf`. Full recipe, trade-offs and Frappe
Cloud steps in `reference/letterhead-stamp.md`; `scripts/stamp_letterhead.py`
stamps a one-off PDF and scaffolds the app.

## The gotchas that cost the most time

1. **Shorthand `margin: 0` is ignored.** Frappe parses page margins only from
   **longhand** `margin-top/right/bottom/left` on a literal `.print-format {}`
   rule. A shorthand falls back to the 15mm default → layout shifted +15mm,
   clipped on the right, spilling to page 2. Declare all four longhands.
2. **A fixed zone needs `display: flow-root`.** Bootstrap adds a descendant
   top-margin that exists only in the live print wrapper; without a block
   formatting context it margin-collapses through and shoves the whole exact-mm
   layout ~8mm down — visible in the real PDF but not in a direct
   `get_chrome_pdf` call.
3. **Header/footer heights are not what you set.** `get_element_height` measures
   Frappe's `chrome_pdf_header_footer.html` `.wrapper`, which adds ~2.2mm
   padding, and bootstrap's `address { margin-bottom: 1rem }` adds ~4.2mm more.
   Set the height on your own inner `.doc-header` and reset
   `.doc-header address { margin: 0 }`, then measure what actually got reserved.
4. **The header→body gap is uniform across pages.** Header height *is* the top
   margin for every page. You cannot add page-2-only space; the `transform:
   translateY` pull-up trick looks right in the browser preview and **clips** in
   the real PDF.
5. **You cannot pin a block to the bottom of the last page.** Flexbox
   `margin-top:auto` and `min-height:100vh` both fail across pagination. Options
   are: let it flow (fine for 1-page docs), make it a repeating footer (prints on
   every page), or switch to Print Designer, which has a real last-page footer.
6. **Images in `#header-html` need an absolute URL** — the header mini-page has
   no base URL, so `/files/x.png` 404s. Use
   `{{ frappe.utils.get_url() }}/files/x.png`.
7. **Never build the format HTML with Python f-strings** — they eat Jinja's
   `{{ }}` into `{ }`. Write the HTML to a file and read it.
8. **Full-page browser print** (`/printview` → Ctrl+P) renders an
   `.action-banner` that pushes the sheet to a second page. Suppress it in the
   format CSS for all media:
   `.action-banner, .print-hide { display: none !important }`.
9. Custom Jinja formats do **not** get the letterhead auto-injected — build the
   letterhead into the HTML yourself; the `letter_head` field is inert.
10. Print Jinja does **not** autoescape, so a Text Editor field renders its raw
    HTML from `{{ doc.field }}` with no `| safe`. Normalize Quill's wrapper:
    `.terms .ql-editor { padding: 0; height: auto; overflow: visible }`.
11. **Bootstrap outranks you inside the print wrapper.** `.print-format td`
    beats a plain `.items td`, so cell padding silently returns. Use
    `!important` on padding in print tables.
12. **A `position: fixed` layer must not be one hair taller than its page** —
    Chrome paints the overflowing slice again at the top of every following
    page. Use `inset: 0` and let it size itself; never an explicit height.
13. **Tables paint an opaque background** and will hide a full-bleed graphic:
    `.items, .items tr, .items td { background: transparent !important }`.
14. **Group what must stay together in one wrapper.** A totals block built from
    `<tr>`s splits across pages even with `break-inside: avoid` on each row.
    Move it into its own table inside a `break-inside: avoid` div together with
    whatever must follow it.
15. `frappe.parse_json` is **not** in the Jinja sandbox; `json.loads` is.
16. The print language reaches the template only when the caller wraps the
    render in `frappe.translate.print_language(...)` — the desk PDF button does,
    a bare `get_print` does not, so `_()` silently returns English in scripts.
17. **One `<tr>` per line staggers the leading.** Chrome rounds every row height
    to whole device pixels independently, so a 3.81mm line-height comes out as
    an alternating 3.70 / 3.97. Put each column's lines in a single cell as a
    block of `<div>`s and the leading stays uniform.
18. **Never put an HTML comment in a Letter Head's header/footer.** The
    generator stringifies BeautifulSoup nodes, which drops the `<!--` `-->`
    delimiters, so the comment prints as visible text *and* inflates the
    measured band height. Keep the commentary in the print format's CSS.
19. **PyMuPDF (`fitz`) is a measurement tool, not a runtime dependency.** It is
    *not* installed by frappe/erpnext/print_designer, so it is absent on a
    stock bench and on Frappe Cloud. Use it freely in the `scripts/` here, but
    any code that ships in an app (a `pdf_generator` hook, a `get_chrome_pdf`
    wrapper) must stamp/merge with **Pillow + pypdf** only.
20. **Do not call `get_chrome_pdf` twice inside one request.** Re-entering the
    chrome pipeline (e.g. a wrapper that renders once to inspect, once to
    return) intermittently corrupts the page-number footer clones — footer
    prints twice, numbers off by one. Call it once, post-process the bytes.

## Scripts

All take `--bench`, and are run with the bench's python (`./env/bin/python`).

| script | purpose |
| --- | --- |
| `scripts/measure_pdf.py` | Dump text lines, rules, rects, images from the reference PDF in pt + mm; optionally extract embedded images. |
| `scripts/apply_pf.py` | Write HTML/CSS files into a Print Format doc (creates it if missing) and commit. |
| `scripts/render_pf.py` | Render a Print Format against a real doc through `get_chrome_pdf`, save PDF + page PNGs, report page count and content bottom. |
| `scripts/compare.py` | Per-word mm shift between two PDFs + pixel diff of rendered pages. |
| `scripts/paginate_test.py` | Grow a long text field by N paragraphs and report page count / which page a marker word lands on. |
| `scripts/stamp_letterhead.py` | Paint a full-page letterhead image behind every page of a PDF (Pillow + pypdf); `--stamp` for a one-off, `--scaffold` to generate the companion wrapper app. See `reference/letterhead-stamp.md`. |
