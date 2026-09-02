from __future__ import annotations

import base64
import hashlib
import hmac
import json
import zipfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from fastapi.testclient import TestClient

from file_organizer import license as license_module
from server.app import app


client = TestClient(app)


TEST_WEBHOOK_SECRET = "test-secret"
TEST_PRODUCT_ID = 1410
TEST_PRO_PRICE_IRR = 990000
TEST_DOWNLOAD_BASE_URL = (
    "http://testserver"
)


class FakeWooCommerceClient:
    """
    Fake WooCommerce REST API client.

    No real network requests are made during tests.
    """

    updated_orders: list[dict[str, Any]] = []
    created_notes: list[dict[str, Any]] = []

    def __init__(
        self,
        settings: Any,
    ) -> None:
        self.settings = settings

    async def update_order_metadata(
        self,
        order_id: int,
        metadata: dict[str, str],
    ) -> dict[str, Any]:
        self.updated_orders.append(
            {
                "order_id": order_id,
                "metadata": metadata,
            }
        )

        return {
            "id": order_id,
            "meta_data": metadata,
        }

    async def create_order_note(
        self,
        order_id: int,
        note: str,
        *,
        customer_note: bool = False,
    ) -> dict[str, Any]:
        self.created_notes.append(
            {
                "order_id": order_id,
                "note": note,
                "customer_note": customer_note,
            }
        )

        return {
            "id": 1,
            "order_id": order_id,
            "note": note,
            "customer_note": customer_note,
        }


def make_signature(
    body: bytes,
    secret: str,
) -> str:
    """
    Create a WooCommerce-compatible
    HMAC-SHA256 Base64 signature.
    """
    digest = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()

    return base64.b64encode(
        digest
    ).decode("ascii")


def create_test_pro_zip(
    tmp_path: Path,
) -> Path:
    """
    Create an isolated fake Pro release ZIP.
    """
    package_root = (
        tmp_path
        / "FileOrganizer-Pro-v0.4.0-Windows-x64"
    )

    package_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        package_root / "FileOrganizerPro.exe"
    ).write_bytes(
        b"test-executable"
    )

    (
        package_root / "config.json"
    ).write_text(
        "{}",
        encoding="utf-8",
    )

    (
        package_root / "README_USER.md"
    ).write_text(
        "Test package",
        encoding="utf-8",
    )

    (
        package_root / "LICENSE.txt"
    ).write_text(
        "Test license",
        encoding="utf-8",
    )

    zip_path = (
        tmp_path
        / "FileOrganizer-Pro-v0.4.0-Windows-x64.zip"
    )

    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for path in package_root.rglob("*"):
            if path.is_file():
                archive.write(
                    path,
                    path.relative_to(tmp_path),
                )

    return zip_path


