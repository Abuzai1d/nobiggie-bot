from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import os, tempfile, datetime

# ── Brand Colors ──────────────────────────────────────────────────────────────
BLUE       = colors.HexColor("#6D92AB")
BLUE_LIGHT = colors.HexColor("#EBF1F5")
BLUE_MID   = colors.HexColor("#C5D6E0")
DARK       = colors.HexColor("#394953")
CREAM      = colors.HexColor("#FBF9EC")
MID_GREY   = colors.HexColor("#8A9BA5")
LIGHT_GREY = colors.HexColor("#E8E8E0")
WHITE      = colors.white

W, H = A4


def generate_quote_pdf(estimate, client_name, client_phone, job_id):
    """Generate a branded NoBiggie quote PDF and return the file path."""
    out_dir = tempfile.mkdtemp()
    output  = os.path.join(out_dir, f"NoBiggie_Quote_{job_id}.pdf")

    cv = canvas.Canvas(output, pagesize=A4)
    cv.setTitle(f"NoBiggie Quote {job_id}")

    # ── Background ────────────────────────────────────────────────────────────
    cv.setFillColor(CREAM)
    cv.rect(0, 0, W, H, fill=1, stroke=0)

    # Blue left bar
    cv.setFillColor(BLUE)
    cv.rect(0, 0, 5, H, fill=1, stroke=0)

    # ── Header ────────────────────────────────────────────────────────────────
    cv.setFillColor(CREAM)
    cv.rect(0, H - 88, W, 88, fill=1, stroke=0)

    # Blue bottom strip on header
    cv.setFillColor(BLUE)
    cv.rect(0, H - 92, W, 4, fill=1, stroke=0)

    # Logo
    logo_x, logo_y = 28, H - 52
    cv.setFillColor(BLUE)
    cv.setFont("Helvetica-BoldOblique", 36)
    no_w = cv.stringWidth("no", "Helvetica-BoldOblique", 36)
    cv.drawString(logo_x, logo_y, "no")
    cv.setFillColor(DARK)
    cv.setFont("Helvetica-Bold", 36)
    cv.drawString(logo_x + no_w, logo_y, "biggie")

    # Tagline
    cv.setFillColor(MID_GREY)
    cv.setFont("Helvetica", 8)
    cv.drawString(logo_x, logo_y - 16, "We move your stuff like it's no biggie")

    # Quote info right
    today = datetime.date.today().strftime("%b %d, %Y")
    cv.setFillColor(DARK)
    cv.setFont("Helvetica-Bold", 10)
    cv.drawRightString(W - 28, H - 42, f"Quote #{job_id}")
    cv.setFillColor(MID_GREY)
    cv.setFont("Helvetica", 9)
    cv.drawRightString(W - 28, H - 56, f"Date: {today}")

    # ── Billed To + Payment ───────────────────────────────────────────────────
    y_info = H - 110

    cv.setFillColor(BLUE)
    cv.setFont("Helvetica-Bold", 7.5)
    cv.drawString(28, y_info, "BILLED TO")
    cv.setFillColor(DARK)
    cv.setFont("Helvetica-Bold", 11)
    cv.drawString(28, y_info - 15, client_name)
    cv.setFont("Helvetica", 9.5)
    cv.setFillColor(MID_GREY)
    cv.drawString(28, y_info - 28, client_phone)
    cv.drawString(28, y_info - 41, "KSA")

    # Separator
    cv.setStrokeColor(LIGHT_GREY)
    cv.setLineWidth(0.7)
    cv.line(W / 2 - 10, y_info + 4, W / 2 - 10, y_info - 48)

    pd_x = W / 2 + 4
    cv.setFillColor(BLUE)
    cv.setFont("Helvetica-Bold", 7.5)
    cv.drawString(pd_x, y_info, "PAYMENT DETAILS")
    cv.setFillColor(DARK)
    cv.setFont("Helvetica", 9)
    cv.drawString(pd_x, y_info - 15, "Name:   Mostawrid Shipping Est")
    cv.drawString(pd_x, y_info - 27, "Bank:    SNB")
    cv.drawString(pd_x, y_info - 39, "A/N:     15400000597807")
    cv.drawString(pd_x, y_info - 51, "IBAN:   SA1510000015400000597807")

    # ── Table Header ──────────────────────────────────────────────────────────
    table_top = H - 176
    tx, tw = 28, W - 56

    cv.setFillColor(DARK)
    cv.rect(tx, table_top - 24, tw, 24, fill=1, stroke=0)
    cv.setFillColor(WHITE)
    cv.setFont("Helvetica-Bold", 8.5)
    cv.drawString(tx + 12, table_top - 15, "ITEM DESCRIPTION")
    cv.drawRightString(tx + tw - 12, table_top - 15, "QTY / NOTE")

    # ── Service Row ───────────────────────────────────────────────────────────
    svc_y = table_top - 24 - 26
    cv.setFillColor(BLUE_LIGHT)
    cv.rect(tx, svc_y, tw, 26, fill=1, stroke=0)
    cv.setStrokeColor(BLUE_MID)
    cv.setLineWidth(0.5)
    cv.rect(tx, svc_y, tw, 26, fill=0, stroke=1)
    cv.setFillColor(BLUE)
    cv.rect(tx, svc_y, 4, 26, fill=1, stroke=0)
    cv.setFillColor(BLUE)
    cv.setFont("Helvetica-Bold", 10)
    cv.drawString(tx + 14, svc_y + 9, "Villa Moving — Full Packing Service")
    cv.setFillColor(MID_GREY)
    cv.setFont("Helvetica", 8.5)
    cv.drawRightString(tx + tw - 12, svc_y + 9, "Full Package")

    # ── Items Two Columns ─────────────────────────────────────────────────────
    items = estimate.get("items", [])
    col1  = items[: len(items) // 2 + len(items) % 2]
    col2  = items[len(items) // 2 + len(items) % 2 :]

    item_h       = 15.5
    items_area_h = max(len(col1), len(col2)) * item_h + 12
    y_items_top  = svc_y - 2
    col1_x       = tx + 10
    col2_x       = tx + tw / 2 + 6

    cv.setFillColor(WHITE)
    cv.rect(tx, y_items_top - items_area_h, tw, items_area_h, fill=1, stroke=0)
    cv.setStrokeColor(LIGHT_GREY)
    cv.setLineWidth(0.5)
    cv.rect(tx, y_items_top - items_area_h, tw, items_area_h, fill=0, stroke=1)
    cv.line(tx + tw / 2, y_items_top - items_area_h, tx + tw / 2, y_items_top)

    for i, item in enumerate(col1):
        iy = y_items_top - 10 - i * item_h
        if i % 2 == 0:
            cv.setFillColor(colors.HexColor("#F5F3E8"))
            cv.rect(tx, iy - 4, tw / 2, item_h, fill=1, stroke=0)
        cv.setFillColor(BLUE)
        cv.circle(col1_x + 2, iy + 3, 2.2, fill=1, stroke=0)
        cv.setFillColor(DARK)
        cv.setFont("Helvetica", 8.5)
        cv.drawString(col1_x + 9, iy, item)

    for i, item in enumerate(col2):
        iy = y_items_top - 10 - i * item_h
        if i % 2 == 0:
            cv.setFillColor(colors.HexColor("#F5F3E8"))
            cv.rect(tx + tw / 2, iy - 4, tw / 2, item_h, fill=1, stroke=0)
        cv.setFillColor(BLUE)
        cv.circle(col2_x + 2, iy + 3, 2.2, fill=1, stroke=0)
        cv.setFillColor(DARK)
        cv.setFont("Helvetica", 8.5)
        cv.drawString(col2_x + 9, iy, item)

    # ── Note ──────────────────────────────────────────────────────────────────
    y_note = y_items_top - items_area_h - 12
    cv.setFillColor(MID_GREY)
    cv.setFont("Helvetica-Oblique", 7.5)
    cv.drawString(tx, y_note,
        "* Extra boxes: 35 SAR each. Other unlisted items will be charged separately.")

    # ── Total Box ─────────────────────────────────────────────────────────────
    y_total  = y_note - 18
    total_h  = 40
    cv.setFillColor(DARK)
    cv.rect(tx, y_total - total_h, tw, total_h, fill=1, stroke=0)
    cv.setFillColor(BLUE)
    cv.rect(tx, y_total - total_h, 5, total_h, fill=1, stroke=0)
    cv.setFillColor(WHITE)
    cv.setFont("Helvetica-Bold", 10)
    cv.drawString(tx + 18, y_total - 15, "TOTAL AMOUNT")
    cv.setFillColor(MID_GREY)
    cv.setFont("Helvetica", 8)
    cv.drawString(tx + 18, y_total - 28, "VAT inclusive · One-time payment")
    cv.setFillColor(BLUE_LIGHT)
    cv.setFont("Helvetica-Bold", 20)
    cv.drawRightString(tx + tw - 14, y_total - 20,
        f"{estimate.get('client_price', 0):,} SR")

    # ── Footer ────────────────────────────────────────────────────────────────
    cv.setFillColor(BLUE)
    cv.rect(0, 0, W, 26, fill=1, stroke=0)
    cv.setFillColor(WHITE)
    cv.setFont("Helvetica-BoldOblique", 12)
    fw_no = cv.stringWidth("no", "Helvetica-BoldOblique", 12)
    total_logo_w = fw_no + cv.stringWidth("biggie", "Helvetica-Bold", 12)
    lx = W / 2 - total_logo_w / 2
    cv.drawString(lx, 8, "no")
    cv.setFont("Helvetica-Bold", 12)
    cv.drawString(lx + fw_no, 8, "biggie")
    cv.setFont("Helvetica", 7)
    cv.drawRightString(W - 28, 9, "Packing · Organizing · Moving")

    cv.save()
    return output
