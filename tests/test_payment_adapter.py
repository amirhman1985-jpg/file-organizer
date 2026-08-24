import json

from file_organizer import license as license_module
from tools import license_manager, order_manager
from tools.payment_adapter import (
    PaymentError,
    process_payment,
)


def prepare_test_environment(
    tmp_path,
    monkeypatch,
):
    import base64

    from cryptography.hazmat.primitives import (
        serialization,
    )
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

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

    public_key_b64 = base64.b64encode(
        public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode("ascii")

    active_dir = (
        tmp_path / "licenses" / "active"
    )

    revoked_dir = (
        tmp_path / "licenses" / "revoked"
    )

    orders_dir = (
        tmp_path / "orders"
    )

    monkeypatch.setattr(
        license_manager,
        "PRIVATE_KEY_PATH",
        private_key_path,
    )

    monkeypatch.setattr(
        license_manager,
        "ACTIVE_DIR",
        active_dir,
    )

    monkeypatch.setattr(
        license_manager,
        "REVOKED_DIR",
        revoked_dir,
    )

    monkeypatch.setattr(
        order_manager,
        "ORDERS_DIR",
        orders_dir,
    )

    monkeypatch.setattr(
        license_module,
        "PUBLIC_KEY_B64",
        public_key_b64,
    )


def create_test_order(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    return order_manager.create_order(
        order_id="ORD-PAY-001",
        customer="Test User",
        customer_email="test@example.com",
        amount=99000,
        currency="IRR",
    )


def test_payment_success(
    tmp_path,
    monkeypatch,
):
    create_test_order(
        tmp_path,
        monkeypatch,
    )

    license_path = process_payment(
        order_id="ORD-PAY-001",
        payment_id="PAY-001",
        status="paid",
        amount=99000,
        currency="IRR",
    )

    assert license_path.exists()

    order = order_manager.load_order(
        "ORD-PAY-001"
    )

    assert order["status"] == "paid"
    assert order["payment_id"] == "PAY-001"
    assert order["license_id"] == (
        "FOP-PAY-001"
    )


def test_payment_amount_mismatch(
    tmp_path,
    monkeypatch,
):
    create_test_order(
        tmp_path,
        monkeypatch,
    )

    try:
        process_payment(
            order_id="ORD-PAY-001",
            payment_id="PAY-002",
            status="paid",
            amount=50000,
            currency="IRR",
        )
    except PaymentError as exc:
        assert (
            "amount does not match"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected PaymentError"
        )


def test_payment_currency_mismatch(
    tmp_path,
    monkeypatch,
):
    create_test_order(
        tmp_path,
        monkeypatch,
    )

    try:
        process_payment(
            order_id="ORD-PAY-001",
            payment_id="PAY-003",
            status="paid",
            amount=99000,
            currency="USD",
        )
    except PaymentError as exc:
        assert (
            "currency does not match"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected PaymentError"
        )


def test_failed_payment_is_rejected(
    tmp_path,
    monkeypatch,
):
    create_test_order(
        tmp_path,
        monkeypatch,
    )

    try:
        process_payment(
            order_id="ORD-PAY-001",
            payment_id="PAY-004",
            status="failed",
            amount=99000,
            currency="IRR",
        )
    except PaymentError as exc:
        assert (
            "not successful"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected PaymentError"
        )


def test_duplicate_payment_is_rejected(
    tmp_path,
    monkeypatch,
):
    create_test_order(
        tmp_path,
        monkeypatch,
    )

    process_payment(
        order_id="ORD-PAY-001",
        payment_id="PAY-005",
        status="paid",
        amount=99000,
        currency="IRR",
    )

    try:
        process_payment(
            order_id="ORD-PAY-001",
            payment_id="PAY-006",
            status="paid",
            amount=99000,
            currency="IRR",
        )
    except PaymentError as exc:
        assert (
            "already paid"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected PaymentError"
        )


def test_generated_license_is_valid(
    tmp_path,
    monkeypatch,
):
    create_test_order(
        tmp_path,
        monkeypatch,
    )

    license_path = process_payment(
        order_id="ORD-PAY-001",
        payment_id="PAY-007",
        status="paid",
        amount=99000,
        currency="IRR",
    )

    license_data = (
        license_module.load_license(
            license_path
        )
    )

    assert license_data.license_id == (
        "FOP-PAY-001"
    )
    assert license_data.order_id == (
        "ORD-PAY-001"
    )
    assert license_data.customer == (
        "Test User"
    )

    def test_duplicate_successful_payment_is_idempotent(
        tmp_path,
        monkeypatch,
    ):
        create_test_order(
            tmp_path,
            monkeypatch,
        )

        first_license = process_payment(
            order_id="ORD-PAY-001",
            payment_id="PAY-IDEMPOTENT-001",
            status="paid",
            amount=99000,
            currency="IRR",
        )

        second_license = process_payment(
            order_id="ORD-PAY-001",
            payment_id="PAY-IDEMPOTENT-001",
            status="paid",
            amount=99000,
            currency="IRR",
        )

        assert first_license == second_license
        assert first_license.exists()

        order = order_manager.load_order(
            "ORD-PAY-001"
        )

        assert order["status"] == "paid"
        assert order["payment_id"] == (
            "PAY-IDEMPOTENT-001"
        )

        active_licenses = list(
            license_manager.ACTIVE_DIR.glob(
                "*.json"
         )
        )

        assert len(active_licenses) == 1

def test_payment_id_cannot_be_reused_for_another_order(
    tmp_path,
    monkeypatch,
):
    create_test_order(
        tmp_path,
        monkeypatch,
    )

    order_manager.create_order(
        order_id="ORD-PAY-002",
        customer="Another User",
        customer_email="another@example.com",
        amount=99000,
        currency="IRR",
    )

    process_payment(
        order_id="ORD-PAY-001",
        payment_id="PAY-REUSED-001",
        status="paid",
        amount=99000,
        currency="IRR",
    )

    try:
        process_payment(
            order_id="ORD-PAY-002",
            payment_id="PAY-REUSED-001",
            status="paid",
            amount=99000,
            currency="IRR",
        )
    except PaymentError as exc:
        assert (
            "already associated"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected PaymentError"
        )