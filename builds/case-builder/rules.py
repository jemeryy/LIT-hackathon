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
    ct = case["claim_type"]
    role = (case.get("intake", {}).get("parties", {}).get("respondent", {}).get("role") or "").lower()
    if ct == "tenancy" and role.startswith("tenant"):
        return "general"   # the tenancy set is written for a tenant claiming a deposit; a landlord gets the general set
    if ct == "goods" and (role.startswith("buyer") or role.startswith("customer")):
        return "general"   # the goods set is written for a buyer; a seller chasing a buyer gets the general set
    return ct if ct in ("tenancy", "goods") else "general"
CAT_WEIGHT = {"agreement": 0, "payment": 1, "other_side_words": 2, "condition": 3, "dispute": 4}
STRENGTH_ORDER = {"strong": 0, "medium": 1, "weak": 2, "context": 3, "needs_review": 4, "irrelevant": 5, "placeholder": 6}
AUTHOR = {"both": "Signed by both of you", "third_party": "Third-party record",
          "respondent": "The other side's own words", "claimant": "Made by you"}
TIMELINE_LABEL = {"deposit_paid": "deposit paid", "handover_acceptance": 'Move out, "all good"',
                  "damage_allegation": "{role} refuses", "payment_made": "paid", "delivery": "delivered",
                  "complaint_sent": "you complained", "seller_response": "{role} replies", "sale_terms": "agreed",
                  "agreement_terms": "agreed", "other_side_words": "{role} says", "dispute": "{role} refuses"}
FUTURE_STEPS = [("written_request", "Send your letter", "next"), ("prefiling", "File your claim online", ""),
                ("serve", "Give the other side a copy", ""), ("consultation", "First court meeting", ""), ("hearing", "Hearing", "")]


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
        if ex.get("side") == "theirs":   # a file added under "what the other side may have" is their evidence, not yours
            continue
        assets = {a["id"]: a for a in ex["assets"]}
        for f in ex.get("facts", []):
            asset = assets[f["asset_id"]]
            if related_fact(f) and asset_assessment(ex, asset)["status"] in ("relevant", "context"):
                yield ex, asset, f


def relevant_fact(f):
    return bool(f.get("evidence_key")) and f.get("fits") is not False


def related_fact(f):
    return f.get("fits") is not False and (bool(f.get("evidence_key")) or bool(f.get("context")))


def asset_assessment(ex, asset):
    """Use the read result, never the heading a user chose, to assess a file."""
    facts = [f for f in ex.get("facts", []) if f.get("asset_id") == asset["id"]]
    if asset.get("relevance") == "placeholder":
        return {"status": "placeholder", "reason": asset.get("relevance_reason") or "This is a placeholder, not a photo or recording of the event. It cannot establish the condition shown."}
    if ex.get("status", "ready") != "ready" or asset.get("review_reason"):
        return {"status": "needs_review", "reason": asset.get("review_reason") or "This file has not finished being read."}
    if asset.get("relevance") != "irrelevant":
        if any(relevant_fact(f) for f in facts):
            return {"status": "relevant", "reason": "Claim-related facts found in this file."}
        if any(related_fact(f) for f in facts) or asset.get("relevance") == "context":
            return {"status": "context", "reason": asset.get("relevance_reason") or "Related background or correspondence. Retained as context; it does not independently establish a ranked point."}
    mismatch = next((f for f in facts if f.get("fits") is False), None)
    if not mismatch and asset.get("relevance") != "irrelevant":
        return {"status": "needs_review", "reason": "No usable fact was extracted. That does not establish that the file is irrelevant. Open it to check its connection to the claim."}
    reason = asset.get("relevance_reason") or (mismatch["fact"] if mismatch else "The reader found no facts connecting this file to this claim.")
    return {"status": "irrelevant", "reason": reason + " Not counted as evidence. Open the file to check its relevance."}


