"""Whitelist firewall for high-level truth keys.

Distilled from truth_firewall.py: when pulling high-level truths
(RULE.META*/PROTOCOL*/AXIOM*/META.*/LAW.*), only keys matching a local
whitelist are trusted; anything else is treated as possibly forged.
"""
from __future__ import annotations

import os
from typing import Dict, Iterable, List

HIGH_LEVEL_PREFIXES = ("RULE.META", "PROTOCOL", "AXIOM", "META.", "LAW.")

TRUSTED, SUSPECT, FETCH_FAIL = "TRUSTED", "SUSPECT", "FETCH_FAIL"


def load_whitelist(path: str) -> List[str]:
    """One key or `prefix*` glob per line; '#' comments allowed."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]


def is_allowed(key: str, whitelist: Iterable[str]) -> bool:
    wl = list(whitelist)
    if key in wl:
        return True
    return any(key.startswith(p[:-1]) for p in wl if p.endswith("*"))


def is_high_level(key: str) -> bool:
    return any(key.startswith(p) for p in HIGH_LEVEL_PREFIXES)


class TruthFirewall:
    """Client-side trust check against a truth gateway.

    ``fetch`` is injectable for testing; default uses urllib with the
    auth headers from :class:`truthledger.auth.Auth`.
    """

    def __init__(self, auth, whitelist_path: str = "", fetch=None):
        self.auth = auth
        self.whitelist_path = whitelist_path
        self._fetch = fetch or self._http_fetch

    # -- default transport ------------------------------------------------
    def _http_fetch(self, key: str) -> Dict:
        import json
        import urllib.request

        url = f"{self.auth.endpoint.rstrip('/')}/{key}"
        req = urllib.request.Request(url, headers=self.auth.headers())
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)

    # -- API ---------------------------------------------------------------
    def check_one(self, key: str, whitelist: Iterable[str] = ()) -> Dict:
        wl = list(whitelist) or load_whitelist(self.whitelist_path)
        try:
            d = self._fetch(key)
        except Exception as e:  # network/parse errors are not a trust verdict
            return {"key": key, "verdict": FETCH_FAIL, "reason": str(e)}
        truth = d.get("truth", {}) if isinstance(d, dict) else {}
        if is_high_level(key) and not is_allowed(key, wl):
            return {"key": key, "verdict": SUSPECT,
                    "reason": "high-level key not in whitelist; treated as forged"}
        return {"key": key, "verdict": TRUSTED, "version": truth.get("version")}
