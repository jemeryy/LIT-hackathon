"""The only file that talks to a model. Two jobs: read facts off one file, write three short texts.
USE_FIXTURES=1 (or no key) returns content/fixtures.json so every lane runs without credits."""
import base64, io, json, os, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
FIX = json.loads((ROOT / "content" / "fixtures.json").read_text(encoding="utf-8"))

EVIDENCE_KEYS = {
    "tenancy": {
        "deposit_terms": "what the agreement says about the deposit and its refund",
        "deposit_paid": "proof the deposit was paid",
        "handover_acceptance": "the other side accepting the flat at handover",
        "moveout_condition": "condition of the flat when the tenant left",
        "damage_allegation": "the other side claiming damage or refusing the refund",
        "movein_condition": "condition of the flat when the tenant moved in",
    },
    "goods": {
        "sale_terms": "what was ordered, price, description",
        "payment_made": "proof of payment",
        "fault_shown": "the fault in the goods",
        "complaint_sent": "the buyer telling the seller about the fault",
        "seller_response": "the seller refusing or replying",
        "delivery": "delivery or collection record",
    },
}
EVIDENCE_KEYS["general"] = {
    "agreement_terms": "what the contract, quote or order says was promised",
    "payment_made": "proof of payment",
    "other_side_words": "the other side admitting, promising or refusing",
    "condition_shown": "the state of the work, item or property",
    "complaint_sent": "the claimant telling the other side about the problem",
    "dispute": "the other side refusing or disputing",
}
CATEGORIES = ["agreement", "payment", "other_side_words", "condition", "dispute"]
PARTIES = ["claimant", "respondent", "both", "third_party"]


def load_env():
    """Tiny stdlib .env loader: first .env found walking up from this folder."""
    for d in [ROOT, *ROOT.parents]:
        p = d / ".env"
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return p
    return None


load_env()
API_KEY = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
MODEL = os.environ.get("MODEL", "anthropic/claude-sonnet-5")
BASE_URL = os.environ.get("ANTHROPIC_BASE_URL")


def use_fixtures():
    return os.environ.get("USE_FIXTURES", "1") == "1" or not API_KEY   # real calls only when USE_FIXTURES=0


def _client():
    import anthropic
    return anthropic.Anthropic(api_key=API_KEY, base_url=BASE_URL)


def _tool_call(system, content, tool, max_tokens=1500):
    resp = _client().messages.create(model=MODEL, max_tokens=max_tokens, system=system, tools=[tool],
                                     tool_choice={"type": "tool", "name": tool["name"]},
                                     messages=[{"role": "user", "content": content}])
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("model returned no tool call")


def _image_block(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((1400, 1400))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.b64encode(buf.getvalue()).decode()}}


SYSTEM_FACTS = ("You read one piece of evidence for a person filing at the Singapore Small Claims Tribunals. "
                "Report only what is on the file. Never guess a date, amount or name. Every fact that rests on text "
                "must carry an exact quote copied from the text you were given (copy OCR text as is, typos included). "
                "A photo or video with no useful text gets quote null. No legal advice, no opinion on who is right.")


def extract_facts(asset, text, case, image_path=None):
    """-> {meta: {author, signed, dated, has_amount, from_picture}, facts: [...]}"""
    if use_fixtures():
        return FIX["files"].get(asset["filename"], {"meta": {"author": "claimant", "signed": False, "dated": False,
                                                              "has_amount": False, "from_picture": True}, "facts": []})
    keys = EVIDENCE_KEYS.get(case["claim_type"], EVIDENCE_KEYS["general"])
    tool = {"name": "record_facts", "description": "Record the facts this file shows.",
            "input_schema": {"type": "object", "properties": {
                "author": {"type": "string", "enum": PARTIES, "description": "who made the file: both = a document signed by both sides; third_party = bank, courier, agent, government; respondent = the other side wrote it; claimant = the person claiming wrote or took it"},
                "signed": {"type": "boolean", "description": "the file carries signatures"},
                "dated": {"type": "boolean", "description": "the file itself shows a date"},
                "has_amount": {"type": "boolean", "description": "the file shows a money amount"},
                "facts": {"type": "array", "maxItems": 3, "items": {"type": "object", "properties": {
                    "evidence_key": {"type": ["string", "null"], "enum": [*keys, None]},
                    "category": {"type": "string", "enum": CATEGORIES},
                    "fact": {"type": "string", "description": "one plain sentence, under 90 characters"},
                    "date": {"type": ["string", "null"], "description": "YYYY-MM-DD or null"},
                    "party": {"type": "string", "enum": PARTIES},
                    "amount": {"type": ["number", "null"]},
                    "where": {"type": ["string", "null"], "description": "clause number or video time, if any"},
                    "note": {"type": ["string", "null"], "description": "why it matters, under 80 characters"},
                    "quote": {"type": ["string", "null"], "description": "exact words copied from the text, 4 to 15 words"},
                    "timeline_label": {"type": ["string", "null"]}},
                    "required": ["evidence_key", "category", "fact", "date", "party", "amount", "quote"]}}},
                "required": ["author", "signed", "dated", "has_amount", "facts"]}}
    parties = case["intake"]["parties"]
    prompt = (f"Claim type: {case['claim_type']}. Claimant: {parties['claimant']['name']}. "
              f"Respondent: {parties['respondent']['name']}.\n"
              f"Claimant's own account: {case['intake'].get('account', '')}\n\n"
              f"Evidence keys you may assign (or null if none fits):\n" +
              "\n".join(f"- {k}: {v}" for k, v in keys.items()) +
              "\n\nRules: at most 3 facts, at most one per evidence key, only facts that matter to the claim. "
              "Skip greetings, plans and requests for photos. In a chat screenshot quote the other side's words first. "
              "party = who wrote the quoted words. author = who made the whole file." +
              f"\n\nFile: {asset['filename']} ({asset['kind']}).\nText read from the file:\n<<<\n{text[:12000]}\n>>>")
    content = [{"type": "text", "text": prompt}]
    if image_path:
        content.append(_image_block(image_path))
    return _clean(_tool_call(SYSTEM_FACTS, content, tool), asset)


