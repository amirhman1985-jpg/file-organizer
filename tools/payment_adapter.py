from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools import order_manager


class PaymentError(ValueError):
    """Raised when a payment cannot be accepted."""


def find_order_by_payment_id(
    payment_id: str,
) -> dict | None:
    """
    Find an order that already uses the given payment ID.

    Returns the order dictionary when found, otherwise None.
    """
    order_manager.ensure_orders_directory()

    for path in order_manager.ORDERS_DIR.glob("*.json"):
        try:
            order = order_manager.load_order(
                path.stem
            )
        except (FileNotFoundError, ValueError):
            continue

        if order.get("payment_id") == payment_id:
            return order

    return None


def get_existing_license_path(
    order: dict,
) -> Path:
    """
    Return the existing license path for an already-paid order.
    """
    license_id = order.get("license_id")

    if not license_id:
        raise PaymentError(
            "Paid order does not have a license ID."
        )

    license_path = (
        Path("licenses")
        / "active"
        / f"{license_id}.json"
    )

    if not license_path.exists():
        raise PaymentError(
            "Order is marked as paid, but its license file "
            f"does not exist: {license_path}"
        )

    return license_path


def process_payment(
    order_id: str,
    payment_id: str,
    status: str,
    amount: int,
    currency: str,
) -> Path:
    """
    Process a payment event.

    This function is idempotent:
    receiving the same successful payment more than once
    does not issue another license.
    """

    if status != "paid":
        raise PaymentError(
            f"Payment is not successful: {status}"
        )

    if not payment_id.strip():
        raise PaymentError(
            "Payment ID is required"
        )

    order = order_manager.load_order(
        order_id
    )

    # -------------------------------------------------
    # Idempotent retry:
    # same paid order + same payment ID
    # -------------------------------------------------
    if order["status"] == "paid":
        stored_payment_id = order.get(
            "payment_id"
        )

        if stored_payment_id == payment_id:
            return get_existing_license_path(
                order
            )

        raise PaymentError(
            f"Order is already paid with a different "
            f"payment ID: {order_id}"
        )

    # -------------------------------------------------
    # Prevent payment ID reuse across orders
    # -------------------------------------------------
    existing_order = find_order_by_payment_id(
        payment_id
    )

    if existing_order is not None:
        if (
            existing_order["order_id"]
            != order_id
        ):
            raise PaymentError(
                "Payment ID is already associated "
                f"with order: "
                f"{existing_order['order_id']}"
            )

    if order["status"] != "pending":
        raise PaymentError(
            "Order cannot be paid from status: "
            f"{order['status']}"
        )

    if amount != order["amount"]:
        raise PaymentError(
            "Payment amount does not match "
            "order amount"
        )

    if currency != order["currency"]:
        raise PaymentError(
            "Payment currency does not match "
            "order currency"
        )

    license_path = order_manager.mark_paid(
        order_id=order_id,
        payment_id=payment_id,
    )

    return license_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "TechYarman payment adapter "
            "for File Organizer."
        )
    )

    parser.add_argument(
        "--order-id",
        required=True,
        help="Order ID.",
    )

    parser.add_argument(
        "--payment-id",
        required=True,
        help="Payment gateway transaction ID.",
    )

    parser.add_argument(
        "--status",
        required=True,
        choices=[
            "paid",
            "failed",
            "pending",
        ],
        help="Payment status.",
    )

    parser.add_argument(
        "--amount",
        required=True,
        type=int,
        help=(
            "Amount reported by the "
            "payment gateway."
        ),
    )

    parser.add_argument(
        "--currency",
        required=True,
        help=(
            "Currency reported by the "
            "payment gateway."
        ),
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        license_path = process_payment(
            order_id=args.order_id,
            payment_id=args.payment_id,
            status=args.status,
            amount=args.amount,
            currency=args.currency,
        )

    except (
        FileNotFoundError,
        PaymentError,
        ValueError,
        RuntimeError,
    ) as exc:
        print(
            f"Payment error: {exc}",
            file=sys.stderr,
        )
        return 1

    print("Payment accepted")
    print(
        f"Order ID   : {args.order_id}"
    )
    print(
        f"Payment ID : {args.payment_id}"
    )
    print(
        f"License    : {license_path}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())