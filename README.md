# MXNB Treasury Sentinel

**An AI risk co-pilot for the *issuer* of a stablecoin.** Real-time, resilient,
on-chain monitoring of **MXNB** — the Mexican-peso stablecoin minted by **Juno (a
Bitso company)** on Arbitrum — plus the surrounding USD-stablecoin corridor.

> *Co-piloto de riesgo on-chain para el emisor de MXNB.*
> Built for **Ethereum México 2026 · AI × Blockchain (w/ Bitso)**.

---

## Why

A regulated stablecoin issuer already does KYC at the on/off-ramp. What it
*doesn't* get for free is a **live, on-chain view of its own token's health**:
how much is being minted vs redeemed, sudden supply swings, holder
concentration, large settlement movements. That's a treasury & risk function —
and it's exactly what this agent watches, in real time, with an LLM that turns
each on-chain event into a short note the treasury desk can act on.

It is **not** third-party AML surveillance of strangers' wallets. It's the
issuer watching **its own** token.

## What it does

Each tick, over Arbitrum:

- **MXNB (the issuer's token — the focus):**
  - `mint` / `redemption` — every issuance and burn (for a young, growing peso
    stablecoin, each one matters), via Transfer to/from the zero address
  - `supply_swing` — net mint − redeem over the window
  - `large_circulation` — outsized single transfers
  - `concentration` — one address holding an outsized share of windowed volume
- **USDC / USDT (corridor context):** transfer volume counts, so the desk sees
  the broader USD↔peso corridor it operates in.
- **LLM treasury note:** each notable event → a 4-line desk alert
  (SIGNAL / WHY / CONFIDENCE / ACTION), framed in issuer/treasury terms
  (reserve coverage, redemption pressure, peg stress). The model only restates
  figures present in the detection — the detection is real, the LLM explains it.

## Resilience (it doesn't fall over)

Both the RPC and the LLM run behind a **retry → circuit-breaker → fallback
chain** (3 Arbitrum endpoints; LLM: TrueFoundry 70b → 8b → raw Groq). Every run
prints a quantitative **scorecard** (success rate, p50/p95 latency, fallback
rate) so the resilience is *shown*, not claimed.

## Quickstart (judges: one command)

```bash
pip install -r requirements.txt
cp .env.example .env        # optional: add an LLM key (GROQ_API_KEY or TFY_*).
                            # No key? It falls back to a deterministic note.
python sentinel.py --demo   # replays a REAL on-chain MXNB mint + relay window
python sentinel.py --once   # one live pass over the basket
```

### `--demo` output (real Arbitrum data)

```
=== MXNB Treasury Sentinel · tick (DEMO) ===
  [MXNB treasury] minted 200.00 / redeemed 0.00 / net Δ +200.00 (3 transfers)
  ┌─ ALERT [HIGH] MXNB · large_mint
  │ SIGNAL     — large mint of 200.00 MXNB to 0x975e20…
  │ WHY        — Mint outpacing demand may cause peg stress.
  │ CONFIDENCE — high signal.
  │ ACTION     — verify reserve coverage.
  └─ (LLM via tfy-groq-70b)
  [USDC] …  (corridor context — counts only)

🛰 Resilience Scorecard — RPC 100% success, p50 279ms · LLM 100% via fallback chain
```

## How it works

```
Arbitrum logs ──▶ ResilientRPC (retry/breaker/fallback, 3 endpoints)
                       │  eth_getLogs(Transfer)
                       ▼
   treasury.py  (MXNB: mint/redeem/supply/concentration)
   flow_monitor.py (USD corridor: large / fan-out / layering, degree-denoised)
                       │  FlowAnomaly
                       ▼
   risk_note.py ──▶ ResilientLLM (TFY 70b → 8b → Groq)  ──▶ treasury desk note
                       │
                       ▼
   sentinel.py  (orchestrate · scorecards · Telegram-ready)
```

## Honest scope

- **MXNB on-chain volume is currently sparse** — it's an early, growing peso
  stablecoin (most flow is still off-chain via Juno rails). The sentinel logs
  *every* MXNB issuance/redemption and uses the USD corridor for live-volume
  context; `--demo` replays a real MXNB mint+relay block window so judges always
  see the full pipeline.
- **USD corridor signals are context, not the headline** — surfaced as counts;
  turning them into high-precision AML signals needs contract-address labeling
  (`eth_getCode`) and is intentionally out of scope here.
- **Roadmap:** Telegram alert feed (wire `TG_BOT_TOKEN`), holder-concentration
  via balance snapshots, depeg/peg-deviation feed, account-abstraction
  session-key alert subscriptions.

## Stack

Python · Arbitrum (public RPC) · `httpx` · OpenAI-compatible LLM gateway
(TrueFoundry / Groq). No private infra required to run the demo.

## License

MIT
