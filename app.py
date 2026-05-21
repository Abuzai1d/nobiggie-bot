import os
import json
import base64
import requests
import tempfile
import random
import string
from flask import Flask, request
from twilio.rest import Client
import anthropic
from quote_generator import generate_quote_pdf
 
app = Flask(__name__)
 
TWILIO_SID        = os.environ.get("TWILIO_ACCOUNT_SID",     "AC4cabc297f8ef1ab124a2150c8fbc46f8")
TWILIO_TOKEN      = os.environ.get("TWILIO_AUTH_TOKEN",      "e7ea89b810289727236c17a9ea572826")
TWILIO_WA_NUMBER  = os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
MANAGER_NUMBER    = os.environ.get("MANAGER_WHATSAPP_NUMBER", "whatsapp:+966505689200")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY",      "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")
 
twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
 
state = {
    "job_id": None,
    "estimate": None,
    "step": None,
    "client_name": None,
    "client_phone": None,
}
 
 
def reset_state():
    state["job_id"] = None
    state["estimate"] = None
    state["step"] = None
    state["client_name"] = None
    state["client_phone"] = None
 
 
def send_whatsapp(to, body):
    twilio_client.messages.create(from_=TWILIO_WA_NUMBER, to=to, body=body)
 
 
def download_media(url):
    r = requests.get(url, auth=(TWILIO_SID, TWILIO_TOKEN))
    mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
    return base64.standard_b64encode(r.content).decode("utf-8"), mime
 
 
def analyze_media_with_claude(media_urls):
    content = []
    for url in media_urls:
        b64, mime = download_media(url)
        if "video" in mime:
            import subprocess
            import glob
            with tempfile.TemporaryDirectory() as tmpdir:
                video_path = os.path.join(tmpdir, "video.mp4")
                with open(video_path, "wb") as f:
                    f.write(base64.b64decode(b64))
                subprocess.run(
                    ["ffmpeg", "-i", video_path, "-vf", "fps=1/2",
                     os.path.join(tmpdir, "frame_%03d.jpg"), "-y"],
                    capture_output=True
                )
                frames = sorted(glob.glob(os.path.join(tmpdir, "frame_*.jpg")))[:6]
                for frame_path in frames:
                    with open(frame_path, "rb") as ff:
                        fb64 = base64.standard_b64encode(ff.read()).decode("utf-8")
                    content.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": fb64}
                    })
        else:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": mime, "data": b64}
            })
 
    prompt = (
        "You are a moving estimator for NoBiggie moving company in Saudi Arabia. "
        "Analyze the images/frames and return ONLY this JSON:\n"
        "{\n"
        '  "rooms": ["list of rooms"],\n'
        '  "items": ["every item to move"],\n'
        '  "boxes_count": 60,\n'
        '  "trucks_count": 3,\n'
        '  "workers_count": 4,\n'
        '  "carpenter_needed": true,\n'
        '  "packer_hours": 8,\n'
        '  "special_items": ["fragile/special items"],\n'
        '  "cost_breakdown": {\n'
        '    "trucks": 900,\n'
        '    "pakistani_workers": 400,\n'
        '    "carpenter": 200,\n'
        '    "filipino_packers_labor": 960,\n'
        '    "filipino_packers_transport": 120,\n'
        '    "boxes": 600,\n'
        '    "bubble_wrap": 168,\n'
        '    "stretch_wrap": 175,\n'
        '    "tape": 35\n'
        "  },\n"
        '  "total_cost": 3558,\n'
        '  "client_price": 5058,\n'
        '  "summary": "2-3 sentence summary"\n'
        "}\n"
        "Pricing: Truck 300 SR, Worker 100 SR/day, Carpenter 200 SR/day, "
        "Packers 30 SR/hr per person groups of 4 + 120 SR transport, "
        "Box 10 SR, Bubble wrap 28 SR, Stretch wrap 25 SR, Tape 3.5 SR. "
        "client_price = total_cost + 1500 SR margin. "
        "Return ONLY valid JSON, no markdown, no extra text."
    )
    content.append({"type": "text", "text": prompt})
 
    response = claude_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": content}]
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
 
 
def apply_edit(estimate, comment):
    prompt = (
        "Adjust this move estimate based on manager instructions.\n\n"
        "Current estimate:\n"
        + json.dumps(estimate, indent=2)
        + "\n\nManager instructions: " + json.dumps(comment)
        + "\n\nApply the changes and recalculate all costs. "
        "client_price = total_cost + 1500 SR margin, UNLESS manager sets a specific final price. "
        "Return ONLY updated JSON, same structure, no markdown."
    )
    response = claude_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
 
 
