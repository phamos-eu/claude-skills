#!/usr/bin/env python
"""Compare a rendered print format against the reference PDF.

Two measures:
  * per-word position shift in mm (matched by text, in reading order)
  * pixel diff of the rendered pages

"Pixel exact" means max word shift ~0.0mm and a near-zero diff pixel count.

    ./env/bin/python compare.py reference.pdf /tmp/pf_render.pdf --page 0 --dpi 150
"""
import argparse

import fitz

PT2MM = 25.4 / 72


def words(page):
    return [w for w in page.get_text("words") if w[4].strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference")
    ap.add_argument("candidate")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--tol", type=float, default=0.5, help="mm, report shifts above this")
    ap.add_argument("--save-diff", metavar="PNG")
    args = ap.parse_args()

    a = fitz.open(args.reference)[args.page]
    b = fitz.open(args.candidate)[args.page]

    wa, wb = words(a), words(b)
    print(f"words: reference={len(wa)} candidate={len(wb)}")

    # match by text occurrence order so duplicated words still line up
    seen = {}
    index_b = {}
    for w in wb:
        k = (w[4], seen.get(w[4], 0))
        seen[w[4]] = seen.get(w[4], 0) + 1
        index_b[k] = w

    seen.clear()
    shifts, missing = [], []
    for w in wa:
        k = (w[4], seen.get(w[4], 0))
        seen[w[4]] = seen.get(w[4], 0) + 1
        m = index_b.get(k)
        if not m:
            missing.append(w[4])
            continue
        dx = (m[0] - w[0]) * PT2MM
        dy = (m[1] - w[1]) * PT2MM
        shifts.append((max(abs(dx), abs(dy)), dx, dy, w[4], w[1] * PT2MM))

    if missing:
        print(f"MISSING from candidate ({len(missing)}): {missing[:15]}")
    if shifts:
        shifts.sort(reverse=True)
        print(f"max shift = {shifts[0][0]:.3f}mm")
        over = [s for s in shifts if s[0] > args.tol]
        print(f"words shifted > {args.tol}mm: {len(over)}")
        for _, dx, dy, txt, top in over[:25]:
            print(f"  {txt[:30]:30s} refTop={top:7.2f}mm  dx={dx:+.2f} dy={dy:+.2f}mm")

    pa = a.get_pixmap(dpi=args.dpi)
    pb = b.get_pixmap(dpi=args.dpi)
    if (pa.width, pa.height) != (pb.width, pb.height):
        print(f"page size differs: {pa.width}x{pa.height} vs {pb.width}x{pb.height}")
        return
    try:
        from PIL import Image, ImageChops
    except ImportError:
        print("pillow not installed — skipping pixel diff")
        return
    ia = Image.frombytes("RGB", (pa.width, pa.height), pa.samples)
    ib = Image.frombytes("RGB", (pb.width, pb.height), pb.samples)
    diff = ImageChops.difference(ia, ib).convert("L")
    n = sum(1 for p in diff.getdata() if p > 32)
    total = pa.width * pa.height
    print(f"pixel diff: {n}/{total} ({100.0*n/total:.4f}%) bbox={diff.getbbox()}")
    if args.save_diff:
        diff.save(args.save_diff)
        print(f"saved {args.save_diff}")


if __name__ == "__main__":
    main()
