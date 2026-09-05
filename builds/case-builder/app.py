"""Case Helper: FastAPI backend. Run: uvicorn app:app --reload --port 8000 (from builds/case-builder)."""
import datetime as dt, io, json, logging, pathlib, re, shutil, threading
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import exports, extract, llm, rules, viewer

ROOT = pathlib.Path(__file__).resolve().parent
DATA, PACK = ROOT / "data", ROOT / "sample" / "pack"
CASE_FILE, UPLOADS = DATA / "case.json", DATA / "uploads"
APP_NAME = "Case Helper"
KINDS = {".pdf": "pdf", ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image",
         ".gif": "image", ".bmp": "image", ".dib": "image", ".tif": "image", ".tiff": "image",
         ".heic": "image", ".heif": "image", ".avif": "image", ".ico": "image", ".jfif": "image",
         ".ppm": "image", ".pgm": "image", ".pbm": "image", ".pnm": "image", ".pcx": "image",
         ".tga": "image", ".mp4": "video", ".mov": "video"}
MAX_UPLOAD = 50 * 1024 * 1024
MAX_CHAT = 4000

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
FIRST_MESSAGE = ("Tell me what happened, in your own words. Who is the other side? What did you agree? "
                 "What went wrong, and when? How much do you want back? I will ask if anything is missing.")
SCOPE_REFUSAL = ("I can only collect facts for a Small Claims case. "
                 "Please describe what was agreed and what happened.")
UNCLEAR_REPLY = ("I cannot safely tell what this concerns yet. "
                 "Was it about goods, services, a home lease, or property damage?")
UNSAFE_OUTPUT_REPLY = ("I cannot safely restate that yet. "
                       "What did the other side agree to do? What happened instead?")
INTAKE_COMPLETE = "I have everything I need. Look at the steps on the left. Tell me if anything is wrong."
NEXT_QUESTION = {   # asked by us, not the model, whenever the model returns nothing we can use
    "story": "Tell me what happened, in your own words.",
    "claimant": "What is your name, and your full address with unit number and postal code?",
    "respondent": "Who are you claiming against? What is their full address, and are they in Singapore?",
    "category": "Was this about goods, services, a home lease, or damage to property?",
    "agreed": "What did the two sides agree?",
    "amount": "How much are you claiming in total?",
    "when": "On what date did they refuse, or the problem start?",
    "files": "Add your files on the right.",
}
SAMPLE_BLINDSPOTS = {"b1": "unsure", "b2": "no", "b3": "yes", "b4": "no"}

app = FastAPI(title=APP_NAME)
CASE = None
SAMPLE_LOCK = threading.Lock()
log = logging.getLogger("case-helper")


def save(case):
    DATA.mkdir(exist_ok=True)
    CASE_FILE.write_text(json.dumps(case, indent=1, ensure_ascii=False), encoding="utf-8")


def make_asset(aid, path, kind=None):
    path = pathlib.Path(path)
    kind = kind or KINDS.get(path.suffix.lower())
    a = {"id": aid, "filename": path.name, "kind": kind, "path": str(path), "size_bytes": path.stat().st_size,
         "viewer_url": f"/api/viewer?asset_id={aid}&page_index=0", "meta": {}}
    if kind == "pdf":
        a["pages"] = viewer.page_count(a)
    return a


def upload_kind(filename, content_type, data):
    """Detect PDFs and images from their contents; extensions are only a video hint."""
    suffix = pathlib.Path(filename or "").suffix.lower()
    if b"%PDF-" in data[:1024]:
        return "pdf"
    if suffix in (".mp4", ".mov") or (content_type or "").startswith("video/"):
        return "video"
    try:
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            pass
        from PIL import Image
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        return "image"
    except Exception:
        return None


def new_case(today, sample=False):
    case = {"case_id": "example" if sample else "mine", "claim_type": "unknown", "app_name": APP_NAME, "today": today.isoformat(),
            "intake": json.loads(json.dumps(EMPTY_INTAKE)), "checklist": rules.content("questions")["checklist"],
            "story": "", "summary": "", "exhibits": [], "evidence": [], "gate": {}, "statutes": rules.content("statutes"),
            "gaps": [], "blindspots": {}, "timeline": [], "next_steps": [], "fee": {}}
    case["intake"]["chat"].append({"who": "bot", "text": FIRST_MESSAGE})
    if not sample:
        return case
    for eid, kind, title, files in SAMPLE:
        ids = [eid] if len(files) == 1 else [f"{eid}-{i}" for i in range(1, len(files) + 1)]
        case["exhibits"].append({"id": eid, "kind": kind, "status": "waiting", "title": title, "facts": [],
                                 "assets": [make_asset(aid, PACK / f) for aid, f in zip(ids, files)]})
    return case


