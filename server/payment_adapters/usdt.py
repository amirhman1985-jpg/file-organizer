from __future__ import annotations

from server.config import Settings
from server.payment_adapters.base import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
)


class USDTAdapter:
    provider = "usdt"

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self.settings = settings

    async def create_payment(
        self,
        request: PaymentRequest,
    ) -> PaymentResponse:
        raise NotImplementedError(
            "USDT provider is not configured yet."
        )

    async def verify_payment(
        self,
        *,
        order_id: str,
        payment_id: str,
        amount: int,
        currency: str,
        callback_data: dict,
    ) -> PaymentVerification:
        raise NotImplementedError(
            "USDT provider is not configured yet."
        )