from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path


TOKEN_BYTES = 32
DEFAULT_EXPIRY_DAYS = 7
DEFAULT_MAX_DOWNLOADS = 5


def create_download_token(
    package_path: Path,
    downloads_dir: Path,
    customer: str,
    *,
    expiry_days: int = DEFAULT_EXPIRY_DAYS,
    max_downloads: int = DEFAULT_MAX_DOWNLOADS,
) -> str:
    """
    Create a secure download token.

    The token is random and tied to a specific delivery package.
    """

    if not package_path.exists():
        raise FileNotFoundError(
            f"Package not found: {package_path}"
        )

    if expiry_days <= 0:
        raise ValueError(
            "expiry_days must be greater than zero."
        )

    if max_downloads <= 0:
        raise ValueError(
            "max_downloads must be greater than zero."
        )

    downloads_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    token = secrets.token_urlsafe(
        TOKEN_BYTES
    )

    now = datetime.now(
        timezone.utc
    )

    expires_at = (
        now
        + timedelta(days=expiry_days)
    )

    metadata = {
        "token": token,
        "package_path": str(
            package_path.resolve()
        ),
        "customer": customer,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "downloads": 0,
        "max_downloads": max_downloads,
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

    return token


def load_download_metadata(
    token: str,
    downloads_dir: Path,
) -> dict:
    """
    Load a download token and validate:
    - token exists
    - token has not expired
    - download limit has not been reached
    - package still exists
    """

    if not token:
        raise ValueError(
            "Download token is required."
        )

    metadata_path = (
        downloads_dir
        / f"{token}.json"
    )

    try:
        metadata = json.loads(
            metadata_path.read_text(
                encoding="utf-8"
            )
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            "Download link not found."
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Download metadata is invalid."
        ) from exc

    try:
        expires_at = datetime.fromisoformat(
            metadata["expires_at"]
        )
    except (
        KeyError,
        ValueError,
    ) as exc:
        raise ValueError(
            "Download metadata has an invalid expiration date."
        ) from exc

    if datetime.now(
        timezone.utc
    ) >= expires_at:
        raise PermissionError(
            "Download link has expired."
        )

    downloads = int(
        metadata.get(
            "downloads",
            0,
        )
    )

    max_downloads = int(
        metadata.get(
            "max_downloads",
            DEFAULT_MAX_DOWNLOADS,
        )
    )

    if downloads >= max_downloads:
        raise PermissionError(
            "Download limit exceeded."
        )

    package_path = Path(
        metadata["package_path"]
    )

    if not package_path.exists():
        raise FileNotFoundError(
            "Delivery package no longer exists."
        )

    return metadata


def register_download(
    token: str,
    downloads_dir: Path,
) -> dict:
    """
    Register one successful download.

    Validation is performed before increasing the counter.
    """

    metadata_path = (
        downloads_dir
        / f"{token}.json"
    )

    metadata = load_download_metadata(
        token,
        downloads_dir,
    )

    metadata["downloads"] = (
        int(
            metadata.get(
                "downloads",
                0,
            )
        )
        + 1
    )

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
        ),
        encoding="utf-8",
    )

    return metadata