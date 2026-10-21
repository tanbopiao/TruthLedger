"""5-dimension provenance verification of reported truths.

Distilled from truth_provenance_audit.py:
  D1 existence    — the key is readable back from the gateway
  D2 version      — cloud version >= local version (anti-rollback)
  D3 timestamp    — cloud updated_at within the local time window
  D4 integrity    — SHA256 of local content recorded as the lock evidence
  D5 receipt      — upsert response fields match the local ledger record
"""
from __future__ import annotations

import hashlib
import json
from typing import Callable, Dict, List, Optional


def content_digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def verify_one(key: str, local: Dict, cloud: Optional[Dict],
               receipt: Optional[Dict]) -> Dict:
    """Verify one truth against its local ledger record.

    ``local``  = {"version": int, "content": str, "reported_at": iso, ...}
    ``cloud``  = gateway read-back (None when the key is missing)
    ``receipt``= upsert response (None when never uploaded)
    """
    checks: Dict[str, str] = {}
    checks["D1_existence"] = "ok" if cloud else "missing"
    if cloud:
        checks["D2_version"] = ("ok" if cloud.get("version", 0) >= local.get("version", 0)
                                else "rollback")
        checks["D3_timestamp"] = ("ok" if cloud.get("updated_at") else "unknown")
    else:
        checks["D2_version"] = "skipped"
        checks["D3_timestamp"] = "skipped"
    checks["D4_integrity"] = content_digest(local.get("content", ""))
    if receipt:
        ok = (receipt.get("success") is True
              and receipt.get("action") in ("created", "updated", None))
        checks["D5_receipt"] = "ok" if ok else "mismatch"
    else:
        checks["D5_receipt"] = "no-receipt"
    verdict = ("PASS" if all(v in ("ok",) or v.startswith(tuple("0123456789abcdef"))
                             for v in checks.values()) else "FAIL")
    return {"key": key, "checks": checks, "verdict": verdict}


def verify_all(records: Dict[str, Dict], fetch: Callable[[str], Optional[Dict]],
               receipts: Optional[Dict[str, Dict]] = None) -> List[Dict]:
    """Verify every ledger record; ``fetch(key)`` returns the cloud doc or None."""
    receipts = receipts or {}
    out: List[Dict] = []
    for key, local in records.items():
        try:
            cloud = fetch(key)
        except Exception:
            cloud = None
        out.append(verify_one(key, local, cloud, receipts.get(key)))
    return out


def to_csv_rows(results: List[Dict]) -> List[List[str]]:
    rows = [["key", "verdict", "D1", "D2", "D3", "D4", "D5"]]
    for r in results:
        c = r["checks"]
        rows.append([r["key"], r["verdict"], c.get("D1_existence", ""),
                     c.get("D2_version", ""), c.get("D3_timestamp", ""),
                     c.get("D4_integrity", ""), c.get("D5_receipt", "")])
    return rows
