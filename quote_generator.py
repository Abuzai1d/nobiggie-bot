from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import os
import tempfile
import datetime

BLUE = colors.HexColor("#6D92AB")
BLUE_LIGHT = colors.HexColor("#EBF1F5")
BLUE_MID = colors.HexColor("#C5D6E0")
DARK = colors.HexColor("#394953")
CREAM = colors.HexColor("#FBF9EC")
MID_GREY = colors.HexColor("#8A9BA5")
LIGHT_GREY = colors.HexColor("#E8E8E0")
WHITE = colors.white
W, H = A4


def safe(val, default=0):
    try:
        return int(val)
    except Exception:
        return default


def generate_quote_pdf(estimate, client_name, client_phone, job_id):
    out_dir = tempfile.mkdtemp()
    output = os.path.join(out_dir, "NoBiggie_Quote_" + str(job_id) + ".pdf")

    cb = estimate.get("cost_breakdown", {})
    items = estimate.get("items", [])
    client_price = safe(estimate.get("client_price", 0))

    cv = canvas.Canvas(output, pagesize=A4)
    cv.setTitle("NoBiggie Quote " + str(job_id))

    cv.setFillColor(CREAM)
    cv.rect(0, 0, W, H, fill=1, stroke=0)
    cv.setFillColor(BLUE)
    cv.rect(0, 0, 5, H, fill=1, stroke=0)

    cv.setFillColor(CREAM)
    cv.rect(0, H - 88, W, 88, fill=1, stroke=0)
    cv.setFillColor(BLUE)
    cv.rect(0, H - 92, W, 4, fill=1, stroke=0)

    lx = 28
    ly = H - 52
    cv.setFillColor(BLUE)
    cv.setFont("Helvetica-BoldOblique", 36)
    nw = cv.stringWidth("no", "Helvetica-BoldOblique", 36)
    cv.drawString(lx, ly, "no")
    cv.setFillColor(DARK)
    cv.setFont("Helvetica-Bold", 36)
    cv.drawString(lx + nw, ly, "biggie")
    cv.setFillColor(MID_GREY)
    cv.setFont("Helvetica", 8)
    cv.drawString(lx, ly - 16, "We move your stuff like it's no biggie")

    today = datetime.date.today().strftime("%b %d, %Y")
    cv.setFillColor(DARK)
    cv.setFont("Helvetica-Bold", 10)
    cv.drawRightString(W - 28, H - 42, "Quote #" + str(job_id))
    cv.setFillColor(MID_GREY)
    cv.setFont("Helvetica", 9)
    cv.drawRightString(W - 28, H - 56, "Date: " + today)

    yi = H - 110
    cv.setFillColor(BLUE)
    cv.setFont("Helvetica-Bold", 7.5)
    cv.drawString(28, yi, "BILLED TO")
    cv.setFillColor(DARK)
    cv.setFont("Helvetica-Bold", 11)
    cv.drawString(28, yi - 15, str(client_name or "Client"))
    cv.setFillColor(MID_GREY)
    cv.setFont("Helvetica", 9.5)
    cv.drawString(28, yi - 28, str(client_phone or ""))
    cv.drawString(28, yi - 41, "KSA")

    cv.setStrokeColor(LIGHT_GREY)
    cv.setLineWidth(0.7)
    cv.line(W / 2 - 10, yi + 4, W / 2 - 10, yi - 48)

    px = W / 2 + 4
    cv.setFillColor(BLUE)
    cv.setFont("Helvetica-Bold", 7.5)
    cv.drawString(px, yi, "PAYMENT DETAILS")
    cv.setFillColor(DARK)
    cv.setFont("Helvetica", 9)
    cv.drawString(px, yi - 15, "Name:   Mostawrid Shipping Est")
    cv.drawString(px, yi - 27, "Bank:    SNB")
    cv.drawString(px, yi - 39, "A/N:     15400000597807")
    cv.drawString(px, yi - 51, "IBAN:   SA1510000015400000597807")

    tt = H - 176
    tx = 28
    tw = W - 56

    cv.setFillColor(DARK)
    cv.rect(tx, tt - 24, tw, 24, fill=1, stroke=0)
    cv.setFillColor(WHITE)
    cv.setFont("Helvetica-Bold", 8.5)
    cv.drawString(tx + 12, tt - 15, "ITEM DESCRIPTION")
    cv.drawRightString(tx + tw - 12, tt - 15, "QTY / NOTE")

    sy = tt - 24 - 26
    cv.setFillColor(BLUE_LIGHT)
    cv.rect(tx, sy, tw, 26, fill=1, stroke=0)
    cv.setStrokeColor(BLUE_MID)
    cv.setLineWidth(0.5)
    cv.rect(tx, sy, tw, 26, fill=0, stroke=1)
    cv.setFillColor(BLUE)
    cv.rect(tx, sy, 4, 26, fill=1, stroke=0)
    cv.setFillColor(BLUE)
    cv.setFont("Helvetica-Bold", 10)
    cv.drawString(tx + 14, sy + 9, "Villa Moving - Full Packing Service")
    cv.setFillColor(MID_GREY)
    cv.setFont("Helvetica", 8.5)
    cv.drawRightString(tx + tw - 12, sy + 9, "Full Package")

    col1 = items[:len(items) // 2 + len(items) % 2]
    col2 = items[len(items) // 2 + len(items) % 2:]
    ih = 15.5
    iah = max(len(col1), len(col2), 1) * ih + 12
    yit = sy - 2
    c1x = tx + 10
    c2x = tx + tw / 2 + 6

    cv.setFillColor(WHITE)
    cv.rect(tx, yit - iah, tw, iah, fill=1, stroke=0)
    cv.setStrokeColor(LIGHT_GREY)
    cv.setLineWidth(0.5)
    cv.rect(tx, yit - iah, tw, iah, fill=0, stroke=1)
    cv.line(tx + tw / 2, yit - iah, tx + tw / 2, yit)

    stripe = colors.HexColor("#F5F3E8")
    for i, item in enumerate(col1):
        iy = yit - 10 - i * ih
        if i % 2 == 0:
            cv.setFillColor(stripe)
            cv.rect(tx, iy - 4, tw / 2, ih, fill=1, stroke=0)
        cv.setFillColor(BLUE)
        cv.circle(c1x + 2, iy + 3, 2.2, fill=1, stroke=0)
        cv.setFillColor(DARK)
        cv.setFont("Helvetica", 8.5)
        cv.drawString(c1x + 9, iy, str(item)[:55])

    for i, item in enumerate(col2):
        iy = yit - 10 - i * ih
        if i % 2 == 0:
            cv.setFillColor(stripe)
            cv.rect(tx + tw / 2, iy - 4, tw / 2, ih, fill=1, stroke=0)
        cv.setFillColor(BLUE)
        cv.circle(c2x + 2, iy + 3, 2.2, fill=1, stroke=0)
        cv.setFillColor(DARK)
        cv.setFont("Helvetica", 8.5)
        cv.drawString(c2x + 9, iy, str(item)[:55])

    yn = yit - iah - 12
    cv.setFillColor(MID_GREY)
    cv.setFont("Helvetica-Oblique", 7.5)
    cv.drawString(tx, yn, "* Extra boxes: 35 SAR each. Other unlisted items will be charged separately.")

    yt = yn - 18
    cv.setFillColor(DARK)
    cv.rect(tx, yt - 40, tw, 40, fill=1, stroke=0)
    cv.setFillColor(BLUE)
    cv.rect(tx, yt - 40, 5, 40, fill=1, stroke=0)
    cv.setFillColor(WHITE)
    cv.setFont("Helvetica-Bold", 10)
    cv.drawString(tx + 18, yt - 15, "TOTAL AMOUNT")
    cv.setFillColor(MID_GREY)
    cv.setFont("Helvetica", 8)
    cv.drawString(tx + 18, yt - 28, "VAT inclusive - One-time payment")
    cv.setFillColor(BLUE_LIGHT)
    cv.setFont("Helvetica-Bold", 20)
    cv.drawRightString(tx + tw - 14, yt - 20, str(client_price) + " SR")

    cv.setFillColor(BLUE)
    cv.rect(0, 0, W, 26, fill=1, stroke=0)
    cv.setFillColor(WHITE)
    cv.setFont("Helvetica-BoldOblique", 12)
    nw2 = cv.stringWidth("no", "Helvetica-BoldOblique", 12)
    bw = nw2 + cv.stringWidth("biggie", "Helvetica-Bold", 12)
    flx = W / 2 - bw / 2
    cv.drawString(flx, 8, "no")
    cv.setFont("Helvetica-Bold", 12)
    cv.drawString(flx + nw2, 8, "biggie")
    cv.setFont("Helvetica", 7)
    cv.drawRightString(W - 28, 9, "Packing - Organizing - Moving")

    cv.save()
    return output
