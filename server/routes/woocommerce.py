from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from server.config import load_settings
from server.security import verify_woocommerce_signature
from server.services.woocommerce import (
    process_woocommerce_order,
)
from server.services.woocommerce_api import (
    WooCommerceAPIError,
    WooCommerceClient,
)


router = APIRouter(
    prefix="/api/webhooks",
    tags=["WooCommerce"],
)


def load_order_from_path(
    order_path: str,
) -> dict[str, Any]:
    """
    Load a local order JSON file.
    """
    path = Path(
        order_path
    )

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(
            f"Could not read local order file: {path}"
        ) from exc

    if not isinstance(
        data,
        dict,
    ):
        raise RuntimeError(
            f"Local order file does not contain an object: {path}"
        )

    return data


def persist_woo_sync_state(
    order_path: str,
    *,
    status: str,
    error: str | None = None,
) -> None:
    """
    Persist WooCommerce synchronization state without
    modifying the rest of the local order.
    """
    path = Path(
        order_path
    )

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(
            f"Could not read local order for WooCommerce sync: {path}"
        ) from exc

    if not isinstance(
        data,
        dict,
    ):
        raise RuntimeError(
            f"Local order file does not contain an object: {path}"
        )

    data["woo_sync_status"] = status
    data["woo_sync_error"] = error

    try:
        path.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        raise RuntimeError(
            f"Could not persist WooCommerce sync state: {path}"
        ) from exc


def build_woocommerce_metadata(
    order: dict[str, Any],
) -> dict[str, str]:
    """
    Build the custom metadata written to WooCommerce.
    """
    return {
        "_techyarman_order_id": str(
            order.get(
                "order_id",
                "",
            )
        ),
        "_techyarman_license_id": str(
            order.get(
                "license_id",
                "",
            )
        ),
        "_techyarman_delivery_status": str(
            order.get(
                "delivery_status",
                "",
            )
        ),
        "_techyarman_download_url": str(
            order.get(
                "download_url",
                "",
            )
        ),
    }


def build_customer_note(
    order: dict[str, Any],
) -> str:
    """
    Build the customer-facing WooCommerce order note.
    """
    note = (
        "پرداخت سفارش با موفقیت تایید شد و "
        "فایل File Organizer Pro آماده دانلود است."
    )

    download_url = order.get(
        "download_url"
    )

    if download_url:
        note += (
            f"\n\nلینک دانلود:\n{download_url}"
        )

    return note


async def sync_order_to_woocommerce(
    *,
    settings: Any,
    order: dict[str, Any],
) -> None:
    """
    Synchronize the local paid order with WooCommerce.

    This function performs ONLY WooCommerce API work.
    License issuance and file delivery never happen here.
    """
    external_order_id_raw = order.get(
        "external_order_id"
    )

    if external_order_id_raw is None:
        raise ValueError(
            "Local order is missing external WooCommerce order ID."
        )

    try:
        external_order_id = int(
            external_order_id_raw
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "Local order has an invalid WooCommerce order ID."
        ) from exc

    woo_client = WooCommerceClient(
        settings
    )

    metadata = build_woocommerce_metadata(
        order
    )

    await woo_client.update_order_metadata(
        order_id=external_order_id,
        metadata=metadata,
    )

    note = build_customer_note(
        order
    )

    await woo_client.create_order_note(
        order_id=external_order_id,
        note=note,
        customer_note=True,
    )


@router.post("/woocommerce")
async def woocommerce_webhook(
    request: Request,
):
    """
    Receive and process a WooCommerce webhook.

    Responsibilities:

    1. Verify webhook signature.
    2. Parse the payload.
    3. Process local payment/license/delivery.
    4. Synchronize the local order to WooCommerce.
    5. Retry ONLY WooCommerce synchronization when
       payment and delivery are already complete but
       a previous API synchronization failed.
    """
    settings = load_settings()

    # --------------------------------
    # Read raw request body
    # --------------------------------
    body = await request.body()

    # --------------------------------
    # Verify WooCommerce signature
    # --------------------------------
    signature = request.headers.get(
        "X-WC-Webhook-Signature",
        "",
    )

    if not verify_woocommerce_signature(
        body=body,
        signature=signature,
        secret=settings.woocommerce_webhook_secret,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature.",
        )

    # --------------------------------
    # Decode JSON
    # --------------------------------
    try:
        payload = json.loads(
            body.decode("utf-8")
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload.",
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise HTTPException(
            status_code=400,
            detail="WooCommerce payload must be an object.",
        )

    order_path: str | None = None

    try:
        # --------------------------------
        # Local payment/license/delivery
        # --------------------------------
        result = process_woocommerce_order(
            payload
        )

        order_path = result.get(
            "order_path"
        )

        # --------------------------------
        # Not a File Organizer Pro order
        # or unpaid order.
        # --------------------------------
        if not order_path:
            return {
                "ok": True,
                **result,
            }

        # --------------------------------
        # Read the current persisted order.
        #
        # process_woocommerce_order() may have
        # returned an existing paid order.
        # --------------------------------
        local_order = load_order_from_path(
            order_path
        )

        woo_sync_status = local_order.get(
            "woo_sync_status",
            "pending",
        )

        # --------------------------------
        # Already synchronized successfully.
        #
        # This is the true idempotent path.
        # Do not call WooCommerce again.
        # --------------------------------
        if woo_sync_status == "completed":
            return {
                "ok": True,
                **result,
                "woo_sync_status": "completed",
                "woo_sync_error": None,
            }

        # --------------------------------
        # Sync pending or previously failed.
        #
        # Important:
        #
        # At this point License and Delivery
        # have already succeeded.
        #
        # Therefore this block performs ONLY
        # WooCommerce synchronization.
        # --------------------------------
        local_order[
            "woo_sync_status"
        ] = "pending"

        local_order[
            "woo_sync_error"
        ] = None

        # Persist the pending state before calling
        # the external API.
        Path(
            order_path
        ).write_text(
            json.dumps(
                local_order,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        try:
            await sync_order_to_woocommerce(
                settings=settings,
                order=local_order,
            )
        except (
            WooCommerceAPIError,
            RuntimeError,
            OSError,
        ) as exc:
            persist_woo_sync_state(
                order_path,
                status="failed",
                error=str(exc),
            )
            raise

        # --------------------------------
        # WooCommerce synchronization succeeded.
        # --------------------------------
        persist_woo_sync_state(
            order_path,
            status="completed",
            error=None,
        )

        return {
            "ok": True,
            **result,
            "woo_sync_status": "completed",
            "woo_sync_error": None,
        }

    except WooCommerceAPIError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    except (
        KeyError,
        ValueError,
        FileNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # If we have a known local order and an unexpected
        # exception occurs during WooCommerce synchronization,
        # preserve the failed state whenever possible.
        if order_path:
            try:
                persist_woo_sync_state(
                    order_path,
                    status="failed",
                    error=str(exc),
                )
            except Exception:
                pass

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc