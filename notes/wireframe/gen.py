# Generates the wireframe artboards (one .dc.html per screen) from a shared shell.
import json, pathlib

W, H = 1280, 820
CSS = """
    @import url('https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap');
    body { margin: 0; font-family: 'Patrick Hand', 'Segoe Print', 'Comic Sans MS', cursive; color: #222; background: #fbfaf7; font-size: 17px; }
    a { color: #1d4ed8; } a:hover { color: #1e3a8a; }
    .box { border: 2px solid #222; border-radius: 4px; background: #fff; }
    .dash { border: 2px dashed #777; border-radius: 4px; background: #fff; color: #666; }
    .grey { background: #e9e6df; border: 2px solid #222; border-radius: 4px; }
    .btn { border: 2px solid #222; border-radius: 4px; padding: 9px 16px; background: #fff; color: #222; font-family: inherit; font-size: 17px; min-height: 42px; display: flex; align-items: center; justify-content: center; box-sizing: border-box; white-space: nowrap; box-shadow: 3px 3px 0 #222; cursor: pointer; }
    .btn:hover { background: #fef9c3; transform: translate(-1px, -1px); box-shadow: 4px 4px 0 #222; }
    .btn.primary { background: #222; color: #fff; font-size: 19px; padding-left: 26px; padding-right: 26px; }
    .btn.primary:hover { background: #333; }
    .btn.small { min-height: 34px; padding: 3px 11px; font-size: 15px; box-shadow: 2px 2px 0 #222; }
    .btn.disabled { color: #888; border-color: #aaa; background: #e9e6df; box-shadow: none; cursor: default; }
    .btn.disabled:hover { background: #e9e6df; transform: none; box-shadow: none; }
    .meta { border-radius: 999px; padding: 3px 10px; font-size: 14px; background: #e9e6df; color: #444; white-space: nowrap; }
    .source-link { border-bottom: 2px solid #1d4ed8; padding: 1px 2px; color: #1d4ed8; cursor: pointer; white-space: nowrap; }
    .source-link:hover { background: #dbeafe; color: #1e3a8a; }
    .dropzone { color: #222; cursor: pointer; text-align: center; }
    .dropzone:hover { border-color: #1d4ed8; background: #dbeafe; }
    .status-label { border-radius: 2px; padding: 3px 8px; font-size: 14px; font-weight: bold; white-space: nowrap; box-shadow: inset 5px 0 0 rgba(34,34,34,.32); }
    .status-label.have, .status-label.strong { background: #bbf7d0; }
    .status-label.missing, .status-label.weak { background: #fecaca; }
    .status-label.medium { background: #fef08a; }
    .status-label.optional { background: #e9e6df; }
    .muted { color: #666; font-size: 15px; }
    .eyebrow { color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }
    .h { font-size: 30px; line-height: 1; margin: 0; font-weight: normal; }
    .section-title { font-size: 20px; line-height: 1.1; }
    .hl { background: #fde047; padding: 0 2px; }
    .step { display: grid; grid-template-columns: 28px 1fr; align-items: center; column-gap: 9px; row-gap: 1px; padding: 7px 8px; border-radius: 4px; min-height: 48px; box-sizing: border-box; color: #666; }
    .step.done { color: #222; }
    .step.current { background: #222; color: #fff; }
    .num { grid-row: 1 / span 2; width: 26px; height: 26px; border: 1.5px solid currentColor; border-radius: 999px; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; }
    .step.done .num { background: #bbf7d0; color: #222; }
    .step-state { font-size: 12px; line-height: 1; text-transform: uppercase; letter-spacing: .6px; opacity: .8; }
    .rank { width: 38px; height: 38px; border: 2px solid #222; border-radius: 999px; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: bold; background: #fff; box-shadow: 2px 2px 0 #222; }
    .rank.top { background: #fde047; }
    .evidence-row { cursor: pointer; }
    .evidence-row:hover td { background: #dbeafe; }
    .strength { display: flex; align-items: center; gap: 7px; min-width: 82px; font-weight: bold; }
    .strength-dot { width: 14px; height: 14px; border: 2px solid #222; border-radius: 999px; flex-shrink: 0; }
    .strength.strong .strength-dot { background: #22c55e; }
    .strength.medium .strength-dot { background: #fde047; }
    .strength.weak .strength-dot { background: #fca5a5; }
    table { border-collapse: collapse; width: 100%; font-size: 14px; }
    th, td { border: 1.5px solid #222; padding: 3px 6px; text-align: left; vertical-align: middle; line-height: 1.25; }
    th { background: #e9e6df; font-weight: normal; }
    .row { display: flex; align-items: center; gap: 12px; }
    .col { display: flex; flex-direction: column; gap: 12px; }
    .nav-footer { border-top: 2px solid #222; padding-top: 12px; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; }
    .preview { padding: 0; overflow: hidden; }
    .preview-head { padding: 12px 14px; border-bottom: 2px solid #222; background: #e9e6df; display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .preview-name { font-size: 21px; line-height: 1.05; overflow-wrap: anywhere; }
    .preview-type { color: #555; font-size: 14px; margin-top: 3px; }
"""
STEPS = ["Tell us what happened", "Can the SCT hear it?", "Your evidence, ranked", "What else to gather", "Evidence blind spots", "Timeline", "Next steps"]

