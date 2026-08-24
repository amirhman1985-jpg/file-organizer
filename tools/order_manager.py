from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from file_organizer import PRODUCT_NAME, PUBLISHER
from tools.license_manager import issue_license


ORDERS_DIR = Path("orders")


def ensure_orders_directory() -> None:
    """Create the orders directory if it does not exist."""
    ORDERS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def order_path(order_id: str) -> Path:
    """Return the filesystem path for an order."""
    return ORDERS_DIR / f"{order_id}.json"


def create_order(
    order_id: str,
    customer: str,
    customer_email: str,
    amount: int,
    currency: str = "IRR",
) -> Path:
    """
    Create a new pending order.
    """
    ensure_orders_directory()

    path = order_path(order_id)

    if path.exists():
        raise FileExistsError(
            f"Order already exists: {order_id}"
        )

    order = {
        "order_id": order_id,
        "product": PRODUCT_NAME,
        "publisher": PUBLISHER,
        "customer": customer,
        "customer_email": customer_email,
        "amount": amount,
        "currency": currency,
        "status": "pending",
        "license_id": None,
        "payment_id": None,
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "paid_at": None,
    }

    path.write_text(
        json.dumps(
            order,
            indent=2,
        ),
        encoding="utf-8",
    )

    return path


def load_order(
    order_id: str,
) -> dict:
    """
    Load an order from disk.
    """
    path = order_path(order_id)

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Order not found: {order_id}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Order file is invalid JSON: {order_id}"
        ) from exc


def save_order(
    order: dict,
) -> Path:
    """
    Save an order to disk.
    """
    path = order_path(
        order["order_id"]
    )

    path.write_text(
        json.dumps(
            order,
            indent=2,
        ),
        encoding="utf-8",
    )

    return path


