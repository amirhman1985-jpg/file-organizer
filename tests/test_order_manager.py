import json

from file_organizer import license as license_module
from tools import license_manager, order_manager


def prepare_test_environment(
    tmp_path,
    monkeypatch,
):
    """
    Isolate orders and licenses inside pytest's tmp_path.
    """

    private_key_path = (
        tmp_path / "license_private.key"
    )

    active_dir = (
        tmp_path / "licenses" / "active"
    )

    revoked_dir = (
        tmp_path / "licenses" / "revoked"
    )

    orders_dir = (
        tmp_path / "orders"
    )

    # Reuse the existing License Manager test helper
    # by generating an isolated key pair here.
    from base64 import b64encode
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    public_key_b64 = b64encode(
        public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode("ascii")

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

    return (
        orders_dir,
        active_dir,
        revoked_dir,
    )


def test_create_order(
    tmp_path,
    monkeypatch,
):
    orders_dir, _, _ = (
        prepare_test_environment(
            tmp_path,
            monkeypatch,
        )
    )

    output = order_manager.create_order(
        order_id="ORD-TEST-001",
        customer="Test User",
        customer_email="test@example.com",
        amount=99000,
        currency="IRR",
    )

    assert output.exists()
    assert output.parent == orders_dir

    data = json.loads(
        output.read_text(
            encoding="utf-8"
        )
    )

    assert data["order_id"] == (
        "ORD-TEST-001"
    )
    assert data["product"] == (
        "File Organizer"
    )
    assert data["publisher"] == (
        "TechYarman"
    )
    assert data["customer"] == (
        "Test User"
    )
    assert data["customer_email"] == (
        "test@example.com"
    )
    assert data["amount"] == 99000
    assert data["currency"] == "IRR"
    assert data["status"] == "pending"
    assert data["license_id"] is None
    assert data["paid_at"] is None


def test_create_duplicate_order_fails(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    order_manager.create_order(
        order_id="ORD-TEST-002",
        customer="Test User",
        customer_email="test@example.com",
        amount=99000,
    )

    try:
        order_manager.create_order(
            order_id="ORD-TEST-002",
            customer="Another User",
            customer_email="another@example.com",
            amount=100000,
        )
    except FileExistsError as exc:
        assert (
            "Order already exists"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected FileExistsError"
        )


def test_load_missing_order_fails(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    try:
        order_manager.load_order(
            "ORD-TEST-999"
        )
    except FileNotFoundError as exc:
        assert (
            "Order not found"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected FileNotFoundError"
        )


def test_mark_paid_creates_license(
    tmp_path,
    monkeypatch,
    capsys,
):
    orders_dir, active_dir, _ = (
        prepare_test_environment(
            tmp_path,
            monkeypatch,
        )
    )

    order_manager.create_order(
        order_id="ORD-TEST-003",
        customer="Test User",
        customer_email="test@example.com",
        amount=99000,
        currency="IRR",
    )

    license_path = order_manager.mark_paid(
        "ORD-TEST-003"
    )

    captured = capsys.readouterr()

    assert license_path.exists()
    assert license_path.parent == active_dir

    order = order_manager.load_order(
        "ORD-TEST-003"
    )

    assert order["status"] == "paid"
    assert order["license_id"] == (
        "FOP-TEST-003"
    )
    assert order["paid_at"] is not None

    assert (
        "Order marked as paid"
        in captured.out
    )

    license_data = (
        license_module.load_license(
            license_path
        )
    )

    assert license_data.license_id == (
        "FOP-TEST-003"
    )
    assert license_data.order_id == (
        "ORD-TEST-003"
    )
    assert license_data.customer == (
        "Test User"
    )


def test_mark_paid_missing_order_fails(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    try:
        order_manager.mark_paid(
            "ORD-TEST-999"
        )
    except FileNotFoundError as exc:
        assert (
            "Order not found"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected FileNotFoundError"
        )


def test_mark_paid_twice_fails(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    order_manager.create_order(
        order_id="ORD-TEST-004",
        customer="Test User",
        customer_email="test@example.com",
        amount=99000,
    )

    order_manager.mark_paid(
        "ORD-TEST-004"
    )

    try:
        order_manager.mark_paid(
            "ORD-TEST-004"
        )
    except ValueError as exc:
        assert (
            "already paid"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_inspect_order(
    tmp_path,
    monkeypatch,
    capsys,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    order_manager.create_order(
        order_id="ORD-TEST-005",
        customer="Test User",
        customer_email="test@example.com",
        amount=99000,
    )

    order = order_manager.load_order(
        "ORD-TEST-005"
    )

    assert order["order_id"] == (
        "ORD-TEST-005"
    )
    assert order["status"] == "pending"

    # Keep this test focused on returned data;
    # CLI formatting is covered separately.
    assert order["customer"] == (
        "Test User"
    )
    assert order["customer_email"] == (
        "test@example.com"
    )


def test_list_orders(
    tmp_path,
    monkeypatch,
    capsys,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    order_manager.create_order(
        order_id="ORD-TEST-006",
        customer="User One",
        customer_email="one@example.com",
        amount=99000,
    )

    order_manager.create_order(
        order_id="ORD-TEST-007",
        customer="User Two",
        customer_email="two@example.com",
        amount=120000,
    )

    order_manager.list_orders()

    captured = capsys.readouterr()

    assert "Orders: 2" in captured.out
    assert (
        "ORD-TEST-006 | pending | User One"
        in captured.out
    )
    assert (
        "ORD-TEST-007 | pending | User Two"
        in captured.out
    )