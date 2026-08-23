import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from file_organizer import license as license_module
from tools.license_manager import (
    issue_license,
    verify_license,
)


def prepare_keys(tmp_path, monkeypatch):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_key_path = tmp_path / "license_private.key"

    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    private_key_path.write_bytes(private_key_bytes)

    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    import base64

    monkeypatch.setattr(
        "tools.license_manager.PRIVATE_KEY_PATH",
        private_key_path,
    )

    monkeypatch.setattr(
        license_module,
        "PUBLIC_KEY_B64",
        base64.b64encode(public_key_bytes).decode("ascii"),
    )


def test_issue_license(
    tmp_path,
    monkeypatch,
):
    prepare_keys(tmp_path, monkeypatch)

    output = issue_license(
        license_id="FOP-TEST-001",
        order_id="ORDER-TEST-001",
        customer="Test User",
    )

    assert output.exists()

    data = json.loads(
        output.read_text(encoding="utf-8")
    )

    assert data["license_id"] == "FOP-TEST-001"
    assert data["order_id"] == "ORDER-TEST-001"
    assert data["product"] == "File Organizer"
    assert data["publisher"] == "TechYarman"
    assert data["customer"] == "Test User"
    assert data["edition"] == "pro"
    assert data["expires_at"] is None
    assert data["signature"]


def test_issued_license_is_valid(
    tmp_path,
    monkeypatch,
):
    prepare_keys(tmp_path, monkeypatch)

    output = issue_license(
        license_id="FOP-TEST-002",
        order_id="ORDER-TEST-002",
        customer="Test User",
    )

    license_data = license_module.load_license(output)

    assert license_data.license_id == "FOP-TEST-002"
    assert license_data.customer == "Test User"
    assert license_data.edition == "pro"


def test_issue_license_with_expiration(
    tmp_path,
    monkeypatch,
):
    prepare_keys(tmp_path, monkeypatch)

    output = issue_license(
        license_id="FOP-TEST-003",
        order_id="ORDER-TEST-003",
        customer="Test User",
        expires_at="2027-08-23",
    )

    data = json.loads(
        output.read_text(encoding="utf-8")
    )

    assert data["order_id"] == "ORDER-TEST-003"
    assert data["expires_at"] == "2027-08-23"


def test_verify_valid_license(
    tmp_path,
    monkeypatch,
    capsys,
):
    prepare_keys(tmp_path, monkeypatch)

    output = issue_license(
        license_id="FOP-TEST-004",
        order_id="ORDER-TEST-004",
        customer="Test User",
    )

    result = verify_license(output)

    captured = capsys.readouterr()

    assert result is True
    assert "VALID" in captured.out


def test_verify_invalid_license(
    tmp_path,
    monkeypatch,
    capsys,
):
    prepare_keys(tmp_path, monkeypatch)

    output = issue_license(
        license_id="FOP-TEST-005",
        order_id="ORDER-TEST-005",
        customer="Test User",
    )

    data = json.loads(
        output.read_text(encoding="utf-8")
    )

    data["customer"] = "Hacker"

    output.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    result = verify_license(output)

    captured = capsys.readouterr()

    assert result is False
    assert "INVALID" in captured.err