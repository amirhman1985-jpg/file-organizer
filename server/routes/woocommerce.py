from __future__ import annotations

import json

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


@router.post("/woocommerce")
async def woocommerce_webhook(
    request: Request,
):
    """
    Receive and process WooCommerce order webhooks.

    Flow:
        1. Verify WooCommerce HMAC signature.
        2. Parse JSON payload.
        3. Process local order/license/delivery.
        4. Sync successful delivery metadata to WooCommerce.
    """

    settings = load_settings()

    # ---------------------------------------------------------
    # Read raw request body
    # ---------------------------------------------------------
    body = await request.body()

    signature = request.headers.get(
        "X-WC-Webhook-Signature",
        "",
    )

    # ---------------------------------------------------------
    # Verify WooCommerce signature
    # ---------------------------------------------------------
    if not verify_woocommerce_signature(
        body=body,
        signature=signature,
        secret=settings.woocommerce_webhook_secret,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature.",
        )

    # ---------------------------------------------------------
    # Parse JSON
    # ---------------------------------------------------------
    try:
        payload = json.loads(
            body.decode("utf-8")
        )
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Webhook body must be valid UTF-8.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="Webhook body must contain valid JSON.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="Webhook payload must be a JSON object.",
        )

    # ---------------------------------------------------------
    # Process local order
    # ---------------------------------------------------------
    try:
        result = process_woocommerce_order(
            payload
        )

        # -----------------------------------------------------
        # Nothing to process
        #
        # Examples:
        # - unpaid order
        # - unrelated product
        # - already completed duplicate webhook
        # -----------------------------------------------------
        if not result.get("processed"):
            return {
                "ok": True,
                **result,
            }

        # -----------------------------------------------------
        # Get external WooCommerce order ID
        # -----------------------------------------------------
        external_order_id = result.get(
            "external_order_id"
        )

        if external_order_id is None:
            raise ValueError(
                "Processed order is missing external_order_id."
            )

        try:
            woo_order_id = int(
                external_order_id
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "WooCommerce order ID must be numeric."
            ) from exc

        # -----------------------------------------------------
        # Sync local result back to WooCommerce
        # -----------------------------------------------------
        woo_client = WooCommerceClient(
            settings
        )

        metadata = {
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

        await woo_client.update_order_metadata(
            order_id=woo_order_id,
            metadata=metadata,
        )

        await woo_client.create_order_note(
            order_id=woo_order_id,
            note=(
                "File Organizer Pro delivery is ready. "
                "The secure download link has been added "
                "to the order metadata."
            ),
            customer_note=True,
        )

    except WooCommerceAPIError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"WooCommerce API error: {exc}",
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
        raise HTTPException(
            status_code=500,
            detail=f"Internal webhook processing error: {exc}",
        ) from exc

    return {
        "ok": True,
        **result,
    }