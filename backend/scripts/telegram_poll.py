"""
Telegram Long-Polling Development Utility for BhaavaBot.
Allows receiving Telegram updates (like `/start <code>` pairing) locally
without requiring an ngrok tunnel or public HTTPS webhook.
"""

import sys
import time
import asyncio
import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.services.telegram_service import process_telegram_update

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("telegram_poll")

TELEGRAM_API_BASE = "https://api.telegram.org"

async def poll_telegram_updates(single_pass: bool = False, timeout_sec: int = 20):
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or not token.strip():
        logger.error(
            "TELEGRAM_BOT_TOKEN is not configured in backend/.env. "
            "Please create a bot via @BotFather and set TELEGRAM_BOT_TOKEN."
        )
        sys.exit(1)

    logger.info(f"Starting Telegram polling for bot @{settings.TELEGRAM_BOT_USERNAME}...")
    offset: Optional[int] = None

    async with httpx.AsyncClient(timeout=timeout_sec + 10) as client:
        # First verify token with getMe
        try:
            me_resp = await client.get(f"{TELEGRAM_API_BASE}/bot{token}/getMe")
            me_data = me_resp.json()
            if not me_data.get("ok"):
                logger.error(f"Failed to authenticate with Telegram: {me_data.get('description')}")
                sys.exit(1)
            bot_user = me_data.get("result", {}).get("username")
            logger.info(f"Successfully authenticated as Telegram Bot @{bot_user}!")
        except Exception as e:
            logger.error(f"Network error connecting to Telegram: {e}")
            sys.exit(1)

        # Polling loop
        while True:
            params = {"timeout": timeout_sec}
            if offset is not None:
                params["offset"] = offset

            try:
                resp = await client.get(f"{TELEGRAM_API_BASE}/bot{token}/getUpdates", params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    updates = data.get("result", [])
                    for up in updates:
                        up_id = up.get("update_id")
                        offset = up_id + 1
                        logger.info(f"Processing update_id={up_id}...")
                        res = await process_telegram_update(up)
                        logger.info(f"Update result: {res}")
                elif resp.status_code == 409:
                    logger.warning("Conflict (409): Another webhook or polling session is active.")
                else:
                    logger.warning(f"Telegram returned status {resp.status_code}: {resp.text}")
            except httpx.TimeoutException:
                pass  # Normal for long-polling timeout
            except Exception as e:
                logger.warning(f"Polling loop error: {e}")
                await asyncio.sleep(3)

            if single_pass:
                break

            await asyncio.sleep(0.5)

if __name__ == "__main__":
    single_pass_arg = "--once" in sys.argv
    try:
        asyncio.run(poll_telegram_updates(single_pass=single_pass_arg))
    except KeyboardInterrupt:
        logger.info("Polling stopped by user.")
