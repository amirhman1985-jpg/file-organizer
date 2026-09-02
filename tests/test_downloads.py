from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from server.app import app


client = TestClient(app)


def create_package(
    tmp_path: Path,
) -> Path:
    package = (
        tmp_path
        / "FileOrganizer-Pro-v0.4.0-Amir.zip"
    )

    package.write_bytes(
        b"fake zip content"
    )

    return package


def create_token_metadata(
    tmp_path: Path,
    token: str,
    package_path: Path,
    expires_at: datetime,
) -> Path:
    downloads_dir = (
        tmp_path
        / "deliveries"
        / ".tokens"
    )

    downloads_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    metadata = {
        "token": token,
        "package_path": str(
            package_path.resolve()
        ),
        "customer": "Amir",
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "expires_at": expires_at.isoformat(),
        "downloads": 0,
    }

    metadata_path = (
        downloads_dir
        / f"{token}.json"
    )

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
        ),
        encoding="utf-8",
    )

    return metadata_path


def test_download_returns_customer_package(
    tmp_path,
    monkeypatch,
):
    package_path = create_package(
        tmp_path
    )

    downloads_dir = (
        tmp_path
        / "deliveries"
        / ".tokens"
    )

    monkeypatch.setenv(
        "DELIVERY_DIR",
        str(
            tmp_path / "deliveries"
        ),
    )

    create_token_metadata(
        tmp_path=tmp_path,
        token="test-token",
        package_path=package_path,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(days=1)
        ),
    )

    response = client.get(
        "/api/download/test-token"
    )

    assert response.status_code == 200

    assert response.content == (
        b"fake zip content"
    )

    assert (
        response.headers["content-type"]
        == "application/zip"
    )

    content_disposition = (
        response.headers.get(
            "content-disposition",
            "",
        )
    )

    assert (
        "FileOrganizer-Pro-v0.4.0-Amir.zip"
        in content_disposition
    )

    metadata = json.loads(
        (
            downloads_dir
            / "test-token.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert metadata["downloads"] == 1


def test_download_rejects_missing_token(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "DELIVERY_DIR",
        str(
            tmp_path / "deliveries"
        ),
    )

    response = client.get(
        "/api/download/does-not-exist"
    )

    assert response.status_code == 404

    assert (
        "Download link not found"
        in response.json()["detail"]
    )


def test_download_rejects_expired_token(
    tmp_path,
    monkeypatch,
):
    package_path = create_package(
        tmp_path
    )

    monkeypatch.setenv(
        "DELIVERY_DIR",
        str(
            tmp_path / "deliveries"
        ),
    )

    create_token_metadata(
        tmp_path=tmp_path,
        token="expired-token",
        package_path=package_path,
        expires_at=(
            datetime.now(timezone.utc)
            - timedelta(seconds=1)
        ),
    )

    response = client.get(
        "/api/download/expired-token"
    )

    assert response.status_code == 410

    assert (
        "Download link has expired"
        in response.json()["detail"]
    )


def test_download_rejects_missing_package(
    tmp_path,
    monkeypatch,
):
    missing_package = (
        tmp_path
        / "missing.zip"
    )

    monkeypatch.setenv(
        "DELIVERY_DIR",
        str(
            tmp_path / "deliveries"
        ),
    )

    create_token_metadata(
        tmp_path=tmp_path,
        token="missing-package-token",
        package_path=missing_package,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(days=1)
        ),
    )

    response = client.get(
        "/api/download/missing-package-token"
    )

    assert response.status_code == 404

    assert (
        "Delivery package no longer exists"
        in response.json()["detail"]
    )

def test_download_limit_is_enforced(
    tmp_path,
    monkeypatch,
):
    package_path = create_package(
        tmp_path
    )

    downloads_dir = (
        tmp_path
        / "deliveries"
        / ".tokens"
    )

    monkeypatch.setenv(
        "DELIVERY_DIR",
        str(
            tmp_path / "deliveries"
        ),
    )

    create_token_metadata(
        tmp_path=tmp_path,
        token="limited-token",
        package_path=package_path,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(days=1)
        ),
    )

    metadata_path = (
        downloads_dir
        / "limited-token.json"
    )

    metadata = json.loads(
        metadata_path.read_text(
            encoding="utf-8"
        )
    )

    metadata["max_downloads"] = 2

    metadata_path.write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    first = client.get(
        "/api/download/limited-token"
    )

    second = client.get(
        "/api/download/limited-token"
    )

    third = client.get(
        "/api/download/limited-token"
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 410

    assert (
        "Download limit exceeded"
        in third.json()["detail"]
    )


def test_download_counter_increases_only_on_success(
    tmp_path,
    monkeypatch,
):
    package_path = create_package(
        tmp_path
    )

    downloads_dir = (
        tmp_path
        / "deliveries"
        / ".tokens"
    )

    monkeypatch.setenv(
        "DELIVERY_DIR",
        str(
            tmp_path / "deliveries"
        ),
    )

    create_token_metadata(
        tmp_path=tmp_path,
        token="counter-token",
        package_path=package_path,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(days=1)
        ),
    )

    metadata_path = (
        downloads_dir
        / "counter-token.json"
    )

    metadata = json.loads(
        metadata_path.read_text(
            encoding="utf-8"
        )
    )

    metadata["max_downloads"] = 1

    metadata_path.write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    first = client.get(
        "/api/download/counter-token"
    )

    second = client.get(
        "/api/download/counter-token"
    )

    assert first.status_code == 200
    assert second.status_code == 410

    final_metadata = json.loads(
        metadata_path.read_text(
            encoding="utf-8"
        )
    )

    assert final_metadata["downloads"] == 1

def test_download_token_defaults_to_five_downloads(
    tmp_path,
):
    package_path = create_package(
        tmp_path
    )

    downloads_dir = (
        tmp_path
        / "deliveries"
        / ".tokens"
    )

    from server.services.downloads import (
        create_download_token,
    )

    token = create_download_token(
        package_path=package_path,
        downloads_dir=downloads_dir,
        customer="Amir",
    )

    metadata = json.loads(
        (
            downloads_dir
            / f"{token}.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert metadata["max_downloads"] == 5
    assert metadata["downloads"] == 0