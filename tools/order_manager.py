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
    ORDERS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def order_path(order_id: str) -> Path:
    return ORDERS_DIR / f"{order_id}.json"


def create_order(
    order_id: str,
    customer: str,
    customer_email: str,
    amount: int,
    currency: str = "IRR",
) -> Path:
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


def save_order(
    order: dict,
) -> Path:
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
) -> Path:
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
    order["paid_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    save_order(order)

    print(
        "Order marked as paid"
    )
    print(
        f"Order ID   : {order['order_id']}"
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
            f"  {order['order_id']} "
            f"| {order['status']} "
            f"| {order['customer']}"
        )


def build_parser() -> argparse.ArgumentParser:
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

    paid_parser = subparsers.add_parser(
        "mark-paid",
        help="Mark an order as paid and issue its license.",
    )

    paid_parser.add_argument(
        "order_id",
        help="Order ID.",
    )

    subparsers.add_parser(
        "list",
        help="List all orders.",
    )

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
    parser = build_parser()
    args = parser.parse_args()

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

        print("Order created successfully")
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
            f"Status   : pending"
        )
        print(
            f"File     : {output}"
        )

        return 0

    if args.command == "mark-paid":
        try:
            mark_paid(args.order_id)
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

    if args.command == "list":
        list_orders()
        return 0

    if args.command == "inspect":
        try:
            order = load_order(
                args.order_id
            )
        except FileNotFoundError as exc:
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
            f"Created        : "
            f"{order['created_at']}"
        )
        print(
            f"Paid at        : "
            f"{order['paid_at'] or '-'}"
        )

        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())