def process_asset(case, ex, asset, use_saved=False):
    """Parse -> model reads facts -> each quote is matched back into our own text. Unfound quotes are dropped."""
    parsed = extract.parse(asset)
    image = None
    if asset["kind"] == "video":
        image = extract.keyframe_path(asset["id"], asset["path"])
        asset["frame_label"] = extract.frame_label(asset["id"], asset["path"])
    elif asset["kind"] == "image":
        image = asset["path"]
    result = llm.extract_facts(asset, parsed["text"], case, image, use_saved=use_saved)
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


def known_value(case, key):
    """The value already recorded for one intake field, or None when it is not set yet."""
    it = case["intake"]
    if key == "claim_type":
        return None if case["claim_type"] == "unknown" else case["claim_type"]
    if key in FIELD_PATH:
        *path, leaf = FIELD_PATH[key]
        node = it
        for step in path:
            node = node[step]
        value = node[leaf]
    else:
        value = it.get(key)
    return None if value is None or value == "" else value


def apply_corrections(case, turn):
    """A low-confidence turn is not trusted to add new facts, but the person may still be fixing one.
    Only a field the model names as changed, that is already recorded and now differs, is written."""
    fields = turn.get("fields", {})
    changed = {}
    for k in turn.get("corrections", []):
        old = known_value(case, k)
        if k in fields and old is not None and fields[k] != old:
            changed[k] = fields[k]
    if changed:
        apply_fields(case, changed)
    return list(changed)


def explicit_claim_amount(message):
    """Return a total the user explicitly calls their claim; never infer one."""
    money = r"(?:S\s*\$|SGD\s*)?\$?\s*([0-9][0-9,]*(?:\.\d{1,2})?)"
    patterns = [
        rf"\btotal\s+claim(?:\s+(?:is|of|for))?\s*{money}",
        rf"\b(?:want|wish)\s+to\s+claim\s*{money}",
        rf"\b(?:I\s+am|I'm|we\s+are|we're)\s+claiming\s*{money}",
        rf"\b(?:claim|claiming|seek|seeking|ask|asking)\s+(?:a\s+)?(?:total\s+)?(?:claim\s+)?(?:of|for)?\s*{money}",
        rf"\bwant\s*{money}\s+back\b",
    ]
    for pattern in patterns:
        matches = list(re.finditer(pattern, message, flags=re.IGNORECASE))
        if matches:
            return float(matches[-1].group(1).replace(",", ""))
    return None


PROMPT_ATTACK = re.compile(
    r"\b(ignore|override|bypass|disregard)\b.{0,45}\b(previous|prior|above|system|developer|instruction|rule|prompt)\b"
    r"|\b(system|developer)\s+(prompt|message)\b"
    r"|\b(reveal|show|print|repeat|leak|expose)\b.{0,35}\b(prompt|secret|api\s*key|instruction|system message)\b"
    r"|\b(jailbreak|do anything now|developer mode|prompt injection)\b",
    re.IGNORECASE | re.DOTALL,
)
UNSAFE_REPLY = re.compile(
    r"\b(you should|you ought|i recommend|my advice|best to|entitled to|will win|likely to win|"
    r"valid claim|tribunal (?:can|will) hear|eligible for|liable for|breach (?:is|was|occurred)|"
    r"this is (?:a|an) (?:tenancy|contract|legal)|legal remedy)\b",
    re.IGNORECASE,
)


def is_prompt_attack(message):
    """Catch common direct attacks before any case fields reach the model."""
    return bool(PROMPT_ATTACK.search(message))


def _plain_sentence(value, prefix=None, max_words=None):
    """Model text is untrusted. Keep one short line and reject advice or conclusions."""
    if not isinstance(value, str):
        return None
    value = " ".join(value.strip().split())
    if not value or len(value) > 260 or "http://" in value.lower() or "https://" in value.lower():
        return None
    if UNSAFE_REPLY.search(value):
        return None
    if prefix and not value.lower().startswith(prefix.lower()):
        return None
    if max_words and len(value.split()) > max_words:
        return None
    return value


