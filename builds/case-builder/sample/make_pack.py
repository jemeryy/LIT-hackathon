"""Generate the synthetic sample pack into sample/pack/. All files are fake and disclosed as such.
Run: python sample/make_pack.py [--no-video]"""
import json, pathlib, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "pack"
FIX = json.loads((HERE.parent / "content" / "fixtures.json").read_text(encoding="utf-8"))["files"]
PDF_FACTS = FIX["Tenancy_Agreement_2025.pdf"]["facts"]
CLAUSE4 = next(f["quote"] for f in PDF_FACTS if f["evidence_key"] == "deposit_terms")   # one shared constant
LEASE_Q = PDF_FACTS[1]["quote"]
INVENT_Q = PDF_FACTS[2]["quote"]


def font(size):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def make_pdf():
    ss = getSampleStyleSheet()
    body, h = ss["BodyText"], ss["Heading2"]
    body.fontSize, body.leading = 11, 15
    P = lambda t: Paragraph(t, body)
    H = lambda t: Paragraph(t, h)
    story = [
        Paragraph("TENANCY AGREEMENT", ss["Title"]),
        P("This Tenancy Agreement is made on 3 August 2025 between:"), Spacer(1, 8),
        P("<b>The Landlord:</b> Tan Ah Kow (NRIC S1234567A) of 45 Bedok Reservoir Road #12-34, Singapore 470045"),
        P("<b>The Tenant:</b> Mei Ling (NRIC S7654321B) of Blk 123 Bedok North Street 1 #05-67, Singapore 460123"),
        Spacer(1, 8),
        P("<b>The Premises:</b> the whole flat at Blk 123 Bedok North Street 1 #05-67, Singapore 460123, "
          "together with the furniture and fittings listed in the Inventory."),
        Spacer(1, 8),
        P("The Landlord agrees to let and the Tenant agrees to take the Premises on the terms set out below."),
        PageBreak(),
        H("1. Term"),
        P(f"The Landlord lets the Premises to the Tenant {LEASE_Q} and ending on 2 August 2026."),
        H("2. Rent"),
        P("The Tenant shall pay rent of S$2,600 (two thousand six hundred dollars) per month in advance on the "
          "3rd day of each month by bank transfer to the Landlord's account."),
        H("3. Use of the Premises"),
        P("The Tenant shall use the Premises only as a private residence for the Tenant and the Tenant's "
          "immediate family, and shall not sublet or assign any part of the Premises."),
        H("4. Security Deposit"),
        P("The Tenant shall pay the Landlord a security deposit of S$2,600 (two thousand six hundred dollars) on "
          f"signing this Agreement. {CLAUSE4}, less the cost of repairing any damage to the Premises or the "
          "Inventory beyond fair wear and tear. The deposit shall not be used by the Tenant as rent."),
        H("5. Utilities"),
        P("The Tenant shall pay all charges for electricity, water, gas and internet used at the Premises during "
          "the term, and shall settle the final bills before handing back the Premises."),
        PageBreak(),
        H("6. Inventory and Condition"),
        P(f"{INVENT_Q} records the furniture, fittings and their condition. The Tenant shall keep the Premises and "
          "the Inventory in good and clean condition, fair wear and tear excepted, and shall hand them back in "
          "the same condition at the end of the term."),
        H("7. Repairs"),
        P("The Tenant shall carry out minor repairs up to S$150 per item. The Landlord shall carry out all other "
          "repairs within a reasonable time after being told in writing."),
        H("8. Access"),
        P("The Landlord may enter the Premises at reasonable times, with at least 24 hours notice, to inspect "
          "or repair, and during the last month of the term to show the Premises to prospective tenants."),
        PageBreak(),
        H("9. Early Termination"),
        P("Either party may end this Agreement after the first 6 months by giving 2 months written notice, or "
          "on any earlier date agreed in writing by both parties."),
        H("10. Handing Back"),
        P("At the end of the term the Tenant shall hand back the Premises, the Inventory and all keys, clean "
          "and in good condition, fair wear and tear excepted. The parties shall inspect the Premises together "
          "and note any damage in writing on the day of handing back."),
        H("11. Stamp Duty"),
        P("The Tenant shall pay the stamp duty on this Agreement within 14 days of signing and give the "
          "Landlord a copy of the stamp certificate."),
        PageBreak(),
        H("12. Notices"),
        P("Any notice under this Agreement may be given by hand, by post to the address above, or by email or "
          "WhatsApp message to the number or address given by the party."),
        H("13. Governing Law"),
        P("This Agreement is governed by the laws of the Republic of Singapore."),
        PageBreak(),
        H("Signed by the parties on 3 August 2025"),
        Spacer(1, 30),
        P("____________________________<br/>Tan Ah Kow, Landlord<br/>Date: 3 August 2025"),
        Spacer(1, 30),
        P("____________________________<br/>Mei Ling, Tenant<br/>Date: 3 August 2025"),
        Spacer(1, 30),
        P("Witnessed by: Lim Siew Hoon, property agent, 3 August 2025"),
    ]
    SimpleDocTemplate(str(OUT / "Tenancy_Agreement_2025.pdf"), pagesize=A4, title="Tenancy Agreement 2025").build(story)


