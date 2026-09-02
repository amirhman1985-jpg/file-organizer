from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from file_organizer.ids import generate_order_id
from server.config import load_settings
from server.services.downloads import create_download_token
from tools import license_manager, order_manager
from tools.delivery_manager import create_customer_package


PAID_STATUSES = {
    "processing",
    "completed",
}


def contains_pro_product(
    payload: dict[str, Any],
    product_id: int,
) -> bool:
    """
    Return True when the WooCommerce order
    contains the configured File Organizer Pro product.
    """
    line_items = payload.get(
        "line_items",
        [],
    )

    if not isinstance(
        line_items,
        list,
    ):
        return False

    for item in line_items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        try:
            item_product_id = int(
                item.get(
                    "product_id",
                    0,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if item_product_id == product_id:
            return True

    return False


def find_order_by_external_id(
    woocommerce_order_id: int,
) -> dict[str, Any] | None:
    """
    Find a local order linked to a WooCommerce order ID.
    """
    order_manager.ensure_orders_directory()

    external_order_id = str(
        woocommerce_order_id
    )

    for path in order_manager.ORDERS_DIR.glob(
        "*.json"
    ):
        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            continue

        if not isinstance(
            data,
            dict,
        ):
            continue

        if data.get(
            "external_order_id"
        ) == external_order_id:
            return data

    return None


def extract_order_data(
    payload: dict[str, Any],
) -> tuple[
    str,
    str,
    str,
    int,
    str,
    str,
    str,
]:
    """
    Extract and validate the basic WooCommerce order data.

    Returns:
        customer,
        customer_email,
        currency,
        amount,
        payment_id,
        external_order_id,
        status
    """
    if "id" not in payload:
        raise ValueError(
            "WooCommerce payload is missing order ID."
        )

    external_order_id = str(
        payload["id"]
    ).strip()

    if not external_order_id:
        raise ValueError(
            "WooCommerce order ID cannot be empty."
        )

    billing = payload.get(
        "billing",
        {},
    )

    if not isinstance(
        billing,
        dict,
    ):
        raise ValueError(
            "WooCommerce billing data is invalid."
        )

    first_name = str(
        billing.get(
            "first_name",
            "",
        )
    ).strip()

    last_name = str(
        billing.get(
            "last_name",
            "",
        )
    ).strip()

    customer = " ".join(
        part
        for part in (
            first_name,
            last_name,
        )
        if part
    )

    if not customer:
        customer = "Customer"

    customer_email = str(
        billing.get(
            "email",
            "",
        )
    ).strip()

    if not customer_email:
        raise ValueError(
            "WooCommerce customer email is required."
        )

    currency = str(
        payload.get(
            "currency",
            "",
        )
    ).strip().upper()

    if not currency:
        raise ValueError(
            "WooCommerce order currency is required."
        )

    total_raw = payload.get(
        "total",
        "0",
    )

    try:
        amount = int(
            float(total_raw)
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"Invalid WooCommerce order amount: {total_raw}"
        ) from exc

    if amount <= 0:
        raise ValueError(
            "WooCommerce order amount must be greater than zero."
        )

    payment_id = str(
        payload.get(
            "transaction_id",
            "",
        )
    ).strip()

    if not payment_id:
        payment_id = (
            f"WOO-{external_order_id}"
        )

    status = str(
        payload.get(
            "status",
            "",
        )
    ).strip().lower()

    if not status:
        raise ValueError(
            "WooCommerce order status is required."
        )

    return (
        customer,
        customer_email,
        currency,
        amount,
        payment_id,
        external_order_id,
        status,
    )


def get_existing_license_path(
    order: dict[str, Any],
) -> Path:
    """
    Return the active license file belonging to a paid order.
    """
    license_id = order.get(
        "license_id"
    )

    if not license_id:
        raise ValueError(
            "Paid order does not have a license ID."
        )

    license_path = (
        license_manager.ACTIVE_DIR
        / f"{license_id}.json"
    )

    if not license_path.exists():
        raise FileNotFoundError(
            "License file for paid order does not exist: "
            f"{license_path}"
        )

    return license_path


def get_woo_sync_status(
    order: dict[str, Any],
) -> str:
    """
    Return the persisted WooCommerce synchronization status.
    """
    return str(
        order.get(
            "woo_sync_status",
            "pending",
        )
    ).strip().lower()


def persist_order(
    order: dict[str, Any],
) -> None:
    """
    Persist the complete order dictionary without filtering
    integration or delivery fields.
    """
    order_id = str(
        order["order_id"]
    )

    path = order_manager.order_path(
        order_id
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            order,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def persist_woo_sync_state(
    order_id: str,
    *,
    status: str,
    error: str | None = None,
) -> None:
    """
    Persist WooCommerce synchronization state
    without changing the rest of the order.
    """
    path = order_manager.order_path(
        order_id
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Order file does not exist: {path}"
        )

    try:
        order = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(
            f"Could not read order file: {path}"
        ) from exc

    if not isinstance(
        order,
        dict,
    ):
        raise RuntimeError(
            f"Order file does not contain an object: {path}"
        )

    order["woo_sync_status"] = status
    order["woo_sync_error"] = error

    persist_order(order)


def complete_delivery(
    order: dict[str, Any],
    license_path: Path,
    settings: Any,
) -> dict[str, str]:
    """
    Create the customer-specific package and secure
    download token for a paid order.
    """
    pro_zip_path = Path(
        settings.delivery_pro_zip_path
    )

    delivery_dir = Path(
        settings.delivery_dir
    )

    customer_package = create_customer_package(
        pro_zip_path=pro_zip_path,
        license_path=license_path,
        customer=order["customer"],
        output_dir=delivery_dir,
    )

    downloads_dir = (
        delivery_dir / ".tokens"
    )

    download_token = create_download_token(
        package_path=customer_package,
        downloads_dir=downloads_dir,
        customer=order["customer"],
    )

    download_url = (
        f"{settings.download_base_url}"
        f"/api/download/{download_token}"
    )

    order["delivery_status"] = (
        "completed"
    )

    order["delivery_package"] = str(
        customer_package
    )

    order["download_token"] = (
        download_token
    )

    order["download_url"] = (
        download_url
    )

    order["delivered_at"] = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    order["delivery_error"] = None

    order_manager.save_order(
        order
    )

    return {
        "delivery_package": str(
            customer_package
        ),
        "download_token": download_token,
        "download_url": download_url,
    }


def process_woocommerce_order(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Process a WooCommerce order webhook.

    Flow:

        Validate payload
            ↓
        Check paid status
            ↓
        Check Pro product
            ↓
        Check currency
            ↓
        Check price
            ↓
        Check duplicate order
            ↓
        Create local order
            ↓
        Issue one license
            ↓
        Create delivery package
            ↓
        Create secure download token

    Existing paid orders are handled idempotently:

        License exists + Delivery failed
            → retry Delivery only

        License exists + Delivery completed
            → do not repeat License or Delivery

        License exists + Delivery completed
        + Woo Sync failed
            → route layer retries Woo Sync only
    """
    settings = load_settings()

    # --------------------------------
    # Required configuration
    # --------------------------------
    if not settings.woocommerce_pro_product_id:
        raise ValueError(
            "WOOCOMMERCE_PRO_PRODUCT_ID "
            "is not configured."
        )

    if not settings.woocommerce_pro_price_irr:
        raise ValueError(
            "WOOCOMMERCE_PRO_PRICE_IRR "
            "is not configured."
        )

    # --------------------------------
    # Extract WooCommerce order data
    # --------------------------------
    (
        customer,
        customer_email,
        currency,
        amount,
        payment_id,
        external_order_id,
        status,
    ) = extract_order_data(
        payload
    )

    # --------------------------------
    # Ignore unpaid orders
    # --------------------------------
    if status not in PAID_STATUSES:
        return {
            "processed": False,
            "reason": (
                f"Order status is {status}"
            ),
            "external_order_id": (
                external_order_id
            ),
        }

    # --------------------------------
    # Verify File Organizer Pro
    # --------------------------------
    if not contains_pro_product(
        payload,
        settings.woocommerce_pro_product_id,
    ):
        return {
            "processed": False,
            "reason": (
                "Order does not contain "
                "File Organizer Pro."
            ),
            "external_order_id": (
                external_order_id
            ),
        }

    # --------------------------------
    # Verify currency
    # --------------------------------
    if currency != "IRR":
        raise ValueError(
            "WooCommerce order currency "
            "must be IRR."
        )

    # --------------------------------
    # Verify price
    # --------------------------------
    if (
        amount
        != settings.woocommerce_pro_price_irr
    ):
        raise ValueError(
            "WooCommerce order amount does not "
            "match the configured Pro price."
        )

    # --------------------------------
    # Check whether the WooCommerce order
    # already exists locally.
    # --------------------------------
    existing_order = find_order_by_external_id(
        int(external_order_id)
    )

    if existing_order is not None:

        # --------------------------------
        # Already paid
        # --------------------------------
        if existing_order.get(
            "status"
        ) == "paid":

            delivery_status = (
                existing_order.get(
                    "delivery_status"
                )
            )

            # --------------------------------
            # Everything already delivered.
            #
            # Do NOT issue a second license.
            # Do NOT create a second package.
            #
            # WooCommerce sync is handled by
            # the route layer.
            # --------------------------------
            if delivery_status == "completed":
                existing_license_path = (
                    get_existing_license_path(
                        existing_order
                    )
                )

                woo_sync_status = (
                    get_woo_sync_status(
                        existing_order
                    )
                )

                return {
                    "processed": False,
                    "already_paid": True,
                    "delivery_completed": True,
                    "woo_sync_required": (
                        woo_sync_status
                        != "completed"
                    ),
                    "retry_woo_sync": (
                        woo_sync_status
                        != "completed"
                    ),
                    "order_id": existing_order[
                        "order_id"
                    ],
                    "external_order_id": (
                        external_order_id
                    ),
                    "payment_id": existing_order.get(
                        "payment_id"
                    ),
                    "customer": existing_order[
                        "customer"
                    ],
                    "customer_email": existing_order[
                        "customer_email"
                    ],
                    "license_id": existing_order.get(
                        "license_id"
                    ),
                    "license_path": str(
                        existing_license_path
                    ),
                    "order_path": str(
                        order_manager.order_path(
                            existing_order[
                                "order_id"
                            ]
                        )
                    ),
                    "delivery_status": (
                        existing_order.get(
                            "delivery_status"
                        )
                    ),
                    "delivery_package": (
                        existing_order.get(
                            "delivery_package"
                        )
                    ),
                    "download_token": (
                        existing_order.get(
                            "download_token"
                        )
                    ),
                    "download_url": (
                        existing_order.get(
                            "download_url"
                        )
                    ),
                    "woo_sync_status": (
                        woo_sync_status
                    ),
                    "woo_sync_error": (
                        existing_order.get(
                            "woo_sync_error"
                        )
                    ),
                }

            # --------------------------------
            # Paid but delivery not completed.
            #
            # Reuse the same license.
            # Retry delivery only.
            # --------------------------------
            license_path = (
                get_existing_license_path(
                    existing_order
                )
            )

            existing_order[
                "delivery_status"
            ] = "pending"

            existing_order[
                "delivery_error"
            ] = None

            order_manager.save_order(
                existing_order
            )

            try:
                delivery = complete_delivery(
                    order=existing_order,
                    license_path=license_path,
                    settings=settings,
                )
            except (
                OSError,
                FileNotFoundError,
                RuntimeError,
            ) as exc:
                existing_order[
                    "delivery_status"
                ] = "failed"

                existing_order[
                    "delivery_error"
                ] = str(exc)

                order_manager.save_order(
                    existing_order
                )

                raise

            existing_order[
                "woo_sync_status"
            ] = "pending"

            existing_order[
                "woo_sync_error"
            ] = None

            persist_order(
                existing_order
            )

            return {
                "processed": True,
                "retry": True,
                "order_id": existing_order[
                    "order_id"
                ],
                "external_order_id": (
                    external_order_id
                ),
                "payment_id": payment_id,
                "customer": existing_order[
                    "customer"
                ],
                "customer_email": existing_order[
                    "customer_email"
                ],
                "license_id": existing_order.get(
                    "license_id"
                ),
                "license_path": str(
                    license_path
                ),
                "delivery_status": (
                    existing_order.get(
                        "delivery_status"
                    )
                ),
                "woo_sync_status": (
                    existing_order.get(
                        "woo_sync_status"
                    )
                ),
                **delivery,
            }

        # --------------------------------
        # Existing order in an unexpected
        # non-paid state.
        # --------------------------------
        raise ValueError(
            "WooCommerce order is already linked "
            "to a local order in an unexpected state."
        )

    # --------------------------------
    # Create local order
    # --------------------------------
    local_order_id = generate_order_id()

    order_path = order_manager.create_order(
        order_id=local_order_id,
        customer=customer,
        customer_email=customer_email,
        amount=amount,
        currency=currency,
    )

    local_order = order_manager.load_order(
        local_order_id
    )

    local_order["source"] = (
        "woocommerce"
    )

    local_order["external_order_id"] = (
        external_order_id
    )

    local_order["payment_method"] = (
        "parspal"
    )

    local_order["payment_id"] = (
        payment_id
    )

    local_order["delivery_status"] = (
        "pending"
    )

    local_order["delivery_package"] = None
    local_order["download_token"] = None
    local_order["download_url"] = None
    local_order["delivered_at"] = None
    local_order["delivery_error"] = None

    local_order["woo_sync_status"] = (
        "pending"
    )

    local_order["woo_sync_error"] = None

    order_manager.save_order(
        local_order
    )

    # --------------------------------
    # Issue exactly one license
    # --------------------------------
    try:
        license_path = order_manager.mark_paid(
            order_id=local_order_id,
            payment_id=payment_id,
        )
    except (
        OSError,
        FileNotFoundError,
        RuntimeError,
    ) as exc:
        local_order[
            "delivery_status"
        ] = "failed"

        local_order[
            "delivery_error"
        ] = (
            f"License issuance failed: {exc}"
        )

        order_manager.save_order(
            local_order
        )

        raise

    # --------------------------------
    # Reload after license issuance.
    # --------------------------------
    local_order = order_manager.load_order(
        local_order_id
    )

    # --------------------------------
    # Make sure Woo sync fields survived
    # the order manager persistence layer.
    # --------------------------------
    local_order[
        "woo_sync_status"
    ] = local_order.get(
        "woo_sync_status",
        "pending",
    )

    local_order[
        "woo_sync_error"
    ] = local_order.get(
        "woo_sync_error"
    )

    # --------------------------------
    # Create delivery package
    # --------------------------------
    try:
        delivery = complete_delivery(
            order=local_order,
            license_path=license_path,
            settings=settings,
        )
    except (
        OSError,
        FileNotFoundError,
        RuntimeError,
    ) as exc:
        local_order[
            "delivery_status"
        ] = "failed"

        local_order[
            "delivery_error"
        ] = str(exc)

        order_manager.save_order(
            local_order
        )

        raise

    # --------------------------------
    # Mark WooCommerce sync as pending.
    # --------------------------------
    local_order[
        "woo_sync_status"
    ] = "pending"

    local_order[
        "woo_sync_error"
    ] = None

    persist_order(
        local_order
    )

    # --------------------------------
    # Reload final order state.
    # --------------------------------
    local_order = order_manager.load_order(
        local_order_id
    )

    return {
        "processed": True,
        "retry": False,
        "order_id": local_order_id,
        "external_order_id": (
            external_order_id
        ),
        "payment_id": payment_id,
        "customer": customer,
        "customer_email": customer_email,
        "license_id": local_order.get(
            "license_id"
        ),
        "license_path": str(
            license_path
        ),
        "order_path": str(
            order_path
        ),
        "delivery_status": (
            local_order.get(
                "delivery_status"
            )
        ),
        "woo_sync_status": (
            local_order.get(
                "woo_sync_status",
                "pending",
            )
        ),
        "woo_sync_error": (
            local_order.get(
                "woo_sync_error"
            )
        ),
        **delivery,
    }