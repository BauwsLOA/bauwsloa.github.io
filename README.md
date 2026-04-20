<div align="center">

<div align="center">
<img src="https://oldschool.runescape.wiki/images/Leagues_VI_-_Demonic_Pacts_League_logo.png" alt="Demonic Pacts Logo" width="140"/>

# OSRS Demonic Pacts League Leaderboard

[![Live Site](https://img.shields.io/badge/Live%20Site-Visit-c8a84b?style=for-the-badge&logo=github&labelColor=0d0d0d)](https://bauwsloa.github.io/OSRS-Demonic-Pacts-Leaderboards/)
[![Auto Update](https://img.shields.io/badge/Auto%20Update-Hourly-2d6a2d?style=for-the-badge&logo=github-actions&labelColor=0d0d0d)](https://github.com/BauwsLOA/OSRS-Demonic-Pacts-Leaderboards/actions)
[![Proxy](https://img.shields.io/badge/Proxy-Cloudflare%20Workers-F38020?style=for-the-badge&logo=cloudflare&labelColor=0d0d0d)](https://workers.cloudflare.com/)

**Leagues VI: Demonic Pacts — April 15 to June 10, 2026**

</div>

---

## What it does

A live leaderboard tracker for OSRS Leagues VI. Pulls rank, league points, and unlocked region data for the top players and presents it in a fast, filterable dark-themed interface.

- **⚔ Fetch Leaderboard** — loads up to 500+ players from Jagex's seasonal hiscores
- **🗺 Fetch Regions** — pulls each player's unlocked regions from TempleOSRS
- **🔎 Player Lookup** — search any player by name; fetches rank, points, and regions live even if they aren't in the loaded pages
- **Filter by region** — Match ANY or ALL with multi-region checkbox filtering
- **Sort & search** — sort by any column, search by name
- **Export CSV** — download the current filtered view

---

## How it works

GitHub Actions runs `export_leaderboard.py` every hour, fetches fresh data through the Cloudflare Worker (to avoid Jagex IP blocks), and commits the result back as `leaderboard_data.json`. The site loads this snapshot on page open, and the live fetch buttons let you pull fresher data on demand.

```
GitHub Actions (hourly)
  → export_leaderboard.py
  → Cloudflare Worker proxy
  → Jagex hiscores + TempleOSRS
  → leaderboard_data.json committed to repo
  → GitHub Pages serves it
```

---

## Stack

| | |
|---|---|
| Frontend | HTML / CSS / Vanilla JS |
| Hosting | GitHub Pages |
| Auto-update | GitHub Actions |
| CORS Proxy | Cloudflare Workers |
| Data | Jagex Hiscores + TempleOSRS |

---

<div align="center">
<sub>Not affiliated with Jagex or TempleOSRS.</sub>
</div>