FOOTER = ("Under the Courts' guide on generative AI (Registrar's Circular 1 of 2024) you are responsible for what you file. "
          "Check sections on Singapore Statutes Online and cases on eLitigation, never by asking another AI. This tool does not give legal advice.")


def shell(active, title, body, eyebrow=None, next_note=None):
    nav_items = []
    for i, step_name in enumerate(STEPS):
        state = "done" if i < active else "current" if i == active else "todo"
        state_text = "Done" if i < active else "Now" if i == active else "To do"
        nav_items.append(
            f'<div class="step {state}"><div class="num">{i + 1}</div>'
            f'<div>{step_name}</div><div class="step-state">{state_text}</div></div>'
        )
    nav = "".join(nav_items)
    back_class = "btn disabled" if active == 0 else "btn"
    next_class = "btn disabled" if (active == len(STEPS) - 1 or next_note) else "btn primary"
    centre = next_note or f"Step {active + 1} of {len(STEPS)}"
    page_note = eyebrow or f"Step {active + 1} of {len(STEPS)}"
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
  <style>{CSS}</style>
</helmet>
<div style="width: {W}px; height: {H}px; display: flex; flex-direction: column; background: #fbfaf7; box-sizing: border-box;">
  <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 24px; border-bottom: 2px solid #222; background: #fff;">
    <div style="font-size: 22px;">[App name] &middot; Build your Small Claims case from your evidence</div>
    <div class="row"><span class="meta">Mei Ling</span><span class="meta">Case: tenancy deposit</span></div>
  </div>
  <div style="display: flex; flex-grow: 1; min-height: 0;">
    <div style="width: 220px; border-right: 2px solid #222; padding: 14px 12px; display: flex; flex-direction: column; gap: 3px; background: #fff; flex-shrink: 0; box-sizing: border-box;">
      <div class="eyebrow" style="padding: 0 8px 5px;">Your progress</div>{nav}
    </div>
    <div style="flex-grow: 1; padding: 16px 28px 12px; display: flex; flex-direction: column; gap: 10px; min-width: 0; overflow: hidden;">
      <div><div class="eyebrow">{page_note}</div><h1 class="h">{title}</h1></div>
      <div style="flex-grow: 1; min-height: 0; overflow: hidden;">{body}</div>
      <div class="nav-footer">
        <div class="{back_class}" style="justify-self: start; min-width: 94px;">Back</div>
        <div class="muted" style="text-align: center;">{centre}</div>
        <div class="{next_class}" style="justify-self: end; min-width: 94px;">Next</div>
      </div>
    </div>
  </div>
  <div style="padding: 8px 24px; border-top: 2px solid #222; background: #e9e6df; font-size: 14px; color: #333;">{FOOTER}</div>
