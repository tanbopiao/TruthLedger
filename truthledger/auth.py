"""Credential handling — env-injected only, never hardcoded.

Distillation note: the upstream scripts contained two hardcoded capture
tokens and a fallback path that read a private token file. Both are
removed; the only supported sources are environment variables.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class Auth:
    """Endpoint + bearer token for a truth gateway."""

    endpoint: str = "https://example.invalid/api/truth"
    token: str = ""
    extra_headers: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, prefix: str = "TRUTHLEDGER") -> "Auth":
        """Build from $<PREFIX>_ENDPOINT / $<PREFIX>_TOKEN.

        Raises RuntimeError when the token is missing — no silent fallback,
        no reading of private credential files (upstream behavior removed).
        """
        endpoint = os.environ.get(f"{prefix}_ENDPOINT", cls.endpoint)
        token = os.environ.get(f"{prefix}_TOKEN", "")
        if not token:
            raise RuntimeError(
                f"missing ${prefix}_TOKEN — set it in the environment; "
                "truthledger never reads hardcoded or file-based tokens"
            )
        return cls(endpoint=endpoint, token=token)

    def headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["X-Capture-Token"] = self.token
        h.update(self.extra_headers)
        return h


def redact(text: str, token: Optional[str] = None, keep: int = 4) -> str:
    """Mask a token in any output/log text (keep last `keep` chars)."""
    if not token:
        return text
    mask = "*" * max(len(token) - keep, 3)
    tail = token[-keep:] if len(token) > keep else ""
    return text.replace(token, mask + tail)
