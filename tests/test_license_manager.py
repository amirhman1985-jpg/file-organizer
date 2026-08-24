import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from file_organizer import license as license_module
from tools import license_manager


def prepare_test_environment(
    tmp_path,
    monkeypatch,
):
    """
    Create an isolated license-management environment
    for the current test.
    """

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_key_path = (
        tmp_path / "license_private.key"
    )

    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    private_key_path.write_bytes(
        private_key_bytes
    )

    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    public_key_b64 = base64.b64encode(
        public_key_bytes
    ).decode("ascii")

    active_dir = (
        tmp_path / "licenses" / "active"
    )

    revoked_dir = (
        tmp_path / "licenses" / "revoked"
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
        license_module,
        "PUBLIC_KEY_B64",
        public_key_b64,
    )

    return active_dir, revoked_dir


def test_issue_license(
    tmp_path,
    monkeypatch,
):
    active_dir, _ = prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    output = license_manager.issue_license(
        license_id="FOP-TEST-001",
        order_id="ORDER-TEST-001",
        customer="Test User",
        customer_email="test@example.com",
    )

    assert output.exists()
    assert output.parent == active_dir

    data = json.loads(
        output.read_text(
            encoding="utf-8"
        )
    )

    assert data["license_id"] == "FOP-TEST-001"
    assert data["order_id"] == "ORDER-TEST-001"
    assert data["product"] == "File Organizer"
    assert data["publisher"] == "TechYarman"
    assert data["customer"] == "Test User"
    assert data["customer_email"] == "test@example.com"
    assert data["edition"] == "pro"
    assert data["expires_at"] is None
    assert data["signature"]


def test_issued_license_is_valid(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    output = license_manager.issue_license(
        license_id="FOP-TEST-002",
        order_id="ORDER-TEST-002",
        customer="Test User",
        customer_email="test@example.com",
    )

    license_data = license_module.load_license(
        output
    )

    assert license_data.license_id == (
        "FOP-TEST-002"
    )
    assert license_data.order_id == (
        "ORDER-TEST-002"
    )
    assert license_data.product == (
        "File Organizer"
    )
    assert license_data.publisher == (
        "TechYarman"
    )
    assert license_data.customer == (
        "Test User"
    )
    assert license_data.customer_email == (
        "test@example.com"
    )
    assert license_data.edition == "pro"


def test_issue_license_with_expiration(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    output = license_manager.issue_license(
        license_id="FOP-TEST-003",
        order_id="ORDER-TEST-003",
        customer="Test User",
        customer_email="test@example.com",
        expires_at="2027-08-23",
    )

    data = json.loads(
        output.read_text(
            encoding="utf-8"
        )
    )

    assert data["expires_at"] == (
        "2027-08-23"
    )


def test_verify_valid_license(
    tmp_path,
    monkeypatch,
    capsys,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    output = license_manager.issue_license(
        license_id="FOP-TEST-004",
        order_id="ORDER-TEST-004",
        customer="Test User",
        customer_email="test@example.com",
    )

    result = license_manager.verify_license(
        output
    )

    captured = capsys.readouterr()

    assert result is True
    assert "VALID" in captured.out


def test_verify_invalid_license(
    tmp_path,
    monkeypatch,
    capsys,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    output = license_manager.issue_license(
        license_id="FOP-TEST-005",
        order_id="ORDER-TEST-005",
        customer="Test User",
        customer_email="test@example.com",
    )

    data = json.loads(
        output.read_text(
            encoding="utf-8"
        )
    )

    data["customer"] = "Hacker"

    output.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    result = license_manager.verify_license(
        output
    )

    captured = capsys.readouterr()

    assert result is False
    assert "INVALID" in captured.err


def test_revoke_license(
    tmp_path,
    monkeypatch,
):
    active_dir, revoked_dir = (
        prepare_test_environment(
            tmp_path,
            monkeypatch,
        )
    )

    output = license_manager.issue_license(
        license_id="FOP-TEST-006",
        order_id="ORDER-TEST-006",
        customer="Test User",
        customer_email="test@example.com",
    )

    assert output.exists()
    assert output.parent == active_dir

    revoked_license, revoke_metadata = (
        license_manager.revoke_license(
            license_id="FOP-TEST-006",
            reason="Refund requested",
        )
    )

    assert not output.exists()

    assert revoked_license.exists()
    assert revoked_license.parent == (
        revoked_dir
    )

    assert revoke_metadata.exists()

    revoke_data = json.loads(
        revoke_metadata.read_text(
            encoding="utf-8"
        )
    )

    assert revoke_data["license_id"] == (
        "FOP-TEST-006"
    )
    assert revoke_data["status"] == "revoked"
    assert revoke_data["reason"] == (
        "Refund requested"
    )
    assert revoke_data["revoked_at"]


def test_revoke_missing_license(
    tmp_path,
    monkeypatch,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    try:
        license_manager.revoke_license(
            license_id="FOP-TEST-999",
            reason="Test",
        )
    except FileNotFoundError as exc:
        assert (
            "Active license not found"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected FileNotFoundError"
        )


def test_list_licenses(
    tmp_path,
    monkeypatch,
    capsys,
):
    prepare_test_environment(
        tmp_path,
        monkeypatch,
    )

    license_manager.issue_license(
        license_id="FOP-TEST-007",
        order_id="ORDER-TEST-007",
        customer="User One",
    )

    license_manager.issue_license(
        license_id="FOP-TEST-008",
        order_id="ORDER-TEST-008",
        customer="User Two",
    )

    license_manager.list_licenses()

    captured = capsys.readouterr()

    assert "Active licenses : 2" in (
        captured.out
    )
    assert "Revoked licenses: 0" in (
        captured.out
    )
    assert "FOP-TEST-007" in captured.out
    assert "FOP-TEST-008" in captured.out