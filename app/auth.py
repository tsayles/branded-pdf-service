# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Tom Sayles
"""
auth.py
─────────────────────────────────────────────────────────────────────────────
Agent-friendly Bearer token authentication for the branded-pdf-service.

Design
------
Operators configure API keys via:

1. ``PDF_API_KEYS`` environment variable — comma-separated list of keys.
2. ``/run/secrets/api-keys.txt`` — one key per line (Docker secrets
   compatible path; configurable via ``PDF_API_KEYS_FILE`` env var).

When no keys are configured the service starts in **open mode**: all
endpoints are accessible without authentication.  A warning is logged at
startup.  This is intentional for development/local use and makes the
default out-of-the-box experience frictionless.

Protected vs open endpoints
----------------------------
Open (no auth required):
  GET  /healthz
  GET  /brands
  GET  /brands/{slug}

Protected (Bearer token required when keys are configured):
  POST  /render
  POST  /brands/{slug}
  DELETE /brands/{slug}
  GET  /brands/{slug}/preview

Usage (FastAPI dependency)
--------------------------
::

    from .auth import require_auth

    @app.post("/render")
    def render(
        request: RenderRequest,
        _: None = Depends(require_auth),
    ) -> Response:
        ...
"""

import logging
import os
import secrets
from typing import FrozenSet, Optional

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# ── Key loading ───────────────────────────────────────────────────────────────

_KEYS_FILE_DEFAULT = "/run/secrets/api-keys.txt"


def _load_keys() -> FrozenSet[str]:
    """Load API keys from environment and/or key file.

    Checks (in order):
    1. ``PDF_API_KEYS`` env var — comma-separated.
    2. ``PDF_API_KEYS_FILE`` env var (default ``/run/secrets/api-keys.txt``)
       — one key per line; missing file is silently ignored.

    Returns:
        Frozenset of valid key strings.  Empty set = open mode.
    """
    keys = set()

    env_keys = os.environ.get("PDF_API_KEYS", "").strip()
    if env_keys:
        for k in env_keys.split(","):
            k = k.strip()
            if k:
                keys.add(k)

    keys_file = os.environ.get(
        "PDF_API_KEYS_FILE", _KEYS_FILE_DEFAULT
    )
    if os.path.isfile(keys_file):
        try:
            with open(keys_file, encoding="utf-8") as fh:
                for line in fh:
                    k = line.strip()
                    if k and not k.startswith("#"):
                        keys.add(k)
        except OSError as exc:
            logger.warning(
                "Could not read API keys file '%s': %s", keys_file, exc
            )

    return frozenset(keys)


def get_valid_keys() -> FrozenSet[str]:
    """Return the current set of valid API keys.

    Re-reads from environment and key file on every call so keys can be
    rotated without restarting the service.

    Returns:
        Frozenset of valid key strings.
    """
    return _load_keys()


def auth_is_enabled() -> bool:
    """Return True if at least one API key is configured.

    Returns:
        True when the service is in protected mode; False for open mode.
    """
    return bool(get_valid_keys())


# ── FastAPI dependency ────────────────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)


def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(
        _bearer_scheme
    ),
) -> None:
    """FastAPI dependency that enforces Bearer token authentication.

    When no API keys are configured (open mode) this dependency is a
    no-op.  When keys are configured, the ``Authorization: Bearer
    <token>`` header must be present and the token must match one of the
    configured keys.

    Args:
        credentials: Parsed ``Authorization`` header (injected by
            FastAPI).

    Raises:
        HTTPException: 401 if the token is missing or invalid when auth
            is enabled.
    """
    keys = get_valid_keys()

    if not keys:
        # Open mode — no keys configured.
        return

    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail=(
                "Authentication required. Provide an API key as "
                "Authorization: Bearer <key>."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    # Use secrets.compare_digest to guard against timing attacks.
    valid = any(
        secrets.compare_digest(token, key) for key in keys
    )
    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
