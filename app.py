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
MANAGER_NUMBER    = os.environ.get("MANAGER_WHATSAPP_NUMBER","whatsapp:+966505689200")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY",      "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")
 
twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
 
pending = {}
waiting_for_comment = {"job_id": None}
 
 
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
 
    content.append({"type": "text", "text": """You are a moving estimator for NoBiggie moving company in Saudi Arabia.
Analyze the images/frames and return ONLY this JSON structure:
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
 
