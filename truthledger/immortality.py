"""Multi-source registry consistency guard (snapshot / verify / restore / audit).

Distilled from truth_immortality_guard.py: keep N copies of a registry in
sync against one authoritative source; detect rollback, loss and content
drift; auto-restore from the authority; compute an "immortality index".

The upstream hardcoded VM paths are replaced by an explicit source map,
so the guard runs on any machine.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
from typing import Callable, Dict, List


def _digest(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def _node_key(node: Dict) -> str:
    return node.get("node_id", "")


def _registry_keys(path: str) -> Dict[str, Dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {_node_key(n): n for n in data.get("nodes", [])}


class ImmortalityGuard:
    def __init__(self, sources: Dict[str, str], authority: str,
                 backup_dir: str = ".truth_guard"):
        """``sources``: name -> path; ``authority`` must be one of them."""
        if authority not in sources:
            raise ValueError("authority must be one of sources")
        self.sources = sources
        self.authority = authority
        self.backup_dir = backup_dir

    # -- snapshot ----------------------------------------------------------
    def snapshot(self) -> str:
        os.makedirs(self.backup_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        snaps = []
        for name, path in self.sources.items():
            if os.path.exists(path):
                dst = os.path.join(self.backup_dir, f"truth_snap_{name}_{ts}.json")
                shutil.copy2(path, dst)
                snaps.append({"source": name, "file": dst, "sha256_16": _digest(dst)})
        idx = os.path.join(self.backup_dir, "snapshot_index.json")
        index = {"snapshots": []}
        if os.path.exists(idx):
            with open(idx, encoding="utf-8") as f:
                index = json.load(f)
        index["snapshots"].append({"ts": ts, "files": snaps})
        with open(idx, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=1)
        return ts

    # -- verify ------------------------------------------------------------
    def verify(self) -> Dict:
        au_map = _registry_keys(self.sources[self.authority])
        report: Dict = {"checked_at": datetime.datetime.now().isoformat(),
                        "authority_count": len(au_map), "sources": {}, "issues": []}
        for name, path in self.sources.items():
            if name == self.authority or not os.path.exists(path):
                continue
            m = _registry_keys(path)
            missing = set(au_map) - set(m)
            extra = set(m) - set(au_map)
            drift = [k for k, n in m.items() if k in au_map
                     and str(n.get("content", "")) != str(au_map[k].get("content", ""))]
            report["sources"][name] = {"count": len(m),
                                       "missing": sorted(missing),
                                       "extra": sorted(extra),
                                       "drift": sorted(drift)}
            if missing or extra or drift:
                report["issues"].append({"source": name, "missing": len(missing),
                                         "extra": len(extra), "drift": len(drift)})
        return report

    # -- restore -----------------------------------------------------------
    def restore(self) -> int:
        au_map = _registry_keys(self.sources[self.authority])
        with open(self.sources[self.authority], encoding="utf-8") as f:
            au_doc = json.load(f)
        fixed = 0
        for name, path in self.sources.items():
            if name == self.authority:
                continue
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(au_doc, f, ensure_ascii=False, indent=1)
                fixed += 1
                continue
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
            m = {_node_key(n): n for n in doc.get("nodes", [])}
            changed = False
            for k, n in au_map.items():
                if k not in m:
                    doc["nodes"].append(n)
                    changed = True
                    fixed += 1
                elif str(m[k].get("content", "")) != str(n.get("content", "")):
                    m[k]["content"] = n["content"]
                    m[k]["connections"] = n.get("connections", [])
                    changed = True
                    fixed += 1
            doc["total_nodes"] = len(doc["nodes"])
            if changed:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(doc, f, ensure_ascii=False, indent=1)
        return fixed

    # -- audit -------------------------------------------------------------
    def audit(self) -> Dict:
        rep = self.verify()
        total = rep["authority_count"]
        issues = sum(i["missing"] + i["extra"] + i["drift"] for i in rep["issues"])
        immortality = max(0.0, 100.0 - (issues / total * 100 if total else 0.0))
        return {"total_truths": total, "issues": issues,
                "immortality_index": round(immortality, 1),
                "ok": not rep["issues"]}