def format_estimate(est):
    cb = est.get("cost_breakdown", {})
    items = est.get("items", [])
    items_preview = "\n".join(["  - " + str(i) for i in items[:12]])
    if len(items) > 12:
        items_preview += "\n  ... +" + str(len(items) - 12) + " more"
    special_list = est.get("special_items", [])
    special = "\n".join(["  * " + str(i) for i in special_list]) if special_list else "  None"
    packers = cb.get("filipino_packers_labor", 0) + cb.get("filipino_packers_transport", 0)
    materials = cb.get("boxes", 0) + cb.get("bubble_wrap", 0) + cb.get("stretch_wrap", 0) + cb.get("tape", 0)
 
    lines = [
        "NoBiggie - Move Estimate",
        "",
        "Rooms: " + ", ".join(est.get("rooms", [])),
        "",
        "Items (" + str(len(items)) + " total):",
        items_preview,
        "",
        "Special Handling:",
        special,
        "",
        "Resources:",
        "  - " + str(est.get("trucks_count", 0)) + " Trucks",
        "  - " + str(est.get("workers_count", 0)) + " Pakistani Workers",
        "  - " + ("1 Carpenter" if est.get("carpenter_needed") else "No Carpenter"),
        "  - 4 Filipino Packers (" + str(est.get("packer_hours", 0)) + " hrs)",
        "  - " + str(est.get("boxes_count", 0)) + " Boxes",
        "",
        "Cost Breakdown:",
        "  Trucks: " + str(cb.get("trucks", 0)) + " SR",
        "  Workers: " + str(cb.get("pakistani_workers", 0)) + " SR",
        "  Carpenter: " + str(cb.get("carpenter", 0)) + " SR",
        "  Packers: " + str(packers) + " SR",
        "  Materials: " + str(materials) + " SR",
        "  -------------",
        "  Our Cost: " + str(est.get("total_cost", 0)) + " SR",
        "  Margin: 1,500 SR",
        "  -------------",
        "  Client Price: " + str(est.get("client_price", 0)) + " SR",
        "",
        str(est.get("summary", "")),
        "",
        "---------------------",
        "Reply:",
        "APPROVE",
        "EDIT",
        "REJECT",
    ]
    return "\n".join(lines)
 
 
