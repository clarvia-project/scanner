#!/usr/bin/env python3
"""Reusable Telegram notification module for Clarvia automation.

Sends messages to a Telegram bot with markdown formatting and retry logic.
Configuration via environment variables:
  - TELEGRAM_BOT_TOKEN: Bot API token from @BotFather
  - TELEGRAM_CHAT_ID: Target chat/group ID
"""

import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds between retries


def send_message(
    text: str,
    *,
    parse_mode: str = "Markdown",
    chat_id: Optional[str] = None,
    bot_token: Optional[str] = None,
    dry_run: bool = False,
) -> bool:
    """Send a message via Telegram Bot API.

    Args:
        text: Message content (supports Markdown).
        parse_mode: Telegram parse mode ("Markdown" or "HTML").
        chat_id: Override default TELEGRAM_CHAT_ID.
        bot_token: Override default TELEGRAM_BOT_TOKEN.
        dry_run: If True, log the message instead of sending.

    Returns:
        True if message was sent (or dry-run logged) successfully.
    """
    token = bot_token or TELEGRAM_BOT_TOKEN
    target_chat = chat_id or TELEGRAM_CHAT_ID

    if dry_run:
        logger.info("[DRY RUN] Telegram message:\n%s", text)
        return True

    if not token or not target_chat:
        logger.warning(
            "Telegram not configured — TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing"
        )
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            logger.warning(
                "Telegram API returned %d: %s (attempt %d/%d)",
                resp.status_code,
                resp.text[:200],
                attempt,
                MAX_RETRIES,
            )
        except requests.RequestException as exc:
            logger.warning(
                "Telegram send failed (attempt %d/%d): %s",
                attempt,
                MAX_RETRIES,
                exc,
            )

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY * attempt)

    logger.error("Failed to send Telegram message after %d attempts", MAX_RETRIES)
    return False


def send_alert(title: str, body: str, *, level: str = "WARNING") -> bool:
    """Send a formatted alert message.

    Args:
        title: Alert title (bold in Markdown).
        body: Alert details.
        level: Severity level for the emoji prefix.
    """
    emoji_map = {
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "ERROR": "🔴",
        "CRITICAL": "🚨",
        "SUCCESS": "✅",
    }
    emoji = emoji_map.get(level, "📋")
    message = f"{emoji} *{title}*\n\n{body}"
    return send_message(message)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Test Telegram notifier")
    parser.add_argument("--dry-run", action="store_true", help="Log instead of sending")
    parser.add_argument("--message", default="Clarvia automation test message", help="Message text")
    args = parser.parse_args()

    success = send_message(
        f"🔧 *Clarvia Automation Test*\n\n{args.message}",
        dry_run=args.dry_run,
    )
    print(f"Result: {'OK' if success else 'FAILED'}")
