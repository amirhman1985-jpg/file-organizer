from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from server.config import load_settings
from server.security import verify_woocommerce_signature
from server.services.woocommerce import (
    persist_woo_sync_state,
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


def build_woocommerce_metadata(
    result: dict[str, Any],
) -> dict[str, str]:
    """
    Build the metadata that is written to the
    WooCommerce order.
    """
    return {
        "_techyarman_order_id": str(
            result["order_id"]
        ),
        "_techyarman_license_id": str(
            result["license_id"]
        ),
        "_techyarman_delivery_status": str(
            result.get(
                "delivery_status",
                "completed",
            )
        ),
        "_techyarman_download_url": str(
            result["download_url"]
        ),
    }


def build_customer_note(
    result: dict[str, Any],
) -> str:
    """
    Build the customer-visible WooCommerce order note.
    """
    return (
        "File Organizer Pro license and delivery "
        "completed. "
        f"Download: {result['download_url']}"
    )


async def sync_order_to_woocommerce(
    result: dict[str, Any],
    settings: Any,
) -> None:
    """
    Synchronize the locally processed order with WooCommerce.

    Both operations must succeed before the local WooCommerce
    sync state is considered completed.
    """
    external_order_id = int(
        result["external_order_id"]
    )

    woo_client = WooCommerceClient(
        settings
    )

    metadata = build_woocommerce_metadata(
        result
    )

    await woo_client.update_order_metadata(
        external_order_id,
        metadata,
    )

    await woo_client.create_order_note(
        external_order_id,
        build_customer_note(
            result
        ),
        customer_note=True,
    )


async def handle_woocommerce_sync(
    result: dict[str, Any],
    settings: Any,
) -> dict[str, Any]:
    """
    Perform WooCommerce synchronization and persist its result.

    Returns the original result enriched with sync information.
    """
    order_id = str(
        result["order_id"]
    )

    try:
        await sync_order_to_woocommerce(
            result,
            settings,
        )

    except Exception as exc:
        try:
            persist_woo_sync_state(
                order_id,
                status="failed",
                error=str(exc),
            )
        except Exception:
            # The original WooCommerce synchronization failure
            # is more relevant than a secondary persistence error.
            pass

        raise

    persist_woo_sync_state(
        order_id,
        status="completed",
        error=None,
    )

    result["woo_sync_status"] = (
        "completed"
    )

    result["woo_sync_error"] = None

    return result


@router.post(
    "/woocommerce",
)
async def woocommerce_webhook(
    request: Request,
) -> dict[str, Any]:
    """
    Receive and process a WooCommerce webhook.

    The endpoint is idempotent:

    - New paid order:
        License → Delivery → Woo Sync

    - Paid order with failed Delivery:
        Delivery retry → Woo Sync

    - Paid order with completed Delivery
      and failed Woo Sync:
        Woo Sync retry only

    - Fully completed order:
        no duplicate License / Delivery / Sync work
    """
    settings = load_settings()

    # --------------------------------
    # Read raw request body.
    # --------------------------------
    body = await request.body()

    signature = request.headers.get(
        "X-WC-Webhook-Signature",
        "",
    )

    # --------------------------------
    # Verify WooCommerce HMAC signature.
    # --------------------------------
    if not verify_woocommerce_signature(
        body,
        signature,
        settings.woocommerce_webhook_secret,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature.",
        )

    # --------------------------------
    # Decode JSON payload.
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
            detail="WooCommerce payload must be a JSON object.",
        )

    # --------------------------------
    # Process local business logic.
    # --------------------------------
    try:
        result = process_woocommerce_order(
            payload
        )

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

    # --------------------------------
    # Case 1:
    # Existing order needs only Woo Sync.
    # --------------------------------
    if (
        not result.get("processed")
        and result.get("woo_sync_required")
    ):
        try:
            result = await handle_woocommerce_sync(
                result,
                settings,
            )

        except WooCommerceAPIError as exc:
            raise HTTPException(
                status_code=500,
                detail=str(exc),
            ) from exc

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=str(exc),
            ) from exc

        return {
            "ok": True,
            **result,
            "processed": True,
            "retry_woo_sync": True,
        }

    # --------------------------------
    # Case 2:
    # Order was not processed and does
    # not require any further action.
    # --------------------------------
    if not result.get("processed"):
        return {
            "ok": True,
            **result,
        }

    # --------------------------------
    # Case 3:
    # New order or Delivery retry succeeded.
    #
    # Now synchronize with WooCommerce.
    # --------------------------------
    try:
        result = await handle_woocommerce_sync(
            result,
            settings,
        )

    except WooCommerceAPIError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    return {
        "ok": True,
        **result,
    }