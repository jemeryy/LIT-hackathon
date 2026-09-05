"""Case Builder: FastAPI backend. Run: uvicorn app:app --reload --port 8000 (from builds/case-builder)."""
import datetime as dt, json, pathlib, shutil
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import exports, extract, llm, rules, viewer

ROOT = pathlib.Path(__file__).resolve().parent
DATA, PACK = ROOT / "data", ROOT / "sample" / "pack"
CASE_FILE, UPLOADS = DATA / "case.json", DATA / "uploads"
APP_NAME = "Case Builder"
KINDS = {".pdf": "pdf", ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image", ".mp4": "video", ".mov": "video"}
MAX_UPLOAD = 50 * 1024 * 1024

SAMPLE = [("E1", "pdf", "Tenancy agreement", ["Tenancy_Agreement_2025.pdf"]),
          ("E2", "image_set", "WhatsApp screenshots", [f"WhatsApp_{i:02d}.png" for i in range(1, 7)]),
          ("E3", "image_set", "Email from the landlord", ["email_landlord.png"]),
          ("E4", "image_set", "Deposit transfer screenshot", ["deposit_transfer.jpg"]),
          ("E5", "video", "Move-out video", ["moveout_walkthrough.mp4"]),
          ("E6", "image_set", "Move-in photos", [f"movein_{i:02d}.jpg" for i in range(1, 6)])]
EMPTY_INTAKE = {
    "chat": [], "account": "", "done": False,
    "parties": {"claimant": {"name": "", "address": "", "id_type": "NRIC"},
                "respondent": {"name": "", "role": None, "address": "", "in_singapore": None, "is_company": None}},
    "amount": None, "consent_30k": False, "cause_of_action_date": None, "moveout_date": None, "what_agreed": "",
    "premises": {"residential": None, "lease_months": None, "refund_days": None}}
FIELD_PATH = {"claimant_name": ("parties", "claimant", "name"), "claimant_address": ("parties", "claimant", "address"),
              "respondent_name": ("parties", "respondent", "name"), "respondent_address": ("parties", "respondent", "address"),
              "respondent_role": ("parties", "respondent", "role"), "respondent_in_singapore": ("parties", "respondent", "in_singapore"),
              "respondent_is_company": ("parties", "respondent", "is_company"), "residential": ("premises", "residential"),
              "lease_months": ("premises", "lease_months"), "refund_days": ("premises", "refund_days")}
FIRST_MESSAGE = ("Tell me what happened, in your own words. Who is the other side, what did you agree, what went wrong, "
                 "when, and how much you want back. I will ask for anything missing. I do not give legal advice.")
SAMPLE_BLINDSPOTS = {"b1": "unsure", "b2": "no", "b3": "yes", "b4": "no"}

app = FastAPI(title=APP_NAME)
CASE = None


def save(case):
    DATA.mkdir(exist_ok=True)
    CASE_FILE.write_text(json.dumps(case, indent=1, ensure_ascii=False), encoding="utf-8")


def make_asset(aid, path):
    path = pathlib.Path(path)
    kind = KINDS.get(path.suffix.lower())
    a = {"id": aid, "filename": path.name, "kind": kind, "path": str(path), "size_bytes": path.stat().st_size,
         "viewer_url": f"/api/viewer?asset_id={aid}&page_index=0", "meta": {}}
    if kind == "pdf":
        a["pages"] = viewer.page_count(a)
    return a


def new_case(today):
    case = {"case_id": "mei-ling", "claim_type": "unknown", "app_name": APP_NAME, "today": today.isoformat(),
            "intake": json.loads(json.dumps(EMPTY_INTAKE)), "checklist": rules.content("questions")["checklist"],
            "story": "", "summary": "", "exhibits": [], "evidence": [], "gate": {}, "statutes": rules.content("statutes"),
            "gaps": [], "blindspots": {}, "timeline": [], "next_steps": [], "fee": {}}
    for eid, kind, title, files in SAMPLE:
        ids = [eid] if len(files) == 1 else [f"{eid}-{i}" for i in range(1, len(files) + 1)]
        case["exhibits"].append({"id": eid, "kind": kind, "status": "waiting", "title": title, "facts": [],
                                 "assets": [make_asset(aid, PACK / f) for aid, f in zip(ids, files)]})
    return case


def process_asset(case, ex, asset):
    """Parse -> model reads facts -> each quote is matched back into our own text. Unfound quotes are dropped."""
    parsed = extract.parse(asset)
    image = None
    if asset["kind"] == "video":
        image = extract.keyframe_path(asset["id"], asset["path"])
    elif asset["kind"] == "image":
        image = asset["path"]
    result = llm.extract_facts(asset, parsed["text"], case, image)
    asset["meta"] = result.get("meta", {})
    kept = []
    for f in result.get("facts", []):
        f = {**f, "asset_id": asset["id"]}
        if f.get("quote"):
            loc = extract.locate(parsed, f["quote"], asset["id"])
            if not loc:
                continue
            f["locator"] = loc
        else:
            f["locator"] = {"asset_id": asset["id"], "page_index": 0, "boxes": [], "coord_space": "normalized"}
        kept.append(f)
    ex["facts"] = [f for f in ex["facts"] if f["asset_id"] != asset["id"]] + kept


def apply_fields(case, fields):
    """Merge one chat turn's fields into the intake. Bad dates and amounts are dropped, never guessed."""
    it = case["intake"]
    for k, v in fields.items():
        if v is None or v == "":
            continue
        if k == "claim_type":
            case["claim_type"] = v
        elif k in ("cause_of_action_date", "moveout_date"):
            try:
                it[k] = dt.date.fromisoformat(str(v)[:10]).isoformat()
            except ValueError:
                pass
        elif k == "amount":
            try:
                it[k] = float(str(v).replace("$", "").replace(",", ""))
            except ValueError:
                pass
        elif k in FIELD_PATH:
            *path, leaf = FIELD_PATH[k]
            node = it
            for step in path:
                node = node[step]
            node[leaf] = v
        elif k in it:
            it[k] = v
    it["account"] = " ".join(m["text"] for m in it["chat"] if m["who"] == "user")


def chat_turn(case, message):
    it = case["intake"]
    if not it["chat"]:
        it["chat"].append({"who": "bot", "text": FIRST_MESSAGE})
    it["chat"].append({"who": "user", "text": message})
    turn = llm.intake_turn(case, case["checklist"])
    apply_fields(case, turn.get("fields", {}))
    it["done"] = it["done"] or bool(turn.get("done"))
    it["chat"].append({"who": "bot", "text": turn["reply"]})
    return recompute(case)


def checklist_state(case):
    it, p = case["intake"], case["intake"]["parties"]
    got = {"story": bool(it["account"]), "claimant": bool(p["claimant"]["name"] and p["claimant"]["address"]),
           "respondent": bool(p["respondent"]["name"] and p["respondent"]["in_singapore"] is not None),
           "category": case["claim_type"] not in ("unknown", "other"), "agreed": bool(it.get("what_agreed")),
           "amount": it.get("amount") is not None, "when": bool(it.get("cause_of_action_date")),
           "files": any(e["status"] == "ready" for e in case["exhibits"])}
    return [{**c, "done": got.get(c["id"], False)} for c in case["checklist"]]


def recompute(case):
    case["checklist"] = checklist_state(case)
    today = dt.date.fromisoformat(case["today"])
    answers = {q["id"]: q.get("answer") for q in case.get("blindspots", {}).get("questions", [])}
    case["evidence"] = rules.evidence(case)
    case["gate"] = rules.gate(case, today)
    case["gaps"] = rules.gaps(case)
    case["blindspots"] = rules.blindspots(case, answers)
    case["timeline"] = rules.timeline(case, today)
    case["next_steps"] = rules.next_steps(case)
    case["fee"] = rules.fee(case["intake"]["amount"])
    case["story"] = llm.write_text("story", case)
    case["summary"] = llm.write_text("summary", case)[:500]
    save(case)
    return case


def build_sample(today=None):
    global CASE
    case = new_case(today or dt.date.today())
    if not case["intake"]["chat"]:
        case["intake"]["chat"].append({"who": "bot", "text": FIRST_MESSAGE})
    for ex in case["exhibits"]:
        for a in ex["assets"]:
            process_asset(case, ex, a)
        ex["status"] = "ready"
    case["blindspots"] = rules.blindspots(case, SAMPLE_BLINDSPOTS)
    CASE = recompute(case)
    return CASE


def current():
    global CASE
    if CASE is None and CASE_FILE.exists():
        CASE = json.loads(CASE_FILE.read_text(encoding="utf-8"))
    today = dt.date.today().isoformat()
    if CASE and CASE.get("today") != today:   # a saved case keeps its facts; only the date-driven parts move
        CASE["today"] = today
        CASE["gate"] = rules.gate(CASE, dt.date.today())
        CASE["timeline"] = rules.timeline(CASE, dt.date.today())
        save(CASE)
    return CASE


def err(code, message, status=400):
    return JSONResponse({"error": message, "code": code, "case": current()}, status_code=status)


def find_asset(case, asset_id):
    for ex in case["exhibits"]:
        for a in ex["assets"]:
            if a["id"] == asset_id:
                return ex, a
    return None, None


@app.post("/api/case/reset")
def reset():
    return build_sample()


@app.get("/api/case")
def get_case():
    case = current()
    return case if case else err("no_case", "No case yet. POST /api/case/reset first.", 404)


@app.post("/api/chat")
def chat(body: dict):
    case = current()
    message = str(body.get("message", "")).strip()[:4000]
    if not message:
        return err("empty", "Type something first.")
    snapshot = json.loads(json.dumps(case))
    try:
        return chat_turn(case, message)
    except Exception as exc:
        case.clear(); case.update(snapshot)
        return err("model_failed", f"Could not read that ({type(exc).__name__}). Try again.")


@app.post("/api/chat/clear")
def chat_clear():
    case = current()
    case["intake"] = json.loads(json.dumps(EMPTY_INTAKE))
    case["intake"]["chat"].append({"who": "bot", "text": FIRST_MESSAGE})
    case["claim_type"] = "unknown"
    return recompute(case)


@app.post("/api/upload")
async def upload(exhibit_id: str = Form(...), asset_id: str = Form(None), file: UploadFile = File(...)):
    global CASE
    case = current()
    kind = KINDS.get(pathlib.Path(file.filename).suffix.lower())
    if not kind:
        return err("unsupported", f"{file.filename}: only PDF, PNG, JPG, WEBP, MP4 or MOV.")
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        return err("too_big", f"{file.filename} is over 50 MB.")
    snapshot = json.loads(json.dumps(case))   # restore point: a bad file must leave case.json unchanged
    try:
        ex = next((e for e in case["exhibits"] if e["id"] == exhibit_id), None)
        if not ex:
            ex = {"id": exhibit_id, "kind": "image_set" if kind == "image" else kind, "status": "waiting",
                  "title": file.filename, "facts": [], "assets": []}
            case["exhibits"].append(ex)
        asset_id = asset_id or (exhibit_id if not ex["assets"] else f"{exhibit_id}-{len(ex['assets']) + 1}")
        UPLOADS.mkdir(parents=True, exist_ok=True)
        path = UPLOADS / asset_id / pathlib.Path(file.filename).name   # keep the original name (fixtures key on it)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        asset = make_asset(asset_id, path)   # opens the file (page_count for PDFs), so it is inside the guard
        ex["assets"] = [a for a in ex["assets"] if a["id"] != asset_id] + [asset]
        for p in (extract.CACHE.glob(f"{asset_id}_*")):
            p.unlink()
        ex["status"] = "reading"
        process_asset(case, ex, asset)
        ex["status"] = "ready"
        return recompute(case)   # recompute can also raise, so it stays inside the guard
    except Exception as exc:
        CASE = snapshot   # roll back in-memory; do not save, so case.json on disk is untouched
        return err("parse_failed", f"Could not read {file.filename} ({type(exc).__name__}).")


@app.post("/api/blindspot")
def blindspot(body: dict):
    case = current()
    if body.get("answer") not in ("yes", "no", "unsure"):
        return err("bad_answer", "answer must be yes, no or unsure")
    for q in case["blindspots"]["questions"]:
        if q["id"] == body.get("id"):
            q["answer"] = body["answer"]
    case["blindspots"]["answered"] = sum(1 for q in case["blindspots"]["questions"] if q.get("answer"))
    save(case)
    return case["blindspots"]


def _viewer_payload(case, asset, page_index, boxes, quote=None, label=None):
    ex, _ = find_asset(case, asset["id"])
    n = len(ex["assets"])
    pos = [a["id"] for a in ex["assets"]].index(asset["id"]) + 1
    sub = {"pdf": f"PDF, {asset.get('pages', 1)} pages", "image": "Image", "video": "Video, frame at 1:12"}[asset["kind"]]
    sub += f" | {ex['id']}" + (f" | {pos} of {n}" if n > 1 else "")
    if asset["kind"] == "video":
        caption = f"Frame at {extract.VIDEO_KEYFRAME_S // 60}:{extract.VIDEO_KEYFRAME_S % 60:02d} of {asset['filename']}. Play the file to check it."
    elif quote:
        where = f"p.{page_index + 1}" if asset["kind"] == "pdf" else "this image"
        caption = f'Text found: "{quote}", {where}. Check it against the {"page" if asset["kind"] == "pdf" else "image"}.'
    else:
        caption = f"{asset['filename']}. Nothing to highlight here: the file itself is the evidence."
    return {"image_url": f"/api/render?asset_id={asset['id']}&page_index={page_index}", "boxes": boxes or [],
            "coord_space": "normalized", "caption": caption, "title": asset["filename"], "subtitle": sub,
            "label": label or ex["id"], "page_index": page_index, "pages": asset.get("pages", 1), "asset_id": asset["id"]}


@app.get("/api/viewer")
def view(evidence_id: str = None, source_index: int = 0, asset_id: str = None, page_index: int = 0):
    case = current()
    if evidence_id:
        row = next((r for r in case["evidence"] if r["id"] == evidence_id), None)
        if not row or source_index >= len(row["sources"]):
            return err("not_found", "no such evidence source", 404)
        s = row["sources"][source_index]
        _, asset = find_asset(case, s["asset_id"])
        loc = s.get("locator") or {}
        return _viewer_payload(case, asset, loc.get("page_index", 0), loc.get("boxes"), s.get("quote"), s["label"])
    ex, asset = find_asset(case, asset_id)
    if not asset:
        return err("not_found", "no such asset", 404)
    boxes, quote = [], None
    for f in ex["facts"]:   # a generic link still highlights whatever was found on that page
        loc = f.get("locator") or {}
        if f["asset_id"] == asset_id and loc.get("page_index") == page_index and loc.get("boxes"):
            boxes += loc["boxes"]
            quote = quote or f.get("quote")
    return _viewer_payload(case, asset, page_index, boxes, quote)


@app.get("/api/render")
def render(asset_id: str, page_index: int = 0):
    _, asset = find_asset(current(), asset_id)
    if not asset:
        return err("not_found", "no such asset", 404)
    return Response(viewer.render(asset, page_index), media_type="image/png")


@app.get("/api/statute")
def statute(section_id: str):
    s = rules.content("statutes").get(section_id)
    return s if s else err("not_found", "no such section", 404)


@app.get("/api/export/xlsx")
def export_xlsx():
    return Response(exports.evidence_xlsx(current()), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=evidence_sheet.xlsx"})


@app.get("/api/export/claimpack")
def export_claimpack():
    return Response(exports.claim_pack_zip(current()), media_type="application/zip",
                    headers={"Content-Disposition": "attachment; filename=claim_pack.zip"})


@app.get("/api/written-request")
def written_request():
    return {"text": exports.written_request(current())}


app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
