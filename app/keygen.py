# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Tom Sayles
"""
keygen.py
─────────────────────────────────────────────────────────────────────────────
CLI helper to generate a cryptographically secure API key.

Usage
-----
::

    python -m app.keygen

Generates a single URL-safe, base64-encoded 32-byte random token and
prints it to stdout.  Suitable for use in ``PDF_API_KEYS`` or an
``api-keys.txt`` secrets file.

Example
-------
::

    $ python -m app.keygen
    gX3vL9mQpAeKFzWs8nRb2cYuJhDiOtTe1xN7BqVlMkIwCjSdUf0PrGaHoZyXvE

The generated token is 43 characters long (32 bytes base64url without
padding).  Generating multiple tokens gives one key per invocation; pipe
to a file to accumulate keys::

    python -m app.keygen >> secrets/api-keys.txt
"""

import secrets
import sys


def generate_key() -> str:
    """Generate a cryptographically secure URL-safe API key.

    Returns:
        43-character URL-safe base64 string (32 bytes of entropy).
    """
    return secrets.token_urlsafe(32)


def main() -> None:
    """CLI entry point: print one new key to stdout."""
    print(generate_key())


if __name__ == "__main__":
    main()
