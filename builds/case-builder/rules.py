"""Every score, rank, gate, gap, blind spot, timeline entry and fee is a rule here. No model."""
import datetime as dt, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent


def content(name):
    return json.loads((ROOT / "content" / f"{name}.json").read_text(encoding="utf-8"))


KEY_ORDER = {"tenancy": ["deposit_terms", "deposit_paid", "handover_acceptance", "moveout_condition",
                         "damage_allegation", "movein_condition"],
             "goods": ["sale_terms", "payment_made", "seller_response", "fault_shown", "complaint_sent", "delivery"],
             "general": ["agreement_terms", "payment_made", "other_side_words", "condition_shown", "complaint_sent", "dispute"]}
CATEGORY_TEXT = {"goods": "a contract for the sale of goods", "services": "a contract for the provision of services",
                 "property_damage": "damage to property, not from a motor accident"}


def ctype(case):
    """Content set for this claim: tenancy and goods have their own, everything else shares the general one."""
    return case["claim_type"] if case["claim_type"] in ("tenancy", "goods") else "general"
CAT_WEIGHT = {"agreement": 0, "payment": 1, "other_side_words": 2, "condition": 3, "dispute": 4}
STRENGTH_ORDER = {"strong": 0, "medium": 1, "weak": 2}
AUTHOR = {"both": "Signed by both of you", "third_party": "Third-party record",
          "respondent": "The other side's own words", "claimant": "Made by you"}
TIMELINE_LABEL = {"deposit_paid": "deposit paid", "handover_acceptance": 'Move out, "all good"',
                  "damage_allegation": "{role} refuses", "payment_made": "paid", "delivery": "delivered",
                  "complaint_sent": "you complained", "seller_response": "{role} replies"}
FUTURE_STEPS = [("written_request", "Written request", "next"), ("prefiling", "Pre-filing check, then file on CJTS", ""),
                ("serve", "Serve within 7 working days", ""), ("consultation", "Consultation", ""), ("hearing", "Hearing", "")]


def d(s):
    return dt.date.fromisoformat(s) if s else None


def fmt(date):
    return f"{date.day} {date.strftime('%b %Y')}" if date else ""


def money(x):
    return f"${x:,.0f}"


def plus_years(date, n):
    try:
        return date.replace(year=date.year + n)
    except ValueError:
        return date.replace(year=date.year + n, day=28)


def _facts(case):
    """Yield (exhibit, asset, fact) for every fact kept after locating."""
    for ex in case["exhibits"]:
        assets = {a["id"]: a for a in ex["assets"]}
        for f in ex.get("facts", []):
            yield ex, assets[f["asset_id"]], f


def source_label(ex, asset, fact, locator):
    n = len(ex["assets"])
    if asset["kind"] == "pdf":
        page = f"p.{locator['page_index'] + 1}" if locator else ""
        return " ".join(x for x in [ex["id"], (fact.get("where") or "") + ("," if fact.get("where") and page else ""), page] if x).strip()
    if asset["kind"] == "video":
        return f"{ex['id']} video, {fact.get('where') or '0:00'}"
    if n > 1:
        idx = [a["id"] for a in ex["assets"]].index(asset["id"]) + 1
        return f"{ex['id']} shot {idx}" if ex["kind"] == "image_set" and "WhatsApp" in ex["title"] else f"{ex['id']} photo {idx}"
    return ex["id"]


def strength(meta, fact):
    dated = bool(meta.get("dated") or fact.get("date"))
    has_amount = bool(meta.get("has_amount") or fact.get("amount"))
    if meta.get("author") in ("both", "third_party", "respondent") and dated and has_amount:
        return "strong"
    if dated and (meta.get("author") != "claimant" or fact.get("category") == "condition"):
        return "medium"
    return "weak"