@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.form.get("From", "")
    body = request.form.get("Body", "").strip()
    num_media = int(request.form.get("NumMedia", 0))
 
    if from_number != MANAGER_NUMBER:
        return "", 200
 
    body_upper = body.upper()
 
    if state["step"] == "awaiting_edit":
        send_whatsapp(MANAGER_NUMBER, "Adjusting estimate...")
        try:
            updated = apply_edit(state["estimate"], body)
            state["estimate"] = updated
            state["step"] = None
            send_whatsapp(MANAGER_NUMBER, "Updated!\n\n" + format_estimate(updated))
        except Exception as e:
            state["step"] = None
            send_whatsapp(MANAGER_NUMBER, "Adjustment failed: " + str(e))
        return "", 200
 
    if state["step"] == "awaiting_name":
        state["client_name"] = body
        state["step"] = "awaiting_phone"
        send_whatsapp(MANAGER_NUMBER, "Got it! Now send the client phone number:")
        return "", 200
 
    if state["step"] == "awaiting_phone":
        state["client_phone"] = body
        name = state["client_name"]
        phone = state["client_phone"]
        est = state["estimate"]
        job_id = state["job_id"]
        send_whatsapp(MANAGER_NUMBER, "Generating quote for " + str(name) + "...")
        try:
            pdf_path = generate_quote_pdf(est, name, phone, job_id)
            with open(pdf_path, "rb") as f:
                upload = requests.post("https://file.io/?expires=1d", files={"file": f})
            pdf_url = upload.json().get("link", "")
            if pdf_url:
                send_whatsapp(MANAGER_NUMBER, "Quote ready! Forward to client:\n" + pdf_url)
            else:
                send_whatsapp(MANAGER_NUMBER, "PDF upload failed. Try approving again.")
        except Exception as e:
            send_whatsapp(MANAGER_NUMBER, "Quote generation failed: " + str(e))
        reset_state()
        return "", 200
 
    if body_upper == "APPROVE":
        if not state["estimate"]:
            send_whatsapp(MANAGER_NUMBER, "No active estimate. Send a video or photo first.")
            return "", 200
        state["step"] = "awaiting_name"
        send_whatsapp(MANAGER_NUMBER, "What is the client name?")
        return "", 200
 
    if body_upper == "EDIT":
        if not state["estimate"]:
            send_whatsapp(MANAGER_NUMBER, "No active estimate. Send a video or photo first.")
            return "", 200
        state["step"] = "awaiting_edit"
        send_whatsapp(MANAGER_NUMBER,
            "What would you like to change?\n\n"
            "Examples:\n"
            "- Make boxes 20 and final price 5000\n"
            "- Remove the carpenter\n"
            "- Add 1 extra truck\n"
            "- Set client price to 4500 SR\n\n"
            "Type your instructions:")
        return "", 200
 
    if body_upper == "REJECT":
        if state["estimate"]:
            reset_state()
            send_whatsapp(MANAGER_NUMBER, "Estimate rejected.")
        else:
            send_whatsapp(MANAGER_NUMBER, "No active estimate.")
        return "", 200
 
    if num_media > 0:
        send_whatsapp(MANAGER_NUMBER, "Got " + str(num_media) + " file(s)! Analyzing with Claude...")
        media_urls = [request.form.get("MediaUrl" + str(i)) for i in range(num_media)]
        try:
            estimate = analyze_media_with_claude(media_urls)
            job_id = "JOB-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
            state["job_id"] = job_id
            state["estimate"] = estimate
            state["step"] = None
            send_whatsapp(MANAGER_NUMBER, format_estimate(estimate))
        except Exception as e:
            send_whatsapp(MANAGER_NUMBER, "Analysis failed: " + str(e))
        return "", 200
 
    send_whatsapp(MANAGER_NUMBER,
        "NoBiggie Bot\n\n"
        "Send photos or videos to get an estimate.\n\n"
        "Then reply:\n"
        "APPROVE\n"
        "EDIT\n"
        "REJECT")
    return "", 200
 
 
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
                         "source": {"type": "base64", "media_type": "image/jpeg", "data": fb64}
                    })
        else:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": mime, "data": b64}
            })
 
    content.append({"type": "text", "text": """You are a moving estimator for NoBiggie moving company in Saudi Arabia.
Analyze the images/frames and return ONLY this JSON:
{
  "rooms": ["list of rooms"],
  "items": ["every item to move"],
  "boxes_count": 60,
  "trucks_count": 3,
  "workers_count": 4,
  "carpenter_needed": true,
  "packer_hours": 8,
  "special_items": ["fragile/special items"],
  "cost_breakdown": {
    "trucks": 900,
    "pakistani_workers": 400,
    "carpenter": 200,
    "filipino_packers_labor": 960,
    "filipino_packers_transport": 120,
    "boxes": 600,
    "bubble_wrap": 168,
    "stretch_wrap": 175,
    "tape": 35
  },
  "total_cost": 3558,
  "client_price": 5058,
  "summary": "2-3 sentence summary"
}
Pricing: Truck 300 SR, Worker 100 SR/day, Carpenter 200 SR/day,
Packers 30 SR/hr per person groups of 4 + 120 SR transport,
Box 10 SR, Bubble wrap 28 SR, Stretch wrap 25 SR, Tape 3.5 SR.
client_price = total_cost + 1500 SR margin.
Return ONLY valid JSON, no markdown, no extra text."""})
 
    response = claude_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": content}]
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
 
 
def apply_edit(estimate, comment):
    prompt = f"""Adjust this move estimate based on manager instructions.
 
Current estimate:
{json.dumps(estimate, indent=2)}
 
Manager instructions: "{comment}"
 
Apply the changes and recalculate all costs.
client_price = total_cost + 1500 SR margin, UNLESS manager sets a specific final price.
Return ONLY updated JSON, same structure, no markdown."""
 
    response = claude_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
 
 
