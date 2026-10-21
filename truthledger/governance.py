"""4-phase truth governance loop: audit → distill → purge → consolidate.

Distilled from truth_governance.py + truth_distill_engine.py:
  P1 audit      — category distribution / coverage / structural imbalance
  P2 distill    — score candidate facts (scarcity/contribution/reuse/freshness),
                  keep only semantically valuable ones missing from the cloud
  P3 purge      — detect probe/test/empty keys and emit cleanup proposals
  P4 consolidate— write a JSON+Markdown governance report (the "ledger")

All endpoints/tokens come from an Auth object; nothing is hardcoded.
"""
from __future__ import annotations

import datetime
import json
import os
import re
from collections import Counter
from typing import Callable, Dict, Iterable, List, Optional

LEGAL_TYPES = ["meta_law", "rule", "config", "decision", "data",
               "creative", "risk", "protocol", "unknown"]

# runtime-observation prefixes — never treated as cognitive assets
RUN_OBS_PREFIXES = ["PERCEPTION", "predictive-engine", "INTELLIGENCE_CALL_MONITOR",
                    "HEARTBEAT", "HEALTH", "observation", "auto_scaling", "SVC",
                    "HEALING", "DISSIPATIVE", "COGNITIVE", "COMPUTE_INJECTION",
                    "CTE", "CLASSIFICATION", "AUTO", "self-healing", "STABILITY",
                    "EXT", "theory", "EXP", "TRACE", "monitor", "METRIC", "probe"]

INVALID_PATTERNS = [r"\.PROBE\.", r"PROBE\.", r"test\.", r"TEST\.",
                    r"\.tmp", r"\.TMP", r"example", r"EXAMPLE", r"^\.", r"\.\."]

SCORE_WEIGHTS = {"scarcity": 0.35, "contribution": 0.30,
                 "reusability": 0.20, "freshness": 0.15}


def p1_audit(keys: Iterable[str]) -> Dict:
    keys = [k for k in keys if k]
    cats = Counter(k.split(".")[0] for k in keys)
    total = len(keys)
    run_obs = sum(v for k, v in cats.items()
                  if any(k.startswith(p) for p in RUN_OBS_PREFIXES))
    return {
        "total": total,
        "prefix_kinds": len(cats),
        "run_observation_share": round(run_obs / total * 100, 1) if total else 0.0,
        "top10": cats.most_common(10),
    }


def score_candidate(text: str, *, scarcity: int = 3, contribution: int = 3,
                    reusability: int = 3, freshness: int = 3) -> int:
    """0-100 weighted score over the four upstream dimensions (each 1-5)."""
    dims = {"scarcity": scarcity, "contribution": contribution,
            "reusability": reusability, "freshness": freshness}
    return round(sum(dims[d] * w for d, w in SCORE_WEIGHTS.items()) / 5 * 100)


def p2_distill(candidates: List[Dict], cloud_keys: Iterable[str],
               threshold: int = 60) -> List[Dict]:
    """Keep candidates that score >= threshold and are absent from the cloud."""
    cloud = set(cloud_keys)
    out = []
    for c in candidates:
        s = c.get("score") or score_candidate(c.get("content", ""))
        if s >= threshold and c.get("key") not in cloud:
            out.append({**c, "score": s})
    return sorted(out, key=lambda x: -x["score"])


def p3_detect_invalid(keys: Iterable[str]) -> List[Dict]:
    """Flag probe/test/empty keys — candidates for cleanup proposals."""
    flagged = []
    for k in keys:
        if not k or not k.strip():
            flagged.append({"key": k, "reason": "empty key"})
            continue
        for pat in INVALID_PATTERNS:
            if re.search(pat, k):
                flagged.append({"key": k, "reason": f"matches {pat}"})
                break
    return flagged


def p4_write_report(report: Dict, out_dir: str) -> Dict[str, str]:
    """Persist the governance ledger as JSON + Markdown; returns file paths."""
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    jpath = os.path.join(out_dir, f"governance_report_{ts}.json")
    mpath = os.path.join(out_dir, f"governance_report_{ts}.md")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    lines = ["# Truth Governance Report", "",
             f"- time: {report.get('time')}",
             f"- total keys: {report.get('audit', {}).get('total')}",
             f"- distilled: {len(report.get('distilled', []))}",
             f"- invalid flagged: {len(report.get('invalid', []))}", ""]
    for d in report.get("distilled", [])[:20]:
        lines.append(f"- [{d.get('score')}] {d.get('key')}: "
                     f"{str(d.get('content'))[:80]}")
    with open(mpath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return {"json": jpath, "markdown": mpath}


def run_cycle(cloud_keys: List[str], candidates: List[Dict],
              out_dir: Optional[str] = None) -> Dict:
    """One full audit→distill→purge→consolidate pass, offline."""
    report = {
        "time": datetime.datetime.now().isoformat(),
        "audit": p1_audit(cloud_keys),
        "distilled": p2_distill(candidates, cloud_keys),
        "invalid": p3_detect_invalid(cloud_keys),
    }
    report["verdict"] = ("GOVERN_ACTIVE" if report["distilled"] or report["invalid"]
                         else "GOVERN_IDLE")
    if out_dir:
        report["files"] = p4_write_report(report, out_dir)
    return report