</div>
</x-dc>
</body>
</html>
"""


screens = {}

screens["Intake"] = (0, "Tell us what happened", """
<div style="display: flex; gap: 20px; height: 100%; min-height: 0;">
  <div class="col" style="flex-grow: 1; min-width: 0; gap: 10px;">
    <div class="row" style="gap: 10px;"><span class="eyebrow">Question 3 of 8</span><div class="grey" style="height: 9px; flex-grow: 1; position: relative;"><div style="position: absolute; left: 0; top: 0; bottom: 0; width: 37%; background: #222;"></div></div></div>
    <div class="box" style="padding: 18px; display: flex; flex-direction: column; gap: 10px;">
      <div style="font-size: 23px; line-height: 1.1;">What did you and the landlord agree about the deposit?</div>
      <div class="muted">Use your own words. Dates and amounts are useful.</div>
      <div class="dash" style="height: 76px; padding: 10px; color: #222;">One month deposit, $2,600. The agreement says he returns it within 14 days after I move out, minus any damage.</div>
      <div class="dash" style="padding: 12px; display: flex; align-items: center; justify-content: space-between; color: #222;">
        <div><b>Add the tenancy agreement</b><br><span class="muted">PDF files work best here.</span></div>
        <div class="btn small">Choose file</div>
      </div>
      <div class="row"><span class="status-label have">Read</span><span>Tenancy_Agreement_2025.pdf, 6 pages</span></div>
    </div>
    <div class="muted">Your answers tell the story. Only files you upload are listed as evidence. This tool covers home tenancies up to 2 years, and buying or selling goods.</div>
  </div>
  <div class="box" style="width: 310px; padding: 14px; display: flex; flex-direction: column; gap: 9px; flex-shrink: 0; box-sizing: border-box;">
    <div><div class="section-title">Your files</div><div class="muted">Open a file to check what was read.</div></div>
    <div><span class="source-link">E1 Tenancy_Agreement.pdf</span><br><span class="status-label have">Read, 6 pages</span></div>
    <div><span class="source-link">E2 WhatsApp screenshots</span><br><span class="status-label have">Read, check it</span></div>
    <div><span class="source-link">E3 email_landlord.png</span><br><span class="status-label have">Read, check it</span></div>
    <div><span class="source-link">E4 deposit_transfer.jpg</span><br><span class="status-label have">Read, check it</span></div>
    <div><span class="source-link">E5 moveout_walkthrough.mp4</span><br><span class="status-label medium">Reading</span></div>
    <div><span class="source-link">E6 movein_photos</span><br><span class="status-label optional">Waiting</span></div>
    <div class="dash dropzone" style="padding: 10px; margin-top: auto;"><b>Drop more files here</b><br><span class="muted">PDF, screenshots, photos, video, voice notes, chats, receipts or spreadsheets.</span></div>
  </div>
</div>
""")


def check(text, section, ok=True):
    mark = "Pass" if ok else "Check"
    return f"""<div class="box" style="padding: 14px 16px; display: flex; align-items: center; gap: 16px;">
      <div class="status-label {'have' if ok else 'missing'}" style="width: 48px; text-align: center;">{mark}</div>
      <div style="flex-grow: 1;">{text}</div>
      <span class="source-link">{section}</span>
    </div>"""


screens["Gate"] = (1, "Can the Small Claims Tribunals hear this?", f"""
<div class="muted" style="margin-bottom: 10px;">Four fixed checks from the Act, using your answers. CJTS runs the same checks in its pre-filing assessment before you can file. Open a source to read the rule.</div>
<div class="col" style="max-width: 900px; gap: 10px;">
  {check("Your claim fits a CJTS category: Lease not exceeding 2 years (residential premises), refund of rental deposit.", "SCTA 1984 s 5 + Schedule")}
  {check("You are claiming $2,600. The limit is $20,000, or $30,000 if both sides agree.", "SCTA 1984 s 2")}
  {check("Date of cause of action: 15 Aug 2026, when the landlord refused. You have 2 years, so until 15 Aug 2028.", "SCTA 1984 s 5")}
  {check("The landlord is in Singapore, so he can be served.", "SCTA 1984 s 5")}
