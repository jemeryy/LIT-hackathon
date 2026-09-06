"""Case Helper: FastAPI backend. Run: uvicorn app:app --reload --port 8000 (from builds/case-builder)."""
import contextvars, datetime as dt, io, json, logging, math, pathlib, re, shutil, threading, uuid
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import exports, extract, llm, rules, viewer

ROOT = pathlib.Path(__file__).resolve().parent
DATA, PACK = ROOT / "data", ROOT / "sample" / "pack"
CASES_DIR, UPLOADS = DATA / "cases", DATA / "uploads"
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
    "chat": [], "account": "", "done": False, "skipped": [],
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
SKIPPABLE = ("claimant", "respondent", "agreed", "amount", "when")   # the story, the kind of claim and files cannot be given up
NO_DETAIL = re.compile(r"(sorry,? )?(no|nope|none|i )?\s*(dont|don't|do not|not)?\s*(have|know|sure)?( it| that| any| one| idea)?( (his|her|their|the|my)( \w+){1,2})?\.?")
NO_DETAIL_ITEM = [("when", r"date|when|day"), ("amount", r"amount|how much"), ("claimant", r"my (full )?address"),
                  ("respondent", r"(his|her|their|the) (full )?(address|name)")]   # which item a "dont have his address" gives up
INTAKE_COMPLETE = "I have everything I can get from you. Press Next to check if the tribunal can hear it."
NEXT_QUESTION = {   # asked by us, not the model, whenever the model returns nothing we can use
    "story": "Tell me what happened, in your own words.",
    "claimant": "What is your name, and your full address with unit number and postal code?",
    "respondent": "Who are you claiming against? What is their full address, and are they in Singapore?",
    "category": "Was this about goods, services, a home lease, or damage to property?",
    "agreed": "What did the two sides agree?",
    "amount": "How much are you claiming in total?",
    "when": "On what date did they refuse, or the problem start?",
    "files": "Press Next to check if the tribunal can hear it, then add your files in step 3.",
}

app = FastAPI(title=APP_NAME)
CASES = {}                      # one case per visitor, keyed by the visitor cookie
EXAMPLE = None                  # the worked example, built once and copied per visitor
VISITOR = contextvars.ContextVar("visitor", default="local")
SAMPLE_LOCK = threading.Lock()
log = logging.getLogger("case-helper")


@app.middleware("http")
async def visitor_cookie(request: Request, call_next):
    """Each browser gets its own case. Without this every visitor shared one case and saw each other's files."""
    vid = request.cookies.get("visitor", "")
    fresh = not re.fullmatch(r"[0-9a-f]{32}", vid)
    if fresh:
        vid = uuid.uuid4().hex
    token = VISITOR.set(vid)
    try:
        response = await call_next(request)
    finally:
        VISITOR.reset(token)
    if fresh:
        response.set_cookie("visitor", vid, max_age=365 * 86400, httponly=True, samesite="lax")
    return response


