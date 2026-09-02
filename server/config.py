from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_base_url: str
    delivery_pro_zip_path: str
    delivery_dir: str
    download_base_url: str
    parspal_merchant_id: str
    parspal_request_url: str
    parspal_verify_url: str
    parspal_payment_url: str
    woocommerce_pro_product_id: int
    woocommerce_pro_price_irr: int
    crypto_api_url: str
    crypto_api_key: str
    woocommerce_url: str
    woocommerce_consumer_key: str
    woocommerce_consumer_secret: str
    woocommerce_webhook_secret: str


def load_settings() -> Settings:
    return Settings(
        app_base_url=os.getenv(
            "APP_BASE_URL",
            "http://localhost:8000",
        ),
        parspal_merchant_id=os.getenv(
            "PARSPAL_MERCHANT_ID",
            "",
        ),
        parspal_request_url=os.getenv(
            "PARSPAL_REQUEST_URL",
            "",
        ),
        parspal_verify_url=os.getenv(
            "PARSPAL_VERIFY_URL",
            "",
        ),
        parspal_payment_url=os.getenv(
            "PARSPAL_PAYMENT_URL",
            "",
        ),
        crypto_api_url=os.getenv(
            "CRYPTO_API_URL",
            "",
        ),
        crypto_api_key=os.getenv(
            "CRYPTO_API_KEY",
            "",
        ),
        woocommerce_webhook_secret=os.getenv(
            "WOOCOMMERCE_WEBHOOK_SECRET",
            "",
        ),
        woocommerce_pro_price_irr=int(
            os.getenv(
            "WOOCOMMERCE_PRO_PRICE_IRR",
            "0",
            )
        ),
        woocommerce_pro_product_id=int(
            os.getenv(
            "WOOCOMMERCE_PRO_PRODUCT_ID",
            "0",
        )
        ),
        delivery_pro_zip_path=os.getenv(
            "DELIVERY_PRO_ZIP_PATH",
            "dist/FileOrganizer-Pro-v0.4.0-Windows-x64.zip",
        ),
        delivery_dir=os.getenv(
            "DELIVERY_DIR",
            "deliveries",
        ),
        download_base_url=os.getenv(
            "DOWNLOAD_BASE_URL",
            "http://127.0.0.1:8000",
        ),
        woocommerce_url=os.getenv(
            "WOOCOMMERCE_URL",
            "",
        ).rstrip("/"),

        woocommerce_consumer_key=os.getenv(
            "WOOCOMMERCE_CONSUMER_KEY",
            "",
        ),

        woocommerce_consumer_secret=os.getenv(
            "WOOCOMMERCE_CONSUMER_SECRET",
            "",
        ),
    )