from __future__ import annotations

from pathlib import Path

import pytest

from server.preflight import (
    PreflightError,
    run_preflight,
    validate_production_configuration,
)


REQUIRED_VALUES = {
    "WOOCOMMERCE_URL": "https://example.com",
    "WOOCOMMERCE_CONSUMER_KEY": "ck_test",
    "WOOCOMMERCE_CONSUMER_SECRET": "cs_test",
    "WOOCOMMERCE_WEBHOOK_SECRET": "webhook-secret",
    "WOOCOMMERCE_PRO_PRODUCT_ID": "1410",
    "WOOCOMMERCE_PRO_PRICE_IRR": "990000",
    "DOWNLOAD_BASE_URL": "https://api.example.com",
}


def prepare_environment(
    monkeypatch,
    tmp_path: Path,
) -> Path:
    for name, value in REQUIRED_VALUES.items():
        monkeypatch.setenv(name, value)

    pro_zip = (
        tmp_path
        / "FileOrganizer-Pro-v0.4.0-Windows-x64.zip"
    )
    pro_zip.write_bytes(b"test zip")

    delivery_dir = (
        tmp_path
        / "deliveries"
    )

    monkeypatch.setenv(
        "DELIVERY_PRO_ZIP_PATH",
        str(pro_zip),
    )

    monkeypatch.setenv(
        "DELIVERY_DIR",
        str(delivery_dir),
    )

    return pro_zip


def test_production_configuration_is_valid(
    monkeypatch,
    tmp_path,
):
    prepare_environment(
        monkeypatch,
        tmp_path,
    )

    validate_production_configuration()


def test_run_preflight_returns_safe_summary(
    monkeypatch,
    tmp_path,
):
    prepare_environment(
        monkeypatch,
        tmp_path,
    )

    result = run_preflight()

    assert result == {
        "status": "ok",
        "woocommerce": "configured",
        "delivery": "configured",
        "download": "configured",
    }


@pytest.mark.parametrize(
    "missing_name",
    [
        "WOOCOMMERCE_URL",
        "WOOCOMMERCE_CONSUMER_KEY",
        "WOOCOMMERCE_CONSUMER_SECRET",
        "WOOCOMMERCE_WEBHOOK_SECRET",
        "WOOCOMMERCE_PRO_PRODUCT_ID",
        "WOOCOMMERCE_PRO_PRICE_IRR",
        "DELIVERY_PRO_ZIP_PATH",
        "DELIVERY_DIR",
        "DOWNLOAD_BASE_URL",
    ],
)
def test_missing_required_environment_variable(
    monkeypatch,
    tmp_path,
    missing_name,
):
    prepare_environment(
        monkeypatch,
        tmp_path,
    )

    monkeypatch.delenv(
        missing_name,
        raising=False,
    )

    with pytest.raises(
        PreflightError,
        match=missing_name,
    ):
        validate_production_configuration()


def test_invalid_woocommerce_url(
    monkeypatch,
    tmp_path,
):
    prepare_environment(
        monkeypatch,
        tmp_path,
    )

    monkeypatch.setenv(
        "WOOCOMMERCE_URL",
        "not-a-url",
    )

    with pytest.raises(
        PreflightError,
        match="WOOCOMMERCE_URL",
    ):
        validate_production_configuration()


def test_invalid_download_base_url(
    monkeypatch,
    tmp_path,
):
    prepare_environment(
        monkeypatch,
        tmp_path,
    )

    monkeypatch.setenv(
        "DOWNLOAD_BASE_URL",
        "ftp://example.com",
    )

    with pytest.raises(
        PreflightError,
        match="DOWNLOAD_BASE_URL",
    ):
        validate_production_configuration()


def test_invalid_product_id(
    monkeypatch,
    tmp_path,
):
    prepare_environment(
        monkeypatch,
        tmp_path,
    )

    monkeypatch.setenv(
        "WOOCOMMERCE_PRO_PRODUCT_ID",
        "abc",
    )

    with pytest.raises(
        PreflightError,
        match="WOOCOMMERCE_PRO_PRODUCT_ID",
    ):
        validate_production_configuration()


def test_invalid_price(
    monkeypatch,
    tmp_path,
):
    prepare_environment(
        monkeypatch,
        tmp_path,
    )

    monkeypatch.setenv(
        "WOOCOMMERCE_PRO_PRICE_IRR",
        "0",
    )

    with pytest.raises(
        PreflightError,
        match="WOOCOMMERCE_PRO_PRICE_IRR",
    ):
        validate_production_configuration()


def test_missing_release_zip(
    monkeypatch,
    tmp_path,
):
    prepare_environment(
        monkeypatch,
        tmp_path,
    )

    missing_zip = (
        tmp_path
        / "missing.zip"
    )

    monkeypatch.setenv(
        "DELIVERY_PRO_ZIP_PATH",
        str(missing_zip),
    )

    with pytest.raises(
        PreflightError,
        match="DELIVERY_PRO_ZIP_PATH",
    ):
        validate_production_configuration()


def test_release_path_must_be_zip(
    monkeypatch,
    tmp_path,
):
    prepare_environment(
        monkeypatch,
        tmp_path,
    )

    release_file = (
        tmp_path
        / "release.exe"
    )
    release_file.write_bytes(
        b"fake"
    )

    monkeypatch.setenv(
        "DELIVERY_PRO_ZIP_PATH",
        str(release_file),
    )

    with pytest.raises(
        PreflightError,
        match="ZIP",
    ):
        validate_production_configuration()