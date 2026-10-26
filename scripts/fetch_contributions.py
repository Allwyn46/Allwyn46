#!/usr/bin/env python3
"""Fetch your public contribution calendar - no API, no token.

GitHub serves it as public HTML at https://github.com/users/<username>/contributions
(the same fragment the profile page uses). We parse the day cells + tooltips and write
data/contributions.json with the raw days and derived stats.

Usage: python scripts/fetch_contributions.py [username]
Username comes from the argument, $GITHUB_USERNAME, $GITHUB_REPOSITORY_OWNER or profile.json.
"""
import json
import os
import re
import sys
from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUT = Path("data/contributions.json")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def resolve_username() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    for var in ("GITHUB_USERNAME", "GITHUB_REPOSITORY_OWNER"):
        if os.environ.get(var):
            return os.environ[var]
    return json.loads(Path("profile.json").read_text(encoding="utf-8"))["username"]


def fetch_days(username: str) -> list[dict]:
    r = requests.get(
        f"https://github.com/users/{username}/contributions",
        headers={"User-Agent": UA, "Accept": "text/html"},
        timeout=30,
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    tips = {t.get("for"): t.get_text(" ", strip=True) for t in soup.find_all("tool-tip")}
    days = []
    for td in soup.select("td[data-date]"):
        level = int(td.get("data-level", 0) or 0)
        tip = tips.get(td.get("id", ""), "")
        m = re.match(r"(No|\d+)\s+contribution", tip)
        if m:
            count = 0 if m.group(1) == "No" else int(m.group(1))
        else:
            count = level  # tooltip missing: fall back to the level so the graph still draws
        days.append({"date": td["data-date"], "count": count, "level": level})
    if not days:
        raise SystemExit("No contribution cells found - did GitHub change its markup?")
    days.sort(key=lambda d: d["date"])
    return days


def streaks(days: list[dict]) -> tuple[int, int]:
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)
    # current streak: walk back from the latest day; an empty *today* doesn't break it yet
    current = 0
    i = len(days) - 1
    if i >= 0 and days[i]["count"] == 0:
        i -= 1
    while i >= 0 and days[i]["count"] > 0:
        current += 1
        i -= 1
    return current, longest


def main() -> None:
    username = resolve_username()
    days = fetch_days(username)
    current, longest = streaks(days)
    best = max(days, key=lambda d: d["count"])
    monthly: "OrderedDict[str, int]" = OrderedDict()
    for d in days:
        monthly[d["date"][:7]] = monthly.get(d["date"][:7], 0) + d["count"]

    data = {
        "username": username,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": sum(d["count"] for d in days),
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly,
        "days": days,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"{username}: {data['total']} contributions, streak {current} (best {longest}), {len(days)} days")


if __name__ == "__main__":
    main()
