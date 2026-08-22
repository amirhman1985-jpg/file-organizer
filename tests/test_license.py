import base64
import json
from datetime import date, timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from file_organizer import license as license_module
from file_organizer.license import (
    LicenseError,
    load_license,
)


def create_signed_license(
    tmp_path,
    monkeypatch,
    *,
    license_id="TEST-001",
    customer="Test User",
    edition="pro",
    expires_at=None,
    product="File Organizer",
    publisher="TechYarman",
):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    public_key_b64 = base64.b64encode(
        public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode("ascii")

    license_data = {
        "license_id": license_id,
        "product": product,
        "publisher": publisher,
        "customer": customer,
        "edition": edition,
        "expires_at": expires_at,
    }

    payload = json.dumps(
        license_data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    signature = private_key.sign(payload)

    license_data["signature"] = base64.b64encode(
        signature
    ).decode("ascii")

    license_file = tmp_path / "license.json"

    license_file.write_text(
        json.dumps(license_data),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        license_module,
        "PUBLIC_KEY_B64",
        public_key_b64,
    )

    return license_file


def test_valid_license(
    tmp_path,
    monkeypatch,
):
    license_file = create_signed_license(
        tmp_path,
        monkeypatch,
    )

    result = load_license(license_file)

    assert result.license_id == "TEST-001"
    assert result.customer == "Test User"
    assert result.edition == "pro"
    assert result.expires_at is None


def test_invalid_signature(
    tmp_path,
    monkeypatch,
):
    license_file = create_signed_license(
        tmp_path,
        monkeypatch,
    )

    data = json.loads(
        license_file.read_text(encoding="utf-8")
    )

    data["customer"] = "Hacker"

    license_file.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    with pytest.raises(
        LicenseError,
        match="Invalid license signature",
    ):
        load_license(license_file)


def test_expired_license(
    tmp_path,
    monkeypatch,
):
    expired_date = (
        date.today() - timedelta(days=1)
    ).isoformat()

    license_file = create_signed_license(
        tmp_path,
        monkeypatch,
        expires_at=expired_date,
    )

    with pytest.raises(
        LicenseError,
        match="License has expired",
    ):
        load_license(license_file)


def test_valid_future_expiration(
    tmp_path,
    monkeypatch,
):
    future_date = (
        date.today() + timedelta(days=30)
    ).isoformat()

    license_file = create_signed_license(
        tmp_path,
        monkeypatch,
        expires_at=future_date,
    )

    result = load_license(license_file)

    assert result.expires_at == date.fromisoformat(
        future_date
    )


def test_non_pro_license(
    tmp_path,
    monkeypatch,
):
    license_file = create_signed_license(
        tmp_path,
        monkeypatch,
        edition="free",
    )

    with pytest.raises(
        LicenseError,
        match="not a Pro license",
    ):
        load_license(license_file)


def test_wrong_product(
    tmp_path,
    monkeypatch,
):
    license_file = create_signed_license(
        tmp_path,
        monkeypatch,
        product="Other Product",
    )

    with pytest.raises(
        LicenseError,
        match="different product",
    ):
        load_license(license_file)


def test_wrong_publisher(
    tmp_path,
    monkeypatch,
):
    license_file = create_signed_license(
        tmp_path,
        monkeypatch,
        publisher="OtherBrand",
    )

    with pytest.raises(
        LicenseError,
        match="not issued by TechYarman",
    ):
        load_license(license_file)


def test_missing_license_field(
    tmp_path,
    monkeypatch,
):
    license_file = create_signed_license(
        tmp_path,
        monkeypatch,
    )

    data = json.loads(
        license_file.read_text(encoding="utf-8")
    )

    del data["customer"]

    license_file.write_text(
        json.dumps(data),
        encoding="utf-8",
    )

    with pytest.raises(
        LicenseError,
        match="License is missing fields",
    ):
        load_license(license_file)


def test_invalid_json(tmp_path):
    license_file = tmp_path / "license.json"

    license_file.write_text(
        "{ invalid json",
        encoding="utf-8",
    )

    with pytest.raises(LicenseError):
        load_license(license_file)


def test_missing_license_file(tmp_path):
    license_file = (
        tmp_path / "does_not_exist.json"
    )

    with pytest.raises(LicenseError):
        load_license(license_file)