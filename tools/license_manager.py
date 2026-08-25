from __future__ import annotations

import argparse
import base64
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from file_organizer import PRODUCT_NAME, PUBLISHER
from file_organizer.license import (
    LicenseError,
    canonical_payload,
    load_license,
)


PRIVATE_KEY_PATH = Path("keys/license_private.key")

LICENSES_DIR = Path("licenses")
ACTIVE_DIR = LICENSES_DIR / "active"
REVOKED_DIR = LICENSES_DIR / "revoked"


def ensure_license_directories() -> None:
    """Create license management directories."""
    ACTIVE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    REVOKED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def load_private_key():
    """Load the private signing key."""
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
    order_id: str,
    customer: str,
    customer_email: str | None = None,
    expires_at: str | None = None,
) -> Path:
    """
    Create and sign a new Pro license.

    The license is stored under licenses/active/.
    """
    ensure_license_directories()

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

    output = (
        ACTIVE_DIR
        / f"{license_id}.json"
    )

    if output.exists():
        raise FileExistsError(
        f"License already exists: {license_id}"
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
) -> int:
    """Display license metadata without verification."""
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
        return 1

    print(
        f"License ID : "
        f"{data.get('license_id', '-')}"
    )
    print(
        f"Order ID   : "
        f"{data.get('order_id', '-')}"
    )
    print(
        f"Product    : "
        f"{data.get('product', '-')}"
    )
    print(
        f"Publisher  : "
        f"{data.get('publisher', '-')}"
    )
    print(
        f"Customer   : "
        f"{data.get('customer', '-')}"
    )
    print(
        f"Email      : "
        f"{data.get('customer_email') or '-'}"
    )
    print(
        f"Edition    : "
        f"{data.get('edition', '-')}"
    )
    print(
        f"Expires    : "
        f"{data.get('expires_at') or 'Never'}"
    )
    print(
        f"Signature  : "
        f"{'Present' if data.get('signature') else 'Missing'}"
    )

    return 0


def verify_license(
    license_path: Path,
) -> bool:
    """Verify license signature and validity."""
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
    print(
        f"License ID : "
        f"{license_data.license_id}"
    )
    print(
        f"Customer   : "
        f"{license_data.customer}"
    )
    print(
        f"Edition    : "
        f"{license_data.edition}"
    )
    print(
        f"Expires    : "
        f"{license_data.expires_at or 'Never'}"
    )

    return True


def find_active_license(
    license_id: str,
) -> Path | None:
    """Find an active license by license ID."""
    ensure_license_directories()

    license_path = (
        ACTIVE_DIR
        / f"{license_id}.json"
    )

    if license_path.exists():
        return license_path

    return None


def revoke_license(
    license_id: str,
    reason: str,
) -> tuple[Path, Path]:
    """
    Move an active license to revoked/
    and create a revocation record.

    Note:
        The current offline application does not
        automatically detect revocation.
    """
    active_license = find_active_license(
        license_id
    )

    if active_license is None:
        raise FileNotFoundError(
            f"Active license not found: {license_id}"
        )

    ensure_license_directories()

    revoked_license = (
        REVOKED_DIR
        / f"{license_id}.json"
    )

    revoke_metadata = (
        REVOKED_DIR
        / f"{license_id}.revoke.json"
    )

    revoke_record = {
        "license_id": license_id,
        "status": "revoked",
        "reason": reason,
        "revoked_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    shutil.move(
        str(active_license),
        str(revoked_license),
    )

    revoke_metadata.write_text(
        json.dumps(
            revoke_record,
            indent=2,
        ),
        encoding="utf-8",
    )

    return (
        revoked_license,
        revoke_metadata,
    )


