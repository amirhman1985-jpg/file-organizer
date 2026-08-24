from __future__ import annotations

import argparse
import sys

from tools import order_manager


class PaymentError(ValueError):
    """Raised when a payment cannot be accepted."""


def process_payment(
    order_id: str,
    payment_id: str,
    status: str,
    amount: int,
    currency: str,
):
    """
    Process a payment event received from a gateway.

    This function deliberately does not trust the incoming
    payment amount or currency. It compares them with the
    original order before marking the order as paid.
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

    if order["status"] == "paid":
        raise PaymentError(
            f"Order is already paid: {order_id}"
        )

    if order["status"] != "pending":
        raise PaymentError(
            f"Order cannot be paid from status: "
            f"{order['status']}"
        )

    if amount != order["amount"]:
        raise PaymentError(
            "Payment amount does not match order amount"
        )

    if currency != order["currency"]:
        raise PaymentError(
            "Payment currency does not match order currency"
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
        help="Amount reported by the payment gateway.",
    )

    parser.add_argument(
        "--currency",
        required=True,
        help="Currency reported by the payment gateway.",
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