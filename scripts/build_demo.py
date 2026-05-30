"""Build the demo video for MXNB Treasury Sentinel (Ethereum México · AI × Blockchain).

Pipeline (same shape as prior submissions):
  1. edge-tts → per-scene narration MP3
  2. Playwright → per-scene visual PNG (HTML rendered headless at 1920x1080)
  3. ffmpeg image+audio → per-scene MP4
  4. ffmpeg concat → final demo.mp4

Run:
    cd remittance-risk-sentinel
    python scripts/build_demo.py
"""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import edge_tts
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "demo"
VOICE = "en-US-AriaNeural"

BG = "#0b1320"
ACCENT = "#20c997"   # teal — stablecoin/treasury
TEXT = "#e8eef2"
MUTED = "#8a97a6"
CARD = "#16202e"
WRAP = ("font-family:system-ui;height:100vh;box-sizing:border-box;"
        f"background:{BG};color:{TEXT};padding:56px")
MONO = "'Cascadia Code',Consolas,monospace"


SCENES: list[dict] = [
    {
        "id": "01_hook",
        "narration": (
            "Stablecoin issuers do K Y C at the on-ramp. But who watches the token once "
            "it's on-chain? MXNB Treasury Sentinel is an A I risk co-pilot for the issuer "
            "of MXNB — Bitso and Juno's Mexican-peso stablecoin on Arbitrum. It watches "
            "your own token's on-chain health, in real time."
        ),
        "html": f"""<div style="{WRAP};display:flex;flex-direction:column;justify-content:center">
            <h1 style="font-size:66px;margin:0;color:{ACCENT}">MXNB Treasury Sentinel</h1>
            <p style="font-size:30px;margin-top:22px">An AI risk co-pilot for the <b>issuer</b> of a stablecoin</p>
            <p style="font-size:21px;margin-top:14px;color:{MUTED}">Live, resilient, on-chain monitoring of MXNB on Arbitrum</p>
            <p style="font-size:19px;margin-top:48px;color:{MUTED}">Ethereum México 2026 &middot; AI × Blockchain (w/ Bitso)</p>
        </div>""",
    },
    {
        "id": "02_problem",
        "narration": (
            "Every mint, every redemption, every swing in supply, every concentration of "
            "holdings is a treasury and risk signal the issuer needs live. This is not "
            "third-party surveillance of strangers' wallets — it's the issuer watching its "
            "own coin. Off the shelf, that view doesn't exist."
        ),
        "html": f"""<div style="{WRAP}">
            <h1 style="font-size:44px;color:{ACCENT};margin:0">Who watches the issuer's own token?</h1>
            <p style="font-size:22px;margin-top:10px;color:{MUTED}">Not AML on strangers — the issuer watching its <b>own</b> stablecoin's on-chain health.</p>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:40px;font-size:22px">
                <div style="background:{CARD};padding:22px;border-radius:8px;border-left:5px solid {ACCENT}">🟢 mint — new issuance</div>
                <div style="background:{CARD};padding:22px;border-radius:8px;border-left:5px solid {ACCENT}">🔴 redemption / burn</div>
                <div style="background:{CARD};padding:22px;border-radius:8px;border-left:5px solid {ACCENT}">📈 net supply swing</div>
                <div style="background:{CARD};padding:22px;border-radius:8px;border-left:5px solid {ACCENT}">🎯 holder concentration</div>
            </div>
            <p style="margin-top:36px;font-size:19px;color:{MUTED}">Reserve coverage · redemption pressure · peg stress — a treasury desk function.</p>
        </div>""",
    },
    {
        "id": "03_what",
        "narration": (
            "The Sentinel pulls MXNB's transfer logs from Arbitrum and flags the issuer "
            "signals, plus the surrounding U S D corridor for context. Each event becomes a "
            "short treasury-desk note, written by a language model that only restates the "
            "real on-chain figures — the detection is real math, the model just explains it."
        ),
        "html": f"""<div style="{WRAP}">
            <h1 style="font-size:40px;color:{ACCENT};margin:0">How it works</h1>
            <pre style="font-size:20px;background:{CARD};padding:26px;border-radius:8px;margin-top:26px;line-height:1.7;color:{TEXT};font-family:{MONO}">Arbitrum logs ─▶ <span style="color:{ACCENT}">ResilientRPC</span> (retry · breaker · fallback)
                  │  eth_getLogs(Transfer)
                  ▼
   <span style="color:{ACCENT}">treasury.py</span>   MXNB: mint / redeem / supply / concentration
   <span style="color:{ACCENT}">flow_monitor</span>  USD corridor context (USDC / USDT)
                  ▼
   <span style="color:{ACCENT}">risk_note.py</span> ─▶ ResilientLLM ─▶ treasury-desk note
                  ▼
   <span style="color:{ACCENT}">sentinel.py</span>   orchestrate · scorecards · Telegram</pre>
        </div>""",
    },
    {
        "id": "04_live",
        "narration": (
            "Here it is on real Arbitrum data. A two-hundred MXNB mint is detected. "
            "The agent writes the desk note: signal — large mint; why — mint outpacing "
            "demand may pressure the peg; confidence — high; action — verify reserve "
            "coverage. And it pushes the alert straight to Telegram."
        ),
        "html": f"""<div style="{WRAP}">
            <h1 style="font-size:36px;color:{ACCENT};margin:0">Live · real Arbitrum data</h1>
            <pre style="font-size:18px;background:{CARD};padding:24px;border-radius:8px;margin-top:20px;line-height:1.6;color:{TEXT};font-family:{MONO}">$ python sentinel.py --demo

  [MXNB treasury] minted 200.00 / redeemed 0.00 / net Δ <span style="color:{ACCENT}">+200.00</span>
  ┌─ ALERT [HIGH] MXNB · large_mint
  │ <span style="color:{ACCENT}">SIGNAL</span>     — large mint of 200.00 MXNB to 0x975e20…
  │ <span style="color:{ACCENT}">WHY</span>        — mint outpacing demand may pressure the peg
  │ <span style="color:{ACCENT}">CONFIDENCE</span> — high signal
  │ <span style="color:{ACCENT}">ACTION</span>     — verify reserve coverage
  └─ TG: sent OK, msg 730        <span style="color:{MUTED}"># pushed to Telegram</span></pre>
            <p style="margin-top:18px;font-size:18px;color:{MUTED}">Detection is real on-chain math; the LLM only restates the figures (no hallucinated numbers).</p>
        </div>""",
    },
    {
        "id": "05_resilience",
        "narration": (
            "Both the R P C and the language model run behind a retry, circuit-breaker, and "
            "fallback chain. Kill the primary provider mid-call, and the request still "
            "succeeds — the scorecard shows a hundred-percent recovery, fallback rate a "
            "hundred percent, mean time to recovery about one second. The resilience is "
            "shown, not claimed."
        ),
        "html": f"""<div style="{WRAP}">
            <h1 style="font-size:40px;color:{ACCENT};margin:0">Resilience, shown — not claimed</h1>
            <pre style="font-size:18px;background:{CARD};padding:24px;border-radius:8px;margin-top:22px;line-height:1.6;color:{TEXT};font-family:{MONO}">$ python chaos.py   <span style="color:{MUTED}"># force the primary LLM to fail</span>

  CHAOS: primary 'tfy-groq-70b' killed → fallback to 'tfy-groq-8b'
  recovered: ok=<span style="color:{ACCENT}">True</span>  served_by=tfy-groq-8b  fallback_jumps=1

  🛰 Resilience Scorecard
     success rate         : <span style="color:{ACCENT}">100.0%</span>
     fallback trigger rate: 100.0%
     MTTR (recovered)     : <span style="color:{ACCENT}">1091 ms</span></pre>
            <p style="margin-top:18px;font-size:18px;color:{MUTED}">Primary down → retried → recovered via fallback → request still served.</p>
        </div>""",
    },
    {
        "id": "06_close",
        "narration": (
            "MXNB Treasury Sentinel. Open source, M I T licensed. Built for Ethereum "
            "Mexico, the A I times Blockchain track, with Bitso. Python, Arbitrum, and a "
            "resilient language-model stack. Thanks for watching."
        ),
        "html": f"""<div style="{WRAP};display:flex;flex-direction:column;justify-content:center">
            <h1 style="font-size:56px;margin:0;color:{ACCENT}">MXNB Treasury Sentinel</h1>
            <p style="font-size:22px;margin-top:24px;font-family:{MONO};color:{MUTED}">github.com/run58669-maker/remittance-risk-sentinel</p>
            <p style="font-size:21px;margin-top:44px">Ethereum México 2026 &middot; AI × Blockchain &middot; w/ Bitso</p>
            <p style="font-size:18px;margin-top:18px;color:{MUTED}">Python · Arbitrum · resilient RPC + LLM · MIT</p>
        </div>""",
    },
]


