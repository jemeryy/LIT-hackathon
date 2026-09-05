"""Parse an asset to text + normalised word boxes, and find a quote in it.
Locators are [left, top, right, bottom] in 0-1 of the page/image/frame."""
import pathlib, re, subprocess, unicodedata

_PDF_WORD_SPACING = {"x_tolerance_ratio": 0.15}   # from fara: stops glued words
VIDEO_KEYFRAME_S = 72
MIN_RUN = 4                                      # consecutive tokens a match needs
CACHE = pathlib.Path(__file__).resolve().parent / "data" / "cache"


def _norm(tok):
    t = unicodedata.normalize("NFKC", tok).lower()
    return re.sub(r"[^\w]", "", t)


def _pdf_pages(path):
    import pdfplumber
    pages = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            W, H = float(page.width), float(page.height)
            words = [{"text": w["text"], "box": [w["x0"] / W, w["top"] / H, w["x1"] / W, w["bottom"] / H],
                      "line": round(w["top"])}
                     for w in page.extract_words(use_text_flow=True, **_PDF_WORD_SPACING)]
            pages.append({"page_index": i, "words": words, "text": page.extract_text(**_PDF_WORD_SPACING) or ""})
    return pages


def load_image(path):
    from PIL import Image, ImageOps
    im = Image.open(path)
    return ImageOps.exif_transpose(im).convert("RGB")


def _image_page(im, page_index=0):
    import pytesseract
    W, H = im.size
    d = pytesseract.image_to_data(im, output_type=pytesseract.Output.DICT)
    words = []
    for i, txt in enumerate(d["text"]):
        if not txt.strip():
            continue
        x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
        words.append({"text": txt, "box": [x / W, y / H, (x + w) / W, (y + h) / H],
                      "line": (d["block_num"][i], d["par_num"][i], d["line_num"][i])})
    return {"page_index": page_index, "words": words, "text": " ".join(w["text"] for w in words)}


def keyframe_path(asset_id, path):
    """Extract (once) and return the PNG of the video frame at VIDEO_KEYFRAME_S."""
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{asset_id}_frame.png"
    if not out.exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(VIDEO_KEYFRAME_S), "-i", str(path),
                        "-frames:v", "1", str(out)], check=True)
    return out


def parse(asset):
    """asset: {id, kind, path}. Returns {pages: [...], text}."""
    kind, path = asset["kind"], asset["path"]
    if kind == "pdf":
        pages = _pdf_pages(path)
    elif kind == "image":
        pages = [_image_page(load_image(path))]
    elif kind == "video":
        pages = [_image_page(load_image(keyframe_path(asset["id"], path)))]
    else:
        raise ValueError(f"unsupported kind {kind}")
    return {"pages": pages, "text": "\n\n".join(p["text"] for p in pages)}


def _boxes_by_line(words):
    lines = {}
    for w in words:
        b = lines.setdefault(w["line"], list(w["box"]))
        b[0], b[1] = min(b[0], w["box"][0]), min(b[1], w["box"][1])
        b[2], b[3] = max(b[2], w["box"][2]), max(b[3], w["box"][3])
    return [[round(v, 4) for v in b] for b in lines.values()]


def locate(parsed, quote, asset_id):
    """Find the quote as a run of consecutive tokens. Returns a locator or None.
    Tries the whole quote first, then the longest sub-run of >= MIN_RUN tokens (tolerates OCR slips)."""
    q = [t for t in (_norm(x) for x in quote.split()) if t]
    if not q:
        return None
    floor = min(len(q), MIN_RUN)
    pages = [(pg["page_index"], [w for w in pg["words"] if _norm(w["text"])]) for pg in parsed["pages"]]
    pages = [(pi, ws, [_norm(w["text"]) for w in ws]) for pi, ws in pages]
    for run in range(len(q), floor - 1, -1):          # longest run first, across every page
        for qs in range(0, len(q) - run + 1):
            sub = q[qs:qs + run]
            for page_index, words, toks in pages:
                for i in range(0, len(toks) - run + 1):
                    if toks[i:i + run] == sub:
                        return {"asset_id": asset_id, "page_index": page_index,
                                "boxes": _boxes_by_line(words[i:i + run]), "coord_space": "normalized",
                                "matched_tokens": run, "quote_tokens": len(q)}
    return None


if __name__ == "__main__":   # self-check on the sample agreement
    import json
    root = pathlib.Path(__file__).resolve().parent
    fx = json.loads((root / "content/fixtures.json").read_text(encoding="utf-8"))["files"]
    parsed = parse({"id": "E1", "kind": "pdf", "path": str(root / "sample/pack/Tenancy_Agreement_2025.pdf")})
    for f in fx["Tenancy_Agreement_2025.pdf"]["facts"]:
        loc = locate(parsed, f["quote"], "E1")
        print(f["where"], loc)
        assert loc and loc["boxes"], f"quote not found: {f['quote']}"
    assert locate(parsed, fx["Tenancy_Agreement_2025.pdf"]["facts"][0]["quote"], "E1")["page_index"] == 1
    print("E1 locator ok")
