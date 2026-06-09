"""Chaos fault injection for the resilient LLM chain.

The point of a resilience layer is worthless if it's never exercised — a clean
run shows 100% success / 0% fallback and proves nothing. These fault hooks let
you *force* a target to fail so the scorecard shows real recovery (fallback
rate > 0, MTTR > 0).

    python chaos.py        # kills the primary LLM target, shows fallback recovery

Plug a hook into ResilientLLM(targets, fault_hook=kill_target("tfy-groq-70b")).
"""
from __future__ import annotations

import random

from resilient_llm import Target


class InjectedFault(Exception):
    """Raised by a chaos hook to simulate a provider outage."""


def kill_target(*names: str):
    """Hook that makes the named target(s) always fail → chain falls to the next."""
    bad = set(names)

    def hook(target: Target, attempt: int) -> None:
        if target.name in bad:
            raise InjectedFault(f"forced outage on {target.name} (attempt {attempt})")
    return hook


def flaky(p: float = 0.5, seed: int = 0):
    """Hook that fails each attempt with probability p (seeded → reproducible)."""
    rng = random.Random(seed)

    def hook(target: Target, attempt: int) -> None:
        if rng.random() < p:
            raise InjectedFault(f"flaky failure on {target.name} (attempt {attempt})")
    return hook


if __name__ == "__main__":
    import risk_note
    from resilient_llm import ResilientLLM, Scorecard

    targets = risk_note.build_targets()
    if len(targets) < 2:
        print("Need ≥2 LLM targets to show fallback — add a second DASHSCOPE target or extend build_targets().")
        raise SystemExit(1)

    primary = targets[0].name
    sc = Scorecard()
    client = ResilientLLM(targets, scorecard=sc, fault_hook=kill_target(primary))
    print(f"CHAOS: forcing primary target '{primary}' to fail — expect fallback to '{targets[1].name}'.\n")

    resp, rec = client.chat(
        [{"role": "system", "content": "You are an on-chain alpha analyst for Mantle L2. Reply in one line."},
         {"role": "user", "content": "Acknowledge: a 500.00 mETH whale transfer was detected on Mantle."}],
        max_tokens=60, temperature=0,
    )
    print(f"recovered: ok={rec.ok}  served_by={rec.final_target}  fallback_jumps={rec.fallback_jumps}")
    print("\n" + sc.render())
