"""Stablecoin flow detector — Arbitrum USD corridor (USDC / USDT) context.

Pulls ERC-20 Transfer logs over a block window and flags circulation signals:
  - large_transfer : single transfer >= per-token threshold
  - fan_out        : one sender -> many recipients (disbursal pattern)
  - layering       : equal-amount relay chain A->B->C... (structuring pattern)

This is corridor *context* around MXNB; MXNB's own issuer/treasury signals
live in treasury.py. Reuses the resilient RPC (retry -> breaker -> fallback)
from evm_rpc, pointed at Arbitrum public endpoints.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from evm_rpc import ResilientRPC, RPCTarget, TRANSFER_TOPIC, topic_to_address

ROOT = Path(__file__).parent
TOKENS_FILE = ROOT / "tokens.json"

ARBITRUM_TARGETS = [
    RPCTarget(name="arb-public", url="https://arb1.arbitrum.io/rpc"),
    RPCTarget(name="arb-ankr", url="https://rpc.ankr.com/arbitrum"),
    RPCTarget(name="arb-publicnode", url="https://arbitrum-one-rpc.publicnode.com"),
]


@dataclass
class Transfer:
    symbol: str
    frm: str
    to: str
    amount: float
    block: int


@dataclass
class FlowAnomaly:
    kind: str        # large_transfer | fan_out | layering
    symbol: str
    severity: str    # flag | high | critical
    detail: str
    addrs: list = field(default_factory=list)
    amount: float = 0.0


def load_tokens() -> dict:
    return json.loads(TOKENS_FILE.read_text(encoding="utf-8"))


def arbitrum_rpc() -> ResilientRPC:
    return ResilientRPC(targets=ARBITRUM_TARGETS)


def fetch_transfers(rpc: ResilientRPC, token: dict, from_block: int, to_block: int,
                    _depth: int = 0) -> list[Transfer]:
    logs, _ = rpc.logs(from_block, to_block, address=token["address"], topics=[TRANSFER_TOPIC])
    # public RPCs cap eth_getLogs by result count / range and return an error
    # (logs=None). Don't silently drop them — bisect the window and recurse.
    if logs is None and (to_block - from_block) > 1 and _depth < 12:
        mid = (from_block + to_block) // 2
        left = fetch_transfers(rpc, token, from_block, mid, _depth + 1)
        time.sleep(0.12)  # gentle pacing — free public RPCs rate-limit bursts of eth_getLogs
        return left + fetch_transfers(rpc, token, mid + 1, to_block, _depth + 1)
    out: list[Transfer] = []
    if not logs:
        return out
    dec = token["decimals"]
    for l in logs:
        topics = l.get("topics", [])
        if len(topics) < 3:
            continue  # not a standard Transfer(from,to,value)
        try:
            amt = int(l["data"], 16) / (10 ** dec)
        except (ValueError, KeyError):
            continue
        out.append(Transfer(
            symbol=token["symbol"],
            frm=topic_to_address(topics[1]),
            to=topic_to_address(topics[2]),
            amount=amt,
            block=int(l["blockNumber"], 16),
        ))
    return out


# --- detectors -------------------------------------------------------------- #

def detect_large(transfers: list[Transfer], threshold: float) -> list[FlowAnomaly]:
    out = []
    for t in transfers:
        if t.amount >= threshold:
            sev = "critical" if t.amount >= threshold * 10 else "high" if t.amount >= threshold * 3 else "flag"
            out.append(FlowAnomaly(
                "large_transfer", t.symbol, sev,
                f"{t.amount:,.2f} {t.symbol}  {t.frm[:10]}…→{t.to[:10]}…  (blk {t.block})",
                [t.frm, t.to], t.amount,
            ))
    return out


def detect_fan_out(transfers: list[Transfer], min_recipients: int = 3) -> list[FlowAnomaly]:
    by_from: dict[str, list[Transfer]] = {}
    for t in transfers:
        by_from.setdefault(t.frm, []).append(t)
    out = []
    for frm, ts in by_from.items():
        tos = {t.to for t in ts}
        if len(tos) >= min_recipients:
            total = sum(t.amount for t in ts)
            out.append(FlowAnomaly(
                "fan_out", ts[0].symbol, "high",
                f"{frm[:10]}… fanned out to {len(tos)} recipients, {total:,.2f} {ts[0].symbol} total "
                f"(possible disbursal / mule)",
                [frm] + sorted(tos), total,
            ))
    return out


def detect_layering(transfers: list[Transfer], min_hops: int = 3, tol: float = 0.005) -> list[FlowAnomaly]:
    """Equal-amount relay chain: to of one hop == from of next, ~same amount.
    Catches structuring/peeling/layering (e.g. mint→A→B→C all of 200)."""
    by_from: dict[str, list[Transfer]] = {}
    for t in transfers:
        by_from.setdefault(t.frm, []).append(t)
    seen_paths: dict[str, FlowAnomaly] = {}
    for start in transfers:
        chain = [start]
        cur = start
        visited = {cur.frm}
        while len(chain) < 10:
            nxts = sorted(
                [x for x in by_from.get(cur.to, [])
                 if abs(x.amount - cur.amount) <= cur.amount * tol and x.to not in visited],
                key=lambda x: x.block)  # deterministic across RPCs / log order
            if not nxts:
                break
            cur = nxts[0]
            chain.append(cur)
            visited.add(cur.frm)
        if len(chain) >= min_hops:
            path = " → ".join([chain[0].frm[:8] + "…"] + [c.to[:8] + "…" for c in chain])
            key = frozenset([c.frm for c in chain] + [chain[-1].to])  # merge overlapping sub-chains
            seen_paths[key] = FlowAnomaly(
                "layering", start.symbol, "critical",
                f"relay chain ×{len(chain)} of ~{start.amount:,.2f} {start.symbol} "
                f"(structuring/layering): {path}",
                [c.frm for c in chain] + [chain[-1].to], start.amount,
            )
    return list(seen_paths.values())


# Addresses touching >= this many transfers in the window are treated as
# infrastructure (DEX routers, aggregators, CEX hot wallets, pools) rather
# than end-user wallets, and are excluded from mule/structuring detection.
# Data-driven so we don't hard-code (and risk mis-typing) specific addresses.
HUB_MIN_DEGREE = 8


def hub_addresses(transfers: list[Transfer], min_degree: int = HUB_MIN_DEGREE) -> set[str]:
    deg: dict[str, int] = {}
    for t in transfers:
        deg[t.frm] = deg.get(t.frm, 0) + 1
        deg[t.to] = deg.get(t.to, 0) + 1
    return {a for a, d in deg.items() if d >= min_degree}


def scan_window(rpc: ResilientRPC, token: dict, from_block: int, to_block: int
                ) -> tuple[list[Transfer], list[FlowAnomaly], set[str]]:
    transfers = fetch_transfers(rpc, token, from_block, to_block)
    hubs = hub_addresses(transfers)
    # mule/structuring signals only make sense between non-infra wallets
    eoa = [t for t in transfers if t.frm not in hubs and t.to not in hubs]
    anomalies = (
        detect_large(transfers, token["large_threshold"])   # large = large, keep all
        + detect_fan_out(eoa)
        + detect_layering(eoa)
    )
    return transfers, anomalies, hubs
