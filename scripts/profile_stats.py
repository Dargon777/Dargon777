#!/usr/bin/env python3
"""Refresh the public-account stats SVG for Dargon777's GitHub profile.

The card is committed into the repository by GitHub Actions, so the README
never depends on an external statistics rendering server.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import pathlib
import urllib.error
import urllib.request

USER = os.getenv("GITHUB_USER", "Dargon777")
TOKEN = os.getenv("GITHUB_TOKEN", "")
DEST = pathlib.Path("assets/stats.svg")


def get_json(url: str):
    headers = {
        "User-Agent": "dargon-profile-visuals",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
        return json.load(response)


def refresh() -> None:
    repos = []
    for page in range(1, 11):
        url = f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}"
        batch = get_json(url)
        if not isinstance(batch, list):
            raise ValueError("Expected GitHub API repository list")
        repos.extend(batch)
        if len(batch) < 100:
            break

    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=90)
    stars = sum(int(repo.get("stargazers_count") or 0) for repo in repos)
    languages = {repo.get("language") for repo in repos if repo.get("language")}
    active = 0
    for repo in repos:
        timestamp = repo.get("pushed_at")
        if not timestamp:
            continue
        try:
            updated = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            active += updated >= cutoff
        except ValueError:
            continue

    values = [
        ("PUBLIC REPOS", len(repos)),
        ("TOTAL STARS", stars),
        ("UPDATED / 90D", active),
        ("LANGUAGES", len(languages)),
    ]
    cards = []
    for i, (title, value) in enumerate(values):
        x = 28 + 264 * i
        cards.append(
            f'<rect x="{x}" y="73" width="237" height="128" rx="13" '
            f'fill="#222942" stroke="#52527d" stroke-opacity=".6"/>'
            f'<text x="{x+18}" y="109" fill="#aebbd5" '
            f'font-family="Segoe UI,Arial,sans-serif" font-size="13" '
            f'letter-spacing="1">{html.escape(title)}</text>'
            f'<text x="{x+18}" y="174" fill="url(#text)" '
            f'font-family="Segoe UI,Arial,sans-serif" font-size="56" '
            f'font-weight="800">{value}</text>'
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 228" role="img" aria-label="Public GitHub statistics, refreshed daily">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#11182e"/><stop offset="1" stop-color="#171b35"/></linearGradient><linearGradient id="text" x2="1" y2="0"><stop stop-color="#a78bfa"/><stop offset="1" stop-color="#67e8f9"/></linearGradient></defs>
<rect width="1080" height="228" rx="20" fill="url(#bg)"/><rect x="1" y="1" width="1078" height="226" rx="19" stroke="#7b6bae" stroke-opacity=".48" fill="none"/>
<circle cx="36" cy="37" r="6" fill="#34d399"/><text x="55" y="43" fill="#ded9ff" font-size="16" font-weight="700" font-family="Segoe UI,Arial,sans-serif" letter-spacing="2">GITHUB / LIVE SIGNAL</text>
<text x="1050" y="42" text-anchor="end" fill="#98a6c4" font-family="monospace" font-size="13">AUTO-REFRESH · DAILY</text>
{"".join(cards)}
</svg>'''
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(svg, encoding="utf-8")
    print(f"Rendered {DEST}: {len(repos)} repos, {stars} stars, {active} recent, {len(languages)} languages")


if __name__ == "__main__":
    try:
        refresh()
    except (urllib.error.URLError, OSError, ValueError, KeyError, TimeoutError) as exc:
        # Retain a usable, last-known-good card on transient API failures.
        print(f"WARNING: Stats refresh failed, keeping the existing image: {exc}")