def format_estimate(est):
    cb = est.get("cost_breakdown", {})
    items = est.get("items", [])
    items_preview = "\n".join([f"  • {i}" for i in items[:12]])
    if len(items) > 12:
        items_preview += f"\n  ... +{len(items) - 12} more"
    special = "\n".join([f"  ⚠️ {i}" for i in est.get("special_items", [])]) or "  None"
    packers  = cb.get("filipino_packers_labor", 0) + cb.get("filipino_packers_transport", 0)
    materials = cb.get("boxes", 0) + cb.get("bubble_wrap", 0) + cb.get("stretch_wrap", 0) + cb.get("tape", 0)
 
    return (
        f"🏠 *NoBiggie — Move Estimate*\n\n"
        f"📋 *Rooms:* {', '.join(est.get('rooms', []))}\n\n"
        f"📦 *Items ({len(items)} total):*\n{items_preview}\n\n"
        f"⚠️ *Special Handling:*\n{special}\n\n"
        f"🚛 *Resources:*\n"
        f"  • {est.get('trucks_count', 0)} Trucks\n"
        f"  • {est.get('workers_count', 0)} Pakistani Workers\n"
        f"  • {'1 Carpenter' if est.get('carpenter_needed') else 'No Carpenter'}\n"
        f"  • 4 Filipino Packers ({est.get('packer_hours', 0)} hrs)\n"
        f"  • {est.get('boxes_count', 0)} Boxes\n\n"
        f"💰 *Cost Breakdown:*\n"
        f"  Trucks: {cb.get('trucks', 0)} SR\n"
        f"  Workers: {cb.get('pakistani_workers', 0)} SR\n"
        f"  Carpenter: {cb.get('carpenter', 0)} SR\n"
        f"  Packers: {packers} SR\n"
        f"  Materials: {materials} SR\n"
        f"  ─────────────\n"
        f"  Our Cost: {est.get('total_cost', 0)} SR\n"
        f"  Margin: 1,500 SR\n"
        f"  ─────────────\n"
        f"  ✅ *Client Price: {est.get('client_price', 0)} SR*\n\n"
        f"📝 {est.get('summary', '')}\n\n"
        f"─────────────────────\n"
        f"Reply:\n"
        f"✅ *APPROVE*\n"
        f"✏️ *EDIT*\n"
        f"❌ *REJECT*"
    )
 
 
