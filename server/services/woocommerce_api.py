from __future__ import annotations

from typing import Any

import httpx

from server.config import Settings


class WooCommerceAPIError(RuntimeError):
    """Raised when WooCommerce REST API fails."""


class WooCommerceClient:
    """
    Minimal WooCommerce REST API v3 client.

    Used to update an existing WooCommerce order with
    TechYarman license and delivery information.
    """

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self.settings = settings

        if not self.settings.woocommerce_url:
            raise WooCommerceAPIError(
                "WOOCOMMERCE_URL is not configured."
            )

        if not self.settings.woocommerce_consumer_key:
            raise WooCommerceAPIError(
                "WOOCOMMERCE_CONSUMER_KEY is not configured."
            )

        if not self.settings.woocommerce_consumer_secret:
            raise WooCommerceAPIError(
                "WOOCOMMERCE_CONSUMER_SECRET is not configured."
            )

    @property
    def orders_url(self) -> str:
        return (
            f"{self.settings.woocommerce_url}"
            "/wp-json/wc/v3/orders"
        )

    async def update_order_metadata(
        self,
        order_id: int,
        metadata: dict[str, str],
    ) -> dict[str, Any]:
        """
        Update WooCommerce order metadata.
        """
        meta_data = [
            {
                "key": key,
                "value": value,
            }
            for key, value in metadata.items()
        ]

        url = (
            f"{self.orders_url}/{order_id}"
        )

        try:
            async with httpx.AsyncClient(
                timeout=20.0
            ) as client:
                response = await client.put(
                    url,
                    auth=(
                        self.settings.woocommerce_consumer_key,
                        self.settings.woocommerce_consumer_secret,
                    ),
                    json={
                        "meta_data": meta_data,
                    },
                )
        except httpx.HTTPError as exc:
            raise WooCommerceAPIError(
                f"WooCommerce API request failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise WooCommerceAPIError(
                "WooCommerce API returned HTTP "
                f"{response.status_code}: "
                f"{response.text}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise WooCommerceAPIError(
                "WooCommerce API returned invalid JSON."
            ) from exc

    async def create_order_note(
        self,
        order_id: int,
        note: str,
        *,
        customer_note: bool = False,
    ) -> dict[str, Any]:
        """
        Create an order note.

        customer_note=False:
            Admin-only note.

        customer_note=True:
            Visible to the customer.
        """
        url = (
            f"{self.orders_url}"
            f"/{order_id}/notes"
        )

        try:
            async with httpx.AsyncClient(
                timeout=20.0
            ) as client:
                response = await client.post(
                    url,
                    auth=(
                        self.settings.woocommerce_consumer_key,
                        self.settings.woocommerce_consumer_secret,
                    ),
                    json={
                        "note": note,
                        "customer_note": customer_note,
                    },
                )
        except httpx.HTTPError as exc:
            raise WooCommerceAPIError(
                f"WooCommerce order-note request failed: "
                f"{exc}"
            ) from exc

        if response.status_code >= 400:
            raise WooCommerceAPIError(
                "WooCommerce order-note API returned "
                f"HTTP {response.status_code}: "
                f"{response.text}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise WooCommerceAPIError(
                "WooCommerce order-note API returned "
                "invalid JSON."
            ) from exc