def evidence(case):
    order = KEY_ORDER[ctype(case)]
    rows = {}
    for ex, asset, f in _facts(case):
        key = f.get("evidence_key")
        if not key:
            continue
        meta = asset.get("meta", {})
        row = rows.setdefault(key, {"id": key, "evidence_key": key, "what": f["fact"], "category": f["category"],
                                    "date": f.get("date"), "strength": "weak", "needs_check": False,
                                    "notes": [], "sources": [], "_authors": set(), "_dated": False, "_amount": False})
        s = strength(meta, f)
        if STRENGTH_ORDER[s] < STRENGTH_ORDER[row["strength"]]:
            row["strength"] = s
        if f.get("quote") and meta.get("from_picture"):
            row["needs_check"] = True
        if f.get("note") and f["note"] not in row["notes"]:
            row["notes"].append(f["note"])
        row["_authors"].add(meta.get("author"))
        row["_dated"] |= bool(meta.get("dated") or f.get("date"))
        row["_amount"] |= bool(meta.get("has_amount") or f.get("amount"))
        row["date"] = row["date"] or f.get("date")
        row["sources"].append({"exhibit_id": ex["id"], "asset_id": asset["id"],
                               "label": source_label(ex, asset, f, f.get("locator")),
                               "locator": f.get("locator"), "quote": f.get("quote"), "fact": f["fact"]})
    out = []
    for row in rows.values():
        if row["notes"]:
            reason = ", ".join(row["notes"]) if len(row["notes"]) == 1 else row["notes"][0]
        else:
            a = next(iter(row["_authors"]), "claimant")
            reason = AUTHOR.get(a, "Made by you") + (", has amount" if row["_amount"] else "") + \
                     (" and dates" if row["_amount"] and row["_dated"] else ", dated" if row["_dated"] else ", no date")
        if row["needs_check"]:
            reason += ". Read from a screenshot, check it"
        row["reason"] = reason
        for k in ("_authors", "_dated", "_amount", "notes"):
            row.pop(k)
        out.append(row)
    out.sort(key=lambda r: (STRENGTH_ORDER[r["strength"]], CAT_WEIGHT.get(r["category"], 9),
                            order.index(r["evidence_key"]) if r["evidence_key"] in order else 99))
    for i, r in enumerate(out, 1):
        r["rank"] = i
        for j, s in enumerate(r["sources"]):
            s["viewer_url"] = f"/api/viewer?evidence_id={r['id']}&source_index={j}"
    return out