def safe_intake_reply(turn):
    """Only fact reflections and fact questions may cross the model boundary."""
    scope = turn.get("scope", "claim_intake")  # saved example fixtures predate scope metadata
    confidence = turn.get("confidence", "high")
    if scope in ("off_topic", "prompt_attack"):
        return SCOPE_REFUSAL
    if scope == "unclear" or confidence == "low":
        return UNCLEAR_REPLY
    reflection = _plain_sentence(turn.get("reflection"), "You say", 22)
    questions = []
    for q in turn.get("questions") or []:
        q = _plain_sentence(q, max_words=22)
        if q and q.endswith("?"):
            questions.append(q)
    if not questions[:2]:
        # Compatibility for the deterministic worked example only.
        legacy = _plain_sentence(turn.get("reply"))
        return legacy or UNSAFE_OUTPUT_REPLY
    # If the model over-summarises, omit its reflection. The questions remain safe
    # and contextual, and omitting a statement is better than misstating the case.
    reply = " ".join([*([reflection] if reflection else []), *questions[:2]])
    return reply if len(reply.split()) <= 65 else UNSAFE_OUTPUT_REPLY


def chat_turn(case, message):
    it = case["intake"]
    if not it["chat"]:
        it["chat"].append({"who": "bot", "text": FIRST_MESSAGE})
    it["chat"].append({"who": "user", "text": message})
    if is_prompt_attack(message):
        it["chat"].append({"who": "bot", "text": SCOPE_REFUSAL})
        return recompute(case)
    turn = llm.intake_turn(case, case["checklist"])
    stated_amount = explicit_claim_amount(message)
    in_scope = turn.get("scope", "claim_intake") == "claim_intake"
    trusted_turn = in_scope and turn.get("confidence", "high") != "low"
    if stated_amount is not None and trusted_turn:
        turn.setdefault("fields", {})["amount"] = stated_amount
    before = case["claim_type"]
    corrected = []
    if trusted_turn:
        apply_fields(case, turn.get("fields", {}))
    elif in_scope:
        corrected = apply_corrections(case, turn)
    if case["claim_type"] != before and rules.ctype(case) != rules.ctype({"claim_type": before}):
        for ex in case["exhibits"]:   # files read before the kind of claim was known: read them again under its keys
            for a in ex["assets"]:
                if ex["status"] == "ready":
                    process_asset(case, ex, a)
    case = recompute(case)   # the gate must reflect this turn before we choose what to say
    blocked = [c for c in case["gate"]["checks"] if c["blocked"]]
    missing = [c["id"] for c in case["checklist"] if not c["done"]]
    reply = safe_intake_reply(turn)
    if reply == UNSAFE_OUTPUT_REPLY or (reply == UNCLEAR_REPLY and corrected):
        # The model asked nothing usable. Having read the person correctly, saying we could not is both
        # wrong and alarming, so ask for the next thing we are genuinely still missing instead.
        reply = NEXT_QUESTION[missing[0]] if missing else INTAKE_COMPLETE
    if blocked:   # facts we already hold rule the claim out, so say that rather than ask for more
        reply = " ".join(c["text"] for c in blocked) + f" {blocked[0]['where']} Tell me if I have that wrong."
    elif missing == ["files"]:
        other = it["parties"]["respondent"].get("name") or "the other side"
        needed = {
            "tenancy": "the agreement, payment records, messages, and photos",
            "goods": "the order, payment records, messages, and photos",
            "services": "the quote, payment records, messages, and photos",
            "property_damage": "messages, photos, videos, and repair quotes",
        }.get(case["claim_type"], "the agreement, payments, messages, and photos")
        reply = f"I have enough details about your claim against {other}. Now add {needed} on the right."
    elif not missing:
        reply = INTAKE_COMPLETE
    if corrected:   # the turn was not trusted overall, but the person did fix a fact we already had
        reply = "I have updated that. " + reply
    it["chat"].append({"who": "bot", "text": reply})
    save(case)
    return case


def checklist_state(case):
    it, p = case["intake"], case["intake"]["parties"]
    got = {"story": bool(it["account"]), "claimant": bool(p["claimant"]["name"] and p["claimant"]["address"]),
           "respondent": bool(p["respondent"]["name"] and p["respondent"]["address"]
                              and p["respondent"]["in_singapore"] is not None),
           "category": case["claim_type"] not in ("unknown", "other"), "agreed": bool(it.get("what_agreed")),
           "amount": it.get("amount") is not None, "when": bool(it.get("cause_of_action_date")),
           "files": any(e["status"] == "ready" for e in case["exhibits"])}
    return [{**c, "done": got.get(c["id"], False)} for c in case["checklist"]]