def unranked_files(case, side="yours"):
    rows = []
    for ex in case["exhibits"]:
        if (ex.get("side") == "theirs") != (side == "theirs"):
            continue
        for asset in ex.get("assets", []):
            assessment = asset_assessment(ex, asset)
            if assessment["status"] == "relevant":
                continue
            description = asset.get("filename") or ex["title"]
            if assessment["status"] == "context":
                description = next((f["fact"] for f in ex.get("facts", []) if f.get("asset_id") == asset["id"] and related_fact(f)), description)
            rows.append({"id": "unranked_" + asset["id"], "rank": None,
                         "what": description, "strength": assessment["status"],
                         "reason": assessment["reason"], "why": assessment["reason"], "needs_check": True,
                         "sources": [{"exhibit_id": ex["id"], "asset_id": asset["id"], "label": ex["id"],
                                      "title": asset.get("filename") or ex["title"],
                                      "viewer_url": asset.get("viewer_url") or f"/api/viewer?asset_id={asset['id']}&page_index=0"}]})
    return sorted(rows, key=lambda r: STRENGTH_ORDER[r["strength"]])


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
        cat_known = prem.get("residential") is not None and prem.get("lease_months") is not None
        cat_ok = bool(prem.get("residential")) and (prem.get("lease_months") or 0) <= 24
        cat_text = "The tribunal hears this kind of claim: a dispute under a home lease of 2 years or less."
        if not cat_known:
            cat_ok, cat_text = False, "Tell us if the place was your home, and how long the lease was."
        elif not cat_ok:
            cat_text = "The tribunal does not hear a lease over 2 years, or a shop or office lease."
    elif ct in CATEGORY_TEXT:
        cat_known, cat_ok, cat_text = True, True, f"The tribunal hears this kind of claim: {CATEGORY_TEXT[ct]}."
    elif ct == "other":
        cat_known, cat_ok, cat_text = True, False, ("The tribunal does not hear this kind of claim. It hears contracts for goods or services, "
                                   "home leases up to 2 years, and damage to property. It does not hear work disputes, loans, "
                                   "or a neighbour dispute about noise, smell or the like.")
    else:
        cat_known, cat_ok = False, False
        cat_text = "Tell us what happened so we can check if the tribunal hears this kind of claim."
    amt_ok = amt is not None and (amt <= 20000 or (it.get("consent_30k") and amt <= 30000))
    bar = plus_years(cause, 2) if cause else None
    time_ok = bool(cause) and today <= bar
    in_sg = it["parties"]["respondent"].get("in_singapore")
    served_ok = bool(in_sg)
    checks = [
        {"id": "category", "pass": cat_ok, "section_id": "scta_schedule", "text": cat_text},
        {"id": "amount", "pass": amt_ok, "section_id": "scta_s2",
         "text": (f"You are claiming {money(amt)}. The limit is $20,000, or $30,000 if both sides agree."
                  + ((" If both sides sign the court's consent form for the $30,000 limit, tell us." if amt <= 30000 else "")
                     + " You can give up the part above the limit and claim the limit instead." if amt is not None and not amt_ok else "") if amt is not None
                  else "Tell us how much you are claiming. The limit is $20,000, or $30,000 if both sides agree.")},
        {"id": "time", "pass": time_ok, "section_id": "scta_s5_time",
         "text": (f"The problem started on {fmt(cause)}, the day the {role} refused or the loss happened. You have 2 years from that day, so until {fmt(bar)}."
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
    # "blocked" means a fact we already have rules the claim out, not that we are still waiting to be told.
    known = {"category": cat_known, "amount": amt is not None, "time": cause is not None, "service": in_sg is not None}
    for c in checks:
        c["where"] = where[c["id"]]
        c["blocked"] = known[c["id"]] and not c["pass"]
    failed = [c for c in checks if not c["pass"]]
    stop = None if ok else "This check did not pass: " + failed[0]["text"] + " " + where[failed[0]["id"]]
    return {"pass": ok, "checks": checks, "stop": stop,
            "result": "The details entered match all four checks below." if ok else "One or more details do not match the checks below."}


def gaps(case):
    g = content("gaps")
    to_key = g["category_to_key"]
    have = {}
    for ex in case["exhibits"]:
        if ex.get("side") == "theirs":
            continue
        for f in ex.get("facts", []):   # name the fact, not just the file: one chat export can hold messages and a receipt
            asset = next((a for a in ex["assets"] if a["id"] == f.get("asset_id")), None)
            if not related_fact(f) or not asset or asset_assessment(ex, asset)["status"] not in ("relevant", "context"):
                continue
            k = to_key.get(f["category"])
            if k and len(have.setdefault(k, [])) < 4:
                have[k].append(f"{f['fact']} ({ex['id']})")
    return [{"key": c["key"], "category": c["category"], "why": c["why"],
             "have": have.get(c["key"]) or ["Nothing yet"], "missing": c["missing"]}
            for c in g[ctype(case)]]


def blindspots(case, answers):
    b = content("blindspots")[ctype(case)]
    qs = [{**q, "answer": answers.get(q["id"])} for q in b["questions"]]
    return {"intro": b["intro"], "note": b["note"], "total": len(qs),
            "answered": sum(1 for q in qs if q["answer"] in ("yes", "no", "unsure")), "questions": qs,
            "theirs": their_evidence(qs, case.get("exhibits", []))}


def their_evidence(qs, exhibits=()):
    """Rank the actual facts in their uploads. Keep answer-only possibilities explicit."""
    weaker = {"strong": "medium", "medium": "weak", "weak": "weak"}
    rows = []
    questions = {q["id"]: q for q in qs}
    for ex in exhibits:
        if ex.get("side") != "theirs":
            continue
        assets = {a["id"]: a for a in ex.get("assets", [])}
        q = questions.get(ex.get("spot"), {})
        for i, f in enumerate(ex.get("facts", [])):
            if not relevant_fact(f):
                continue
            a = assets[f["asset_id"]]
            if asset_assessment(ex, a)["status"] != "relevant":
                continue
            meta = a.get("meta", {})
            rows.append({"id": f"their_{ex['id']}_{i}", "what": f["fact"],
                         "strength": strength(meta, f), "sure": True, "basis": "file",
                         "answer": "Check whether this file supports the point raised. " + (q.get("reply") or q.get("hint", "")),
                         "why": AUTHOR.get(meta.get("author"), "File uploaded") + ". Rated from the facts read in this file; check the source.",
                         "sources": [{"label": ex["id"], "title": a.get("filename") or ex["title"],
                                      "viewer_url": f"/api/viewer?asset_id={a['id']}&page_index={(f.get('locator') or {}).get('page_index', 0)}"}]})
    for q in qs:
        if q["answer"] == q.get("when", "yes"):
            rows.append({"id": q["id"], "what": q["they"], "strength": q["strength"], "sure": True, "answer": q.get("reply") or q["hint"],
                         "basis": "answer", "sources": [], "why": "Possible evidence, based only on your answer. This rating does not assess an uploaded file."})
        elif q["answer"] == "unsure":
            s = weaker[q["strength"]]
            rows.append({"id": q["id"], "what": q["they"], "strength": s, "sure": False, "answer": q.get("reply") or q["hint"],
                         "basis": "answer", "sources": [], "why": "Possible evidence, based only on your answer. You are not sure they have it, so one step weaker."})
    rows.sort(key=lambda r: STRENGTH_ORDER[r["strength"]])
    rank = 0
    for r in rows:
        if r["basis"] == "file":
            rank += 1
            r["rank"] = rank
        else:
            r["rank"] = None
    return rows + unranked_files({"exhibits": exhibits}, "theirs")


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
        if not f.get("date") or f.get("fits") is False:   # a file about other people or another deal is not an event in this case
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
    events.append({"id": "today", "label": "Today", "date": today.isoformat(), "future": False, "marker": True,
                   "computed": True, "detail": "Where you are now.", "sources": []})
    events.sort(key=lambda e: e["date"])   # today sorts in by date, so an event dated after today shows after it
    for i, (eid, lab, when) in enumerate(FUTURE_STEPS):
        events.append({"id": eid, "label": lab, "date": None, "date_text": when, "future": True, "marker": False,
                       "computed": True, "detail": "A step still ahead. See Next steps.", "sources": []})
    cause = d(it.get("cause_of_action_date"))
    if cause:
        bar = plus_years(cause, 2)
        events.append({"id": "time_bar", "label": "Time bar", "date": bar.isoformat(), "future": True, "marker": True,
                       "computed": True, "detail": f"2 years after {fmt(cause)}, the day the {role} refused or the loss happened. You must file by then.",
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
    assert got == ["deposit_terms", "deposit_paid", "handover_acceptance", "damage_allegation"], got
    assert [r["strength"] for r in rows] == ["strong", "strong", "medium", "medium"]
    assert [r["needs_check"] for r in rows] == [False, True, True, True]
    assert fee(2600)["amount"] == 10 and fee(12000)["amount"] == 120
    case["exhibits"].append({"id": "E9", "side": "theirs", "spot": "b2", "title": "their_invoice.pdf", "assets": [{"id": "A9", "viewer_url": "/v"}],
                             "facts": [{"asset_id": "A9", "fact": "x", "category": "payment", "evidence_key": "deposit_paid"}]})
    assert [r["evidence_key"] for r in evidence(case)] == got, "their file must not enter your evidence"
    theirs = their_evidence([{"id": "b2", "they": "Invoice", "strength": "strong", "when": "yes", "hint": "h", "answer": "unsure"}], case["exhibits"])
    uploaded = next(r for r in theirs if r.get("basis") == "file")
    possible = next(r for r in theirs if r.get("basis") == "answer")
    assert uploaded["strength"] == "weak" and uploaded["sources"][0]["label"] == "E9"
    assert possible["sources"] == [] and possible["rank"] is None and "not sure" in possible["why"]
    print("rules ok:", got)
