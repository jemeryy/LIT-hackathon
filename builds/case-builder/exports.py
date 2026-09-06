"""Evidence sheet (xlsx), claim pack (zip) and the written request text."""
import datetime as dt, io, zipfile
import llm, rules
from extract import keyframe_path, load_image

MAX_PDF_BYTES = 5 * 1024 * 1024


def evidence_xlsx(case):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Evidence"
    ws.append(["No.", "Exhibit", "Date", "What it shows", "Where", "Strength", "Rank", "Check it", "Notes"])
    for r in case["evidence"]:
        ws.append([r["rank"], ", ".join(sorted({s["exhibit_id"] for s in r["sources"]})),
                   rules.fmt(rules.d(r.get("date"))), r["what"], "; ".join(s["label"] for s in r["sources"]),
                   r["strength"].capitalize(), r["rank"], "yes" if r["needs_check"] else "", r["reason"]])
    ws.append([len(case["evidence"]) + 1, "", "", "(add your next item here)", "", "", "", "", ""])
    for col, w in zip("ABCDEFGHI", (5, 10, 12, 60, 24, 10, 6, 9, 50)):
        ws.column_dimensions[col].width = w
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _asset_pdf(asset):
    """One PDF per asset: PDFs pass through, images and video keyframes are wrapped."""
    if asset["kind"] == "pdf":
        return open(asset["path"], "rb").read()
    src = keyframe_path(asset["id"], asset["path"]) if asset["kind"] == "video" else asset["path"]
    im = load_image(src)
    buf = io.BytesIO()
    im.save(buf, "PDF", resolution=100)
    return buf.getvalue()


def claim_form_text(case):
    it, p = case["intake"], case["intake"]["parties"]
    lines = ["CJTS CLAIM FORM, prepared text (paste into the portal yourself)", "",
             "1. CLAIMANT", f"Name: {p['claimant']['name']}", f"Address: {p['claimant'].get('address', '')}",
             f"ID type: {p['claimant'].get('id_type', '')}", "",
             "2. RESPONDENT", f"Name: {p['respondent']['name']}", f"Address: {p['respondent'].get('address', '')}",
             f"Company: {'yes' if p['respondent'].get('is_company') else 'no'}", "",
             "3. CLAIM", f"Type: {case['claim_type']}", f"Amount: {rules.money(it['amount'])}",
             f"Date of cause of action: {rules.fmt(rules.d(it.get('cause_of_action_date')))}", "",
             "4. SUMMARY (500 characters max)", case.get("summary", ""), f"({len(case.get('summary', ''))} characters)", "",
             "5. DOCUMENTS (PDF only, 5 MB each, with page numbers)"]
    for r in case["evidence"]:
        lines.append(f"{r['rank']}. {r['what']} | {'; '.join(s['label'] for s in r['sources'])}")
    lines += ["", "6. MONEY ORDER", f"Order that the Respondent pays the Claimant {rules.money(it['amount'])}.", "",
              f"Filing fee: ${case['fee']['amount']} ({case['fee']['basis']})"]
    return "\n".join(lines)


def events_text(case):
    lines = ["EVENTS IN DATE ORDER (for the Submission for Hearing form)", ""]
    for e in case["timeline"]:
        if e.get("date") and not e["future"] and e["id"] != "today":
            lines.append(f"{rules.fmt(rules.d(e['date']))}: {e['label']}. {e['detail']}")
    return "\n".join(lines)


def claim_pack_zip(case):
    buf = io.BytesIO()
    manifest = ["CLAIM PACK MANIFEST", f"Made {dt.date.today().isoformat()}", "",
                "Each file below is a PDF measured against the 5 MB CJTS limit.", ""]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("claim_form.txt", claim_form_text(case))
        z.writestr("events.txt", events_text(case))
        z.writestr("written_request.txt", written_request(case))
        for ex in case["exhibits"]:
            if ex.get("side") == "theirs":   # the pack is what you file; their file is not your exhibit
                continue
            for a in ex["assets"]:
                try:
                    data = _asset_pdf(a)
                except Exception as exc:  # a broken file must not break the pack
                    manifest.append(f"{a['id']}: could not convert ({type(exc).__name__})")
                    continue
                name = f"exhibits/{a['id']}_{a['filename'].rsplit('.', 1)[0]}.pdf"
                z.writestr(name, data)
                status = "ready" if len(data) <= MAX_PDF_BYTES else "oversized, split or compress it"
                manifest.append(f"{name}: {len(data) / 1024 / 1024:.2f} MB, {status}")
        z.writestr("manifest.txt", "\n".join(manifest))
    return buf.getvalue()


def written_request(case):
    return llm.write_text("written_request", case)