def gate(case, today):
    it = case["intake"]
    role = it["parties"]["respondent"].get("role") or "other side"
    amt, cause = it.get("amount"), d(it.get("cause_of_action_date"))
    prem = it.get("premises", {})
    ct = case["claim_type"]
    if ct == "tenancy":
        cat_ok = bool(prem.get("residential")) and (prem.get("lease_months") or 0) <= 24
        cat_text = "Your claim fits a CJTS category: lease not exceeding 2 years (residential premises), refund of rental deposit."
        if prem.get("residential") is None or prem.get("lease_months") is None:
            cat_ok, cat_text = False, "Tell us if the place was your home, and how long the lease was."
        elif not cat_ok:
            cat_text = "A lease over 2 years, or a shop or office lease, is not a CJTS category."
    elif ct in CATEGORY_TEXT:
        cat_ok, cat_text = True, f"Your claim fits a CJTS category: {CATEGORY_TEXT[ct]}."
    elif ct == "other":
        cat_ok, cat_text = False, ("This does not fit a CJTS category. The tribunal hears contracts for goods or services, "
                                   "home leases up to 2 years, and damage to property not from a motor accident.")
    else:
        cat_ok, cat_text = False, "Tell us what happened so we can check which CJTS category fits."
    amt_ok = amt is not None and (amt <= 20000 or (it.get("consent_30k") and amt <= 30000))
    bar = plus_years(cause, 2) if cause else None
    time_ok = bool(cause) and today <= bar
    in_sg = it["parties"]["respondent"].get("in_singapore")
    served_ok = bool(in_sg)
    checks = [
        {"id": "category", "pass": cat_ok, "section_id": "scta_schedule", "text": cat_text},
        {"id": "amount", "pass": amt_ok, "section_id": "scta_s2",
         "text": (f"You are claiming {money(amt)}. The limit is $20,000, or $30,000 if both sides agree." if amt is not None
                  else "Tell us how much you are claiming. The limit is $20,000, or $30,000 if both sides agree.")},
        {"id": "time", "pass": time_ok, "section_id": "scta_s5_time",
         "text": (f"Date of cause of action: {fmt(cause)}, when the {role} refused. You have 2 years, so until {fmt(bar)}."
                  if cause else "Tell us the date the other side refused, or the problem started.")},
        {"id": "service", "pass": served_ok, "section_id": "scta_s5_service",
         "text": f"The {role} is in Singapore, so the claim can be served." if served_ok
         else f"Tell us if the {role} is in Singapore." if in_sg is None
         else f"The {role} is outside Singapore. The tribunal cannot serve a claim outside Singapore."},
    ]
    ok = all(c["pass"] for c in checks)
    where = {"category": "Try CASE mediation, the Employment Claims Tribunals for work matters, or the Magistrate's Court.",
             "amount": "A claim over the limit goes to the Magistrate's Court (up to $60,000) or the District Court.",
             "time": "More than 2 years have passed. The civil courts, for example the Magistrate's Court, may still hear it.",
             "service": "The Magistrate's Court can serve outside Singapore. Ask the court registry."}
    failed = [c for c in checks if not c["pass"]]
    stop = None if ok else "This check did not pass: " + failed[0]["text"] + " " + where[failed[0]["id"]]
    return {"pass": ok, "checks": checks, "stop": stop,
            "result": "All four checks pass. You can continue." if ok else "The tribunal cannot hear this claim as it stands."}


def gaps(case):
    g = content("gaps")
    to_key = g["category_to_key"]
    have = {}
    for ex in case["exhibits"]:
        keys = {to_key.get(f["category"]) for f in ex.get("facts", [])} - {None}
        for k in keys:
            have.setdefault(k, []).append(f"{ex['title']} ({ex['id']})")
    return [{"key": c["key"], "category": c["category"], "why": c["why"],
             "have": have.get(c["key"]) or ["Nothing yet"], "missing": c["missing"]}
            for c in g[ctype(case)]]


def blindspots(case, answers):
    b = content("blindspots")[ctype(case)]
    qs = [{**q, "answer": answers.get(q["id"])} for q in b["questions"]]
    return {"intro": b["intro"], "note": b["note"], "total": len(qs),
            "answered": sum(1 for q in qs if q["answer"] in ("yes", "no", "unsure")), "questions": qs}


