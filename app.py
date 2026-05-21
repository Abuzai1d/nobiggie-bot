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
from prompts import ANALYSIS_PROMPT, EDIT_PROMPT_PREFIX

app = Flask(__name__)

TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID", "AC4cabc297f8ef1ab124a2150c8fbc46f8")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "e7ea89b810289727236c17a9ea572826")
TWILIO_WA_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
MANAGER_NUMBER = os.environ.get("MANAGER_WHATSAPP_NUMBER", "whatsapp:+966505689200")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "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")

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


def send_wa(body):
    twilio_client.messages.create(from_=TWILIO_WA_NUMBER, to=MANAGER_NUMBER, body=body)


def download_media(url):
    r = requests.get(url, auth=(TWILIO_SID, TWILIO_TOKEN))
    mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
    return base64.standard_b64encode(r.content).decode("utf-8"), mime


def analyze_media(media_urls):
    import subprocess
    import glob
    content = []
    for url in media_urls:
        b64, mime = download_media(url)
        if "video" in mime:
            with tempfile.TemporaryDirectory() as tmpdir:
                vpath = os.path.join(tmpdir, "v.mp4")
                with open(vpath, "wb") as vf:
                    vf.write(base64.b64decode(b64))
                subprocess.run(
                    ["ffmpeg", "-i", vpath, "-vf", "fps=1/2",
                     os.path.join(tmpdir, "f_%03d.jpg"), "-y"],
                    capture_output=True
                )
                for fp in sorted(glob.glob(os.path.join(tmpdir, "f_*.jpg")))[:6]:
                    with open(fp, "rb") as ff:
                        fb = base64.standard_b64encode(ff.read()).decode("utf-8")
                    content.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": fb}
                    })
        else:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": mime, "data": b64}
            })
    content.append({"type": "text", "text": ANALYSIS_PROMPT})
    resp = claude_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": content}]
    )
    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def apply_edit(estimate, comment):
    prompt = EDIT_PROMPT_PREFIX + json.dumps(estimate) + " Manager instructions: " + comment
    resp = claude_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def format_estimate(est):
    cb = est.get("cost_breakdown", {})
    items = est.get("items", [])
    preview = "\n".join(["- " + str(x) for x in items[:12]])
    if len(items) > 12:
        preview += "\n... +" + str(len(items) - 12) + " more"
    sp = est.get("special_items", [])
    special = "\n".join(["* " + str(x) for x in sp]) if sp else "None"
    packers = cb.get("filipino_packers_labor", 0) + cb.get("filipino_packers_transport", 0)
    mats = cb.get("boxes", 0) + cb.get("bubble_wrap", 0) + cb.get("stretch_wrap", 0) + cb.get("tape", 0)
    msg = "NoBiggie Move Estimate\n\n"
    msg += "Rooms: " + ", ".join(est.get("rooms", [])) + "\n\n"
    msg += "Items (" + str(len(items)) + " total):\n" + preview + "\n\n"
    msg += "Special Handling:\n" + special + "\n\n"
    msg += "Resources:\n"
    msg += "- " + str(est.get("trucks_count", 0)) + " Trucks\n"
    msg += "- " + str(est.get("workers_count", 0)) + " Workers\n"
    msg += "- " + ("1 Carpenter" if est.get("carpenter_needed") else "No Carpenter") + "\n"
    msg += "- 4 Packers (" + str(est.get("packer_hours", 0)) + " hrs)\n"
    msg += "- " + str(est.get("boxes_count", 0)) + " Boxes\n\n"
    msg += "Cost Breakdown:\n"
    msg += "Trucks: " + str(cb.get("trucks", 0)) + " SR\n"
    msg += "Workers: " + str(cb.get("pakistani_workers", 0)) + " SR\n"
    msg += "Carpenter: " + str(cb.get("carpenter", 0)) + " SR\n"
    msg += "Packers: " + str(packers) + " SR\n"
    msg += "Materials: " + str(mats) + " SR\n"
    msg += "Our Cost: " + str(est.get("total_cost", 0)) + " SR\n"
    msg += "Margin: 1500 SR\n"
    msg += "CLIENT PRICE: " + str(est.get("client_price", 0)) + " SR\n\n"
    msg += str(est.get("summary", "")) + "\n\n"
    msg += "Reply: APPROVE / EDIT / REJECT"
    return msg


@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.form.get("From", "")
    body = request.form.get("Body", "").strip()
    num_media = int(request.form.get("NumMedia", 0))

    if from_number != MANAGER_NUMBER:
        return "", 200

    bu = body.upper()

    if state["step"] == "awaiting_edit":
        send_wa("Adjusting estimate...")
        try:
            updated = apply_edit(state["estimate"], body)
            state["estimate"] = updated
            state["step"] = None
            send_wa("Updated!\n\n" + format_estimate(updated))
        except Exception as e:
            state["step"] = None
            send_wa("Failed: " + str(e))
        return "", 200

    if state["step"] == "awaiting_name":
        state["client_name"] = body
        state["step"] = "awaiting_phone"
        send_wa("Got it! Now send the client phone number:")
        return "", 200

    if state["step"] == "awaiting_phone":
        state["client_phone"] = body
        name = state["client_name"]
        phone = state["client_phone"]
        est = state["estimate"]
        job_id = state["job_id"]
        send_wa("Generating quote for " + str(name) + "...")
        try:
            pdf_path = generate_quote_pdf(est, name, phone, job_id)
            with open(pdf_path, "rb") as pf:
                up = requests.post("https://file.io/?expires=1d", files={"file": pf})
            url = up.json().get("link", "")
            if url:
                send_wa("Quote ready! Forward to client:\n" + url)
            else:
                send_wa("PDF upload failed.")
        except Exception as e:
            send_wa("Quote failed: " + str(e))
        reset_state()
        return "", 200

    if bu == "APPROVE":
        if not state["estimate"]:
            send_wa("No active estimate. Send a video or photo first.")
            return "", 200
        state["step"] = "awaiting_name"
        send_wa("What is the client name?")
        return "", 200

    if bu == "EDIT":
        if not state["estimate"]:
            send_wa("No active estimate. Send a video or photo first.")
            return "", 200
        state["step"] = "awaiting_edit"
        send_wa("What to change? Examples:\n- Make boxes 20 and price 5000\n- Remove carpenter\n- Add 1 truck\n- Set price to 4500 SR")
        return "", 200

    if bu == "REJECT":
        reset_state()
        send_wa("Estimate rejected.")
        return "", 200

    if num_media > 0:
        send_wa("Got " + str(num_media) + " file(s)! Analyzing...")
        media_urls = [request.form.get("MediaUrl" + str(i)) for i in range(num_media)]
        try:
            estimate = analyze_media(media_urls)
            job_id = "JOB-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
            state["job_id"] = job_id
            state["estimate"] = estimate
            state["step"] = None
            send_wa(format_estimate(estimate))
        except Exception as e:
            send_wa("Analysis failed: " + str(e))
        return "", 200

    send_wa("NoBiggie Bot\nSend photos or videos to get an estimate.\nThen reply: APPROVE / EDIT / REJECT")
    return "", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