def save(case):
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    (CASES_DIR / f"{case['visitor']}.json").write_text(json.dumps(case, indent=1, ensure_ascii=False), encoding="utf-8")


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
    case = {"case_id": "example" if sample else "mine", "visitor": VISITOR.get(), "claim_type": "unknown", "app_name": APP_NAME, "today": today.isoformat(),
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
    result = llm.extract_facts(asset, parsed["text"], case, image, use_saved=use_saved, exhibit=ex)
    asset["assessment_source"] = "saved_example" if use_saved else "demo_reader" if llm.use_fixtures() else "live_reader"
    asset["meta"] = result.get("meta", {})
    asset["relevance"] = result.get("relevance")
    asset["relevance_reason"] = result.get("relevance_reason") or ""
    asset.pop("review_reason", None)
    if result.get("relevance") == "needs_review":
        asset["review_reason"] = result.get("relevance_reason") or "The reader could not determine whether this file relates to the claim."
    if asset["kind"] == "pdf" and not parsed["text"].strip():
        asset["review_reason"] = "No readable text was extracted from this PDF. Upload a searchable PDF or clear images of its pages."
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
    if any(rules.related_fact(f) for f in result.get("facts", [])) and not any(rules.related_fact(f) for f in kept):
        asset["review_reason"] = "The reader suggested relevant facts, but their quotes could not be verified in the file. Check the file or upload a clearer copy."
    if result.get("relevance") in ("relevant", "context") and not any(rules.related_fact(f) for f in kept):
        asset.setdefault("review_reason", "The reader indicated a possible connection but found no usable supporting facts. Check the file.")
    if len(parsed["text"]) > 12000 and not any(rules.related_fact(f) for f in kept):
        asset.setdefault("review_reason", "Only part of this long file was checked for relevance. No relevant facts were found in that part; check the remaining pages.")
    if re.search(r"\bplaceholder\s+(?:photo|image|video)\b", parsed["text"], re.IGNORECASE):
        asset["relevance"] = "placeholder"
        asset["relevance_reason"] = "The file is labelled as a placeholder. It does not show the actual property or event."
    ex["facts"] = [f for f in ex["facts"] if f["asset_id"] != asset["id"]] + kept


def apply_fields(case, fields):
    """Merge one chat turn's fields into the intake. Bad dates and amounts are dropped, never guessed."""
    it = case["intake"]
    for k, v in (fields.items() if isinstance(fields, dict) else []):
        if k not in llm.INTAKE_FIELDS:
            continue
        if v is None or v == "":
            continue
        if k in ("respondent_in_singapore", "respondent_is_company", "residential", "consent_30k") and not isinstance(v, bool):
            continue
        if k in ("lease_months", "refund_days") and (isinstance(v, bool) or not isinstance(v, int) or v <= 0):
            continue
        if k in ("claimant_name", "claimant_address", "respondent_name", "respondent_address", "respondent_role", "what_agreed"):
            if not isinstance(v, str):
                continue
            v = v.strip()
            if not v:
                continue
        if k == "claim_type":
            if v in llm.CLAIM_TYPES:
                case["claim_type"] = v
        elif k in ("cause_of_action_date", "moveout_date"):
            try:
                it[k] = dt.date.fromisoformat(str(v)[:10]).isoformat()
            except ValueError:
                pass
        elif k == "amount":
            try:
                amount = float(str(v).replace("$", "").replace(",", ""))
                if math.isfinite(amount) and amount > 0:
                    it[k] = amount
            except (ValueError, TypeError):
                pass
        elif k in FIELD_PATH:
            if k.endswith("_address"):
                v = re.sub(r",\s*#\s*(?=,|$)", "", str(v)).strip().strip(",")   # empty unit slot the model leaves behind
                if re.search(r"\?|\b(?:unknown|not (?:known|provided|specified)|please (?:provide|confirm)|to be confirmed)\b", v, re.I):
                    continue   # the model hedged or invented part of it; an address goes on a court form, so drop it
            *path, leaf = FIELD_PATH[k]
            node = it
            for step in path:
                node = node[step]
            node[leaf] = v
        elif k in it:
            it[k] = v
    it["account"] = " ".join(m["text"] for m in it["chat"] if m["who"] == "user")
    it["unavailable"] = [k for k in it.get("unavailable", []) if known_value(case, k) is None]


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
    before = {k: known_value(case, k) for k in changed}
    if changed:
        apply_fields(case, changed)
    return [k for k in changed if known_value(case, k) != before[k]]


def explicit_claim_amount(message):
    """Return a total the user explicitly calls their claim; never infer one."""
    money = r"(?:S\s*\$|SGD\s*)?\$?\s*([0-9][0-9,]*(?:\.\d{1,2})?)"
    patterns = [
        rf"\btotal\s+claim(?:\s+(?:is|of|for))?\s*{money}",
        rf"\b(?:want|wish)\s+to\s+claim\s*{money}",
        rf"\b(?:I\s+am|I'm|we\s+are|we're)\s+claiming\s*{money}",
        rf"\b(?:claim|claiming|seek|seeking|ask|asking)\s+(?:a\s+)?(?:total\s+)?(?:claim\s+)?(?:of|for)?\s*{money}",
        rf"\bwant\s*{money}\s+back\b",
        rf"\bclaim\s+amount\s+(?:is|of|:|should\s+be|to)?\s*{money}",
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


ADDRESS_WORDS = ("address", "postal code", "postcode", "unit number", "block number")


def asks_for_recorded_address(question, case):
    """The model sometimes chases an address it already holds, postal code included. Drop that question."""
    q = question.lower()
    if not any(w in q for w in ADDRESS_WORDS):
        return False
    p = case["intake"]["parties"]
    return bool(p["claimant"]["address"] if "your" in q else p["respondent"]["address"])


def safe_intake_reply(turn, case=None):
    """Only fact reflections and fact questions may cross the model boundary."""
    scope = turn.get("scope", "claim_intake")  # saved example fixtures predate scope metadata
    confidence = turn.get("confidence", "high")
    if scope in ("off_topic", "prompt_attack"):
        return SCOPE_REFUSAL
    if scope == "unclear" or confidence == "low":
        return UNCLEAR_REPLY
    reflection = _plain_sentence(turn.get("reflection"), "You say", 22)
    questions = []
    for q in llm.question_list(turn.get("questions")):
        q = _plain_sentence(q, max_words=22)
        if q and q.endswith("?") and not (case and asks_for_recorded_address(q, case)):
            questions.append(q)
    if not questions[:2]:
        # Compatibility for the deterministic worked example only.
        legacy = _plain_sentence(turn.get("reply"))
        return legacy or reflection or ""
    # If the model over-summarises, omit its reflection. The questions remain safe
    # and contextual, and omitting a statement is better than misstating the case.
    reply = " ".join([*([reflection] if reflection else []), *questions[:2]])
    return reply if len(reply.split()) <= 65 else UNSAFE_OUTPUT_REPLY


CHANGE_WORDS = {"amount": "the amount you claim", "cause_of_action_date": "the date the other side refused",
                "moveout_date": "the move-out date", "what_agreed": "what was agreed", "consent_30k": "the $30,000 agreement"}
PARTY_WORDS = {"name": "name", "address": "address", "in_singapore": "in Singapore", "is_company": "a company", "role": "role"}
BLOCKED_COVERS = {"service": "in Singapore", "amount": "the amount you claim",   # a failed check already states these
                  "time": "the date the other side refused", "category": "the kind of claim"}


def describe_changes(before, case):
    """Plain words for every fact that was already known and has now been corrected."""
    a, b = before["intake"], case["intake"]
    out = []
    for k, w in CHANGE_WORDS.items():
        if a.get(k) not in (None, "", False) and b.get(k) != a.get(k):   # False is the default, not a fact the person gave
            v = b.get(k)
            out.append(f"{w} is now {rules.money(v) if k == 'amount' else rules.fmt(dt.date.fromisoformat(v)) if k.endswith('_date') else v}")
    for who in ("claimant", "respondent"):
        for k, w in PARTY_WORDS.items():
            old, new = a["parties"][who].get(k), b["parties"][who].get(k)
            if old not in (None, "") and new != old:
                label = "your" if who == "claimant" else "the other side's"
                if k in ("in_singapore", "is_company"):
                    out.append(f"the other side is {'' if new else 'not '}{w}")
                else:
                    out.append(f"{label} {w} is now {new}")
    for k, w in (("residential", "a home"), ("lease_months", "months long")):
        old, new = a.get("premises", {}).get(k), b.get("premises", {}).get(k)
        if old is not None and new != old:
            out.append(f"the lease is {'' if new else 'not '}{w}" if k == "residential" else f"the lease is {new} {w}")
    if before["claim_type"] not in ("unknown", "other") and case["claim_type"] != before["claim_type"]:
        out.append("the kind of claim has changed")
    return ("Noted: " + "; ".join(out) + ".") if out else ""


def next_question(case, item):
    """Ask in our own words for the one thing still missing, naming only the part we do not already hold."""
    p = case["intake"]["parties"]
    if item == "claimant":
        return ("What is your full address, with unit number and postal code?" if p["claimant"]["name"]
                else "What is your name, and your full address with unit number and postal code?")
    if item == "respondent":
        r = p["respondent"]
        if not r.get("name") or not r.get("address"):
            return "Who are you claiming against? What is their full address, with postal code?"
        return f"Is {r['name']} in Singapore?"
    return NEXT_QUESTION[item]


def intake_followup(case):
    pending = intake_pending(case)
    return pending[0][1] if pending else None


def intake_pending(case):
    """A single source of truth for unanswered facts; uploads belong to step 3."""
    it = case["intake"]
    questions = [
        ("account", NEXT_QUESTION["story"]),
        ("claim_type", NEXT_QUESTION["category"]),
        ("claimant_name", "What is your full name?"),
        ("claimant_address", "What is your full address, including the postal code?"),
        ("respondent_name", "What is the other side's full name or business name?"),
        ("respondent_address", "What is the other side's full address, including the postal code?"),
        ("respondent_in_singapore", "Is the other side based in Singapore?"),
        ("what_agreed", NEXT_QUESTION["agreed"]),
        ("amount", NEXT_QUESTION["amount"]),
        ("cause_of_action_date", NEXT_QUESTION["when"]),
    ]
    if case["claim_type"] == "tenancy":
        questions += [("residential", "Was the rented property a home, rather than a shop or office?"),
                      ("lease_months", "How many months was the lease for?")]
    unavailable = set(it.get("unavailable", []))
    # Honour older cases whose unknown details were stored by checklist section.
    legacy = {"claimant": ("claimant_name", "claimant_address"), "respondent": ("respondent_name", "respondent_address"),
              "agreed": ("what_agreed",), "amount": ("amount",), "when": ("cause_of_action_date",)}
    for key in it.get("skipped", []):
        unavailable.update(legacy.get(key, ()))
    return [(key, question) for key, question in questions if key not in unavailable and known_value(case, key) is None]


def intake_next_step(case):
    gate = rules.gate(case, dt.date.fromisoformat(case["today"]))
    if not gate["pass"]:
        return "I have recorded what you know. Press Next to see which tribunal checks still need information. You can return here when you have it."
    if any(e["status"] == "ready" for e in case["exhibits"]):
        return INTAKE_COMPLETE
    needed = {"tenancy": "the agreement, payment records, messages, and photos",
              "goods": "the order, payment records, messages, and photos",
              "services": "the quote, payment records, messages, and photos",
              "property_damage": "messages, photos, videos, and repair quotes"}.get(case["claim_type"], "your evidence files")
    return f"I have recorded your claim details. Press Next to check if the tribunal can hear it, then add {needed} in step 3."


def chat_turn(case, message):
    snap = json.loads(json.dumps(case))
    it = case["intake"]
    if not it["chat"]:
        it["chat"].append({"who": "bot", "text": FIRST_MESSAGE})
    it["chat"].append({"who": "user", "text": message})
    if is_prompt_attack(message):
        it["chat"].append({"who": "bot", "text": SCOPE_REFUSAL})
        return recompute(case)
    previous_reply = next((m["text"] for m in reversed(snap["intake"]["chat"]) if m["who"] == "bot"), "")
    pending_before = intake_pending(snap)
    asked = snap.get("_pending_intake_field")
    if asked is None:
        asked = next((key for key, question in pending_before if previous_reply.endswith(question)), None)
    short_answer = message.strip().lower().rstrip(".! ")
    answering_boolean = asked in ("respondent_in_singapore", "residential") and short_answer in ("yes", "no", "yes they are", "no they are not")
    unknown_field = None
    if not answering_boolean and NO_DETAIL.fullmatch(short_answer):
        named = next((k for k, pat in NO_DETAIL_ITEM if re.search(pat, short_answer)), None)
        named = {"claimant": "claimant_address", "respondent": "respondent_address", "agreed": "what_agreed", "when": "cause_of_action_date"}.get(named, named)
        unknown_field = named or asked
        if unknown_field in ("account", "claim_type"):
            unknown_field = None
    if answering_boolean or unknown_field:
        turn = {"scope": "claim_intake", "confidence": "high", "reflection": None, "questions": [],
                "fields": {asked: short_answer.startswith("yes")} if answering_boolean else {}}
    else:
        turn = llm.intake_turn(case, case["checklist"])
    stated_amount = explicit_claim_amount(message)
    in_scope = turn.get("scope", "claim_intake") == "claim_intake"
    trusted_turn = in_scope and turn.get("confidence", "high") != "low"
    if stated_amount is not None and turn.get("scope", "claim_intake") not in ("off_topic", "prompt_attack"):
        # A stated total is a fact we can read ourselves. Keep it even when the model found the message unclear.
        if not trusted_turn:
            turn.update(scope="claim_intake", confidence="high", questions=[], reflection=None, fields={})
            trusted_turn = True
            in_scope = True
        turn.setdefault("fields", {})["amount"] = stated_amount
    corrected = []
    if unknown_field:
        if unknown_field not in it.setdefault("unavailable", []):
            it["unavailable"].append(unknown_field)
    if trusted_turn:
        if stated_amount is not None:
            turn.setdefault("fields", {})["amount"] = stated_amount
        apply_fields(case, turn.get("fields", {}))
    elif in_scope:
        corrected = apply_corrections(case, turn)
    if rules.ctype(case) != rules.ctype(snap):
        for ex in case["exhibits"]:   # files read before the kind of claim was known: read them again under its keys
            for a in ex["assets"]:
                if ex["status"] == "ready":
                    process_asset(case, ex, a)
    missing = [c["id"] for c in checklist_state(case) if not c["done"]]
    it["done"] = not missing
    blocked = [c for c in rules.gate(case, dt.date.fromisoformat(case["today"]))["checks"] if c["blocked"]]
    changed = describe_changes(snap, case)
    if changed:
        turn["reflection"] = None   # the change note already says it; do not say it twice
    if not isinstance(turn.get("reflection"), str):
        turn["reflection"] = None
    if turn.get("reflection") and any(m["who"] == "bot" and turn["reflection"] in m["text"] for m in it["chat"][:-1]):
        turn["reflection"] = None   # already said in an earlier turn; saying it again reads as not listening
    followup = intake_followup(case)
    next_step = followup or intake_next_step(case)
    if not in_scope:
        reply = (SCOPE_REFUSAL if turn.get("scope") in ("off_topic", "prompt_attack") else "I am not sure I understood that.") + " " + next_step
    elif not trusted_turn and not corrected:
        questions = [q for q in (_plain_sentence(q, max_words=22) for q in llm.question_list(turn.get("questions"))) if q and q.endswith("?")]
        reply = "I am not sure I understood that. " + (" ".join(questions[:2]) if questions else next_step)
    elif blocked:   # facts we already hold rule the claim out, so say that rather than ask for more
        reply = " ".join(c["text"] for c in blocked) + f" {blocked[0]['where']} Tell me if I have that wrong."
    else:
        # The server owns progression. A model instruction, repeated question or
        # empty reply must never leave only an acknowledgement on the screen.
        reflection = _plain_sentence(turn.get("reflection"), "You say", 22)
        reply = " ".join(x for x in (reflection, next_step) if x)
    if unknown_field:
        reply = "That detail is marked as not known. You can add it later. " + reply
    reply = f"{changed} {reply}".strip()
    case["_pending_intake_field"] = next((key for key, question in intake_pending(case) if reply.endswith(question)), None)
    it["chat"].append({"who": "bot", "text": reply})
    return recompute(case)


def checklist_state(case):
    it, p = case["intake"], case["intake"]["parties"]
    got = {"story": bool(it["account"]), "claimant": bool(p["claimant"]["name"] and p["claimant"]["address"]),
           "respondent": bool(p["respondent"]["name"] and p["respondent"]["address"]
                              and p["respondent"]["in_singapore"] is not None),
           "category": case["claim_type"] not in ("unknown", "other"), "agreed": bool(it.get("what_agreed")),
           "amount": it.get("amount") is not None, "when": bool(it.get("cause_of_action_date")),
           "files": any(e["status"] == "ready" for e in case["exhibits"])}
    skipped = it.get("skipped", [])
    return [{**c, "done": got.get(c["id"], False) or c["id"] in skipped} for c in case["checklist"]]


def recompute(case):
    case["checklist"] = checklist_state(case)
    case["intake"]["done"] = all(c["done"] for c in case["checklist"])
    today = dt.date.fromisoformat(case["today"])
    answers = {q["id"]: q.get("answer") for q in case.get("blindspots", {}).get("questions", [])}
    case["evidence"] = rules.evidence(case)
    case["unranked_evidence"] = rules.unranked_files(case)
    for ex in case["exhibits"]:
        for asset in ex["assets"]:
            asset["assessment"] = rules.asset_assessment(ex, asset)
            asset["removable"] = uploaded_asset_path(case, asset) is not None
    case["gate"] = rules.gate(case, today)
    case["gaps"] = rules.gaps(case)
    case["blindspots"] = rules.blindspots(case, answers)
    case["timeline"] = rules.timeline(case, today)
    case["next_steps"] = rules.next_steps(case)
    case["fee"] = rules.fee(case["intake"]["amount"])
    case["_assessment_version"] = 2
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
    case = new_case(today or dt.date.today(), sample=True)
    if include_chat:
        # Know the claim type before reading files, so each file is read only once
        # and ranked under the correct tenancy rules.
        _add_sample_chat(case)
    for ex in case["exhibits"]:
        for a in ex["assets"]:
            process_asset(case, ex, a, use_saved=True)
        ex["status"] = "ready"
    CASES[case["visitor"]] = recompute(case)
    return CASES[case["visitor"]]


def sample_is_ready(case):
    return bool(case and case.get("case_id") == "example"
                and case.get("intake", {}).get("done")
                and len(case.get("intake", {}).get("chat", [])) == 1 + 2 * len(llm.FIX["chat_user"])
                and len(case.get("exhibits", [])) == len(SAMPLE)
                and all(ex.get("status") == "ready" for ex in case.get("exhibits", [])))


def current():
    vid = VISITOR.get()
    case = CASES.get(vid)
    if case is None and (CASES_DIR / f"{vid}.json").exists():
        case = json.loads((CASES_DIR / f"{vid}.json").read_text(encoding="utf-8"))
    if case is None:
        case = recompute(new_case(dt.date.today()))
    CASES[vid] = case
    if case.get("_assessment_version") != 2:
        if case.get("case_id") == "example":
            for ex in case["exhibits"]:
                for asset in ex.get("assets", []):
                    # Update only bundled example files, never a user's upload with the same name.
                    if pathlib.Path(asset.get("path", "")).resolve().parent == PACK.resolve():
                        process_asset(case, ex, asset, use_saved=True)
        recompute(case)
    today = dt.date.today().isoformat()
    if case.get("today") != today:   # a saved case keeps its facts; only the date-driven parts move
        case["today"] = today
        case["gate"] = rules.gate(case, dt.date.today())
        case["timeline"] = rules.timeline(case, dt.date.today())
        save(case)
    return case


def err(code, message, status=400):
    return JSONResponse({"error": message, "code": code, "case": current()}, status_code=status)


def find_asset(case, asset_id):
    for ex in case["exhibits"]:
        for a in ex["assets"]:
            if a["id"] == asset_id:
                return ex, a
    return None, None


def uploaded_asset_path(case, asset):
    """Return the path only when it belongs to this visitor's upload directory."""
    try:
        root = (UPLOADS / case["visitor"]).resolve()
        path = pathlib.Path(asset.get("path", "")).resolve()
    except (OSError, TypeError, ValueError):
        return None
    return path if path != root and path.is_relative_to(root) else None


@app.post("/api/case/reset")
def reset():
    """Load the worked example (Mei Ling's deposit) from the sample pack."""
    # Browser Back or a double-click can leave an earlier reset running. Let that
    # one finish, then reuse it instead of reading all sample files a second time.
    global EXAMPLE
    with SAMPLE_LOCK:
        case = current()
        if sample_is_ready(case):
            return case
        if EXAMPLE is None or not sample_is_ready(EXAMPLE):
            EXAMPLE = build_sample(include_chat=True)
        case = json.loads(json.dumps(EXAMPLE))
        case["visitor"] = VISITOR.get()
        CASES[case["visitor"]] = case
        save(case)
        return case


@app.post("/api/case/new")
def new():
    CASES[VISITOR.get()] = recompute(new_case(dt.date.today()))
    return CASES[VISITOR.get()]


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
    case.pop("_pending_intake_field", None)
    return recompute(case)


@app.post("/api/upload")
async def upload(exhibit_id: str = Form(...), asset_id: str = Form(None), file: UploadFile = File(...),
                 side: str = Form(None), spot: str = Form(None), gap: str = Form(None)):
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
            if side == "theirs":   # added under "what the other side may have": their evidence, kept out of your ranking
                ex.update(side="theirs", spot=spot or "")
            if gap:   # added under a "what else to gather" heading: the card lists it even if the reader finds nothing
                ex["gap"] = gap
            case["exhibits"].append(ex)
        asset_id = asset_id or (exhibit_id if not ex["assets"] else f"{exhibit_id}-{len(ex['assets']) + 1}")
        UPLOADS.mkdir(parents=True, exist_ok=True)
        path = UPLOADS / case["visitor"] / asset_id / pathlib.Path(file.filename).name   # per visitor: E1 must never mean another person's E1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        asset = make_asset(asset_id, path, kind)   # opens the file (page_count for PDFs), so it is inside the guard
        ex["assets"] = [a for a in ex["assets"] if a["id"] != asset_id] + [asset]
        for p in extract.CACHE.glob(f"{extract.cache_key(asset_id, path)}_*"):
            p.unlink()
        ex["status"] = "reading"
        process_asset(case, ex, asset)
        ex["status"] = "ready"
        return recompute(case)   # recompute can also raise, so it stays inside the guard
    except Exception as exc:
        CASES[case["visitor"]] = snapshot   # roll back in-memory; do not save, so the file on disk is untouched
        return err("parse_failed", f"Could not read {file.filename} ({type(exc).__name__}).")


@app.post("/api/upload/remove")
def remove_upload(body: dict):
    """Remove one file and every derived fact, scoped to the current visitor."""
    case = current()
    asset_id = str(body.get("asset_id", ""))
    ex, asset = find_asset(case, asset_id)
    if not ex or not asset:
        return err("not_found", "No such uploaded file.", 404)
    path = uploaded_asset_path(case, asset)
    if path is None:
        return err("not_removable", "Only files you uploaded can be removed.")
    snapshot = json.loads(json.dumps(case))
    try:
        ex["facts"] = [f for f in ex.get("facts", []) if f.get("asset_id") != asset_id]
        ex["assets"] = [a for a in ex["assets"] if a["id"] != asset_id]
        if not ex["assets"]:
            case["exhibits"] = [item for item in case["exhibits"] if item is not ex]
        else:
            ex["status"] = "ready"
            if ex.get("title") == asset.get("filename"):
                ex["title"] = ex["assets"][0]["filename"]
        updated = recompute(case)
    except Exception as exc:
        case.clear(); case.update(snapshot)
        CASES[case["visitor"]] = case
        log.exception("Could not remove uploaded file")
        return err("remove_failed", f"Could not remove that file ({type(exc).__name__}).")
    try:
        cache_prefix = extract.cache_key(asset_id, path)
        path.unlink(missing_ok=True)
        for cached in extract.CACHE.glob(f"{cache_prefix}_*"):
            cached.unlink(missing_ok=True)
        if path.parent != (UPLOADS / case["visitor"]).resolve():
            path.parent.rmdir()
    except OSError:
        log.warning("Removed file from case but could not delete all stored bytes for %s", asset_id, exc_info=True)
    return updated


@app.post("/api/blindspot")
def blindspot(body: dict):
    case = current()
    if body.get("answer") not in ("yes", "no", "unsure"):
        return err("bad_answer", "answer must be yes, no or unsure")
    for q in case["blindspots"]["questions"]:
        if q["id"] == body.get("id"):
            q["answer"] = body["answer"]
    case["blindspots"] = rules.blindspots(case, {q["id"]: q.get("answer") for q in case["blindspots"]["questions"]})
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
        caption = f"{asset['filename']}. No text highlight is available. Check the file's relevance result."
    assessment = rules.asset_assessment(ex, asset)
    if assessment["status"] in ("placeholder", "irrelevant", "needs_review", "context"):
        caption = assessment["reason"]
    if asset.get("assessment_source") == "saved_example":
        caption = "Worked example, saved relevance result. " + caption
    return {"image_url": f"/api/render?asset_id={asset['id']}&page_index={page_index}", "boxes": boxes or [],
            "coord_space": "normalized", "caption": caption, "title": asset["filename"], "subtitle": sub,
            "label": label or ex["id"], "page_index": page_index, "pages": asset.get("pages", 1), "asset_id": asset["id"],
            "eyebrow": "The other side's file" if ex.get("side") == "theirs" else "Your file",
            "removable": uploaded_asset_path(case, asset) is not None}


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