def recompute(case):
    case["checklist"] = checklist_state(case)
    case["intake"]["done"] = all(c["done"] for c in case["checklist"])
    today = dt.date.fromisoformat(case["today"])
    answers = {q["id"]: q.get("answer") for q in case.get("blindspots", {}).get("questions", [])}
    case["evidence"] = rules.evidence(case)
    case["gate"] = rules.gate(case, today)
    case["gaps"] = rules.gaps(case)
    case["blindspots"] = rules.blindspots(case, answers)
    case["timeline"] = rules.timeline(case, today)
    case["next_steps"] = rules.next_steps(case)
    case["fee"] = rules.fee(case["intake"]["amount"])
    it = {k: v for k, v in case["intake"].items() if k != "chat"}
    key = json.dumps([it, [(r["what"], r["rank"]) for r in case["evidence"]], case["claim_type"]], sort_keys=True, default=str)
    if not case["evidence"]:
        case["story"], case["summary"] = "", ""
    elif key != case.get("_text_key"):   # only write the story and summary again when the facts behind them changed
        case["story"] = llm.write_text("story", case)
        case["summary"] = llm.write_text("summary", case)[:500]
        case["_text_key"] = key
    save(case)
    return case


def _add_sample_chat(case):
    """Replay the saved worked-example conversation without making model calls."""
    for message, turn in zip(llm.FIX["chat_user"], llm.FIX["chat"]):
        case["intake"]["chat"].append({"who": "user", "text": message})
        apply_fields(case, turn.get("fields", {}))
        case["intake"]["done"] = case["intake"]["done"] or bool(turn.get("done"))
        case["intake"]["chat"].append({"who": "bot", "text": turn["reply"]})


def build_sample(today=None, include_chat=False):
    global CASE
    case = new_case(today or dt.date.today(), sample=True)
    if include_chat:
        # Know the claim type before reading files, so each file is read only once
        # and ranked under the correct tenancy rules.
        _add_sample_chat(case)
    for ex in case["exhibits"]:
        for a in ex["assets"]:
            process_asset(case, ex, a, use_saved=True)
        ex["status"] = "ready"
    case["blindspots"] = rules.blindspots(case, SAMPLE_BLINDSPOTS)
    CASE = recompute(case)
    return CASE


def sample_is_ready(case):
    return bool(case and case.get("case_id") == "example"
                and case.get("intake", {}).get("done")
                and len(case.get("intake", {}).get("chat", [])) == 1 + 2 * len(llm.FIX["chat_user"])
                and len(case.get("exhibits", [])) == len(SAMPLE)
                and all(ex.get("status") == "ready" for ex in case.get("exhibits", [])))


def current():
    global CASE
    if CASE is None and CASE_FILE.exists():
        CASE = json.loads(CASE_FILE.read_text(encoding="utf-8"))
        CASE["gate"] = rules.gate(CASE, dt.date.fromisoformat(CASE["today"]))   # the rules may have moved on since it was saved
    if CASE is None:
        CASE = recompute(new_case(dt.date.today()))
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
    """Load the worked example (Mei Ling's deposit) from the sample pack."""
    # Browser Back or a double-click can leave an earlier reset running. Let that
    # one finish, then reuse it instead of reading all sample files a second time.
    with SAMPLE_LOCK:
        case = current()
        if sample_is_ready(case):
            return case
        return build_sample(include_chat=True)


@app.post("/api/case/new")
def new():
    global CASE
    CASE = recompute(new_case(dt.date.today()))
    return CASE


@app.get("/api/case")
def get_case():
    case = current()
    return case if case else err("no_case", "No case yet. POST /api/case/reset first.", 404)


@app.post("/api/chat")
def chat(body: dict):
    case = current()
    message = str(body.get("message", "")).strip()[:MAX_CHAT]
    if not message:
        return err("empty", "Type something first.")
    snapshot = json.loads(json.dumps(case))
    try:
        return chat_turn(case, message)
    except Exception as exc:
        log.exception("AI intake failed")
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
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        return err("too_big", f"{file.filename} is over 50 MB.")
    kind = upload_kind(file.filename, file.content_type, data)
    if not kind:
        return err("unsupported", f"{file.filename}: use a PDF, image, MP4 or MOV file.")
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
        asset = make_asset(asset_id, path, kind)   # opens the file (page_count for PDFs), so it is inside the guard
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
    sub = {"pdf": f"PDF, {asset.get('pages', 1)} pages", "image": "Image", "video": f"Video, frame at {asset.get('frame_label', '')}"}[asset["kind"]]
    sub += f" | {ex['id']}" + (f" | {pos} of {n}" if n > 1 else "")
    if asset["kind"] == "video":
        caption = f"Frame at {asset.get('frame_label', '')} of {asset['filename']}. Play the file to check it."
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