def prepare_test_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Prepare a fully isolated webhook test environment.
    """

    # --------------------------------
    # WooCommerce webhook settings
    # --------------------------------
    monkeypatch.setenv(
        "WOOCOMMERCE_WEBHOOK_SECRET",
        TEST_WEBHOOK_SECRET,
    )

    monkeypatch.setenv(
        "WOOCOMMERCE_PRO_PRODUCT_ID",
        str(TEST_PRODUCT_ID),
    )

    monkeypatch.setenv(
        "WOOCOMMERCE_PRO_PRICE_IRR",
        str(TEST_PRO_PRICE_IRR),
    )

    # --------------------------------
    # Delivery settings
    # --------------------------------
    pro_zip_path = create_test_pro_zip(
        tmp_path
    )

    delivery_dir = (
        tmp_path / "deliveries"
    )

    monkeypatch.setenv(
        "DELIVERY_PRO_ZIP_PATH",
        str(pro_zip_path),
    )

    monkeypatch.setenv(
        "DELIVERY_DIR",
        str(delivery_dir),
    )

    monkeypatch.setenv(
        "DOWNLOAD_BASE_URL",
        TEST_DOWNLOAD_BASE_URL,
    )

    # --------------------------------
    # Local order storage
    # --------------------------------
    monkeypatch.setattr(
        "tools.order_manager.ORDERS_DIR",
        tmp_path / "orders",
    )

    # --------------------------------
    # License storage
    # --------------------------------
    monkeypatch.setattr(
        "tools.license_manager.ACTIVE_DIR",
        tmp_path
        / "licenses"
        / "active",
    )

    monkeypatch.setattr(
        "tools.license_manager.REVOKED_DIR",
        tmp_path
        / "licenses"
        / "revoked",
    )

    # --------------------------------
    # Isolated Ed25519 key pair
    # --------------------------------
    private_key = (
        Ed25519PrivateKey.generate()
    )

    public_key = (
        private_key.public_key()
    )

    private_key_path = (
        tmp_path / "license_private.key"
    )

    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    public_key_b64 = (
        base64.b64encode(
            public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        )
        .decode("ascii")
    )

    monkeypatch.setattr(
        "tools.license_manager.PRIVATE_KEY_PATH",
        private_key_path,
    )

    monkeypatch.setattr(
        license_module,
        "PUBLIC_KEY_B64",
        public_key_b64,
    )

    # --------------------------------
    # Reset fake WooCommerce calls.
    # --------------------------------
    FakeWooCommerceClient.updated_orders = []
    FakeWooCommerceClient.created_notes = []

    monkeypatch.setattr(
        "server.routes.woocommerce.WooCommerceClient",
        FakeWooCommerceClient,
    )


def valid_pro_payload(
    *,
    order_id: int = 12345,
    total: str = "990000",
    currency: str = "IRR",
    transaction_id: str = "PAY-WC-001",
) -> dict[str, Any]:
    """
    Return a valid WooCommerce Pro order payload.
    """
    return {
        "id": order_id,
        "status": "processing",
        "total": total,
        "currency": currency,
        "transaction_id": transaction_id,
        "billing": {
            "first_name": "Amir",
            "last_name": "Ahmadi",
            "email": "amir@example.com",
        },
        "line_items": [
            {
                "product_id": TEST_PRODUCT_ID,
            }
        ],
    }


def post_webhook(
    payload: dict[str, Any],
    secret: str = TEST_WEBHOOK_SECRET,
):
    """
    Send a signed WooCommerce webhook.
    """
    body = json.dumps(
        payload
    ).encode("utf-8")

    signature = make_signature(
        body,
        secret,
    )

    return client.post(
        "/api/webhooks/woocommerce",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-WC-Webhook-Signature": signature,
        },
    )


def load_single_order(
    tmp_path: Path,
) -> dict[str, Any]:
    """
    Load the only local order in the isolated test.
    """
    order_files = list(
        (
            tmp_path / "orders"
        ).glob("*.json")
    )

    assert len(order_files) == 1

    return json.loads(
        order_files[0].read_text(
            encoding="utf-8"
        )
    )


def count_license_files(
    tmp_path: Path,
) -> int:
    """
    Return the number of active license files.
    """
    return len(
        list(
            (
                tmp_path
                / "licenses"
                / "active"
            ).glob("*.json")
        )
    )


def count_delivery_files(
    tmp_path: Path,
) -> int:
    """
    Return the number of generated delivery ZIPs.
    """
    return len(
        list(
            (
                tmp_path
                / "deliveries"
            ).glob("*.zip")
        )
    )


def test_health():
    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok",
        "service": "TechYarman Payment API",
    }


def test_woocommerce_webhook_rejects_missing_signature():
    payload = valid_pro_payload()

    body = json.dumps(
        payload
    ).encode("utf-8")

    response = client.post(
        "/api/webhooks/woocommerce",
        content=body,
        headers={
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == "Invalid webhook signature."
    )


def test_woocommerce_webhook_rejects_invalid_signature():
    payload = valid_pro_payload()

    body = json.dumps(
        payload
    ).encode("utf-8")

    response = client.post(
        "/api/webhooks/woocommerce",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-WC-Webhook-Signature": "invalid",
        },
    )

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == "Invalid webhook signature."
    )


def test_woocommerce_webhook_accepts_valid_signature(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    payload = valid_pro_payload()

    response = post_webhook(
        payload
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ok"] is True
    assert data["processed"] is True
    assert data["retry"] is False

    assert (
        data["external_order_id"]
        == "12345"
    )

    assert (
        data["payment_id"]
        == "PAY-WC-001"
    )

    assert data["customer"] == (
        "Amir Ahmadi"
    )

    assert (
        data["customer_email"]
        == "amir@example.com"
    )

    assert data["license_id"].startswith(
        "FOP-"
    )

    assert data["license_path"]
    assert data["order_path"]

    assert data["delivery_package"]

    assert data["download_url"].startswith(
        f"{TEST_DOWNLOAD_BASE_URL}/api/download/"
    )

    assert count_license_files(
        tmp_path
    ) == 1

    assert count_delivery_files(
        tmp_path
    ) == 1

    order = load_single_order(
        tmp_path
    )

    assert order["status"] == "paid"
    assert order["license_id"] == (
        data["license_id"]
    )
    assert order["delivery_status"] == (
        "completed"
    )

    assert order["download_token"]
    assert order["download_url"]

    assert len(
        FakeWooCommerceClient.updated_orders
    ) == 1

    updated_order = (
        FakeWooCommerceClient.updated_orders[
            0
        ]
    )

    assert updated_order["order_id"] == (
        12345
    )

    metadata = updated_order[
        "metadata"
    ]

    assert (
        metadata["_techyarman_order_id"]
        == data["order_id"]
    )

    assert (
        metadata["_techyarman_license_id"]
        == data["license_id"]
    )

    assert (
        metadata["_techyarman_delivery_status"]
        == "completed"
    )

    assert (
        metadata["_techyarman_download_url"]
        == data["download_url"]
    )

    assert len(
        FakeWooCommerceClient.created_notes
    ) == 1

    note = (
        FakeWooCommerceClient.created_notes[
            0
        ]
    )

    assert note["order_id"] == 12345
    assert note["customer_note"] is True


def test_woocommerce_webhook_ignores_other_products(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    payload = valid_pro_payload(
        order_id=99999,
        transaction_id="PAY-WC-OTHER",
    )

    payload["line_items"] = [
        {
            "product_id": 9999,
        }
    ]

    response = post_webhook(
        payload
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ok"] is True
    assert data["processed"] is False

    assert (
        data["external_order_id"]
        == "99999"
    )

    assert (
        data["reason"]
        == "Order does not contain File Organizer Pro."
    )

    assert not (
        tmp_path / "orders"
    ).exists()

    assert not (
        tmp_path
        / "licenses"
        / "active"
    ).exists()

    assert not (
        tmp_path / "deliveries"
    ).exists()

    assert (
        FakeWooCommerceClient.updated_orders
        == []
    )

    assert (
        FakeWooCommerceClient.created_notes
        == []
    )


def test_woocommerce_webhook_rejects_wrong_amount(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    payload = valid_pro_payload(
        order_id=12346,
        total="1",
        transaction_id="PAY-WC-WRONG-AMOUNT",
    )

    response = post_webhook(
        payload
    )

    assert response.status_code == 400

    detail = response.json()["detail"]

    assert (
        "amount"
        in detail.lower()
    )

    assert not (
        tmp_path / "orders"
    ).exists()

    assert not (
        tmp_path
        / "licenses"
        / "active"
    ).exists()

    assert not (
        tmp_path / "deliveries"
    ).exists()

    assert (
        FakeWooCommerceClient.updated_orders
        == []
    )


def test_woocommerce_webhook_rejects_wrong_currency(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    payload = valid_pro_payload(
        order_id=12347,
        total="990000",
        currency="USD",
        transaction_id="PAY-WC-WRONG-CURRENCY",
    )

    response = post_webhook(
        payload
    )

    assert response.status_code == 400

    detail = response.json()["detail"]

    assert (
        "currency"
        in detail.lower()
    )

    assert not (
        tmp_path / "orders"
    ).exists()

    assert not (
        tmp_path
        / "licenses"
        / "active"
    ).exists()

    assert not (
        tmp_path / "deliveries"
    ).exists()

    assert (
        FakeWooCommerceClient.updated_orders
        == []
    )


def test_woocommerce_webhook_is_idempotent(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    payload = valid_pro_payload(
        order_id=12348,
        transaction_id="PAY-WC-IDEMPOTENT",
    )

    first_response = post_webhook(
        payload
    )

    assert first_response.status_code == 200

    first_data = (
        first_response.json()
    )

    assert first_data["processed"] is True
    assert first_data["retry"] is False

    first_license_id = (
        first_data["license_id"]
    )

    first_download_url = (
        first_data["download_url"]
    )

    first_updated_count = len(
        FakeWooCommerceClient.updated_orders
    )

    first_note_count = len(
        FakeWooCommerceClient.created_notes
    )

    second_response = post_webhook(
        payload
    )

    assert second_response.status_code == 200

    second_data = (
        second_response.json()
    )

    assert second_data["ok"] is True
    assert second_data["processed"] is False
    assert second_data["already_paid"] is True
    assert (
        second_data["delivery_completed"]
        is True
    )

    assert (
        second_data["license_id"]
        == first_license_id
    )

    assert (
        second_data["download_url"]
        == first_download_url
    )

    # A completed webhook retry must not
    # make another WooCommerce API update.
    assert len(
        FakeWooCommerceClient.updated_orders
    ) == first_updated_count

    assert len(
        FakeWooCommerceClient.created_notes
    ) == first_note_count

    assert count_license_files(
        tmp_path
    ) == 1

    assert count_delivery_files(
        tmp_path
    ) == 1

    assert load_single_order(
        tmp_path
    )["license_id"] == first_license_id


def test_woocommerce_webhook_retries_failed_delivery_without_new_license(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    payload = valid_pro_payload(
        order_id=12349,
        transaction_id="PAY-WC-RETRY",
    )

    delivery_calls: list[
        dict[str, Any]
    ] = []

    def fake_complete_delivery(
        order: dict[str, Any],
        license_path: Path,
        settings: Any,
    ):
        delivery_calls.append(
            {
                "order_id": order[
                    "order_id"
                ],
                "license_path": license_path,
            }
        )

        if len(delivery_calls) == 1:
            raise RuntimeError(
                "Simulated delivery failure"
            )

        order[
            "delivery_status"
        ] = "completed"

        order[
            "delivery_package"
        ] = str(
            tmp_path
            / "delivery"
            / "customer.zip"
        )

        order[
            "download_token"
        ] = "retry-download-token"

        order[
            "download_url"
        ] = (
            f"{TEST_DOWNLOAD_BASE_URL}"
            "/api/download/"
            "retry-download-token"
        )

        order[
            "delivered_at"
        ] = (
            "2026-08-30T00:00:00+00:00"
        )

        order[
            "delivery_error"
        ] = None

        return {
            "delivery_package": order[
                "delivery_package"
            ],
            "download_token": order[
                "download_token"
            ],
            "download_url": order[
                "download_url"
            ],
        }

    monkeypatch.setattr(
        "server.services.woocommerce.complete_delivery",
        fake_complete_delivery,
    )

    # --------------------------------
    # First webhook:
    # License succeeds.
    # Delivery fails.
    # --------------------------------
    first_response = post_webhook(
        payload
    )

    assert first_response.status_code == 500

    assert len(
        delivery_calls
    ) == 1

    order = load_single_order(
        tmp_path
    )

    assert order["status"] == "paid"

    assert order["license_id"].startswith(
        "FOP-"
    )

    assert order["delivery_status"] == (
        "failed"
    )

    assert (
        "Simulated delivery failure"
        in order["delivery_error"]
    )

    first_license_id = (
        order["license_id"]
    )

    assert count_license_files(
        tmp_path
    ) == 1

    # No successful WooCommerce sync should
    # occur because delivery did not finish.
    assert (
        FakeWooCommerceClient.updated_orders
        == []
    )

    assert (
        FakeWooCommerceClient.created_notes
        == []
    )

    # --------------------------------
    # Second webhook:
    # Reuse the existing License.
    # Retry Delivery only.
    # --------------------------------
    second_response = post_webhook(
        payload
    )

    assert second_response.status_code == 200

    second_data = (
        second_response.json()
    )

    assert second_data["ok"] is True
    assert second_data["processed"] is True
    assert second_data["retry"] is True

    assert (
        second_data["license_id"]
        == first_license_id
    )

    assert (
        second_data["download_token"]
        == "retry-download-token"
    )

    assert (
        second_data["download_url"]
        == (
            f"{TEST_DOWNLOAD_BASE_URL}"
            "/api/download/"
            "retry-download-token"
        )
    )

    assert len(
        delivery_calls
    ) == 2

    # Both Delivery attempts must use
    # exactly the same License.
    assert (
        delivery_calls[0]["license_path"]
        == delivery_calls[1]["license_path"]
    )

    final_order = load_single_order(
        tmp_path
    )

    assert final_order["status"] == (
        "paid"
    )

    assert final_order["license_id"] == (
        first_license_id
    )

    assert final_order["delivery_status"] == (
        "completed"
    )

    assert (
        final_order["delivery_error"]
        is None
    )

    assert (
        final_order["download_token"]
        == "retry-download-token"
    )

    assert (
        len(FakeWooCommerceClient.updated_orders)
        == 1
    )

    assert (
        len(FakeWooCommerceClient.created_notes)
        == 1
    )

    assert (
        FakeWooCommerceClient.created_notes[
            0
        ]["customer_note"]
        is True
    )

    # Exactly one License must exist.
    assert count_license_files(
        tmp_path
    ) == 1

def test_woocommerce_webhook_retries_only_woo_sync_after_api_failure(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    payload = valid_pro_payload(
        order_id=12350,
        transaction_id="PAY-WC-SYNC-RETRY",
    )

    sync_calls = []

    original_update = (
        FakeWooCommerceClient.update_order_metadata
    )

    async def failing_then_successful_update(
        self,
        order_id,
        metadata,
    ):
        sync_calls.append(
            {
                "order_id": order_id,
                "metadata": metadata,
            }
        )

        if len(sync_calls) == 1:
            raise RuntimeError(
                "Simulated WooCommerce sync failure"
            )

        return await original_update(
            self,
            order_id,
            metadata,
        )

    monkeypatch.setattr(
        FakeWooCommerceClient,
        "update_order_metadata",
        failing_then_successful_update,
    )

    # --------------------------------
    # First webhook:
    # License + Delivery succeed,
    # but WooCommerce sync fails.
    # --------------------------------
    first_response = post_webhook(
        payload
    )

    assert first_response.status_code == 500

    orders = list(
        (
            tmp_path / "orders"
        ).glob("*.json")
    )

    assert len(orders) == 1

    first_order = json.loads(
        orders[0].read_text(
            encoding="utf-8"
        )
    )

    assert first_order["status"] == "paid"
    assert first_order["delivery_status"] == "completed"

    first_license_id = (
        first_order["license_id"]
    )

    delivery_files = list(
        (
            tmp_path / "deliveries"
        ).glob("*.zip")
    )

    assert len(delivery_files) == 1

    license_files = list(
        (
            tmp_path
            / "licenses"
            / "active"
        ).glob("*.json")
    )

    assert len(license_files) == 1

    # --------------------------------
    # Second webhook:
    # Must retry WooCommerce sync only.
    # --------------------------------
    second_response = post_webhook(
        payload
    )

    assert second_response.status_code == 200

    second_data = (
        second_response.json()
    )

    assert second_data["ok"] is True

    assert (
        second_data["license_id"]
        == first_license_id
    )

    # Exactly two WooCommerce sync attempts.
    assert len(sync_calls) == 2

    # No second delivery package.
    delivery_files_after = list(
        (
            tmp_path / "deliveries"
        ).glob("*.zip")
    )

    assert len(delivery_files_after) == 1

    # No second license.
    license_files_after = list(
        (
            tmp_path
            / "licenses"
            / "active"
        ).glob("*.json")
    )

    assert len(license_files_after) == 1