def _clean(raw, asset):
    """The model's tool input is untrusted: keep only well-formed facts, log the raw reply for the dry-run notes."""
    with open(ROOT / "data" / "llm_log.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"file": asset["filename"], "raw": raw}, ensure_ascii=False) + "\n")
    m = raw.get("meta") if isinstance(raw.get("meta"), dict) else raw   # flat fields, or the old nested shape
    facts = []
    for f in raw.get("facts") or []:
        if isinstance(f, str):
            try:
                f = json.loads(f)
            except ValueError:
                continue
        if not isinstance(f, dict) or not f.get("fact"):
            continue
        facts.append({"evidence_key": f.get("evidence_key") or None,
                      "category": f.get("category") if f.get("category") in CATEGORIES else "other_side_words",
                      "fact": str(f["fact"])[:120], "date": f.get("date") or None,
                      "party": f.get("party") if f.get("party") in PARTIES else "claimant",
                      "amount": f.get("amount") if isinstance(f.get("amount"), (int, float)) else None,
                      "where": f.get("where") or None, "note": f.get("note") or None,
                      "quote": f.get("quote") or None, "timeline_label": f.get("timeline_label") or None})
    parties = {f["party"] for f in facts}
    guess = "both" if asset["kind"] == "pdf" and parties >= {"claimant", "respondent"} else (
        next(iter(parties)) if len(parties) == 1 else "claimant")
    author = m.get("author") if m.get("author") in PARTIES else guess
    if author == "both" and asset["kind"] != "pdf" and not m.get("signed"):      # a chat is nobody's signed document
        author = "respondent" if "respondent" in parties else "claimant"
    meta = {"author": author,   # the model may skip the flags
            "signed": bool(m.get("signed")),
            "dated": bool(m.get("dated")) or any(f["date"] for f in facts),
            "has_amount": bool(m.get("has_amount")) or any(f["amount"] for f in facts),
            "from_picture": asset["kind"] != "pdf"}
    return {"meta": meta, "facts": facts}


SYSTEM_TEXT = ("You write for a person filing at the Singapore Small Claims Tribunals without a lawyer. Plain words a "
               "child could read. Use only the facts given. Never invent a date, amount, name or law. No legal advice.")

TEXT_SPECS = {
    "story": ("Write one short paragraph (3 sentences, second person: 'You rented...') telling what happened, "
              "in date order, using only the facts and evidence below.", 300),
    "summary": ("Write the claim summary for the CJTS claim form, first person, at most 500 characters, in date "
                "order, ending with what is claimed.", 400),
    "written_request": ("Write a polite letter from the claimant to the respondent asking for the money, citing the "
                        "agreement clause and the dates, giving 7 days to reply, and saying the next step is a "
                        "Small Claims Tribunals claim. Use [date] where a reply date goes.", 700),
}


def write_text(kind, case):
    if use_fixtures():
        return FIX["texts"][kind]
    instr, max_tokens = TEXT_SPECS[kind]
    facts = "\n".join(f"- {r['what']} (source {r['sources'][0]['label']})" for r in case.get("evidence", []))
    p = case["intake"]["parties"]
    events = "\n".join(f"- {e['date']}: {e['label']}. {e['detail']}" for e in case.get("timeline", [])
                       if e.get("date") and not e.get("future") and e["id"] != "today")
    prompt = (f"{instr}\n\nClaimant: {p['claimant']['name']}, {p['claimant'].get('address', '')}\n"
              f"Respondent: {p['respondent']['name']} (the {p['respondent'].get('role', 'other side')}), "
              f"lives at {p['respondent'].get('address', '')}\n"
              f"The claim is about: {case['intake'].get('what_agreed', '')}\n"
              f"Dated events (use these dates, no others):\n{events}\n"
              f"Amount claimed: ${case['intake']['amount']:,.0f}\nClaim type: {case['claim_type']}\n"
              f"Claimant's own account: {case['intake'].get('account', '')}\n\nFacts from the files:\n{facts}")
    tool = {"name": "write", "description": "Return the text.",
            "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}
    out = _tool_call(SYSTEM_TEXT, [{"type": "text", "text": prompt}], tool, max_tokens)
    with open(ROOT / "data" / "llm_log.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"text": kind, "raw": out}, ensure_ascii=False) + "\n")
    text = str(out.get("text") or next((v for v in out.values() if isinstance(v, str)), "")).strip()
    if not text:   # the model returned nothing usable: fall back to the dated events, never to an empty screen
        text = " ".join(f"{e['date']}: {e['label']}." for e in case.get("timeline", []) if e.get("date") and not e.get("future"))
    if kind == "summary" and len(text) > 500:
        cut = text[:500]
        text = cut[:max(cut.rfind(". "), cut.rfind(".\n"), 0) + 1] or cut
    return text


SYSTEM_INTAKE = ("You gather the facts for a person filing a claim at the Singapore Small Claims Tribunals without a lawyer. "
                 "Plain words a child could read. Ask for one or two things at a time and say why each is needed. "
                 "Record only what the person told you. Never guess a name, date or amount. Never give legal advice, "
                 "never say who is right, never predict the outcome. Files are added by the person on the side panel, "
                 "not by you. When every item on the checklist is known, say so and set done.")

CLAIM_TYPES = ["tenancy", "goods", "services", "property_damage", "other", "unknown"]
INTAKE_FIELDS = {
    "claim_type": {"type": "string", "enum": CLAIM_TYPES, "description": "tenancy = home lease up to 2 years (deposit, rent); goods = bought or sold an item; services = work done or not done; property_damage = damage to property not from a motor accident; other = none of these; unknown = not clear yet"},
    "respondent_role": {"type": ["string", "null"], "description": "one or two plain words: landlord, tenant, seller, buyer, contractor, neighbour"},
    "claimant_name": {"type": ["string", "null"]}, "claimant_address": {"type": ["string", "null"]},
    "respondent_name": {"type": ["string", "null"]}, "respondent_address": {"type": ["string", "null"]},
    "respondent_in_singapore": {"type": ["boolean", "null"]}, "respondent_is_company": {"type": ["boolean", "null"]},
    "what_agreed": {"type": ["string", "null"], "description": "what the two sides agreed, in one or two sentences"},
    "amount": {"type": ["number", "null"], "description": "amount claimed in dollars"},
    "cause_of_action_date": {"type": ["string", "null"], "description": "YYYY-MM-DD the other side refused or the problem started"},
    "moveout_date": {"type": ["string", "null"], "description": "YYYY-MM-DD, tenancy only"},
    "residential": {"type": ["boolean", "null"], "description": "tenancy only: the place was a home"},
    "lease_months": {"type": ["integer", "null"], "description": "tenancy only"},
    "refund_days": {"type": ["integer", "null"], "description": "tenancy only: days the agreement gives to refund the deposit"},
}


def intake_turn(case, checklist):
    """One chat turn -> {reply, fields, done}. Fixtures replay the scripted Mei Ling conversation."""
    it = case["intake"]
    n_user = sum(1 for m in it["chat"] if m["who"] == "user")
    if use_fixtures():
        return FIX["chat"][min(n_user, len(FIX["chat"])) - 1]
    known = {k: v for k, v in it.items() if k not in ("chat", "account", "parties", "premises") and v not in (None, "", [])}
    known.update({k: v for k, v in it.get("premises", {}).items() if v is not None})
    known.update({f"claimant_{k}": v for k, v in it["parties"]["claimant"].items() if v})
    known.update({f"respondent_{k}": v for k, v in it["parties"]["respondent"].items() if v is not None and v != ""})
    known["claim_type"] = case["claim_type"]
    tool = {"name": "update_intake", "description": "Record what the person said and reply.",
            "input_schema": {"type": "object", "properties": {
                "reply": {"type": "string", "description": "what you say next: acknowledge in one sentence, then ask for the next missing item(s) with the reason, under 80 words"},
                "done": {"type": "boolean", "description": "true when every checklist item is known"},
                **INTAKE_FIELDS}, "required": ["reply", "done", "claim_type"]}}
    prompt = ("Checklist of what you must learn:\n" + "\n".join(f"- {c['label']}: {c['why']}" for c in checklist) +
              f"\n\nAlready known (do not ask again): {json.dumps(known, ensure_ascii=False)}\n"
              f"Files added so far: {', '.join(e['title'] for e in case['exhibits']) or 'none'}\n\n"
              "Conversation so far:\n" + "\n".join(f"{m['who']}: {m['text']}" for m in it["chat"]) +
              "\n\nSet every field the person has told you (keep known ones as they are), then write the reply.")
    out = _tool_call(SYSTEM_INTAKE, [{"type": "text", "text": prompt}], tool, 800)
    with open(ROOT / "data" / "llm_log.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"chat": n_user, "raw": out}, ensure_ascii=False) + "\n")
    fields = {k: out.get(k) for k in INTAKE_FIELDS if out.get(k) is not None}
    if fields.get("claim_type") not in CLAIM_TYPES:
        fields.pop("claim_type", None)
    return {"reply": str(out.get("reply") or "Tell me more about what happened."), "fields": fields, "done": bool(out.get("done"))}
