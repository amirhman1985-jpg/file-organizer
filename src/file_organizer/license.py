from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)

from file_organizer import PRODUCT_NAME, PUBLISHER


PUBLIC_KEY_B64 = "qI4liUKqokNQJyEDvM989pTFLL1/TVCyJ/qrpKGBrU4="


@dataclass(frozen=True)
class License:
    license_id: str
    customer: str
    edition: str
    expires_at: date | None


class LicenseError(ValueError):
    pass


def _canonical_payload(data: dict) -> bytes:
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


def load_license(license_path: str | Path) -> License:
    license_path = Path(license_path)

    try:
        data = json.loads(
            license_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise LicenseError(
            f"Could not read license file: {exc}"
        ) from exc

    required_fields = {
        "license_id",
        "product",
        "publisher",
        "customer",
        "edition",
        "expires_at",
        "signature",
    }

    missing = required_fields - data.keys()

    if missing:
        raise LicenseError(
            "License is missing fields: "
            + ", ".join(sorted(missing))
        )

    try:
        signature = base64.b64decode(
            data["signature"],
            validate=True,
        )

        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(PUBLIC_KEY_B64)
        )

        public_key.verify(
            signature,
            _canonical_payload(data),
        )

    except (ValueError, InvalidSignature) as exc:
        raise LicenseError(
            "Invalid license signature"
        ) from exc

    if data["product"] != PRODUCT_NAME:
        raise LicenseError(
            "License is for a different product"
        )

    if data["publisher"] != PUBLISHER:
        raise LicenseError(
            "License was not issued by TechYarman"
        )

    if data["edition"] != "pro":
        raise LicenseError(
            "This license is not a Pro license"
        )

    expires_at = None

    if data["expires_at"]:
        try:
            expires_at = date.fromisoformat(
                data["expires_at"]
            )
        except ValueError as exc:
            raise LicenseError(
                "Invalid license expiration date"
            ) from exc

        if expires_at < date.today():
            raise LicenseError(
                "License has expired"
            )

    return License(
        license_id=data["license_id"],
        customer=data["customer"],
        edition=data["edition"],
        expires_at=expires_at,
    )