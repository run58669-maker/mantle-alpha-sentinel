"""Mantle Alpha Sentinel — AI-powered on-chain intelligence for Mantle L2.

Monitors mETH, USDY, and USDC flows on Mantle: whale movements, smart money
patterns, fan-out disbursals, and layering chains. Anomalies get an AI-written
alpha note via DeepSeek; alerts push to Telegram.

Usage:
    python sentinel.py --once   # one live pass
    python sentinel.py          # loop (default 60s)
"""
from __future__ import annotations

import argparse
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv
load_dotenv()

import flow_monitor as fm
import risk_note as rn
from tg_bot import TGBot

LIVE_WINDOW_BLOCKS = 500
NOTE_SEVERITIES = {"critical", "high"}
MAX_NOTES_PER_TICK = 4
SEV_RANK = {"critical": 0, "high": 1, "flag": 2}


def emit(symbol: str, anomalies: list, tg=None) -> None:
    notable = sorted([a for a in anomalies if a.severity in NOTE_SEVERITIES],
                     key=lambda a: SEV_RANK.get(a.severity, 9))
    counts: dict[str, int] = {}
    for a in anomalies:
        counts[a.kind] = counts.get(a.kind, 0) + 1
    print(f"  [{symbol}] " + (", ".join(f"{k}:{v}" for k, v in counts.items()) or "clean"))
    for a in notable[:MAX_NOTES_PER_TICK]:
        note, meta = rn.write_note(a)
        print(f"\n  ┌─ ALPHA [{a.severity.upper()}] {symbol} · {a.kind}")
        for line in note.splitlines():
            print(f"  │ {line}")
        print(f"  └─ (AI via {meta.get('via')})")
        if tg:
            ok, info = tg.send_alert(wallet_tag=f"{symbol} {a.kind}",
                                     wallet_addr=(a.addrs[0] if a.addrs else "-"),
                                     kind=a.kind, details=a.detail, interpretation=note)
            print(f"  └─ TG: {'sent OK, msg ' + str(info) if ok else 'FAILED ' + str(info)}")
    if len(notable) > MAX_NOTES_PER_TICK:
        print(f"  … +{len(notable) - MAX_NOTES_PER_TICK} more critical/high (capped)")


def run_once(rpc, tokens, tg=None, seen=None) -> None:
    bn, _ = rpc.block_number()
    if bn is None:
        print("  RPC chain exhausted"); return
    frm, to = bn - LIVE_WINDOW_BLOCKS, bn
    for tok in tokens:
        _, anomalies, _ = fm.scan_window(rpc, tok, frm, to)
        if seen is not None:
            new = []
            for a in anomalies:
                key = (a.kind, a.symbol, a.detail)
                if key not in seen:
                    seen.add(key)
                    new.append(a)
            anomalies = new
        emit(tok["symbol"], anomalies, tg=tg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    args = ap.parse_args()

    tokens = fm.load_tokens()["tokens"]
    rpc = fm.mantle_rpc()
    _tg = TGBot()
    tg = _tg if _tg.token else None
    print("  (Telegram alerts: " + ("ON" if tg else "off — no TG_BOT_TOKEN") + ")")
    seen: set = set()
    try:
        while True:
            print(f"\n=== Mantle Alpha Sentinel · tick @ {time.strftime('%H:%M:%S')} ===")
            run_once(rpc, tokens, tg=tg,
                     seen=None if args.once else seen)
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        print("\n" + rpc.scorecard.render())
        if rn.scorecard().calls:
            print("LLM " + rn.scorecard().render())
        rpc.close()


if __name__ == "__main__":
    main()
