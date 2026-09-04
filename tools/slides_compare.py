"""Diff a reconstructed PPTX against the PDF it was rebuilt from.

PowerPoint exports the pptx to PDF, then pymupdf rasterises both sides, so one
engine draws both pictures and the only differences left are real. Per page it
reports the worst-differing regions and writes a side-by-side crop of each
(original | rebuilt) to look at.

Usage:
    python tools/slides_compare.py in.pdf rebuilt.pptx outdir
        [--pages 1,4,10] [--top 4] [--selfcheck]
"""
import argparse
import os
import sys

import fitz
import numpy as np
from PIL import Image

TARGET_W = 1376          # px; the deck's native raster width
# smoothed per-pixel channel-sum difference that counts. PowerPoint re-encodes
# the background picture on export, which dusts the whole page with ~30-90;
# text that moved or changed size runs 200-700.
DIFF_THRESH = 140
BLUR = 5                 # px; antialiasing differs everywhere, structure does not
MIN_AREA = 900           # px^2; smaller regions are edge noise
GROW = 6                 # px; join the glyphs of one moved line into one region


def pptx_to_pdf(pptx):
    """Export via PowerPoint COM. Returns the pdf path (next to the pptx).

    Known ceiling: PowerPoint JPEG-compresses the page pictures on the way out
    (DCTDecode, at full resolution), whatever the export route -- SaveAs and
    ExportAsFixedFormat at print intent give byte-identical output. That wipes
    1px drawn texture, so a finely dithered area (the mesh on page 1's plate)
    always reads as a difference here even though the picture inside the pptx
    is lossless PNG and pixel-identical to the source. Verify such a region
    against ppt/media/*.png before believing it.
    """
    import win32com.client
    out = os.path.splitext(os.path.abspath(pptx))[0] + ".render.pdf"
    app = win32com.client.Dispatch("PowerPoint.Application")
    pres = app.Presentations.Open(os.path.abspath(pptx), WithWindow=False)
    try:
        pres.SaveAs(out, 32)             # ppSaveAsPDF
    finally:
        pres.Close()
    return out


def render(pdf_path):
    doc = fitz.open(pdf_path)
    zoom = TARGET_W / doc[0].rect.width
    return [np.array(Image.open(fitz.io.BytesIO(
        p.get_pixmap(matrix=fitz.Matrix(zoom, zoom)).tobytes("png")))
        .convert("RGB")) for p in doc]


def diff_regions(a, b, top=6):
    """Worst-differing regions between two page rasters, worst first."""
    from scipy import ndimage
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    d = np.abs(a[:h, :w].astype(int) - b[:h, :w].astype(int)).sum(axis=2)
    mask = ndimage.uniform_filter(d.astype(float), BLUR) > DIFF_THRESH
    labels, _ = ndimage.label(ndimage.binary_dilation(mask, iterations=GROW))
    out = []
    for sl in ndimage.find_objects(labels):
        y, x = sl
        if (y.stop - y.start) * (x.stop - x.start) < MIN_AREA:
            continue
        out.append({"box": (x.start, y.start, x.stop, y.stop),
                    "ink": float(d[sl].sum() / 1e6),
                    "mean": float(d[sl].mean())})
    out.sort(key=lambda r: -r["ink"])
    return out[:top]


def side_by_side(a, b, box, pad=12):
    x0, y0, x1, y1 = box
    h, w = a.shape[:2]
    X0, Y0 = max(x0 - pad, 0), max(y0 - pad, 0)
    X1, Y1 = min(x1 + pad, w), min(y1 + pad, h)
    ca, cb = a[Y0:Y1, X0:X1], b[Y0:Y1, X0:X1]
    gap = np.full((ca.shape[0], 8, 3), 255, np.uint8)
    return Image.fromarray(np.hstack([ca, gap, cb]))


def compare(pdf, pptx, outdir, pages=None, top=4):
    os.makedirs(outdir, exist_ok=True)
    orig, new = render(pdf), render(pptx_to_pdf(pptx))
    report = []
    for n, (a, b) in enumerate(zip(orig, new), 1):
        if pages and n not in pages:
            continue
        regs = diff_regions(a, b, top)
        for k, r in enumerate(regs):
            p = os.path.join(outdir, f"p{n:02d}_r{k}.png")
            side_by_side(a, b, r["box"]).save(p)
            r["crop"] = p
        Image.fromarray(np.vstack([a, np.full((8, a.shape[1], 3), 255, np.uint8),
                                   b[:, :a.shape[1]]])).save(
            os.path.join(outdir, f"p{n:02d}_page.png"))
        report.append({"page": n, "regions": regs})
    return report


def demo():
    a = np.full((200, 300, 3), 255, np.uint8)
    b = a.copy()
    b[50:80, 40:160] = 0                       # one moved line
    r = diff_regions(a, b)
    assert len(r) == 1, r
    x0, y0, x1, y1 = r[0]["box"]
    assert x0 <= 40 and y0 <= 50 and x1 >= 160 and y1 >= 80, r
    b[5:7, 5:7] = 0                            # speck, under MIN_AREA
    assert len(diff_regions(a, b)) == 1
    assert diff_regions(a, a) == []
    print("ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("pptx")
    ap.add_argument("outdir")
    ap.add_argument("--pages", help="1-based, comma separated (default all)")
    ap.add_argument("--top", type=int, default=4)
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return demo()
    pages = {int(p) for p in a.pages.split(",")} if a.pages else None
    for r in compare(a.pdf, a.pptx, a.outdir, pages, a.top):
        worst = ", ".join(f"{x['box']} ink={x['ink']:.1f}" for x in r["regions"])
        print(f"page {r['page']}: {worst or 'clean'}")
    print("crops:", a.outdir)


if __name__ == "__main__":
    sys.exit(main())
