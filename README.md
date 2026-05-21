# NoBiggie WhatsApp Bot — Setup Guide

## What this does
You forward client videos/photos → Claude analyzes → sends you estimate → you approve → PDF quote generated automatically.

---

## Step 1 — Get your Anthropic API Key
1. Go to console.anthropic.com
2. Click "API Keys" → "Create Key"
3. Copy it — you'll need it in Step 3

---

## Step 2 — Set up Twilio WhatsApp Sandbox
1. Go to console.twilio.com
2. Messaging → Try it out → Send a WhatsApp message
3. You'll see a sandbox number (like +1 415 523 8886)
4. Save that number — it's your TWILIO_WHATSAPP_NUMBER
5. Follow the instructions to join the sandbox from YOUR WhatsApp
   (you send a code like "join <word>-<word>" to activate)

---

## Step 3 — Deploy to Railway (free, 5 minutes)
1. Go to railway.app → sign up with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Upload this folder as a GitHub repo (or use Railway CLI)
4. In Railway dashboard → your project → "Variables" tab
   Add these environment variables:

   TWILIO_ACCOUNT_SID     = AC4cabc297f8ef1ab124a2150c8fbc46f8
   TWILIO_AUTH_TOKEN      = e7ea89b810289727236c17a9ea572826
   TWILIO_WHATSAPP_NUMBER = whatsapp:+14155238886
   MANAGER_WHATSAPP_NUMBER= whatsapp:+966XXXXXXXXXX  ← YOUR number
   ANTHROPIC_API_KEY      = your_key_from_step_1

5. Railway will give you a URL like: https://nobiggie-bot.up.railway.app

---

## Step 4 — Connect Twilio to your Railway server
1. Go to Twilio → Messaging → Try it out → Send a WhatsApp message
2. Scroll down to "Sandbox Configuration"
3. In "WHEN A MESSAGE COMES IN" paste:
   https://nobiggie-bot.up.railway.app/webhook
4. Method: HTTP POST
5. Click Save

---

## Step 5 — You're live! How to use it

### Send an estimate request:
- Open WhatsApp
- Forward client photos/videos to the Twilio sandbox number
- Wait ~30 seconds
- You'll receive the full estimate breakdown

### Approve a quote:
Reply to the bot:
  APPROVE JOB-XXXXX Client Name +966XXXXXXXXX

### Reject an estimate:
  REJECT JOB-XXXXX

---

## ⚠️ Security reminder
Regenerate your Twilio Auth Token after setup:
Twilio Dashboard → Account → Auth Token → Regenerate
Then update the Railway environment variable.
