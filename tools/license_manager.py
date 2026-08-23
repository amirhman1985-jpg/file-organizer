from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from file_organizer import PRODUCT_NAME, PUBLISHER
from file_organizer.license import (
    LicenseError,
    canonical_payload,
)


PRIVATE_KEY_PATH = Path("keys/license_private.key")


def load_private_key():
    try:
        return serialization.load_pem_private_key(
            PRIVATE_KEY_PATH.read_bytes(),
            password=None,
        )
    except OSError as exc:
        raise RuntimeError(
            f"Could not read private key: {exc}"
        ) from exc


def issue_license(
    license_id: str,
    customer: str,
    order_id: str,
    customer_email: str | None = None,
    expires_at: str | None = None,
) -> Path:
    private_key = load_private_key()

    data = {
    "license_id": license_id,
    "order_id": order_id,
    "product": PRODUCT_NAME,
    "publisher": PUBLISHER,
    "customer": customer,
    "customer_email": customer_email,
    "edition": "pro",
    "expires_at": expires_at,
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

    return output


def inspect_license(
    license_path: Path,
) -> None:
    try:
        data = json.loads(
            license_path.read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"Error: Could not read license: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(f"License ID : {data.get('license_id', '-')}")
    print(f"Product    : {data.get('product', '-')}")
    print(f"Publisher  : {data.get('publisher', '-')}")
    print(f"Customer   : {data.get('customer', '-')}")
    print(f"Edition    : {data.get('edition', '-')}")
    print(
        f"Expires    : "
        f"{data.get('expires_at') or 'Never'}"
    )
    print(
        f"Signature  : "
        f"{'Present' if data.get('signature') else 'Missing'}"
    )


def verify_license(
    license_path: Path,
) -> bool:
    from file_organizer.license import load_license

    try:
        license_data = load_license(
            license_path
        )
    except LicenseError as exc:
        print(
            f"INVALID: {exc}",
            file=sys.stderr,
        )
        return False

    print("VALID")
    print(f"License ID : {license_data.license_id}")
    print(f"Customer   : {license_data.customer}")
    print(f"Edition    : {license_data.edition}")
    print(
        f"Expires    : "
        f"{license_data.expires_at or 'Never'}"
    )

    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "TechYarman License Manager "
            "for File Organizer Pro."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    issue_parser = subparsers.add_parser(
        "issue",
        help="Issue a new Pro license.",
    )

    issue_parser.add_argument(
        "--license-id",
        required=True,
        help="Unique license ID.",
    )

    issue_parser.add_argument(
        "--customer",
        required=True,
        help="Customer name.",
    )

    issue_parser.add_argument(
        "--expires-at",
        default=None,
        help="Expiration date in YYYY-MM-DD format.",
    )

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect license information without verification.",
    )

    inspect_parser.add_argument(
        "license",
        type=Path,
        help="Path to license.json",
    )

    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify a license signature and validity.",
    )

    verify_parser.add_argument(
        "license",
        type=Path,
        help="Path to license.json",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "issue":
        try:
            output = issue_license(
                license_id=args.license_id,
                customer=args.customer,
                expires_at=args.expires_at,
            )
        except RuntimeError as exc:
            print(
                f"Error: {exc}",
                file=sys.stderr,
            )
            return 1

        print("License created successfully")
        print(f"Product    : {PRODUCT_NAME}")
        print(f"Publisher  : {PUBLISHER}")
        print(f"Customer   : {args.customer}")
        print("Edition    : Pro")
        print(f"License ID : {args.license_id}")
        print(
            f"Expires    : "
            f"{args.expires_at or 'Never'}"
        )
        print(f"File       : {output}")

        return 0

    if args.command == "inspect":
        inspect_license(args.license)
        return 0

    if args.command == "verify":
        return 0 if verify_license(
            args.license
        ) else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())