</div>
<div class="box" style="max-width: 900px; padding: 15px; margin-top: 10px; background: #bbf7d0; border-width: 3px;"><div class="eyebrow" style="color: #222;">Result</div><div style="font-size: 23px;">All four checks pass. You can continue.</div></div>
<div class="dash muted" style="max-width: 900px; padding: 10px; margin-top: 10px;">If a check does not pass, this page says which one and lists other places to start, such as CASE mediation, the Employment Claims Tribunals or the Magistrate's Court. No case page is built.</div>
""")


def erow(rank, what, ex, tag, why):
    bg = ' style="background: #fef9c3;"' if rank <= 2 else ""
    top = " top" if rank <= 2 else ""
    strength = tag.lower()
    return (f'<tr class="evidence-row"{bg}><td><div class="rank{top}">{rank}</div></td><td>{what}</td>'
            f'<td><span class="source-link">{ex}</span></td><td><div class="strength {strength}">'
            f'<span class="strength-dot"></span>{tag}</div></td><td>{why}</td></tr>')


screens["Evidence"] = (2, "Your evidence, ranked", """
<div style="display: flex; gap: 18px; height: 100%; min-height: 0;">
  <div class="col" style="flex-grow: 1; min-width: 0; gap: 10px;">
    <div class="box" style="padding: 10px 12px; display: flex; flex-direction: column; gap: 4px;">
      <div class="section-title">Your story in plain words</div>
      <div>You rented Mr Tan's flat for 12 months and paid a $2,600 deposit on 3 Aug 2025. You moved out on 31 Jul 2026 and he wrote "ok, all good". On 15 Aug he refused to return the deposit, saying the sofa was damaged.</div>
    </div>
    <div class="box" style="padding: 10px; flex-grow: 1; min-height: 0;">
      <div class="row" style="justify-content: space-between; margin-bottom: 7px;"><div><div class="section-title">Start with ranks 1 and 2</div><div class="muted">Select a row to open the exact source.</div></div><div class="btn small">Export evidence sheet</div></div>
      <table>
        <tr><th style="width: 42px;">Rank</th><th>What it shows</th><th>Source</th><th style="width: 92px;">Strength</th><th>Why</th></tr>
