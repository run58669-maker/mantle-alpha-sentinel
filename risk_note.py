"""LLM risk/compliance note layer — turns a FlowAnomaly into a short alert a
stablecoin-remittance compliance/ops desk can act on.

Reuses ResilientLLM (retry → breaker → fallback: TFY 70b → TFY 8b → raw Groq).
Strict prompt: the model may only restate numbers/addresses present in the
input — the detection logic is real; the LLM only *explains* it (no thin
wrapper). Falls back to a deterministic rule-based note if no LLM is configured.
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


SYSTEM_PROMPT = textwrap.dedent("""\
    You are a stablecoin-payments RISK & AML analyst for a LATAM remittance
    desk (context: Bitso / Juno, MXNB — the Mexican-peso stablecoin on
    Arbitrum). For each on-chain flow anomaly, write a short alert a
    compliance/ops officer can act on. Output EXACTLY these four lines, no more:

    SIGNAL — name the pattern in AML terms (layering/structuring/smurfing,
      mule disbursal / fan-out, large settlement) and restate the key figures
      VERBATIM from the input (token, amount, hop count or #recipients).
    WHY — one sentence on the remittance/payments risk it implies, using ONLY
      what's in the input (e.g. structuring to dodge reporting thresholds,
      mule-network disbursal, large corridor settlement).
    CONFIDENCE — one of: flag / high signal / critical. Justify in <= 10 words.
    ACTION — one concrete desk step (e.g. add addresses to review queue,
      manual KYC, monitor corridor).

    HARD RULES: use ONLY numbers and addresses that appear in the input. Never
    invent counterparties, amounts, timeframes, or token names. No emojis.
    Institutional tone. If the input is sparse, CONFIDENCE must be
    "flag — sparse input".
""")


def _fallback_note(a: FlowAnomaly) -> str:
    """Deterministic note if no LLM target is configured — still useful."""
    aml = {"layering": "layering / structuring (equal-amount relay chain)",
           "fan_out": "mule disbursal / fan-out (one sender → many recipients)",
           "large_transfer": "large settlement transfer"}.get(a.kind, a.kind)
    return (f"SIGNAL — {aml}: {a.detail}\n"
            f"WHY — {a.symbol} flow pattern consistent with {aml}; review against remittance/AML policy.\n"
            f"CONFIDENCE — {a.severity}\n"
            f"ACTION — add involved addresses to the compliance review queue.")


def write_note(a: FlowAnomaly, scorecard: Scorecard | None = None) -> tuple[str, dict]:
    targets = build_targets()
    if not targets:
        return _fallback_note(a), {"ok": True, "via": "rule-template"}
    client = ResilientLLM(targets, scorecard=scorecard)
    user_msg = textwrap.dedent(f"""\
        Token: {a.symbol} (Arbitrum)
        Detected pattern: {a.kind}
        Detector severity: {a.severity}
        Total amount involved: {a.amount:,.2f} {a.symbol}
        Addresses involved ({len(a.addrs)}): {', '.join(a.addrs[:8])}
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


if __name__ == "__main__":
    # Smoke test on the real 200-MXNB relay anomaly shape.
    demo = FlowAnomaly(
        kind="layering", symbol="MXNB", severity="critical",
        detail="relay chain ×3 of ~200.00 MXNB (structuring/layering): "
               "0x000000… → 0x975e20… → 0xd63bba… → 0x58b704…",
        addrs=["0x0000000000000000000000000000000000000000",
               "0x975e20f3", "0xd63bba23", "0x58b70406"],
        amount=200.0,
    )
    note, meta = write_note(demo)
    print("=== compliance note ===")
    print(note)
    print("\nmeta:", meta)
