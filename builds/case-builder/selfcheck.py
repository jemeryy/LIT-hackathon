"""The one check. Builds the sample case through the real pipeline and asserts the demo path.
Run from builds/case-builder: python selfcheck.py   (USE_FIXTURES=1 unless you set it to 0)"""
import datetime as dt, io, json, os, pathlib, sys, zipfile

os.environ.setdefault("USE_FIXTURES", "1")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import app, exports, llm, rules

PACK = app.PACK
if not (PACK / "Tenancy_Agreement_2025.pdf").exists():
    sys.exit("sample pack missing: run python sample/make_pack.py first")

today = dt.date(2026, 9, 5)
case = app.build_sample(today)

assert not case["gate"]["pass"] and case["claim_type"] == "unknown"   # nothing typed yet: the gate must not pass
assert case["fee"] == {} and case["evidence"]                           # files are read before the chat, ranked under the general keys
for msg in llm.FIX["chat_user"]:                                        # the scripted conversation fills the intake
    case = app.chat_turn(case, msg)
it = case["intake"]
assert it["done"] and case["claim_type"] == "tenancy" and it["parties"]["respondent"]["role"] == "landlord"
assert it["amount"] == 2600 and it["cause_of_action_date"] == "2026-08-15" and it["premises"]["refund_days"] == 14, it
assert all(c["done"] for c in case["checklist"]), [c["id"] for c in case["checklist"] if not c["done"]]
assert case["gate"]["pass"], case["gate"]
assert len(case["exhibits"]) == 6, [e["id"] for e in case["exhibits"]]
assert all(e["status"] == "ready" for e in case["exhibits"])
keys = [r["evidence_key"] for r in case["evidence"]]
assert keys == rules.KEY_ORDER["tenancy"], keys
assert [r["rank"] for r in case["evidence"]] == [1, 2, 3, 4, 5, 6]
top = case["evidence"][0]
loc = top["sources"][0]["locator"]
assert loc["asset_id"] == "E1" and loc["page_index"] == 1 and loc["boxes"], loc
assert all(0 <= v <= 1 for b in loc["boxes"] for v in b)
assert top["sources"][0]["label"] == "E1 cl. 4, p.2", top["sources"][0]["label"]
assert case["evidence"][1]["needs_check"] and not top["needs_check"]
assert case["evidence"][4]["sources"][0]["exhibit_id"] == "E2" and case["evidence"][4]["sources"][1]["exhibit_id"] == "E3"
refund = next(e for e in case["timeline"] if e["id"] == "refund_due")
assert refund["date"] == "2026-08-14", refund
assert next(e for e in case["timeline"] if e["id"] == "time_bar")["date"] == "2028-08-15"
assert case["blindspots"]["answered"] == 4 and case["blindspots"]["total"] == 6
assert case["fee"]["amount"] == 10
assert 0 < len(case["summary"]) <= 500

xlsx = exports.evidence_xlsx(case)
assert xlsx[:2] == b"PK" and len(xlsx) > 4000
pack = exports.claim_pack_zip(case)
names = zipfile.ZipFile(io.BytesIO(pack)).namelist()
assert {"claim_form.txt", "events.txt", "written_request.txt", "manifest.txt"} <= set(names), names
assert sum(n.startswith("exhibits/") for n in names) == 15, names
assert len(exports.written_request(case)) > 200

out = app.DATA
(out / "evidence_sheet.xlsx").write_bytes(xlsx)
(out / "claim_pack.zip").write_bytes(pack)

# the viewer route for row 1 must return the same boxes the front end will draw
from fastapi.testclient import TestClient
c = TestClient(app.app)
v = c.get(top["sources"][0]["viewer_url"]).json()
assert v["boxes"] == loc["boxes"] and v["image_url"].startswith("/api/render?asset_id=E1&page_index=1"), v
png = c.get(v["image_url"]).content
assert png[:8] == b"\x89PNG\r\n\x1a\n"
assert c.get("/api/statute?section_id=scta_schedule").json()["quote"].startswith("5.")
demo = app.CASE
demo["intake"] = {**json.loads(json.dumps(app.EMPTY_INTAKE)), "chat": [{"who": "bot", "text": app.FIRST_MESSAGE}]}
demo["claim_type"] = "unknown"
app.recompute(demo)   # leaves case.json demo-ready: files read, chat empty, gate waiting
print("selfcheck ok:", keys, "| E1 boxes", loc["boxes"], "| files in", out)