""" + erow(1, "Deposit $2,600, refund within 14 days of moving out, less damage", "E1 cl. 4, p.2", "Strong", "Signed by both of you, has amount and dates")
 + erow(2, "Deposit $2,600 paid 3 Aug 2025", "E4", "Strong", "Bank record, third party. Read from a screenshot, check it")
 + erow(3, "Landlord wrote \"ok, all good\" at handover, 31 Jul", "E2 shot 4", "Medium", "His own words, dated, in your chat screenshot")
 + erow(4, "Flat condition when you left", "E5 video, 0:00-3:40", "Medium", "Filmed by you on 31 Jul, sofa shown at 1:12")
 + erow(5, "Landlord says sofa damaged, 15 Aug", "E2 shot 5, E3", "Medium", "His claim in chat and email, no photo sent")
 + erow(6, "Flat condition when you moved in", "E6, 5 photos", "Weak", "No date stamp, sofa not in any photo") + """
      </table>
    </div>
  </div>
  <div class="box preview" style="width: 390px; flex-shrink: 0; display: flex; flex-direction: column; box-sizing: border-box;">
    <div class="preview-head"><div><div class="eyebrow">File preview</div><div class="preview-name">WhatsApp_31-Jul-2026.png</div><div class="preview-type">PNG image | E2 | Screenshot 4 of 6</div></div><div class="btn small">Close</div></div>
    <div class="grey" style="flex-grow: 1; margin: 12px; padding: 12px; display: flex; flex-direction: column; gap: 8px; font-size: 14px; min-height: 0;">
      <div class="muted">WhatsApp screenshot, 31 Jul 2026</div>
      <div style="align-self: flex-end; background: #fff; border: 1.5px solid #999; border-radius: 8px; padding: 6px 10px; max-width: 80%;">Hi Mr Tan, keys in the mailbox. Flat cleaned. 17:02</div>
      <div style="align-self: flex-start; background: #fff; border: 1.5px solid #999; border-radius: 8px; padding: 6px 10px; max-width: 80%;">Received 17:30</div>
      <div style="align-self: flex-start; background: #fff; border: 3px solid #d97706; border-radius: 8px; padding: 6px 10px; max-width: 80%; box-shadow: 0 0 0 4px #fde047;">ok, all good. will transfer deposit after i check 17:41</div>
      <div style="align-self: flex-end; background: #fff; border: 1.5px solid #999; border-radius: 8px; padding: 6px 10px; max-width: 80%;">Thank you! 17:42</div>
      <div class="muted" style="margin-top: 6px;">Text found: "ok, all good. will transfer deposit after i check", 31 Jul at 17:41, from Mr Tan. Check it against the image.</div>
    </div>
    <div class="muted" style="padding: 0 12px 12px;">This preview opens the right page, picture, message, video time or transcript line.</div>
  </div>
</div>
""")


def gap(cat, have, missing):
    li = lambda items: "".join(f"<li>{x}</li>" for x in items)
    return f"""<div class="box" style="padding: 6px 12px; display: flex; flex-direction: column; gap: 2px; font-size: 14px; line-height: 1.2;">
      <div class="row" style="justify-content: space-between;"><div class="section-title" style="font-size: 18px;">{cat}</div><div class="btn small">Upload</div></div>
      <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px;">
        <div><div class="eyebrow" style="color: #15803d;">You have</div><ul style="margin: 2px 0 0; padding-left: 18px;">{li(have)}</ul></div>
        <div><div class="eyebrow" style="color: #b91c1c;">Missing</div><ul style="margin: 2px 0 0; padding-left: 18px;">{li(missing)}</ul></div>
      </div>
    </div>"""


screens["Gaps"] = (3, "What else to gather", """
<div class="muted" style="margin-bottom: 8px;">Based on your claim type and what you uploaded. Use any file type you have. Nothing here is made for you: you gather it.</div>
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px;">
""" + gap("Communication (chat, email, SMS, calls, spoken)",
          ["WhatsApp screenshots (E2)", "Email from Mr Tan (E3)"],
          ["The full chat export, in order", "Any voice note or call log", "Anything agreed face to face: date, words, who was there"])
 + gap("Agreement (contract, listing, terms)",
       ["Tenancy agreement (E1)"],
       ["Inventory list signed at handover (cl. 6)", "Stamp duty certificate (the SCT asks for it)", "Property listing, if it described the furniture"])
 + gap("Payment (transfers, receipts, invoices)",
       ["Deposit transfer screenshot (E4)"],
       ["Last month's rent transfer", "Final utility bill and receipt", "Any repair invoice he sent you"])
 + gap("Condition (photos, video, reports)",
       ["Move-out video, dated (E5)", "Move-in photos, no dates (E6)"],
       ["Dated move-in photos or video of the sofa", "Handover form", "Cleaner or mover receipt, 31 Jul"])
 + gap("Your request for the money",
       ["Nothing yet"],
       ["A written request to Mr Tan for the $2,600 with a reply date. Draft on the Next steps page."]) + """
  <div class="dash" style="padding: 6px 12px; font-size: 14px; line-height: 1.2;"><div class="section-title" style="font-size: 18px;">For a goods claim, this list changes</div><ul style="margin: 2px 0 0; padding-left: 18px;"><li>Receipt or invoice, order page, delivery record</li><li>Product listing and photos</li><li>Photos or video of the fault, repair quotes, warranty</li><li>Your messages to the seller</li></ul></div>
