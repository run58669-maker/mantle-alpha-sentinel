# DoraHacks Submission — Mantle Alpha Sentinel

**Track:** 02 · AI Alpha & Data

---

## Project Name

Mantle Alpha Sentinel

## Tagline

AI-powered on-chain intelligence that watches whale movements, layering chains, and smart money patterns across Mantle's core assets — in real time.

## Problem

DeFi traders and risk desks on Mantle lack live, on-chain signal beyond price feeds. When a whale moves 500 mETH, when someone layers USDC through a relay chain to obscure origin, when a single wallet fans out to dozens of recipients — these are alpha signals that move markets. But no one is watching them in real time, and raw Transfer logs are too noisy for humans to read.

## Solution

Mantle Alpha Sentinel is an AI agent that continuously monitors ERC-20 flows for mETH, USDY, and USDC on Mantle L2. It detects three classes of anomalies:

- **Whale movements** — single transfers above per-token thresholds (50 mETH / 100K USDY / 250K USDC)
- **Fan-out disbursals** — one sender distributing to many recipients (possible mule network or OTC deal)
- **Layering chains** — equal-amount relay hops A→B→C→D (structuring / peeling pattern used to obscure fund flows)

Each detection is real math on real on-chain data. An LLM (DeepSeek) then writes a 4-line intelligence briefing — SIGNAL / WHY / CONFIDENCE / ACTION — explaining what the pattern means for Mantle ecosystem participants. Alerts push to Telegram in real time.

## How It Works

```
Mantle L2 logs ──▶ ResilientRPC (retry → breaker → fallback, 3 endpoints)
                       │  eth_getLogs(Transfer)
                       ▼
   flow_monitor.py  (large / fan-out / layering detectors, hub-degree denoised)
                       │  FlowAnomaly objects
                       ▼
   risk_note.py ──▶ ResilientLLM (DeepSeek via DashScope) ──▶ alpha note
                       │
                       ▼
   sentinel.py  (orchestrate · scorecards · Telegram alerts)
```

### Key design decisions

1. **Hub-degree denoising**: Addresses that appear in ≥8 transfers per window are classified as infrastructure (DEX routers, pools, CEX hot wallets) and excluded from mule/structuring detection. This is data-driven — no hardcoded address lists that go stale.

2. **Bisecting log fetcher**: When a public RPC caps `eth_getLogs` results, the fetcher recursively bisects the block range and retries. No silent data loss.

3. **AI explains, math detects**: The LLM is strictly constrained to restate figures from the detection. It never invents numbers, addresses, or counterparties. Detection is deterministic; the AI only translates it into actionable language.

4. **Full resilience stack**: Both RPC and LLM run behind retry → circuit-breaker → fallback chains. Every run prints a quantitative scorecard (success rate, p50/p95 latency, fallback rate, MTTR). The resilience is measured, not claimed.

## Token Basket

| Token | Role | Threshold |
|-------|------|-----------|
| mETH | Mantle Staked Ether — LSP flagship, yield-bearing | 50 mETH |
| USDY | Ondo U.S. Dollar Yield — RWA moat token | 100,000 USDY |
| USDC | Bridged USDC — high-volume stablecoin corridor | 250,000 USDC |

## Tech Stack

- **Chain**: Mantle L2 (3 public RPC endpoints with fallback)
- **Language**: Python
- **LLM**: DeepSeek v4 Pro via DashScope (OpenAI-compatible)
- **Transport**: httpx (RPC), OpenAI SDK (LLM)
- **Alerts**: Telegram Bot API
- **Resilience**: Custom retry → circuit-breaker → fallback for both RPC and LLM layers

## What Makes This Different

- **Mantle-native**: Not a generic EVM scanner. The token basket, thresholds, and AI prompts are tuned for Mantle's specific ecosystem assets (mETH as LSP flagship, USDY as RWA moat, USDC as liquidity corridor).
- **Detection + interpretation**: Most on-chain monitors show raw data. This one explains *why it matters* — in one glance, a trader knows if it's whale accumulation, smart money rotation, or possible structuring.
- **Resilient by design**: Public RPCs go down. LLM APIs rate-limit. The sentinel keeps running through outages and prints proof (scorecard) that it did.
- **Honest scope**: We detect what we can detect well. We don't overclaim AML capability — we flag patterns and let humans decide.

## Demo

```bash
pip install -r requirements.txt
cp .env.example .env   # add DASHSCOPE_API_KEY
python sentinel.py --once
```

Live output from a real Mantle scan:

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
```

## Links

- **GitHub**: [to be added before submission]
- **Demo video**: [to be recorded]
- **X thread**: [to be posted with #MantleAIHackathon]

## Team

Solo builder.

## License

MIT
