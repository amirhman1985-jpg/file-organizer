from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from file_organizer import PRODUCT_NAME, PUBLISHER


PRIVATE_KEY_PATH = Path("keys/license_private.key")


def canonical_payload(data: dict) -> bytes:
    payload = {
        "license_id": data["license_id"],
        "product": data["product"],
        "publisher": data["publisher"],
        "customer": data["customer"],
        "edition": data["edition"],
        "expires_at": data.get("expires_at"),
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: python tools/issue_license.py "
            "<license_id> <customer>"
        )
        raise SystemExit(1)

    license_id = sys.argv[1]
    customer = sys.argv[2]

    private_key = serialization.load_pem_private_key(
        PRIVATE_KEY_PATH.read_bytes(),
        password=None,
    )

    data = {
        "license_id": license_id,
        "product": PRODUCT_NAME,
        "publisher": PUBLISHER,
        "customer": customer,
        "edition": "pro",
        "expires_at": None,
    }

    signature = private_key.sign(
        canonical_payload(data)
    )

    data["signature"] = base64.b64encode(
        signature
    ).decode("ascii")

    output = Path(
        f"license-{license_id}.json"
    )

    output.write_text(
        json.dumps(
            data,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"License created: {output}")


if __name__ == "__main__":
    main()