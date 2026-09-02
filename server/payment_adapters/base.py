from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PaymentRequest:
    order_id: str
    amount: int
    currency: str
    callback_url: str
    description: str


@dataclass(frozen=True)
class PaymentResponse:
    provider: str
    payment_id: str
    checkout_url: str


@dataclass(frozen=True)
class PaymentVerification:
    success: bool
    provider: str
    payment_id: str
    amount: int
    currency: str


class PaymentAdapter(Protocol):
    def create_payment(
        self,
        request: PaymentRequest,
    ) -> PaymentResponse:
        ...

    def verify_payment(
        self,
        *,
        order_id: str,
        payment_id: str,
        amount: int,
        currency: str,
        callback_data: dict,
    ) -> PaymentVerification:
        ...