def list_licenses() -> None:
    """List active and revoked licenses."""
    ensure_license_directories()

    active = sorted(
        ACTIVE_DIR.glob("*.json")
    )

    revoked = sorted(
        path
        for path in REVOKED_DIR.glob("*.json")
        if not path.name.endswith(
            ".revoke.json"
        )
    )

    print(
        f"Active licenses : {len(active)}"
    )
    print(
        f"Revoked licenses: {len(revoked)}"
    )

    if active:
        print()
        print("Active:")

        for path in active:
            print(
                f"  {path.stem}"
            )

    if revoked:
        print()
        print("Revoked:")

        for path in revoked:
            print(
                f"  {path.stem}"
            )


def build_parser() -> argparse.ArgumentParser:
    """Build the License Manager CLI."""
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

    # -----------------------------
    # issue
    # -----------------------------
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
        "--order-id",
        required=True,
        help="Order ID associated with the purchase.",
    )

    issue_parser.add_argument(
        "--customer",
        required=True,
        help="Customer name.",
    )

    issue_parser.add_argument(
        "--email",
        dest="customer_email",
        default=None,
        help="Customer email address.",
    )

    issue_parser.add_argument(
        "--expires-at",
        default=None,
        help="Expiration date in YYYY-MM-DD format.",
    )

    # -----------------------------
    # inspect
    # -----------------------------
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect license metadata.",
    )

    inspect_parser.add_argument(
        "license",
        type=Path,
        help="Path to license.json.",
    )

    # -----------------------------
    # verify
    # -----------------------------
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify license signature and validity.",
    )

    verify_parser.add_argument(
        "license",
        type=Path,
        help="Path to license.json.",
    )

    # -----------------------------
    # revoke
    # -----------------------------
    revoke_parser = subparsers.add_parser(
        "revoke",
        help="Revoke an active license.",
    )

    revoke_parser.add_argument(
        "license_id",
        help="License ID to revoke.",
    )

    revoke_parser.add_argument(
        "--reason",
        required=True,
        help="Reason for revocation.",
    )

    # -----------------------------
    # list
    # -----------------------------
    subparsers.add_parser(
        "list",
        help="List managed licenses.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # -----------------------------
    # issue
    # -----------------------------
    if args.command == "issue":
        try:
            output = issue_license(
                license_id=args.license_id,
                order_id=args.order_id,
                customer=args.customer,
                customer_email=args.customer_email,
                expires_at=args.expires_at,
            )

        except RuntimeError as exc:
            print(
                f"Error: {exc}",
                file=sys.stderr,
            )
            return 1

        print(
            "License created successfully"
        )
        print(
            f"Product    : {PRODUCT_NAME}"
        )
        print(
            f"Publisher  : {PUBLISHER}"
        )
        print(
            f"Customer   : {args.customer}"
        )
        print(
            f"Email      : "
            f"{args.customer_email or '-'}"
        )
        print("Edition    : Pro")
        print(
            f"License ID : "
            f"{args.license_id}"
        )
        print(
            f"Order ID   : "
            f"{args.order_id}"
        )
        print(
            f"Expires    : "
            f"{args.expires_at or 'Never'}"
        )
        print(
            f"File       : {output}"
        )

        return 0

    # -----------------------------
    # inspect
    # -----------------------------
    if args.command == "inspect":
        return inspect_license(
            args.license
        )

    # -----------------------------
    # verify
    # -----------------------------
    if args.command == "verify":
        return (
            0
            if verify_license(
                args.license
            )
            else 1
        )

    # -----------------------------
    # revoke
    # -----------------------------
    if args.command == "revoke":
        try:
            revoked_license, revoke_metadata = (
                revoke_license(
                    license_id=args.license_id,
                    reason=args.reason,
                )
            )

        except FileNotFoundError as exc:
            print(
                f"Error: {exc}",
                file=sys.stderr,
            )
            return 1

        print("License revoked")
        print(
            f"License ID : "
            f"{args.license_id}"
        )
        print(
            f"Reason     : "
            f"{args.reason}"
        )
        print(
            f"License    : "
            f"{revoked_license}"
        )
        print(
            f"Record     : "
            f"{revoke_metadata}"
        )

        return 0

    # -----------------------------
    # list
    # -----------------------------
    if args.command == "list":
        list_licenses()
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())