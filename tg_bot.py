"""Telegram bot wrapper for Mantle Alpha Sentinel alerts.

Outbound-only: posts alpha alerts to a chat_id via the Telegram Bot API
over HTTPS. Create a bot with @BotFather and set TG_BOT_TOKEN / TG_CHAT_ID
in .env.
"""
from __future__ import annotations

import html
import os
import time
from dataclasses import dataclass
from typing import Optional

import httpx


# Credentials come from env only — NEVER hard-code a live token (public repo).
# Create a bot via @BotFather, then set TG_BOT_TOKEN / TG_CHAT_ID in .env.
DEFAULT_TOKEN = ""
DEFAULT_CHAT_ID = ""


@dataclass
class TGBot:
    token: str = ""
    chat_id: str = ""
    timeout_s: float = 8.0

    def __post_init__(self):
        self.token = self.token or os.environ.get("TG_BOT_TOKEN") or DEFAULT_TOKEN
        self.chat_id = self.chat_id or os.environ.get("TG_CHAT_ID") or DEFAULT_CHAT_ID

    def send(self, text: str, parse_mode: str = "HTML") -> tuple[bool, str]:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            r = httpx.post(
                url,
                json={"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode,
                      "disable_web_page_preview": True},
                timeout=self.timeout_s,
            )
            r.raise_for_status()
            return True, r.json().get("result", {}).get("message_id", "?")
        except httpx.HTTPStatusError as e:
            return False, f"HTTP {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    def send_alert(
        self,
        wallet_tag: str,
        wallet_addr: str,
        kind: str,
        details: str,
        interpretation: str = "",
    ) -> tuple[bool, str]:
        esc = html.escape
        text = (
            f"🛰 <b>Mantle Alpha Sentinel</b>  ·  <i>{esc(kind)}</i>\n\n"
            f"<b>Wallet:</b> <code>{esc(wallet_addr)}</code>\n"
            f"<b>Tag:</b> {esc(wallet_tag)}\n\n"
            f"<b>Detail:</b>\n{esc(details)}\n"
        )
        if interpretation:
            text += f"\n<b>LLM read:</b>\n{esc(interpretation)}\n"
        text += f"\n<i>at {time.strftime('%Y-%m-%d %H:%M:%S')}</i>"
        return self.send(text)


if __name__ == "__main__":
    bot = TGBot()
    ok, info = bot.send_alert(
        wallet_tag="mETH large_transfer",
        wallet_addr="0xcDA86A27...",
        kind="large_transfer",
        details="500.00 mETH  0xcDA86A27…→0x5bE26527…  (blk 12345678)",
        interpretation=(
            "SIGNAL — whale movement of 500.00 mETH.\n"
            "WHY — large mETH transfer suggests smart money repositioning.\n"
            "CONFIDENCE — high signal.\n"
            "ACTION — monitor recipient wallet for further moves."
        ),
    )
    print(f"send_alert -> ok={ok}  info={info}")