</div>
""")


def dot(label, date, future=False, marker=False):
    style = "border: 2px dashed #777; background: #fff;" if future else "background: #222; border: 2px solid #222;"
    if marker:
        style = "background: #fde047; border: 2px solid #222;"
    return f"""<div style="display: flex; flex-direction: column; align-items: center; gap: 6px; width: 86px; text-align: center;">
      <div style="width: 18px; height: 18px; border-radius: 999px; box-sizing: border-box; {style}"></div>
      <div style="font-size: 15px; min-height: 20px; font-weight: bold;">{date}</div>
      <div class="muted" style="font-size: 14px;">{label}</div>
    </div>"""


screens["Timeline"] = (5, "Your case on one line", """
<div class="row" style="justify-content: space-between; margin-bottom: 10px;"><div class="muted">Past dates come from your files. Dotted points are steps still ahead.</div><div class="row" style="gap: 8px;"><span class="status-label have">From your files</span><span class="status-label optional">Still ahead</span></div></div>
<div class="box" style="padding: 24px 16px; position: relative;">
  <div style="position: absolute; left: 60px; right: 60px; top: 33px; height: 2px; background: #222;"></div>
  <div style="display: flex; justify-content: space-between; position: relative;">
""" + dot("Lease starts, deposit paid (E1, E4)", "3 Aug 25") + dot("Move out, \"all good\" (E2, E5)", "31 Jul 26") + dot("Refund due (E1 cl. 4)", "14 Aug") + dot("Landlord refuses (E2, E3)", "15 Aug")
 + dot("Today", "5 Sep", marker=True) + dot("Written request", "next", True) + dot("Pre-filing check, then file on CJTS", "", True) + dot("Serve within 7 working days", "", True)
 + dot("Consultation", "", True) + dot("Hearing", "", True) + dot("Time bar", "15 Aug 2028", marker=True) + """
  </div>
</div>
<div style="display: flex; gap: 16px;">
  <div class="box" style="flex-grow: 1; padding: 12px;"><div class="section-title">Selected: 15 Aug, landlord refuses</div><div>He wrote "sofa got scratch, deposit cannot return". You replied twice asking for photos. None sent. <span class="source-link">Open E2 screenshot 5</span> or <span class="source-link">E3 email</span>.</div></div>
  <div class="box" style="width: 320px; padding: 12px; background: #fef9c3; box-sizing: border-box;"><span class="status-label medium">Latest filing date shown</span><div style="font-size: 22px; margin-top: 6px;">15 Aug 2028</div><div class="muted">2 years after the refusal date.</div></div>
</div>
""")


def prompt(q, hint, answered=None):
    def b(label, key):
        on = ' style="background: #222; color: #fff;"' if answered == key else ""
        return f'<div class="btn small"{on}>{label}</div>'
    tick = '<span class="status-label have">Answered</span>' if answered else '<span class="status-label optional">Waiting for your answer</span>'
    return f"""<div class="box" style="padding: 8px 12px; display: flex; flex-direction: column; gap: 4px;{'' if answered else ' border-color: #b91c1c;'}">
      <div class="row" style="justify-content: space-between; align-items: flex-start;"><div style="font-size: 17px; line-height: 1.15;">{q}</div>{tick}</div>
      <div class="muted">{hint}</div>
      <div class="row">{b("Yes, add it", "yes")}{b("No", "no")}{b("Not sure", "unsure")}</div>
    </div>"""


screens["Blindspots"] = (4, "Evidence blind spots", """
<div class="muted" style="margin-bottom: 8px;">Things that could exist and are not in your files yet: what the landlord may hold, and what you may have missed. Listed so you are not surprised at the Consultation. We do not argue his case.</div>
<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px;">
""" + prompt("Could he have his own photos of the sofa, taken after you left?", "Your move-out video (E5) shows the sofa at 1:12. Keep it.", "unsure")
 + prompt("Has he sent, or could he get, a repair or cleaning invoice?", "Ask for it in your written request. On CJTS a Defects Schedule form lists each defect and its cost.", "no")
 + prompt("Did you sign an inventory or handover form?", "Your agreement, cl. 6, says there is one. Get your copy. If it notes the sofa, it matters either way.", "yes")
 + prompt("Were there any other agreed conditions, spoken or in messages on any channel? Cleaning, repainting, bills, keys.", "Check SMS, email and other apps you used with him. Anything agreed can change what he can hold back.", "no")
 + prompt("Did anyone else see the handover? A friend, mover or agent.", "Witnesses go on the Submission for Hearing form on CJTS.")
 + prompt("Did you accept any deduction, even in passing?", "If yes, say how much and when. It changes the amount you claim.") + """
