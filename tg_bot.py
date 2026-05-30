"""Telegram bot wrapper for Sentinel alerts.

Outbound-only: posts treasury alerts to a chat_id via the Telegram Bot API
over HTTPS. Create a bot with @BotFather and set TG_BOT_TOKEN / TG_CHAT_ID
in .env.
"""
from __future__ import annotations

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
        text = (
            f"🛰 <b>MXNB Treasury Sentinel</b>  ·  <i>{kind}</i>\n\n"
            f"<b>Wallet:</b> <code>{wallet_addr}</code>\n"
            f"<b>Tag:</b> {wallet_tag}\n\n"
            f"<b>Detail:</b>\n{details}\n"
        )
        if interpretation:
            text += f"\n<b>LLM read:</b>\n{interpretation}\n"
        text += f"\n<i>at {time.strftime('%Y-%m-%d %H:%M:%S')}</i>"
        return self.send(text)


if __name__ == "__main__":
    bot = TGBot()
    ok, info = bot.send_alert(
        wallet_tag="MXNB large_mint",
        wallet_addr="0x975e20f3...",
        kind="large_mint",
        details=(
            "+200.00 MXNB minted to <code>0x975e20f3…</code>\n"
            "net supply Δ this window: <b>+200.00 MXNB</b>"
        ),
        interpretation=(
            "SIGNAL — new issuance of 200.00 MXNB.\n"
            "WHY — mint outpacing redemptions; watch reserve coverage.\n"
            "CONFIDENCE — high signal.\n"
            "ACTION — verify 1:1 reserve backing for the new issuance."
        ),
    )
    print(f"send_alert -> ok={ok}  info={info}")