async def gen_audio():
    for scene in SCENES:
        out = OUT / f"{scene['id']}.mp3"
        comm = edge_tts.Communicate(scene["narration"], VOICE, rate="+0%")
        await comm.save(str(out))
        print(f"  audio: {out.name} ({out.stat().st_size // 1024}KB)")


def gen_images():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = ctx.new_page()
        for scene in SCENES:
            html = f"<!doctype html><html><body style='margin:0'>{scene['html']}</body></html>"
            page.set_content(html)
            page.wait_for_timeout(200)
            out = OUT / f"{scene['id']}.png"
            page.screenshot(path=str(out), full_page=False)
            print(f"  image: {out.name}")
        browser.close()


def get_duration(audio_path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())


def render_scenes():
    list_file = OUT / "concat.txt"
    list_lines = []
    for scene in SCENES:
        img = OUT / f"{scene['id']}.png"
        aud = OUT / f"{scene['id']}.mp3"
        mp4 = OUT / f"{scene['id']}.mp4"
        dur = get_duration(aud) + 0.5
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error",
             "-loop", "1", "-i", str(img), "-i", str(aud),
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-tune", "stillimage",
             "-c:a", "aac", "-b:a", "192k", "-shortest", "-t", str(dur),
             "-vf", "scale=1920:1080", str(mp4)],
            check=True,
        )
        list_lines.append(f"file '{mp4.name}'")
        print(f"  scene mp4: {mp4.name} ({dur:.1f}s)")
    list_file.write_text("\n".join(list_lines), encoding="utf-8")
    final = OUT / "demo.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(list_file), "-c", "copy", str(final)],
        check=True,
    )
    print(f"\nFinal: {final} ({final.stat().st_size // 1024}KB)")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("=== 1. narration (edge-tts) ===")
    asyncio.run(gen_audio())
    print("\n=== 2. scene images (Playwright) ===")
    gen_images()
    print("\n=== 3. render + concat (ffmpeg) ===")
    render_scenes()


if __name__ == "__main__":
    main()
