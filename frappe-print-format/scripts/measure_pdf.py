#!/usr/bin/env python
"""Dump every positioned element of a reference PDF in pt and mm.

The output is the spec for an exact-match print format: text top = line bbox y0,
font size stays in pt, coordinates are top-left origin (same as CSS `top`/`left`).

    ./env/bin/python measure_pdf.py sample.pdf --page 0 --extract-images out/
"""
import argparse
import os

import fitz

PT2MM = 25.4 / 72


def mm(v, nd=2):
    return round(v * PT2MM, nd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--extract-images", metavar="DIR", help="save embedded images here")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    print(f"PAGES: {doc.page_count}")
    page = doc[args.page]
    r = page.rect
    print(f"PAGE {args.page} rect {r} -> {mm(r.width,1)} x {mm(r.height,1)} mm\n")

    print("===== TEXT LINES =====")
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for line in b["lines"]:
            txt = "".join(s["text"] for s in line["spans"]).strip()
            if not txt:
                continue
            x0, y0, x1, y1 = line["bbox"]
            sp = line["spans"][0]
            print(
                f"L={mm(x0):7.2f} T={mm(y0):7.2f} R={mm(x1):7.2f} B={mm(y1):7.2f}mm "
                f"| sz={sp['size']:.1f}pt {sp['font'][:22]:22s} | {txt[:70]}"
            )

    print("\n===== DRAWINGS (rules / rects) =====")
    for dr in page.get_drawings():
        w, kind = dr.get("width"), dr.get("type")
        for it in dr["items"]:
            if it[0] == "l":
                p1, p2 = it[1], it[2]
                vert = abs(p1.x - p2.x) < 0.5
                print(
                    f"LINE {'V' if vert else 'H'} y={mm(p1.y):7.2f} "
                    f"x {mm(p1.x):7.2f}->{mm(p2.x):7.2f}mm  w={w} type={kind}"
                )
            elif it[0] == "re":
                rr = it[1]
                print(
                    f"RECT L={mm(rr.x0):7.2f} T={mm(rr.y0):7.2f} R={mm(rr.x1):7.2f} "
                    f"B={mm(rr.y1):7.2f}mm h={mm(rr.y1-rr.y0):.2f}mm "
                    f"w={w} type={kind} fill={dr.get('fill')}"
                )

    print("\n===== IMAGES =====")
    for i, img in enumerate(page.get_images(full=True)):
        xref = img[0]
        for rc in page.get_image_rects(xref):
            print(
                f"xref={xref} L={mm(rc.x0):7.2f} T={mm(rc.y0):7.2f} "
                f"R={mm(rc.x1):7.2f} B={mm(rc.y1):7.2f}mm "
                f"({rc.width:.0f}x{rc.height:.0f}pt)"
            )
        if args.extract_images:
            os.makedirs(args.extract_images, exist_ok=True)
            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha >= 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            fn = os.path.join(args.extract_images, f"img_{i}_xref{xref}.png")
            pix.save(fn)
            print(f"  saved {fn} ({pix.width}x{pix.height})")

    doc.close()


if __name__ == "__main__":
    main()
