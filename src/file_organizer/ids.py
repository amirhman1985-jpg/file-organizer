from __future__ import annotations

import secrets
from datetime import datetime


def _random_token(length: int = 12) -> str:
    """
    Generate a readable uppercase hexadecimal token.
    """
    return secrets.token_hex(
        length // 2
    ).upper()


def generate_order_id() -> str:
    year = datetime.now().year
    token = secrets.token_hex(4).upper()

    return f"ORD-{year}-{token}"

def generate_license_id() -> str:
    year = datetime.now().year
    token = secrets.token_hex(4).upper()

    return f"FOP-{year}-{token}"

def license_id_from_order_id(order_id: str) -> str:
    if not order_id.startswith("ORD-"):
        raise ValueError(
            f"Invalid order ID: {order_id}"
        )

    return f"FOP-{order_id[4:]}"