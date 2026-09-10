# Full-page letterhead stamp — killing the body/footer seam for good

## When to use this (and when not)

This is a **last-resort escape hatch**, not the normal way to do a letterhead.
Build the format in HTML/CSS first (see `SKILL.md`); keep letterhead graphics as
`background-image` on `#header-html` / `.print-format` / a fixed body layer.

Use the stamp **only** when **all** of these hold:

- a full-bleed graphic (corner wedge, framed border, side bar) must reach the
  page edge on **every** page, so it is drawn in both the body layer and the
  footer band and gets **split at the body↔footer PDF-merge join**;
- the document can run to more than one page (the seam only shows where the body
  actually meets the footer band on a continuation page);
- the seam does not close by sweeping the band heights
  (`reference/frappe-pdf-pipeline.md`) — and in particular it **looks fine on
  your Mac but breaks on the Linux / Frappe-Cloud server**, because the seam
  position is quantised against the measured band heights and macOS (CoreText)
  vs. Linux `chrome-headless-shell` (fontconfig/freetype) round text metrics
  differently.

If the graphic is header-only or footer-only, or the doc is always one page, or
tuning closes the seam — don't do any of this.

`reference/frappe-pdf-pipeline.md` explains why the split is unavoidable in HTML.
Sweeping the band heights (as that file suggests) only narrows it. This approach
removes it: **let Chrome render the page with no letterhead graphics at all, then
paint the whole letterhead as one image behind every finished page.** One image
object per page ⇒ no seam is possible, and the output is identical on every OS
and Chromium build.

## Architecture: wrap `get_chrome_pdf`, don't add a `pdf_generator` hook

A companion app (`<something>_print`) does exactly one thing: it monkey-wraps
`frappe.utils.pdf.get_chrome_pdf`. After the stock generator returns the PDF for
a registered print format, it draws the letterhead image behind each page.

Decisions that matter, learned the hard way:

- **Wrap the function, don't register a second `pdf_generator` hook.** The hook
  loop calls `frappe.utils.pdf.get_chrome_pdf` *first*; for a format on
  `pdf_generator = "chrome"` it returns immediately and your hook never runs.
  Keeping the format on stock `"chrome"` and wrapping the callee is the only
  thing that reliably intercepts the desk button, `frappe.get_print`,
  `attach_print` (email) and background jobs alike.
- **Never call `get_chrome_pdf` a second time inside the same request.**
  Re-entering the chrome pipeline within one request intermittently corrupts the
  page-number footer clones (footer prints twice, page numbers off by one). The
  wrapper calls the original **once** and post-processes its bytes.
- **Stamp with Pillow + pypdf, NOT PyMuPDF.** `fitz` is not a dependency of
  frappe / erpnext / print_designer — it is absent on a stock bench and on
  Frappe Cloud. Pillow and pypdf are always present.
- **Merge the content *over* a letterhead canvas**, not the letterhead *under*
  the content. `stamp_page.merge_page(content_page, over=True)` keeps the
  content page (its footer form-XObjects, page-number clones) referenced, never
  rewritten. `content_page.merge_page(stamp, over=False)` rewrites the content
  stream and garbles the merged footer.
- **The chrome body page is opaque white.** For the letterhead to show, the
  print format CSS must force the page transparent:
  `html, body, .print-format, .print-format .wrapper, .sheet { background: transparent !important }`.
- **Load the letterhead image from a public File**, named exactly
  `<basename>.png` (so `/files/<basename>.png`), installed like the web fonts.
  A copy bundled in the app under `stationery/` is a dev fallback. The File is
  what makes it swappable without redeploying the app, and dodges any
  package-data-not-in-wheel surprise.
- **The image itself:** extract the existing letterhead frame from the reference
  PDF with `scripts/measure_pdf.py ref.pdf --extract-images out/` — it is usually
  a single near-full-page background image (aspect ~ A4, 0.707); pick that one.
  It replaces every `background-image` you'd otherwise put in `#header-html` /
  `.print-format` / a fixed body layer, so strip those from the format CSS. If
  the reference has no such image (vector letterhead), rasterise page 1 of a
  blank instance at ~300 dpi.

## Wiring the wrapper so it actually runs

`frappe.get_hooks` serves a **cached** dict on a warm site and does not re-import
`hooks.py`, so a module-level `apply()` in `hooks.py` only covers a cold worker.
Register it on the request/job entry points too:

```python
# hooks.py
from <app>.patch import apply as _apply_stamp_patch
_apply_stamp_patch()                                   # cold worker
before_request = ["<app>.patch.before_request"]        # warm web worker
before_job     = ["<app>.patch.before_job"]            # warm background worker
```

`apply()` is idempotent (flag on the wrapped function).

## Frappe Cloud

1. App must be in a **Git repo**. `pyproject.toml` needs
   `[tool.bench.frappe-dependencies]` with `frappe = ">=16.0.0,<17.0.0"` or FC
   refuses it ("Could not find a compatible Frappe version").
2. Bench group → **Apps** → **Add App** → from the repo/branch → **Deploy** →
   **Add to site**.
3. Site **Console**: run the installer that uploads the letterhead PNG + fonts as
   public Files and sets the format to `pdf_generator = "chrome"`.
4. Verify from the Console (no `fitz` there — count images with pypdf):
   ```python
   from pypdf import PdfReader; import io
   from frappe.translate import print_language
   with print_language("de"):
       pdf = frappe.get_print("<DocType>", "<name>", "<Print Format>",
                              as_pdf=True, pdf_generator="chrome")
   print([len(p.images) for p in PdfReader(io.BytesIO(pdf)).pages])   # [1, 1, ...] == stamped
   ```

## Scaffolding

`scripts/stamp_letterhead.py`:

- `--stamp in.pdf --image lh.png --out out.pdf` — stamp any PDF once, no app
  needed (use it to prove the image + geometry before committing to the app).
- `--scaffold <bench>/apps --app-name acme_print --format "ACME Invoice=acme-invoice-a4.png"`
  — writes a complete, installable companion app (hooks, patch, chrome_stamp,
  setup, pyproject with FC deps, README). Drop the PNG into its `stationery/`,
  `bench get-app` + `install-app`, done.

The `stamp_pdf_bytes()` in that script is the exact function the generated app
uses — import it directly in a test.