</div>
<div class="row" style="margin-top: 10px; gap: 12px;"><div class="dash" style="padding: 8px 12px; flex-grow: 1;">He can file a counterclaim for damage on CJTS up to 3 days before the Consultation. Your evidence sheet is your answer to it.</div><div class="box" style="padding: 8px 12px; background: #fef9c3; white-space: nowrap;"><b>4 of 6 answered.</b> Answer all 6 to continue.</div></div>
""", "Answer all 6 questions to unlock Next (4 of 6 done)")


screens["NextSteps"] = (6, "What to do next", """
<div style="display: flex; gap: 20px; height: 100%; min-height: 0;">
  <div class="box" style="flex-grow: 1; padding: 12px 14px; display: flex; flex-direction: column; gap: 7px;">
    <div><div class="section-title">Your checklist</div><div class="muted">Start with item 1. Keep this page as you work through the list.</div></div>
    <div class="row" style="justify-content: space-between; padding: 8px; background: #fef9c3;"><div><b>1. Send a written request for the deposit</b><br><span class="muted">Your biggest gap. Give him 7 days to reply. The draft uses only your facts and your agreement.</span></div><div class="btn small">Open draft</div></div>
    <div class="row" style="justify-content: space-between;"><div><b>2. Gather what is missing</b><br><span class="muted">Stamp duty certificate, signed inventory list, final bill, dated move-in photos.</span></div><div class="btn small">Open checklist</div></div>
    <div class="row" style="justify-content: space-between;"><div><b>3. Pre-filing assessment on CJTS</b><br><span class="muted">Pick the category, enter 15 Aug 2026 and $2,600, answer the questions. The ID it gives you lasts 7 days.</span></div><div class="btn small">Open CJTS</div></div>
    <div class="row" style="justify-content: space-between;"><div><b>4. Fill the claim form and pay</b><br><span class="muted">Six parts: you, him, the claim, a summary of at most 500 characters, documents (PDF only, 5MB each, with page numbers), money order $2,600. Singpass login. Fee $10 up to $5,000. Then pick a Consultation date.</span></div><div class="source-link">Guide s.12</div></div>
    <div class="row" style="justify-content: space-between;"><div><b>5. Serve him within 7 working days</b><br><span class="muted">Save the Respondent Copy from CJTS, hand it to him or send by registered post, then file the Declaration of Service.</span></div><div class="source-link">Guide p.11</div></div>
    <div class="row" style="justify-content: space-between;"><div><b>6. Before the Consultation</b><br><span class="muted">He may open e-Negotiation (5 rounds). Fill the Submission for Hearing form: events in date order, witnesses. Bring E1 to E6 in evidence sheet order.</span></div><div class="source-link">Guide s.21, s.36</div></div>
  </div>
  <div class="col" style="width: 400px; flex-shrink: 0;">
    <div class="box" style="padding: 14px; display: flex; flex-direction: column; gap: 8px;">
      <div class="section-title">Evidence sheet (xlsx)</div>
      <div class="grey" style="padding: 8px; font-size: 13px; display: flex; flex-direction: column; gap: 2px;">
        <div class="row" style="gap: 6px;"><b style="width: 30px;">No.</b><b style="width: 40px;">Exh.</b><b style="width: 70px;">Date</b><b style="flex-grow: 1;">What it shows</b><b style="width: 60px;">Where</b><b style="width: 50px;">Rank</b></div>
        <div class="row" style="gap: 6px;"><span style="width: 30px;">1</span><span style="width: 40px;">E1</span><span style="width: 70px;">3 Aug 25</span><span style="flex-grow: 1;">Deposit clause</span><span style="width: 60px;">p.2 cl.4</span><span style="width: 50px;">1</span></div>
        <div class="row" style="gap: 6px;"><span style="width: 30px;">2</span><span style="width: 40px;">E4</span><span style="width: 70px;">3 Aug 25</span><span style="flex-grow: 1;">Deposit paid</span><span style="width: 60px;">image</span><span style="width: 50px;">2</span></div>
        <div class="row" style="gap: 6px;"><span style="width: 30px;">3</span><span style="width: 40px;">E2</span><span style="width: 70px;">31 Jul 26</span><span style="flex-grow: 1;">"ok, all good"</span><span style="width: 60px;">shot 4</span><span style="width: 50px;">3</span></div>
        <div class="row" style="gap: 6px; color: #888;"><span style="width: 30px;">7</span><span style="width: 40px;">E7</span><span style="width: 70px;"></span><span style="flex-grow: 1;">(you add rows here)</span><span style="width: 60px;"></span><span style="width: 50px;"></span></div>
      </div>
      <div class="btn small">Download sheet</div>
      <div class="muted">Every upload, any format, listed in order with a notes column. Add rows as you gather more.</div>
    </div>
    <div class="box" style="padding: 14px; display: flex; flex-direction: column; gap: 8px;">
      <div class="section-title">Claim pack</div>
      <div class="muted">Everything the CJTS claim form asks for, ready to paste and upload: your and his particulars, the 500-character summary, each file turned into a PDF under 5MB with a description and page number, the money order amount, and the events list for the Submission for Hearing form.</div>
      <div class="btn primary">Export claim pack</div>
      <div class="muted">Filing on the portal itself is not built. You upload this yourself.</div>
    </div>
  </div>
