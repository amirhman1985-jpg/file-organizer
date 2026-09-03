from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse


class PreflightError(RuntimeError):
    """Raised when production configuration is invalid."""


REQUIRED_ENV_VARS = (
    "WOOCOMMERCE_URL",
    "WOOCOMMERCE_CONSUMER_KEY",
    "WOOCOMMERCE_CONSUMER_SECRET",
    "WOOCOMMERCE_WEBHOOK_SECRET",
    "WOOCOMMERCE_PRO_PRODUCT_ID",
    "WOOCOMMERCE_PRO_PRICE_IRR",
    "DELIVERY_PRO_ZIP_PATH",
    "DELIVERY_DIR",
    "DOWNLOAD_BASE_URL",
)


def _get_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise PreflightError(
            f"Required environment variable is missing: {name}"
        )

    return value


def _validate_https_url(name: str, value: str) -> None:
    parsed = urlparse(value)

    if parsed.scheme not in {"http", "https"}:
        raise PreflightError(
            f"{name} must use http or https."
        )

    if not parsed.netloc:
        raise PreflightError(
            f"{name} is not a valid URL."
        )


def _validate_positive_int(name: str, value: str) -> None:
    try:
        number = int(value)
    except ValueError as exc:
        raise PreflightError(
            f"{name} must be an integer."
        ) from exc

    if number <= 0:
        raise PreflightError(
            f"{name} must be greater than zero."
        )


def validate_production_configuration() -> None:
    """
    Validate all configuration required by the production
    WooCommerce + delivery integration.

    This function only validates configuration.
    It does not perform any network request.
    """
    values = {
        name: _get_env(name)
        for name in REQUIRED_ENV_VARS
    }

    _validate_https_url(
        "WOOCOMMERCE_URL",
        values["WOOCOMMERCE_URL"],
    )

    _validate_https_url(
        "DOWNLOAD_BASE_URL",
        values["DOWNLOAD_BASE_URL"],
    )

    _validate_positive_int(
        "WOOCOMMERCE_PRO_PRODUCT_ID",
        values["WOOCOMMERCE_PRO_PRODUCT_ID"],
    )

    _validate_positive_int(
        "WOOCOMMERCE_PRO_PRICE_IRR",
        values["WOOCOMMERCE_PRO_PRICE_IRR"],
    )

    pro_zip = Path(
        values["DELIVERY_PRO_ZIP_PATH"]
    )

    if not pro_zip.is_file():
        raise PreflightError(
            "DELIVERY_PRO_ZIP_PATH does not point to an existing file: "
            f"{pro_zip}"
        )

    if pro_zip.suffix.lower() != ".zip":
        raise PreflightError(
            "DELIVERY_PRO_ZIP_PATH must point to a ZIP file."
        )

    delivery_dir = Path(
        values["DELIVERY_DIR"]
    )

    delivery_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not delivery_dir.is_dir():
        raise PreflightError(
            "DELIVERY_DIR is not a directory: "
            f"{delivery_dir}"
        )


def run_preflight() -> dict[str, str]:
    """
    Validate production configuration and return
    a safe summary without exposing secrets.
    """
    validate_production_configuration()

    return {
        "status": "ok",
        "woocommerce": "configured",
        "delivery": "configured",
        "download": "configured",
    }