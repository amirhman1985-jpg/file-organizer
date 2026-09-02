from __future__ import annotations

import base64
import hashlib
import hmac


def verify_woocommerce_signature(
    body: bytes,
    signature: str,
    secret: str,
) -> bool:
    """
    Verify WooCommerce's HMAC-SHA256 webhook signature.

    WooCommerce sends the signature as base64.
    """

    if not secret:
        return False

    if not signature:
        return False

    digest = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()

    expected = base64.b64encode(
        digest
    ).decode("ascii")

    return hmac.compare_digest(
        expected,
        signature,
    )