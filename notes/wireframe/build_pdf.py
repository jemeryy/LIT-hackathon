# Renders the wireframe artboards to one landscape PDF, one screen per page.
import json, pathlib, re
from playwright.sync_api import sync_playwright

here = pathlib.Path(__file__).parent
canvas = json.loads((here / "canvas.json").read_text(encoding="utf-8"))
W, H = 1280, 820
pages = []
style = ""
for b in canvas["artboards"]:
    src = (here / b["file"]).read_text(encoding="utf-8")
    style = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
    body = re.search(r"</helmet>(.*?)</x-dc>", src, re.S).group(1)
    pages.append(f'<div class="page"><div class="cap">{b["title"]}</div>{body}</div>')

note = canvas["annotations"][0]["text"].replace("\n", "<br>")
html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{style}
@page {{ size: {W + 80}px {H + 120}px; margin: 0; }}
.page {{ width: {W + 80}px; height: {H + 120}px; padding: 40px; box-sizing: border-box; page-break-after: always; background: #fff; }}
.cap {{ font-size: 18px; color: #555; margin-bottom: 8px; height: 32px; }}
.cover {{ padding: 60px; }}
</style></head><body>
<div class="page cover"><div style="font-size: 40px;">SCT Case Builder, wireframe</div><div style="font-size: 20px; margin-top: 24px; max-width: 900px;">{note}</div></div>
{"".join(pages)}
</body></html>"""
out_html = here / "wireframe-print.html"
out_html.write_text(html, encoding="utf-8")
out_pdf = here / "sct-case-builder-wireframe.pdf"
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page()
    pg.goto(out_html.as_uri())
    pg.wait_for_timeout(1500)  # let the web font load
    pg.pdf(path=str(out_pdf), width=f"{W + 80}px", height=f"{H + 120}px", print_background=True, prefer_css_page_size=True)
    br.close()
print("wrote", out_pdf, out_pdf.stat().st_size // 1024, "KB")