@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.form.get("From", "")
    body        = request.form.get("Body", "").strip()
    num_media   = int(request.form.get("NumMedia", 0))
 
    if from_number != MANAGER_NUMBER:
        return "", 200
 
    body_upper = body.upper()
 
    # ── Step: waiting for edit instructions ──────────────────────────────────
    if state["step"] == "awaiting_edit":
        send_whatsapp(MANAGER_NUMBER, "✏️ Adjusting estimate...")
        try:
            updated = apply_edit(state["estimate"], body)
            state["estimate"] = updated
            state["step"] = None
            send_whatsapp(MANAGER_NUMBER, "✅ Updated!\n\n" + format_estimate(updated))
        except Exception as e:
            state["step"] = None
            send_whatsapp(MANAGER_NUMBER, f"❌ Adjustment failed: {str(e)}")
        return "", 200
 
    # ── Step: waiting for client name ─────────────────────────────────────────
    if state["step"] == "awaiting_name":
        state["client_name"] = body
        state["step"] = "awaiting_phone"
        send_whatsapp(MANAGER_NUMBER, f"📱 Got it! Now send the *client's phone number:*")
        return "", 200
 
    # ── Step: waiting for client phone → generate PDF ─────────────────────────
    if state["step"] == "awaiting_phone":
        state["client_phone"] = body
        name  = state["client_name"]
        phone = state["client_phone"]
        est   = state["estimate"]
        job_id = state["job_id"]
 
        send_whatsapp(MANAGER_NUMBER, f"✅ Generating quote for *{name}*...")
        try:
            pdf_path = generate_quote_pdf(est, name, phone, job_id)
            with open(pdf_path, "rb") as f:
                upload = requests.post("https://file.io/?expires=1d", files={"file": f})
            pdf_url = upload.json().get("link", "")
            if pdf_url:
                send_whatsapp(MANAGER_NUMBER, f"📄 Quote ready! Forward to client:\n{pdf_url}")
            else:
                send_whatsapp(MANAGER_NUMBER, "⚠️ PDF upload failed. Try approving again.")
        except Exception as e:
            send_whatsapp(MANAGER_NUMBER, f"❌ Quote generation failed: {str(e)}")
 
        reset_state()
        return "", 200
 
    # ── APPROVE ───────────────────────────────────────────────────────────────
    if body_upper == "APPROVE":
        if not state["estimate"]:
            send_whatsapp(MANAGER_NUMBER, "⚠️ No active estimate. Send a video/photo first.")
            return "", 200
        state["step"] = "awaiting_name"
        send_whatsapp(MANAGER_NUMBER, "👤 What is the *client's name?*")
        return "", 200
 
    # ── EDIT ──────────────────────────────────────────────────────────────────
    if body_upper == "EDIT":
        if not state["estimate"]:
            send_whatsapp(MANAGER_NUMBER, "⚠️ No active estimate. Send a video/photo first.")
            return "", 200
        state["step"] = "awaiting_edit"
        send_whatsapp(MANAGER_NUMBER,
            "✏️ *What would you like to change?*\n\n"
            "Examples:\n"
            "• _Make boxes 20 and final price 5000_\n"
            "• _Remove the carpenter_\n"
            "• _Add 1 extra truck_\n"
            "• _Set client price to 4500 SR_\n\n"
            "Type your instructions 👇")
        return "", 200
 
    # ── REJECT ────────────────────────────────────────────────────────────────
    if body_upper == "REJECT":
        if state["estimate"]:
            reset_state()
            send_whatsapp(MANAGER_NUMBER, "🗑️ Estimate rejected.")
        else:
            send_whatsapp(MANAGER_NUMBER, "⚠️ No active estimate to reject.")
        return "", 200
 
    # ── Media received ────────────────────────────────────────────────────────
    if num_media > 0:
        send_whatsapp(MANAGER_NUMBER, f"📥 Got {num_media} file(s)! Analyzing with Claude... 🔍")
        media_urls = [request.form.get(f"MediaUrl{i}") for i in range(num_media)]
        try:
            estimate = analyze_media_with_claude(media_urls)
            job_id   = "JOB-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
            state["job_id"]   = job_id
            state["estimate"] = estimate
            state["step"]     = None
            send_whatsapp(MANAGER_NUMBER, format_estimate(estimate))
        except Exception as e:
            send_whatsapp(MANAGER_NUMBER, f"❌ Analysis failed: {str(e)}")
        return "", 200
 
    # ── Help ──────────────────────────────────────────────────────────────────
    send_whatsapp(MANAGER_NUMBER,
        "👋 *NoBiggie Bot*\n\n"
        "Send photos/videos to get an estimate.\n\n"
        "Then reply:\n"
        "✅ *APPROVE*\n"
        "✏️ *EDIT*\n"
        "❌ *REJECT*")
    return "", 200
 
 
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
   "trucks_count": 3,
  "workers_count": 4,
  "carpenter_needed": true,
  "packer_hours": 8,
  "special_items": ["fragile/special items"],
  "cost_breakdown": {
    "trucks": 900,
    "pakistani_workers": 400,
    "carpenter": 200,
    "filipino_packers_labor": 960,
    "filipino_packers_transport": 120,
    "boxes": 600,
    "bubble_wrap": 168,
    "stretch_wrap": 175,
    "tape": 35
  },
  "total_cost": 3558,
  "client_price": 5058,
  "summary": "2-3 sentence summary"
}
Pricing: Truck 300 SR, Worker 100 SR/day, Carpenter 200 SR/day,
Packers 30 SR/hr per person groups of 4 + 120 SR transport,
Box 10 SR, Bubble wrap 28 SR, Stretch wrap 25 SR, Tape 3.5 SR.
client_price = total_cost + 1500 SR margin.
Return ONLY valid JSON, no markdown."""})
 
    response = claude_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": content}]
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
 
 
def apply_comment_to_estimate(estimate, comment):
    prompt = f"""You are adjusting a move estimate based on manager instructions.
 