def timeline(case, today):
    it = case["intake"]
    role = it["parties"]["respondent"].get("role") or "other side"
    by_date = {}
    deposit_src = None
    exact = {(s["asset_id"], s.get("quote")): s["viewer_url"] for r in case.get("evidence", []) for s in r["sources"]}
    for ex, asset, f in _facts(case):
        src = {"exhibit_id": ex["id"], "asset_id": asset["id"], "label": source_label(ex, asset, f, f.get("locator")),
               "viewer_url": exact.get((asset["id"], f.get("quote")),
                                       f"/api/viewer?asset_id={asset['id']}&page_index={(f.get('locator') or {}).get('page_index', 0)}")}
        if f.get("evidence_key") == "deposit_terms":
            deposit_src = src
        if not f.get("date"):
            continue
        ev = by_date.setdefault(f["date"], {"labels": [], "exhibits": [], "details": [], "sources": []})
        lab = f.get("timeline_label") or TIMELINE_LABEL.get(f.get("evidence_key"))
        if lab and lab.format(role=role.capitalize()) not in ev["labels"]:
            ev["labels"].append(lab.format(role=role.capitalize()))
        if ex["id"] not in ev["exhibits"]:
            ev["exhibits"].append(ex["id"])
        ev["details"].append(f["fact"] + (f' ("{f["quote"]}")' if f.get("quote") else ""))
        ev["sources"].append(src)
    events = []
    for date, ev in sorted(by_date.items()):
        label = ", ".join(ev["labels"]) or "Event"
        label = label[0].upper() + label[1:]
        events.append({"id": f"d_{date}", "label": f"{label} ({', '.join(ev['exhibits'])})", "date": date,
                       "future": False, "marker": False, "computed": False,
                       "detail": ". ".join(ev["details"]) + ".", "sources": ev["sources"]})
    moveout = d(it.get("moveout_date")) or next((d(f["date"]) for _, _, f in _facts(case)
                                                 if f.get("evidence_key") == "handover_acceptance" and f.get("date")), None)
    days = it.get("premises", {}).get("refund_days")
    if moveout and days:
        due = moveout + dt.timedelta(days=days)
        lab = deposit_src["label"] if deposit_src else "agreement"
        events.append({"id": "refund_due", "label": f"Refund due ({lab})", "date": due.isoformat(), "future": False,
                       "marker": False, "computed": True,
                       "detail": f"{days} days after move-out on {fmt(moveout)}, under {lab}.",
                       "sources": [deposit_src] if deposit_src else []})
    events.sort(key=lambda e: e["date"])
    events.append({"id": "today", "label": "Today", "date": today.isoformat(), "future": False, "marker": True,
                   "computed": True, "detail": "Where you are now.", "sources": []})
    for i, (eid, lab, when) in enumerate(FUTURE_STEPS):
        events.append({"id": eid, "label": lab, "date": None, "date_text": when, "future": True, "marker": False,
                       "computed": True, "detail": "A step still ahead. See Next steps.", "sources": []})
    cause = d(it.get("cause_of_action_date"))
    if cause:
        bar = plus_years(cause, 2)
        events.append({"id": "time_bar", "label": "Time bar", "date": bar.isoformat(), "future": True, "marker": True,
                       "computed": True, "detail": f"2 years after {fmt(cause)}, the date the {role} refused. Latest filing date.",
                       "sources": []})
    return events


def fee(amount):
    ns = content("nextsteps")
    if amount is None:
        return {}
    for f in ns["fees"]:
        if f["max"] is None or amount <= f["max"]:
            amt = f.get("amount", round(amount * f.get("percent", 0) / 100, 2))
            return {"amount": amt, "basis": f["basis"], "source_label": ns["fee_source"]["label"],
                    "source_url": ns["fee_source"]["url"]}


def next_steps(case):
    return content("nextsteps")[ctype(case)]


if __name__ == "__main__":   # rank self-check: the frozen table must sort to ranks 1-6
    fx = content("fixtures")["files"]
    case = {"claim_type": "tenancy", "exhibits": []}
    for i, (name, kind) in enumerate([("Tenancy_Agreement_2025.pdf", "pdf"), ("deposit_transfer.jpg", "image"),
                                      ("WhatsApp_04.png", "image"), ("moveout_walkthrough.mp4", "video"),
                                      ("WhatsApp_05.png", "image"), ("movein_01.jpg", "image")]):
        a = {"id": f"A{i}", "kind": kind, "meta": fx[name]["meta"]}
        case["exhibits"].append({"id": f"E{i}", "kind": kind, "title": name, "assets": [a],
                                 "facts": [{**f, "asset_id": a["id"]} for f in fx[name]["facts"]]})
    rows = evidence(case)
    got = [r["evidence_key"] for r in rows]
    assert got == KEY_ORDER["tenancy"], got
    assert [r["strength"] for r in rows] == ["strong", "strong", "medium", "medium", "medium", "weak"]
    assert [r["needs_check"] for r in rows] == [False, True, True, False, True, False]
    assert fee(2600)["amount"] == 10 and fee(12000)["amount"] == 120
    print("rules ok:", got)
