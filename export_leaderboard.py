#!/usr/bin/env python3
"""
OSRS Demonic Pacts League — JSON Exporter for GitHub Pages
Run this script locally to generate leaderboard_data.json.
Then commit both index.html and leaderboard_data.json to your GitHub Pages repo.

Requirements: pip install requests beautifulsoup4
Usage:
    python export_leaderboard.py              # fetch 4 pages (~100 players)
    python export_leaderboard.py --pages 20   # fetch 20 pages (~500 players)
    python export_leaderboard.py --from-cache # re-export from existing cache only
"""

import argparse
import json
import os
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

# ─────────────────────────────────────────────────────────────────────────────
#  Constants (mirrored from leagues_gui.py)
# ─────────────────────────────────────────────────────────────────────────────

BASE            = "https://secure.runescape.com"
SEASONAL        = f"{BASE}/m=hiscore_oldschool_seasonal"
LEADERBOARD_URL = f"{SEASONAL}/overall.ws"
LEADERBOARD_PRM = {"category_type": 1, "table": 1}
TEMPLE_API      = "https://templeosrs.com/api/leagues/vi/tracking.php"
CACHE_FILE      = "league_cache.json"
OUTPUT_FILE     = "leaderboard_data.json"
MAX_WORKERS     = 10

HEADERS_JAGEX = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
HEADERS_TEMPLE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":     "application/json",
    "Referer":    "https://templeosrs.com/",
}

AREA_MAP = {
    "asgarnia":   "Asgarnia",
    "desert":     "Desert",
    "fremennik":  "Fremennik Province",
    "kandarin":   "Kandarin",
    "kourend":    "Kebos and Kourend",
    "morytania":  "Morytania",
    "tirannwn":   "Tirannwn",
    "wilderness": "Wilderness",
}
ALWAYS_UNLOCKED = ["Varlamore", "Karamja"]

_ROW_RE = re.compile(
    r'<td[^>]*>\s*(\d[\d,]*)\s*</td>\s*'
    r'<td[^>]*>.*?<a[^>]*>([^<]+)</a>.*?</td>\s*'
    r'<td[^>]*>\s*([\d,]+)\s*</td>',
    re.DOTALL
)

# ─────────────────────────────────────────────────────────────────────────────

def parse_leaderboard_html(html):
    players = []
    for m in _ROW_RE.finditer(html):
        try:
            rank  = int(m.group(1).replace(",", ""))
            name  = m.group(2).strip()
            score = int(m.group(3).replace(",", ""))
            players.append({"rank": rank, "name": name, "points": score, "regions": []})
        except (ValueError, IndexError):
            continue
    return players

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"players": {}, "leaderboard": []}

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def http_get(session, url, params=None, headers=None):
    try:
        r = session.get(url, params=params, headers=headers or HEADERS_JAGEX,
                        timeout=12, allow_redirects=True)
        r.raise_for_status()
        return r
    except Exception:
        return None

def fetch_leaderboard_page(page, session):
    resp = http_get(session, LEADERBOARD_URL, {**LEADERBOARD_PRM, "page": page})
    return parse_leaderboard_html(resp.text) if resp else []

def parse_areas(data):
    regions = list(ALWAYS_UNLOCKED)
    for key, val in data.get("info", {}).get("areas", {}).items():
        if val == 1 and key in AREA_MAP:
            regions.append(AREA_MAP[key])
    return regions

def fetch_one_region(name, session):
    resp = http_get(session, TEMPLE_API, {"player": name}, HEADERS_TEMPLE)
    if not resp:
        return name, None
    try:
        data = resp.json()
        if "error" in data or "info" not in data:
            return name, []
        return name, parse_areas(data)
    except Exception:
        return name, None

# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Export OSRS league leaderboard to JSON")
    parser.add_argument("--pages",      type=int, default=4,    help="Leaderboard pages to fetch (25 players each)")
    parser.add_argument("--from-cache", action="store_true",    help="Skip fetching; re-export from cache only")
    args = parser.parse_args()

    cache   = load_cache()
    session = requests.Session()

    # ── 1. Fetch leaderboard ─────────────────────────────────────────────────
    if args.from_cache:
        print("Using cached leaderboard…")
        all_players = list(cache.get("leaderboard", []))
    else:
        all_players = []
        pc = cache.get("players", {})
        for page in range(1, args.pages + 1):
            print(f"  Fetching leaderboard page {page}/{args.pages}…")
            players = fetch_leaderboard_page(page, session)
            for p in players:
                p["regions"] = pc.get(p["name"], [])
            all_players.extend(players)
            if not players and page > 1:
                print("  (empty page — stopping early)")
                break
            if page < args.pages:
                time.sleep(0.3)

        cache["leaderboard"] = all_players
        save_cache(cache)
        print(f"  → {len(all_players):,} players loaded.\n")

    # ── 2. Fetch regions for players without them ────────────────────────────
    needs = [p for p in all_players if not p.get("regions")]
    if needs:
        print(f"Fetching regions for {len(needs):,} players (concurrently)…")
        pc   = cache.setdefault("players", {})
        lock = threading.Lock()
        done = [0]
        ok   = [0]
        sessions = [requests.Session() for _ in range(MAX_WORKERS)]

        def worker(args):
            idx, player = args
            s = sessions[idx % MAX_WORKERS]
            name, regions = fetch_one_region(player["name"], s)
            with lock:
                done[0] += 1
                if regions is not None:
                    player["regions"] = regions
                    pc[name] = regions
                    ok[0] += 1
                if done[0] % 10 == 0 or done[0] == len(needs):
                    print(f"  [{done[0]}/{len(needs)}]  {ok[0]} found, "
                          f"{done[0]-ok[0]} untracked/errors")
                    save_cache(cache)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            list(ex.map(worker, enumerate(needs)))

        save_cache(cache)
        print(f"  → Regions done.\n")
    else:
        print("All regions already cached — skipping region fetch.\n")

    # ── 3. Write output JSON ─────────────────────────────────────────────────
    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "total": len(all_players),
        "players": all_players,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"), ensure_ascii=False)

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"✔  Written {OUTPUT_FILE}  ({len(all_players):,} players, {size_kb:.1f} KB)")
    print(f"\nNext steps:")
    print(f"  1. Commit index.html and {OUTPUT_FILE} to your GitHub Pages repo.")
    print(f"  2. Push — the site will load the JSON automatically.")
    print(f"  3. Re-run this script whenever you want fresh data.")

if __name__ == "__main__":
    main()