def mark_paid(
    order_id: str,
    payment_id: str | None = None,
) -> Path:
    """
    Mark a pending order as paid and issue its Pro license.
    """
    order = load_order(order_id)

    if order["status"] == "paid":
        raise ValueError(
            f"Order is already paid: {order_id}"
        )

    if order["status"] != "pending":
        raise ValueError(
            f"Cannot mark order as paid "
            f"from status: {order['status']}"
        )

    if payment_id is not None and not payment_id.strip():
        raise ValueError(
            "Payment ID cannot be empty."
        )

    license_id = (
        f"FOP-{order_id.removeprefix('ORD-')}"
    )

    license_path = issue_license(
        license_id=license_id,
        order_id=order["order_id"],
        customer=order["customer"],
        customer_email=order["customer_email"],
    )

    order["status"] = "paid"
    order["license_id"] = license_id
    order["payment_id"] = payment_id
    order["paid_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    save_order(order)

    print("Order marked as paid")
    print(
        f"Order ID   : {order['order_id']}"
    )
    print(
        f"Payment ID : {payment_id or '-'}"
    )
    print(
        f"Customer   : {order['customer']}"
    )
    print(
        f"License ID : {license_id}"
    )
    print(
        f"License    : {license_path}"
    )

    return license_path


def list_orders() -> None:
    """
    List all valid order files.
    """
    ensure_orders_directory()

    orders = sorted(
        ORDERS_DIR.glob("*.json")
    )

    if not orders:
        print("No orders found.")
        return

    print(
        f"Orders: {len(orders)}"
    )

    for path in orders:
        try:
            order = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            print(
                f"  {path.stem} [INVALID]"
            )
            continue

        print(
            f"  {order.get('order_id', path.stem)} "
            f"| {order.get('status', 'unknown')} "
            f"| {order.get('customer', '-')}"
        )


def inspect_order(
    order_id: str,
) -> int:
    """
    Display order details.
    """
    try:
        order = load_order(order_id)
    except (
        FileNotFoundError,
        ValueError,
    ) as exc:
        print(
            f"Error: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        f"Order ID       : "
        f"{order['order_id']}"
    )
    print(
        f"Product        : "
        f"{order['product']}"
    )
    print(
        f"Publisher      : "
        f"{order['publisher']}"
    )
    print(
        f"Customer       : "
        f"{order['customer']}"
    )
    print(
        f"Email          : "
        f"{order['customer_email']}"
    )
    print(
        f"Amount         : "
        f"{order['amount']} "
        f"{order['currency']}"
    )
    print(
        f"Status         : "
        f"{order['status']}"
    )
    print(
        f"License ID     : "
        f"{order['license_id'] or '-'}"
    )
    print(
        f"Payment ID     : "
        f"{order['payment_id'] or '-'}"
    )
    print(
        f"Created        : "
        f"{order['created_at']}"
    )
    print(
        f"Paid at        : "
        f"{order['paid_at'] or '-'}"
    )

    return 0


def build_parser() -> argparse.ArgumentParser:
    """
    Build the Order Manager CLI parser.
    """
    parser = argparse.ArgumentParser(
        description=(
            "TechYarman Order Manager "
            "for File Organizer."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # -----------------------------
    # create
    # -----------------------------
    create_parser = subparsers.add_parser(
        "create",
        help="Create a new order.",
    )

    create_parser.add_argument(
        "--order-id",
        required=True,
        help="Unique order ID.",
    )

    create_parser.add_argument(
        "--customer",
        required=True,
        help="Customer name.",
    )

    create_parser.add_argument(
        "--email",
        required=True,
        help="Customer email.",
    )

    create_parser.add_argument(
        "--amount",
        required=True,
        type=int,
        help="Order amount.",
    )

    create_parser.add_argument(
        "--currency",
        default="IRR",
        help="Order currency.",
    )

    # -----------------------------
    # mark-paid
    # -----------------------------
    paid_parser = subparsers.add_parser(
        "mark-paid",
        help=(
            "Mark an order as paid "
            "and issue its license."
        ),
    )

    paid_parser.add_argument(
        "order_id",
        help="Order ID.",
    )

    paid_parser.add_argument(
        "--payment-id",
        default=None,
        help="Payment gateway transaction ID.",
    )

    # -----------------------------
    # list
    # -----------------------------
    subparsers.add_parser(
        "list",
        help="List all orders.",
    )

    # -----------------------------
    # inspect
    # -----------------------------
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect a single order.",
    )

    inspect_parser.add_argument(
        "order_id",
        help="Order ID.",
    )

    return parser


def main() -> int:
    """
    CLI entry point.
    """
    parser = build_parser()
    args = parser.parse_args()

    # -----------------------------
    # create
    # -----------------------------
    if args.command == "create":
        try:
            output = create_order(
                order_id=args.order_id,
                customer=args.customer,
                customer_email=args.email,
                amount=args.amount,
                currency=args.currency,
            )
        except FileExistsError as exc:
            print(
                f"Error: {exc}",
                file=sys.stderr,
            )
            return 1

        print(
            "Order created successfully"
        )
        print(
            f"Order ID : {args.order_id}"
        )
        print(
            f"Product  : {PRODUCT_NAME}"
        )
        print(
            f"Publisher: {PUBLISHER}"
        )
        print(
            f"Customer : {args.customer}"
        )
        print(
            f"Amount   : "
            f"{args.amount} {args.currency}"
        )
        print(
            "Status   : pending"
        )
        print(
            f"File     : {output}"
        )

        return 0

    # -----------------------------
    # mark-paid
    # -----------------------------
    if args.command == "mark-paid":
        try:
            mark_paid(
                order_id=args.order_id,
                payment_id=args.payment_id,
            )
        except (
            FileNotFoundError,
            ValueError,
            RuntimeError,
        ) as exc:
            print(
                f"Error: {exc}",
                file=sys.stderr,
            )
            return 1

        return 0

    # -----------------------------
    # list
    # -----------------------------
    if args.command == "list":
        list_orders()
        return 0

    # -----------------------------
    # inspect
    # -----------------------------
    if args.command == "inspect":
        return inspect_order(
            args.order_id
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())