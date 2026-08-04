#!/usr/bin/env python3
"""Build a small Mihomo/Clash profile from live-tested regional shards."""

from __future__ import annotations

import copy
import json
import urllib.request
from pathlib import Path

import yaml


BASE = (
    "https://raw.githubusercontent.com/Au1rxx/free-vpn-subscriptions/"
    "refs/heads/main/output/country"
)

# Nearby Asian regions get more slots. US is only a backup.
REGIONS = [
    ("PH", "🇵🇭", 2),
    ("HK", "🇭🇰", 5),
    ("JP", "🇯🇵", 5),
    ("SG", "🇸🇬", 5),
    ("TW", "🇹🇼", 4),
    ("US", "🇺🇸", 3),
]

OUTPUT = Path(__file__).with_name("clash.yaml")


def download_region(code: str) -> list[dict]:
    url = f"{BASE}/{code}/clash-0001.yaml"
    request = urllib.request.Request(url, headers={"User-Agent": "KrizziaVPN-Updater/2"})
    with urllib.request.urlopen(request, timeout=45) as response:
        document = yaml.safe_load(response.read()) or {}
    proxies = document.get("proxies", [])
    if not isinstance(proxies, list):
        raise ValueError(f"Invalid proxy list for {code}")
    return [item for item in proxies if isinstance(item, dict)]


def fingerprint(proxy: dict) -> str:
    comparable = {key: value for key, value in proxy.items() if key != "name"}
    return json.dumps(comparable, sort_keys=True, ensure_ascii=False, default=str)


def main() -> None:
    selected: list[dict] = []
    region_names: dict[str, list[str]] = {}
    seen: set[str] = set()

    for code, flag, limit in REGIONS:
        names: list[str] = []
        try:
            candidates = download_region(code)
        except Exception as exc:
            print(f"Warning: could not update {code}: {exc}")
            candidates = []

        for candidate in candidates:
            marker = fingerprint(candidate)
            if marker in seen:
                continue
            seen.add(marker)
            proxy = copy.deepcopy(candidate)
            name = f"{flag} {code} {len(names) + 1:02d}"
            proxy["name"] = name
            selected.append(proxy)
            names.append(name)
            if len(names) >= limit:
                break
        region_names[code] = names

    if not selected:
        raise RuntimeError("No proxy nodes were downloaded; keeping the previous profile")

    all_names = [proxy["name"] for proxy in selected]
    country_groups: list[dict] = []
    country_group_names: list[str] = []
    for code, flag, _ in REGIONS:
        names = region_names.get(code, [])
        if not names:
            continue
        group_name = f"{flag} {code} SERVERS"
        country_group_names.append(group_name)
        country_groups.append({"name": group_name, "type": "select", "proxies": names})

    profile = {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "info",
        "ipv6": False,
        "unified-delay": True,
        "tcp-concurrent": True,
        "proxies": selected,
        "proxy-groups": [
            {
                "name": "💎 KRIZZIA VPN",
                "type": "select",
                "proxies": ["⚡ AUTO FASTEST", "🌏 CHOOSE COUNTRY", *country_group_names],
            },
            {
                "name": "⚡ AUTO FASTEST",
                "type": "url-test",
                "proxies": all_names,
                "url": "https://www.gstatic.com/generate_204",
                "interval": 300,
                "tolerance": 100,
                "lazy": True,
            },
            {
                "name": "🌏 CHOOSE COUNTRY",
                "type": "select",
                "proxies": country_group_names,
            },
            *country_groups,
        ],
        "rules": ["MATCH,💎 KRIZZIA VPN"],
    }

    header = (
        "# KRIZZIA VPN - lightweight live-tested profile\n"
        "# Generated automatically. Do not paste passwords or private data here.\n"
    )
    rendered = yaml.safe_dump(
        profile,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=120,
    )
    OUTPUT.write_text(header + rendered, encoding="utf-8")
    print(f"Created {OUTPUT.name} with {len(selected)} unique nodes")


if __name__ == "__main__":
    main()