</div>
""")

names = {"Intake": "Main"}  # entry artboard must be Main
order = ["Intake", "Gate", "Evidence", "Gaps", "Blindspots", "Timeline", "NextSteps"]
boards = []
for k, name in enumerate(order):
    i, title, body, *extra = screens[name]
    fname = f"{names.get(name, name)}.dc.html"
    pathlib.Path(fname).write_text(shell(i, title, body, next_note=extra[0] if extra else None), encoding="utf-8")
    col, row = k % 3, k // 3
    boards.append({"file": fname, "x": col * (W + 100), "y": 160 + row * (H + 140), "w": W, "h": H,
                   "title": f"{k + 1}. {STEPS[k]}"})
canvas = {"artboards": boards,
          "annotations": [{"id": "flow", "x": 0, "y": 0, "w": 900,
                           "text": "Wireframe v4, 5 Sep 2026. Read left to right, top to bottom: 1 intake, 2 gate, 3 evidence ranked, 4 what else to gather, 5 evidence blind spots, 6 timeline, 7 next steps.\nChecked against the CJTS filing guide: pre-filing assessment, 6-part claim form, 500-character summary, PDF-only uploads of 5MB, money order, Submission for Hearing, Defects Schedule, counterclaims.\nScenario: Mei Ling, $2,600 tenancy deposit withheld by the landlord. Claim types in scope: tenancy and sale of goods."}],
          "launch": {"view": "canvas"}}
pathlib.Path("canvas.json").write_text(json.dumps(canvas, indent=1), encoding="utf-8")
for stale in ("Strength.dc.html", "Argument.dc.html", "Check.dc.html"):
    p = pathlib.Path(stale)
    if p.exists():
        p.unlink()
print("wrote", len(order), "artboards")
