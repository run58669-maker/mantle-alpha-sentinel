# Mantle Alpha Sentinel

**AI-powered on-chain intelligence for the Mantle L2 ecosystem.** Real-time,
resilient monitoring of **mETH**, **USDY**, and **USDC** flows on Mantle:
whale movements, smart money patterns, fan-out disbursals, and layering chains.
Anomalies get an AI-written alpha note via DeepSeek; alerts push to Telegram.

> Built for **Mantle Turing Test Hackathon · Track 02: AI Alpha & Data**.

---

## Why

DeFi traders and risk desks need live, on-chain signal — not just price feeds.
Who's moving large positions in Mantle's key assets? Is someone layering funds
through relay chains? Did a whale just rotate out of mETH into USDC? These are
alpha signals the market needs, and this agent watches them in real time with an
LLM that turns each on-chain event into a short intelligence note.

## What it does

Each tick, over Mantle L2:

- **mETH (Mantle Staked Ether):** whale transfers, accumulation/distribution
- **USDY (Ondo RWA yield token):** large movements, smart money rotation
- **USDC (bridged stablecoin):** high-volume corridor flows, liquidity migration
- **Cross-token detection:**
  - `large_transfer` — single transfer above per-token threshold
  - `fan_out` — one sender → many recipients (disbursal / mule pattern)
  - `layering` — equal-amount relay chain A→B→C (structuring / peeling)
- **AI alpha note:** each notable event → a 4-line intelligence briefing
  (SIGNAL / WHY / CONFIDENCE / ACTION) via DeepSeek. The model only restates
  figures present in the detection — the detection is real, the LLM explains it.

## Resilience (it doesn't fall over)

Both the RPC and the LLM run behind a **retry → circuit-breaker → fallback
chain** (3 Mantle endpoints; LLM: DeepSeek via DashScope). Every run prints a
quantitative **scorecard** (success rate, p50/p95 latency, fallback rate, MTTR)
so the resilience is *shown*, not claimed — run `python chaos.py` to force a
primary-provider outage and watch the chain recover.

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env        # add DASHSCOPE_API_KEY (DeepSeek via DashScope)
                            # No key? Falls back to a deterministic note.
python sentinel.py --once   # one live pass over all three tokens
python sentinel.py          # continuous loop (default 60s interval)
python chaos.py             # kill the primary LLM mid-call → watch fallback recover
```

### Live output (real Mantle data)

```
=== Mantle Alpha Sentinel · tick @ 16:53:29 ===
  [mETH] clean
  [USDY] clean
  [USDC] layering:2

  ┌─ ALPHA [CRITICAL] USDC · layering
  │ SIGNAL — Layering relay chain ×3 of 74.98 USDC
  │ WHY — Small-amount structuring through multiple hops suggests obfuscation.
  │ CONFIDENCE — critical — structured layering chain with 3 hops.
  │ ACTION — Flag for compliance review and monitor recipient.
  └─ (AI via deepseek-v4-pro)
  └─ TG: sent OK

─── Resilience Scorecard ───
  total calls   : 4
  success rate  : 100.0%
  user latency  : p50 94ms / p95 325ms
```

## How it works

```
Mantle L2 logs ──▶ ResilientRPC (retry/breaker/fallback, 3 endpoints)
                       │  eth_getLogs(Transfer)
                       ▼
   flow_monitor.py (large / fan-out / layering, hub-degree denoised)
                       │  FlowAnomaly
                       ▼
   risk_note.py ──▶ ResilientLLM (DeepSeek via DashScope) ──▶ alpha note
                       │
                       ▼
   sentinel.py  (orchestrate · scorecards · Telegram alerts)
```

## Token basket

| Token | Role | Large threshold |
|-------|------|----------------|
| mETH | Mantle Staked Ether — LSP flagship, yield-bearing | 50 mETH |
| USDY | Ondo U.S. Dollar Yield — RWA-backed yield token | 100,000 USDY |
| USDC | Bridged USDC — high-volume stablecoin corridor | 250,000 USDC |

## Stack

Python · Mantle L2 (public RPC) · `httpx` · OpenAI-compatible LLM gateway
(DeepSeek via DashScope). No private infra required.

## License

MIT
