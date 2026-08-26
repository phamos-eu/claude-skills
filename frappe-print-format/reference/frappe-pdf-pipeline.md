# How Frappe turns a Print Format into a PDF

Reference for the v15/v16 Chrome generator. Read before changing margins,
headers, footers or anything that affects pagination.

## The code path

```
Desk "PDF" button
  → /api/method/frappe.utils.print_format.download_pdf
  → frappe.get_print(..., as_pdf=True, pdf_generator="chrome")
  → frappe.utils.pdf.get_chrome_pdf(...)          # utils/pdf.py
  → frappe.utils.pdf_generator.browser            # headless Chrome printToPDF
```

To reproduce it exactly from a script, render the format's Jinja yourself and
wrap it in `.print-format`:

```python
body = render_template(pf.html, {"doc": doc})
html = f'<div class="print-format"><style>{pf.css}</style>{body}</div>'
pdf  = get_chrome_pdf("x", html, {}, None, pdf_generator="chrome")
```

Anything you verify only in the desk preview or the browser's print dialog is
not verified. Several failure modes (gotcha 2, gotcha 4) appear in exactly one
of the three paths.

## Page margins

`get_print_format_styles` (in `utils/pdf.py`) walks the format's CSS with
cssutils looking for a literal `.print-format { }` rule and reads the
**longhand** properties `margin-top`, `margin-right`, `margin-bottom`,
`margin-left`. These become Chrome `printToPDF` options.

- A shorthand `margin: 0` is **not expanded** and therefore not seen → Frappe
  applies its 15mm default on all sides.
