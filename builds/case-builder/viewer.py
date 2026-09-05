"""Render one PDF page, image or video keyframe to PNG. One path for every format. Cached on disk."""
import io, pathlib
from extract import keyframe_path, load_image

CACHE = pathlib.Path(__file__).resolve().parent / "data" / "cache"


def page_count(asset):
    if asset["kind"] != "pdf":
        return 1
    import fitz
    with fitz.open(asset["path"]) as doc:
        return doc.page_count


def render(asset, page_index=0):
    """-> PNG bytes of the page/image/frame, normalised the same way the locator boxes were."""
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{asset['id']}_p{page_index}.png"
    if out.exists():
        return out.read_bytes()
    if asset["kind"] == "pdf":
        import fitz
        with fitz.open(asset["path"]) as doc:
            page_index = max(0, min(page_index, doc.page_count - 1))
            data = doc[page_index].get_pixmap(dpi=110).tobytes("png")
    else:
        src = keyframe_path(asset["id"], asset["path"]) if asset["kind"] == "video" else asset["path"]
        im = load_image(src)
        im.thumbnail((1600, 1600))
        buf = io.BytesIO()
        im.save(buf, "PNG")
        data = buf.getvalue()
    out.write_bytes(data)
    return data