def chat_shot(name, date_text, msgs):
    """msgs: list of (who, text, time). who = 'me' | 'them'."""
    W, H = 720, 1280
    im = Image.new("RGB", (W, H), "#efe7dd")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 110], fill="#075e54")
    d.text((90, 30), "Mr Tan (Landlord)", font=font(34), fill="white")
    d.ellipse([20, 25, 76, 81], fill="#cccccc")
    d.rounded_rectangle([W // 2 - 110, 130, W // 2 + 110, 176], 8, fill="#d9e6f2")
    d.text((W // 2 - 95, 140), date_text, font=font(24), fill="#333")
    y = 210
    f = font(26)
    for who, text, tm in msgs:
        lines, line = [], ""
        for word in text.split():
            if d.textlength(line + " " + word, font=f) > 440:
                lines.append(line.strip())
                line = word
            else:
                line += " " + word
        lines.append(line.strip())
        bw = max(d.textlength(l, font=f) for l in lines) + 40
        bh = 40 * len(lines) + 44
        x0 = W - 40 - bw if who == "me" else 40
        d.rounded_rectangle([x0, y, x0 + bw, y + bh], 14, fill="#dcf8c6" if who == "me" else "white")
        for i, l in enumerate(lines):
            d.text((x0 + 20, y + 16 + i * 40), l, font=f, fill="#111")
        d.text((x0 + bw - 70, y + bh - 26), tm, font=font(18), fill="#777")
        y += bh + 18
    im.save(OUT / name)


def screen_lines(name, lines, size=(720, 1280), bg="white", header=None):
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    y = 40
    if header:
        d.rectangle([0, 0, size[0], 100], fill=header[1])
        d.text((30, 30), header[0], font=font(34), fill="white")
        y = 140
    for text, sz, col in lines:
        d.text((40, y), text, font=font(sz), fill=col)
        y += sz + 26
    im.save(OUT / name, quality=92)


def photo(name, label, colour):
    im = Image.new("RGB", (1024, 768), colour)
    d = ImageDraw.Draw(im)
    d.rectangle([80, 500, 940, 700], fill="#555555")
    d.text((90, 60), label, font=font(48), fill="white")
    d.text((90, 130), "(placeholder photo, synthetic)", font=font(28), fill="white")
    im.save(OUT / name, quality=85)


def video():
    frames = OUT / "_frames"
    frames.mkdir(exist_ok=True)
    scenes = [("Living room", "#6b7f99", 60), ("Sofa, close up. 31 Jul 2026 17:05", "#9c6b4e", 30),
              ("Kitchen", "#7a9c6b", 60), ("Bedroom", "#8c6b9c", 90)]
    lst = []
    for i, (label, col, secs) in enumerate(scenes):
        im = Image.new("RGB", (640, 360), col)
        d = ImageDraw.Draw(im)
        d.text((20, 20), label, font=font(30), fill="white")
        d.text((20, 300), "moveout_walkthrough.mp4  31 Jul 2026", font=font(20), fill="white")
        p = frames / f"f{i}.png"
        im.save(p)
        lst.append(f"file '{p.as_posix()}'\nduration {secs}")
    lst.append(f"file '{(frames / 'f3.png').as_posix()}'")
    (frames / "list.txt").write_text("\n".join(lst), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(frames / "list.txt"),
                    "-r", "1", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast",
                    str(OUT / "moveout_walkthrough.mp4")], check=True)


def main():
    OUT.mkdir(exist_ok=True)
    make_pdf()
    chat_shot("WhatsApp_01.png", "2 Aug 2025", [("me", "Hi Mr Tan, signed copy received. I will transfer the deposit tomorrow morning.", "21:10"),
                                                ("them", "Ok. Send me the screenshot after transfer.", "21:15")])
    chat_shot("WhatsApp_02.png", "15 Jul 2026", [("me", "Hi Mr Tan, as agreed I will move out on 31 Jul. I will clean the flat before I go.", "12:02"),
                                                 ("them", "Noted. Leave the keys in the mailbox.", "12:30")])
    chat_shot("WhatsApp_03.png", "31 Jul 2026", [("me", "Hi Mr Tan, keys in the mailbox. Flat cleaned.", "17:02"),
                                                 ("them", "Received", "17:30")])
    chat_shot("WhatsApp_04.png", "31 Jul 2026", [("me", "Hi Mr Tan, keys in the mailbox. Flat cleaned.", "17:02"),
                                                 ("them", "Received", "17:30"),
                                                 ("them", "ok, all good. will transfer deposit after i check", "17:41"),
                                                 ("me", "Thank you!", "17:42")])
    chat_shot("WhatsApp_05.png", "15 Aug 2026", [("me", "Hi Mr Tan, the 14 days passed yesterday. Can you transfer the deposit today?", "09:15"),
                                                 ("them", "sofa got scratch, deposit cannot return", "10:48"),
                                                 ("me", "Which scratch? Can you send me a photo please?", "10:52")])
    chat_shot("WhatsApp_06.png", "20 Aug 2026", [("me", "Hi Mr Tan, still waiting for the photo of the scratch. Please send it.", "19:00"),
                                                 ("me", "If there is no damage please return the $2,600 deposit.", "19:01")])
    screen_lines("email_landlord.png", [
        ("From: Tan Ah Kow <tanahkow@example.com>", 24, "#333"), ("To: Mei Ling", 24, "#333"),
        ("Date: 15 Aug 2026, 11:20", 24, "#333"), ("Subject: Deposit", 30, "#111"),
        ("", 10, "#333"),
        ("Mei Ling,", 26, "#111"), ("", 6, "#111"),
        ("The sofa has a scratch on the left arm.", 26, "#111"),
        ("I will not be returning the deposit until this is settled.", 26, "#111"),
        ("", 6, "#111"), ("Regards,", 26, "#111"), ("Tan", 26, "#111")], header=("Inbox", "#3b5998"))
    screen_lines("deposit_transfer.jpg", [
        ("Transfer successful", 40, "#0a7d3c"), ("", 10, "#333"),
        ("Amount", 22, "#777"), ("SGD 2,600.00", 44, "#111"), ("", 10, "#333"),
        ("Transfer of SGD 2,600.00 to TAN AH KOW", 26, "#111"),
        ("To account: 123-45678-9 (DBS)", 26, "#111"), ("", 10, "#333"),
        ("Date: 3 Aug 2025, 10:14", 26, "#111"), ("Reference: Deposit Blk 123", 26, "#111"),
        ("Transaction ID: 20250803101400123", 22, "#777")], header=("MyBank", "#c00"))
    for i, (label, col) in enumerate([("Living room", "#8a9ab0"), ("Kitchen", "#8fb08a"), ("Bedroom", "#a08ab0"),
                                      ("Bathroom", "#8ab0ad"), ("Hallway", "#b0a08a")], 1):
        photo(f"movein_{i:02d}.jpg", label, col)
    if "--no-video" not in sys.argv:
        video()
    print("wrote sample pack to", OUT)


if __name__ == "__main__":
    main()
