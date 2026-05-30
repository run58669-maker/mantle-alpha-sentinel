"""MXNB issuer / treasury risk monitor (Arbitrum).

Watches the issuer's OWN stablecoin health — the signals a stablecoin treasury
desk actually owns, rather than surveilling third-party flows:
  - mint        : Transfer from 0x0  (new MXNB issued)
  - redemption  : Transfer to   0x0  (MXNB burned/redeemed)
  - supply_swing: net |mint - redeem| over the window
  - large_circulation : a single large user transfer
  - concentration     : one address receiving an outsized share of window volume

For a sparse, growing peso stablecoin EVERY mint/redeem matters, so those are
reported regardless of size; circulation/concentration use a size floor.
"""
from __future__ import annotations

from flow_monitor import FlowAnomaly, Transfer, fetch_transfers

ZERO = "0x" + "0" * 40


def classify(t: Transfer) -> str:
    if t.frm == ZERO:
        return "mint"
    if t.to == ZERO:
        return "redemption"
    return "transfer"


def scan_treasury(rpc, token: dict, from_block: int, to_block: int) -> tuple[dict, list[FlowAnomaly]]:
    transfers = fetch_transfers(rpc, token, from_block, to_block)
    sym = token["symbol"]
    floor = token.get("large_threshold", 50000)

    minted = sum(t.amount for t in transfers if classify(t) == "mint")
    redeemed = sum(t.amount for t in transfers if classify(t) == "redemption")
    net = minted - redeemed
    circ = [t for t in transfers if classify(t) == "transfer"]

    events: list[FlowAnomaly] = []

    # every issuance / redemption is logged (sparse token: each one matters)
    for t in transfers:
        k = classify(t)
        if k == "mint":
            events.append(FlowAnomaly(
                "large_mint", sym, "critical" if t.amount >= floor else "high",
                f"+{t.amount:,.2f} {sym} minted → {t.to[:12]}… (blk {t.block})",
                [t.to], t.amount))
        elif k == "redemption":
            events.append(FlowAnomaly(
                "large_redemption", sym, "critical" if t.amount >= floor else "high",
                f"-{t.amount:,.2f} {sym} redeemed ← {t.frm[:12]}… (blk {t.block})",
                [t.frm], t.amount))
        elif t.amount >= floor:
            events.append(FlowAnomaly(
                "large_circulation", sym, "high" if t.amount >= floor * 5 else "flag",
                f"{t.amount:,.2f} {sym}  {t.frm[:10]}…→{t.to[:10]}… (blk {t.block})",
                [t.frm, t.to], t.amount))

    # net supply swing over the window
    if abs(net) >= floor:
        events.append(FlowAnomaly(
            "supply_swing", sym, "high",
            f"net supply Δ {net:+,.2f} {sym} (minted {minted:,.2f} / redeemed {redeemed:,.2f}) this window",
            [], abs(net)))

    # concentration: top recipient share of circulating volume
    recv: dict[str, float] = {}
    for t in circ:
        recv[t.to] = recv.get(t.to, 0.0) + t.amount
    total = sum(recv.values())
    if total > 0 and recv:
        top_addr, top_amt = max(recv.items(), key=lambda kv: kv[1])
        share = top_amt / total
        if share >= 0.5 and top_amt >= floor:
            events.append(FlowAnomaly(
                "concentration", sym, "high",
                f"{top_addr[:12]}… received {share*100:.0f}% of windowed {sym} circulation "
                f"({top_amt:,.2f} of {total:,.2f})",
                [top_addr], top_amt))

    summary = {
        "transfers": len(transfers), "mints": sum(1 for t in transfers if classify(t) == "mint"),
        "redemptions": sum(1 for t in transfers if classify(t) == "redemption"),
        "minted": minted, "redeemed": redeemed, "net_supply_delta": net,
    }
    return summary, events
