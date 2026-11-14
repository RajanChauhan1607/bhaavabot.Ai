# Telegram Bot Emergency Safety Notification Setup Guide

This guide walks through configuring, testing, and running BhaavaBot's zero-cost emergency crisis notification system powered by Telegram's Bot API.

---

## 1. Overview & Architecture

BhaavaBot integrates with the Telegram Bot API to notify trusted contacts when acute crisis or suicidal thoughts are detected. This completely replaces paid SMS gateways like Twilio with a free, instant, and reliable communication channel.

### Key Capabilities:
- **Simulation Mode (Default)**: Safely inspect and test crisis detection and pairing workflows locally without needing credentials or network access.
- **Deep-Link Pairing**: Emergency contacts pair with the bot in one click using `https://t.me/<bot>?start=<code>`.
- **Cryptographic Security**: Pairing codes are 8-character single-use tokens hashed with SHA-256 and expire after 10 minutes.
- **Fail-Safe Crisis Handling**: If Telegram is unreachable, rate-limited, or blocked, the user experience is never blocked—the user immediately receives crisis support hotlines (e.g., 988) and stabilizing care.
- **Privacy Preservation**: Alert messages never disclose confidential chat transcripts or personal thoughts—only essential alerts and support resources are provided.

---

## 2. Step 1: Create Your Telegram Bot

1. Open Telegram and search for **[@BotFather](https://t.me/BotFather)**.
2. Send `/start` and then `/newbot`.
3. Choose a friendly display name (e.g., `BhaavaBot Safety Companion`).
4. Choose a unique username ending in `bot` (e.g., `BhaavaBotSafetyBot` or `MyBhaavaSafetyBot`).
5. @BotFather will provide an API token formatted like:
   ```text
   7123456789:AAF1a2b3C4d5E6f7G8h9I0j-kLmNoPqRsTu
   ```
6. **(Optional)** Customize your bot:
   - Send `/setdescription` to describe the bot's purpose.
   - Send `/setuserpic` to upload an avatar.

---

## 3. Step 2: Configure Environment Variables

Edit your backend `.env` file (`backend/.env`):

```bash
# ==========================================
# TELEGRAM EMERGENCY BOT CONFIGURATION
# ==========================================
# Mode: "simulation" for local development/testing; "live" for real Telegram API delivery
TELEGRAM_MODE=simulation

# The HTTP API bot token provided by @BotFather
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Bot username without the "@" symbol
TELEGRAM_BOT_USERNAME=BhaavaBotSafetyBot

# Optional secret token to authenticate Telegram webhook requests (1-256 characters)
TELEGRAM_WEBHOOK_SECRET=your_custom_webhook_secret_here
```

---

## 4. Step 3: Run the Database Migration

If you are using PostgreSQL (Neon/Supabase), run the idempotent migration to add the Telegram fields:

```bash
python backend/scripts/migrate_telegram.py
```

This safely creates or updates columns (`telegram_chat_id`, `telegram_username`, `telegram_status`, `pairing_code_hash`, `pairing_code_expires_at`, `connected_at`, `consent_at`) without affecting existing records.

---

## 5. Step 4: Webhook vs. Local Polling

### Option A: Local Development Long-Polling (No Public HTTPS Required)
For local development, you do not need ngrok or public domain certificates. Simply run the provided polling daemon in a background terminal:

```bash
python backend/scripts/telegram_poll.py
```

This script:
1. Long-polls Telegram for updates via `getUpdates`.
2. Forwards incoming messages and `/start <code>` commands to BhaavaBot's update processor.
3. Pairs contacts instantly when they click "Start" in Telegram.

### Option B: Production Webhook Mode
When deploying to a public server with an HTTPS domain:
1. Register the webhook with Telegram:
   ```bash
   curl -F "url=https://your-domain.com/api/telegram/webhook" \
        -F "secret_token=your_custom_webhook_secret_here" \
        https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
   ```
2. Verify registration:
   ```bash
   curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
   ```

---

## 6. How Emergency Contact Pairing Works

1. **User Registers Contact**: The user inputs their trusted contact's name and relationship in BhaavaBot.
2. **Pairing Link Generated**: Clicking **"Pair via Telegram"** generates a secure 10-minute pairing link (`https://t.me/<bot>?start=ABC12345`).
3. **Contact Clicks Link**: The contact opens the link on their mobile or desktop Telegram and taps **"Start"**.
4. **Instant Linkage**: BhaavaBot verifies the code hash, securely records the contact's `chat_id`, sends a confirmation message to the contact, and sets status to `CONNECTED`.
5. **Single-Use**: Once paired, the code is immediately invalidated to prevent replay attacks.

---

## 7. Testing & Diagnostics

### Run the Automated Test Suite
Run the 18 automated test scenarios:
```bash
python -m pytest backend/tests/test_emergency_telegram.py -v
```

### Send a Test Notification (Without Triggering a Crisis)
Users can test their setup at any time:
1. In the **Safety & Privacy** drawer, click **Update Contact**.
2. Click **"Send Test Alert"**.
3. A non-emergency diagnostic message will be sent to confirm connectivity.

Alternatively, test via the API:
```bash
curl -X POST http://localhost:8000/api/safety/test-telegram \
     -H "Content-Type: application/json" \
     -d '{"user_id": "guest", "confirm": true}'
```

---

## 8. Troubleshooting

| Issue | Cause | Resolution |
| :--- | :--- | :--- |
| `status: SIMULATED` | `TELEGRAM_MODE=simulation` | Change `TELEGRAM_MODE=live` in `backend/.env` to enable real messaging. |
| `Invalid Telegram secret token` (403) | Mismatch on webhook header | Check `TELEGRAM_WEBHOOK_SECRET` matches the `secret_token` passed to `setWebhook`. |
| `Forbidden: bot was blocked by the user` | Contact blocked the bot | Have the contact unblock the bot and send `/start`. |
| `Invalid pairing code or code expired` | Code used after 10 min | Generate a fresh pairing link in the UI and click Start within 10 minutes. |
| `Chat not found` | Contact hasn't started bot | Ensure contact taps "Start" in the bot before sending notifications. |
