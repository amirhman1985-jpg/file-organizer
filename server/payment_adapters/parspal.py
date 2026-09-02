from __future__ import annotations

from dataclasses import dataclass

import httpx

from server.config import Settings
from server.payment_adapters.base import (
    PaymentRequest,
    PaymentResponse,
    PaymentVerification,
)


class ParsPalError(RuntimeError):
    """Raised when ParsPal rejects or cannot process a request."""


class ParsPalAdapter:
    provider = "parspal"

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self.settings = settings

    def build_request_payload(
        self,
        request: PaymentRequest,
    ) -> dict:
        """
        Build ParsPal request payload.

        IMPORTANT:
        Verify these field names/types against your current
        ParsPal merchant API documentation before production.
        """
        return {
            "merchantId": self.settings.parspal_merchant_id,
            "amount": request.amount,
            "callbackUrl": request.callback_url,
            "orderId": request.order_id,
            "description": request.description,
        }

    def build_verify_payload(
        self,
        *,
        payment_id: str,
        amount: int,
    ) -> dict:
        """
        Build ParsPal verification payload.

        IMPORTANT:
        Verify these field names/types against your current
        ParsPal merchant API documentation before production.
        """
        return {
            "merchantId": self.settings.parspal_merchant_id,
            "paymentId": payment_id,
            "amount": amount,
        }

    async def create_payment(
        self,
        request: PaymentRequest,
    ) -> PaymentResponse:
        if not self.settings.parspal_merchant_id:
            raise ParsPalError(
                "PARSPAL_MERCHANT_ID is not configured."
            )

        payload = self.build_request_payload(
            request
        )

        try:
            async with httpx.AsyncClient(
                timeout=20.0
            ) as client:
                response = await client.post(
                    self.settings.parspal_request_url,
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise ParsPalError(
                f"ParsPal request failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise ParsPalError(
                "ParsPal request returned HTTP "
                f"{response.status_code}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ParsPalError(
                "ParsPal returned invalid JSON."
            ) from exc

        payment_id = (
            data.get("paymentId")
            or data.get("token")
            or data.get("transactionId")
        )

        if not payment_id:
            raise ParsPalError(
                "ParsPal response did not contain "
                "a payment identifier."
            )

        checkout_url = (
            data.get("paymentUrl")
            or data.get("url")
            or (
                f"{self.settings.parspal_payment_url}"
                f"{payment_id}"
                if self.settings.parspal_payment_url
                else ""
            )
        )

        if not checkout_url:
            raise ParsPalError(
                "ParsPal payment URL is missing."
            )

        return PaymentResponse(
            provider=self.provider,
            payment_id=str(payment_id),
            checkout_url=checkout_url,
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
        payload = self.build_verify_payload(
            payment_id=payment_id,
            amount=amount,
        )

        try:
            async with httpx.AsyncClient(
                timeout=20.0
            ) as client:
                response = await client.post(
                    self.settings.parspal_verify_url,
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise ParsPalError(
                f"ParsPal verification failed: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise ParsPalError(
                "ParsPal verification returned HTTP "
                f"{response.status_code}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ParsPalError(
                "ParsPal verification returned invalid JSON."
            ) from exc

        status = str(
            data.get("status", "")
        ).lower()

        success = status in {
            "success",
            "successful",
            "paid",
            "ok",
        }

        verified_amount = int(
            data.get(
                "amount",
                amount,
            )
        )

        if success and verified_amount != amount:
            raise ParsPalError(
                "Verified payment amount does not "
                "match the order amount."
            )

        return PaymentVerification(
            success=success,
            provider=self.provider,
            payment_id=payment_id,
            amount=verified_amount,
            currency=currency,
        )