"""LLM alpha note layer — turns a detected on-chain anomaly into a short
intelligence briefing for Mantle ecosystem participants.

Reuses ResilientLLM (retry → breaker → fallback) with DeepSeek via DashScope.
The client is built ONCE and shared, so the circuit breaker / scorecard persist
across alerts. Strict prompt: the model may only restate figures present in the
input — detection is real, the LLM only explains it.
"""
from __future__ import annotations

import os
import textwrap

from dotenv import load_dotenv

from flow_monitor import FlowAnomaly
from resilient_llm import ResilientLLM, Scorecard, Target

load_dotenv()

DS_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
DS_URL = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
DS_MODEL = os.environ.get("DASHSCOPE_MODEL", "deepseek-v4-pro")

_SCORECARD = Scorecard()
_CLIENT: ResilientLLM | None = None
_CLIENT_INIT = False


def build_targets() -> list[Target]:
    targets: list[Target] = []
    if DS_KEY:
        targets.append(Target(name="deepseek-v4-pro", base_url=DS_URL, api_key=DS_KEY,
                              model=DS_MODEL, max_retries=2))
    return targets


def get_client() -> ResilientLLM | None:
    """Single shared client so breaker + scorecard persist across all alerts."""
    global _CLIENT, _CLIENT_INIT
    if not _CLIENT_INIT:
        _CLIENT_INIT = True
        targets = build_targets()
        _CLIENT = ResilientLLM(targets, scorecard=_SCORECARD) if targets else None
    return _CLIENT


def scorecard() -> Scorecard:
    return _SCORECARD


SYSTEM_PROMPT = textwrap.dedent("""\
    You are an AI alpha analyst for the Mantle L2 ecosystem. You monitor on-chain
    flows of mETH (Mantle Staked Ether), USDY (Ondo RWA yield token), and USDC
    (bridged stablecoin) and write concise intelligence notes for DeFi traders
    and risk desks. Output EXACTLY these four lines, nothing else:

    SIGNAL — name the event (whale transfer, fan-out disbursal, layering/
      structuring relay chain, large movement) and restate the key figures
      VERBATIM from the input (amount, token, addresses).
    WHY — one sentence on what this pattern implies for the Mantle ecosystem
      (e.g. whale accumulation, smart money rotation, possible OTC deal,
      mule network, liquidity migration, yield farming position change).
    CONFIDENCE — one of: flag / high signal / critical. Justify in <= 10 words.
    ACTION — one concrete next step (e.g. watch recipient wallet for further
      moves, check if correlated with governance proposal, monitor DEX pools
      for impact, flag for compliance review).

    HARD RULES: use ONLY numbers and addresses that appear in the input. Never
    invent figures, counterparties, timeframes, or token names. No emojis.
    Institutional tone. If input is sparse, CONFIDENCE = "flag — sparse input".
""")


def _fallback_note(a: FlowAnomaly) -> str:
    label = {
        "large_transfer": "whale movement",
        "fan_out": "one-to-many disbursal pattern",
        "layering": "equal-amount relay chain (structuring)",
    }.get(a.kind, a.kind)
    return (f"SIGNAL — {label}: {a.detail}\n"
            f"WHY — {a.symbol} on-chain anomaly on Mantle; warrants monitoring.\n"
            f"CONFIDENCE — {a.severity}\n"
            f"ACTION — monitor involved wallets and check DEX pool impact.")


def write_note(a: FlowAnomaly) -> tuple[str, dict]:
    client = get_client()
    if client is None:
        return _fallback_note(a), {"ok": True, "via": "rule-template"}
    user_msg = textwrap.dedent(f"""\
        Token: {a.symbol} (Mantle L2)
        Event: {a.kind}
        Detector severity: {a.severity}
        Amount involved: {a.amount:,.2f} {a.symbol}
        Addresses ({len(a.addrs)}): {', '.join(a.addrs[:8])}
        Detail: {a.detail}
    """)
    resp, rec = client.chat(
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": user_msg}],
        max_tokens=240, temperature=0.1,
    )
    if not rec.ok:
        return _fallback_note(a), {"ok": False, "via": "rule-template (LLM chain exhausted)"}
    return resp.choices[0].message.content.strip(), {
        "ok": True, "via": rec.final_target, "latency_ms": rec.user_latency_ms}