- `@page` margins are ignored by the generator (Chrome's options win), so
  `@page:first { margin: ... }` cannot give page 1 different margins.
- `.print-format { margin-bottom: Xmm }` does apply a bottom margin on every
  page **without** re-shifting the top, which stays governed by the header band.

Full-bleed exact layouts therefore need:

```css
.print-format { margin-top:0mm; margin-right:0mm; margin-bottom:0mm; margin-left:0mm;
                min-height:0; padding:0; max-width:none; }
@page { size: A4; margin: 0; }
```

## Repeating header / footer

The generator looks for elements with **id** `header-html` and `footer-html`:

```python
soup.find(id="header-html")
soup.find(id="footer-html")
```

Each is rendered as a Chrome repeating page header/footer — it prints on
**every** page — and its measured height is reserved as the body's top/bottom
page margin.

Height measurement (`get_element_height` in `pdf_generator/page.py`) measures
the `.wrapper` of Frappe's `chrome_pdf_header_footer.html` template, not your
element. That template contributes:

- `.wrapper { padding: 1mm 0 }` + `body { padding-top: 1mm }` ≈ **2.2mm**
- bootstrap `address { margin-bottom: 1rem }` ≈ **4.2mm** if you use `<address>`

So: put the real height on an inner div (`.doc-header`), reset
`.doc-header address { margin: 0 }`, and empirically check what got reserved by
measuring where page-1 content actually lands in the output PDF. A worked
example: a 55.34mm `.doc-header` reserved ~57.58mm.

Consequences to plan around:

- Header height = top margin for **all** pages. There is no page-2-only spacing.
- Removing `#footer-html` makes Frappe apply its default 15mm bottom margin
  again (unless you set `.print-format { margin-bottom }`), and gives the body
  back the whole footer band per page — which can pull a 2-page doc back to 1.
- The header renders as its own mini-page with no base URL: images must use
  `{{ frappe.utils.get_url() }}/files/...`.

## print_designer's generator (v15, and the same architecture upstream)

`print_designer.pdf_generator.browser.Browser` does **not** drive Chrome page
margins for the header and footer. It renders three documents and
`pdf_merge.PDFTransformer` stacks them into each final page:

```
header PDF   paperHeight = measured .wrapper height of #header-html
body   PDF   paperHeight = page height − header total − footer total
footer PDF   paperHeight = measured .wrapper height of #footer-html
```

Consequences that drive the whole design:

- **A `position: fixed` layer in the body can only paint inside the body band.**
  A full-bleed graphic must be cut in two: the body slice in a fixed layer, the
  bottom slice inside `#footer-html`, each offset by its band origin. Aligned
  correctly the seam is invisible.
- **A body page is painted slightly short of its own mediabox**, so a graphic
  split across the body/footer seam shows a white hairline (0.0–0.5mm) at the
  join. Nothing can paint that strip — it belongs to the body page, and the
  footer cannot paint above its band. Overflowing the fixed layer, removing its
  clip, a canvas background and overlapping the footer slice all fail. The
  shortfall is **quantised against page-height and the band heights**, so the
  fix is to sweep those two numbers and pick a combination that measures zero.
  Expect to trade a few tenths of a millimetre of sheet height for it, and to
  re-derive the footer's internal offsets afterwards.
- **Every band height is rounded up**, so a nominal A4 comes out around
  210.23 x 297.77mm. `page-width` and `page-height` declared on the
  `.print-format` rule are read by `_parse_pdf_options_from_html` and are the
  knob for correcting this — but they quantize to whole points (~0.35mm), so a
  small nudge can jump a whole step. Calibrate by measuring, not by arithmetic.
- **`_parse_pdf_options_from_html` runs after** the backwards-compatibility code
  that forces `margin-top`/`margin-bottom` to 15mm when there is no header or
  footer element, so your longhand `.print-format` margins still win.
- **Setting a large `.print-format` margin-bottom while using `#footer-html`
  crashes** with `invalid print parameters: content area is empty` — the footer
  page is only as tall as the band, and your margin eats all of it.
- **Page numbers work through wkhtmltopdf-style spans**: `<span class="page">`
  and `<span class="topage">` (also `date`, `isodate`, `time`), filled by
  `update_page_no.js`. Their presence is what makes the band "dynamic".
- A dynamic footer document ends up holding **one `.wrapper` per page**, so
  `.wrapper:last-child` and `.wrapper:first-child` select the final and first
  page — the only clean way to show a "continued overleaf" notice everywhere but
  the last page.

## Putting the bands in a Letter Head

A **custom** Jinja format is not auto-wrapped with the letterhead, but printview
renders `Letter Head.content` and `.footer` (as Jinja, with `doc` in context) and
passes them to the template as `{{ letter_head }}` and `{{ footer }}`. So the
repeating bands can live in the Letter Head doctype while the format keeps only
the pickup points:

```jinja
<div id="header-html">{% if letter_head %}{{ letter_head }}{% else %}<div class="doc-header"></div>{% endif %}</div>
<div id="footer-html">{% if footer %}{{ footer }}{% else %}<div class="doc-footer"></div>{% endif %}</div>
```

The fallbacks matter: printed with **No Letterhead**, both variables are empty
and the bands would collapse, changing every coordinate on the sheet. Emitting
empty wrappers keeps the geometry.

Keep the band **coordinates** in the print format's CSS, not the Letter Head —
the format's `<style>` tag is what the generator copies into the header/footer
mini-pages, so the classes resolve there.

Two things bite in practice:

- **`no_letterhead=1` silently removes the whole band.** The desk print view
  seeds its Letter Head selector from the document's `letter_head` field, else
  the `is_default` Letter Head — so a print view opened before the Letter Head
  existed, or a document whose field is blank on a site with no default, exports
  without it. Set the Company's `default_letter_head` so new documents carry it.
- **A full-bleed graphic split across the bands is cut** whenever the letterhead
  is off, because the footer slice disappears. Put the graphic in the fallback
  too, so only the imprint depends on the letterhead.

`get_letter_head` resolves, in order: an explicit `letterhead` argument, the
document's own `letter_head` field, then the Letter Head flagged `is_default`.
The Print Format's `letter_head` field is not part of that chain, so set
`is_default` (or the field on the document) if it must apply automatically.

Set `source` and `footer_source` to `"HTML"`; `content` and `footer` are HTML
Editor fields and store raw markup unmangled. **No HTML comments inside them** —
see gotcha 17.

## Where print formats live

A custom-Jinja print format (`custom_format=1`, `standard="No"`) is a **row in
the `Print Format` doctype** — nothing on disk, so grepping `apps/` finds
nothing. Read and write it with `frappe.get_doc("Print Format", name)` and its
`.html` / `.css` fields. Dump them to files before editing, and re-dump after
any change made through the UI.

On Frappe Cloud there is no bench shell: use **Desk > System Console** (Python,
runs under `safe_exec`, tick Commit for writes) or **Dev Tools > SQL Playground**
in Read Write mode.

## Units

- 1 pt = 25.4/72 mm ≈ 0.352778 mm; 1 mm = 72/25.4 pt ≈ 2.834646 pt
- A4 = 595.28 × 841.89 pt = 210 × 297 mm
- Use `296mm` for the sheet height; 297 rounds onto a second page.
- PyMuPDF coordinates are pt from the **top-left**, which matches CSS `top`
  directly — no flipping needed.
