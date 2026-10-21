"""truthledger — TruthLedger: governance for an AI agent's truth store.

Distilled from ZONGYUAN-ROOT (branch converge-20260928), files:
07_代码与脚本/truth_firewall.py · truth_governance.py ·
truth_provenance_audit.py · truth_immortality_guard.py · truth_distill_engine.py

Submodules:
    firewall    — whitelist gate for high-level truth keys (client-side trust check)
    governance  — 4-phase loop: audit / distill / purge / consolidate
    provenance  — 5-dimension provenance verification of reported truths
    immortality — multi-source registry consistency: snapshot / verify / restore / audit

Credentials are NEVER hardcoded: pass tokens via environment
(TRUTHLEDGER_TOKEN / TRUTHLEDGER_ENDPOINT) or an explicit Auth object.
"""
from .auth import Auth
from .firewall import TruthFirewall
from .immortality import ImmortalityGuard

__version__ = "0.1.0"
__all__ = ["Auth", "TruthFirewall", "ImmortalityGuard", "__version__"]