Current estimate:
{json.dumps(estimate, indent=2)}
 
Manager instructions: "{comment}"
 
Apply the changes. Recalculate all costs.
client_price = total_cost + 1500 SR, UNLESS manager sets a specific final price.
Return ONLY updated JSON, same structure, no markdown."""
 
    response = claude_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
 
 
def format_estimate_message(est, job_id):
    cb = est["cost_breakdown"]
    items_preview = "\n".join([f"  • {i}" for i in est["items"][:12]])
    if len(est["items"]) > 12:
        items_preview += f"\n  ... +{len(est['items']) - 12} more"
    special = "\n".join([f"  ⚠️ {i}" for i in est["special_items"]]) if est["special_items"] else "  None"
    materials = cb.get("boxes", 0) + cb.get("bubble_wrap", 0) + cb.get("stretch_wrap", 0) + cb.get("tape", 0)
    packers = cb.get("filipino_packers_labor", 0) + cb.get("filipino_packers_transport", 0)
 
    return (
        f"🏠 *NoBiggie — Move Estimate*\n"
        f"🔖 Job: *{job_id}*\n\n"
        f"📋 *Rooms:* {', '.join(est['rooms'])}\n\n"
        f"📦 *Items ({len(est['items'])} total):*\n{items_preview}\n\n"
        f"⚠️ *Special Handling:*\n{special}\n\n"
        f"🚛 *Resources:*\n"
        f"  • {est['trucks_count']} Trucks\n"
        f"  • {est['workers_count']} Pakistani Workers\n"
        f"  • {'1 Carpenter' if est['carpenter_needed'] else 'No Carpenter'}\n"
        f"  • 4 Filipino Packers ({est['packer_hours']} hrs)\n"
        f"  • {est['boxes_count']} Boxes\n\n"
        f"💰 *Cost Breakdown:*\n"
        f"  Trucks: {cb.get('trucks', 0)} SR\n"
        f"  Workers: {cb.get('pakistani_workers', 0)} SR\n"
        f"  Carpenter: {cb.get('carpenter', 0)} SR\n"
        f"  Packers: {packers} SR\n"
        f"  Materials: {materials} SR\n"
        f"  ─────────────\n"
        f"  Our Cost: {est['total_cost']} SR\n"
        f"  Margin: 1,500 SR\n"
        f"  ─────────────\n"
        f"  ✅ *Client Price: {est['client_price']} SR*\n\n"
        f"📝 {est['summary']}\n\n"
        f"─────────────────────\n"
        f"1️⃣ *APPROVE {job_id} [Name] [Phone]*\n"
        f"2️⃣ *EDIT {job_id}* — adjust numbers\n"
        f"3️⃣ *REJECT {job_id}*"
    )
 
 
@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.form.get("From", "")
    body = request.form.get("Body", "").strip()
    num_media = int(request.form.get("NumMedia", 0))
 
    if from_number != MANAGER_NUMBER:
        return "", 200
 
    body_upper = body.upper()
 
    # Waiting for edit comment
    if waiting_for_comment["job_id"]:
        job_id = waiting_for_comment["job_id"]
        if job_id in pending:
            send_whatsapp(MANAGER_NUMBER, "✏️ Adjusting estimate...")
            try:
                updated = apply_comment_to_estimate(pending[job_id]["estimate"], body)
                pending[job_id]["estimate"] = updated
                waiting_for_comment["job_id"] = None
                send_whatsapp(MANAGER_NUMBER, "✅ Updated!\n\n" + format_estimate_message(updated, job_id))
            except Exception as e:
                waiting_for_comment["job_id"] = None
                send_whatsapp(MANAGER_NUMBER, f"❌ Adjustment failed: {str(e)}")
        return "", 200
 
    # APPROVE
    if body_upper.startswith("APPROVE"):
        parts = body.split(" ", 3)
        if len(parts) < 4:
            send_whatsapp(MANAGER_NUMBER, "⚠️ Format: APPROVE [job_id] [Client Name] [Phone]")
            return "", 200
        job_id, client_name, client_phone = parts[1], parts[2], parts[3]
        if job_id not in pending:
            send_whatsapp(MANAGER_NUMBER, f"❌ Job `{job_id}` not found.")
            return "", 200
        est = pending[job_id]["estimate"]
        send_whatsapp(MANAGER_NUMBER, f"✅ Generating quote for *{client_name}*...")
        try:
            pdf_path = generate_quote_pdf(est, client_name, client_phone, job_id)
            with open(pdf_path, "rb") as f:
                upload = requests.post("https://file.io/?expires=1d", files={"file": f})
            pdf_url = upload.json().get("link", "")
            if pdf_url:
                send_whatsapp(MANAGER_NUMBER, f"📄 Quote ready! Forward to client:\n{pdf_url}")
            else:
                send_whatsapp(MANAGER_NUMBER, "⚠️ PDF upload failed.")
        except Exception as e:
            send_whatsapp(MANAGER_NUMBER, f"❌ Quote generation failed: {str(e)}")
        del pending[job_id]
        return "", 200
 
    # EDIT
    if body_upper.startswith("EDIT"):
        parts = body.split(" ", 1)
        job_id = parts[1].strip() if len(parts) > 1 else ""
        if job_id not in pending:
            send_whatsapp(MANAGER_NUMBER, f"❌ Job `{job_id}` not found.")
            return "", 200
        waiting_for_comment["job_id"] = job_id
        send_whatsapp(MANAGER_NUMBER,
            f"✏️ *Edit Job {job_id}*\n\n"
            "Type your adjustments, for example:\n\n"
            "• _Make boxes 20 and final price 5000_\n"
            "• _Remove the carpenter_\n"
            "• _Add 1 extra truck_\n"
            "• _Set client price to 4500 SR_\n\n"
            "Send your instructions 👇")
        return "", 200
 
    # REJECT
    if body_upper.startswith("REJECT"):
        parts = body.split(" ", 1)
        job_id = parts[1].strip() if len(parts) > 1 else ""
        if job_id in pending:
            del pending[job_id]
            send_whatsapp(MANAGER_NUMBER, f"🗑️ Job `{job_id}` rejected.")
        else:
            send_whatsapp(MANAGER_NUMBER, f"❌ Job `{job_id}` not found.")
        return "", 200
 
    # Media
    if num_media > 0:
        send_whatsapp(MANAGER_NUMBER, f"📥 Got {num_media} file(s)! Analyzing with Claude... 🔍")
        media_urls = [request.form.get(f"MediaUrl{i}") for i in range(num_media)]
        try:
            estimate = analyze_media_with_claude(media_urls)
            job_id = "JOB-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
            pending[job_id] = {"estimate": estimate, "from": from_number}
            send_whatsapp(MANAGER_NUMBER, format_estimate_message(estimate, job_id))
        except Exception as e:
            send_whatsapp(MANAGER_NUMBER, f"❌ Analysis failed: {str(e)}")
        return "", 200
 
    # Help
    send_whatsapp(MANAGER_NUMBER,
        "👋 *NoBiggie Bot*\n\n"
        "Send photos/videos to get an estimate.\n\n"
        "• *APPROVE [job_id] [Name] [Phone]*\n"
        "• *EDIT [job_id]* — adjust numbers\n"
        "• *REJECT [job_id]*")
    return "", 200
 
 
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
 
