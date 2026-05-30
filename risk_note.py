"""LLM risk note layer — turns a detected event into a short alert the MXNB
ISSUER's treasury/risk desk can act on (issuer co-pilot framing, not third-party
surveillance).

Reuses ResilientLLM (retry → breaker → fallback: TFY 70b → TFY 8b → raw Groq).
The client is built ONCE and shared, so the circuit breaker / scorecard persist
across alerts (this is the resilience story — it must be a singleton, not rebuilt
per call). Strict prompt: the model may only restate figures present in the
input — detection is real, the LLM only explains it.
"""
from __future__ import annotations

import os
import textwrap

from dotenv import load_dotenv

from flow_monitor import FlowAnomaly
from resilient_llm import ResilientLLM, Scorecard, Target

load_dotenv()

GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
TFY_URL = os.environ.get("TFY_GATEWAY_URL", "https://gateway.truefoundry.ai")
TFY_KEY = os.environ.get("TFY_API_KEY", "")

_SCORECARD = Scorecard()
_CLIENT: ResilientLLM | None = None
_CLIENT_INIT = False


def build_targets() -> list[Target]:
    targets: list[Target] = []
    if TFY_KEY:
        targets.append(Target(name="tfy-groq-70b", base_url=TFY_URL, api_key=TFY_KEY,
                              model="groq/llama-3.3-70b-versatile", max_retries=2))
        targets.append(Target(name="tfy-groq-8b", base_url=TFY_URL, api_key=TFY_KEY,
                              model="groq/llama-3.1-8b-instant", max_retries=1))
    if GROQ_KEY:
        targets.append(Target(name="raw-groq-8b", base_url="https://api.groq.com/openai/v1",
                              api_key=GROQ_KEY, model="llama-3.1-8b-instant", max_retries=1))
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
    You are a treasury & risk co-pilot for the ISSUER of MXNB — the Mexican-peso
    stablecoin minted by Juno (a Bitso company) on Arbitrum. You watch your OWN
    token's on-chain health and write one short alert the treasury/risk desk can
    act on. Output EXACTLY these four lines, nothing else:

    SIGNAL — name the event (new issuance / large mint, redemption / burn, net
      supply swing, large circulation transfer, holder concentration) and
      restate the key figures VERBATIM from the input (amount, token, net supply
      change, recipient/holder).
    WHY — one sentence on the issuer/treasury risk it implies, using ONLY the
      input (e.g. redemption pressure / reserve drawdown, mint outpacing demand,
      concentration / liquidity risk, peg stress).
    CONFIDENCE — one of: flag / high signal / critical. Justify in <= 10 words.
    ACTION — one concrete treasury-desk step (e.g. verify reserve coverage,
      contact counterparty, monitor peg, pre-position liquidity).

    HARD RULES: use ONLY numbers and addresses that appear in the input. Never
    invent figures, counterparties, timeframes, or token names. No emojis.
    Institutional tone. If input is sparse, CONFIDENCE = "flag — sparse input".
""")


def _fallback_note(a: FlowAnomaly) -> str:
    label = {
        "large_mint": "new issuance / large mint",
        "large_redemption": "redemption / burn",
        "supply_swing": "net supply swing",
        "large_circulation": "large circulation transfer",
        "concentration": "holder concentration",
        "layering": "suspicious equal-amount relay (circulation)",
        "fan_out": "one-to-many disbursal (circulation)",
        "large_transfer": "large transfer",
    }.get(a.kind, a.kind)
    return (f"SIGNAL — {label}: {a.detail}\n"
            f"WHY — {a.symbol} treasury signal; review against issuance/reserve policy.\n"
            f"CONFIDENCE — {a.severity}\n"
            f"ACTION — verify reserve coverage and log for the treasury desk.")


def write_note(a: FlowAnomaly) -> tuple[str, dict]:
    client = get_client()
    if client is None:
        return _fallback_note(a), {"ok": True, "via": "rule-template"}
    user_msg = textwrap.dedent(f"""\
        Token: {a.symbol} (Arbitrum, issuer = Juno/Bitso)
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
