from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from server.config import load_settings
from server.routes.woocommerce import (
    router as woocommerce_router,
)
from server.services.downloads import (
    register_download,
)


app = FastAPI(
    title="TechYarman Payment API",
    version="0.1.0",
    description=(
        "Backend API for TechYarman "
        "order, payment, licensing, and delivery."
    ),
)


@app.get(
    "/health",
    tags=["System"],
)
async def health() -> dict[str, str]:
    """
    Return the current API health status.
    """
    return {
        "status": "ok",
        "service": "TechYarman Payment API",
    }


@app.get(
    "/api/download/{token}",
    tags=["Download"],
)
async def download_package(
    token: str,
):
    """
    Download a customer-specific delivery package.

    The token must:
    - exist
    - not be expired
    - not exceed the download limit
    - point to an existing package
    """

    settings = load_settings()

    downloads_dir = (
        Path(settings.delivery_dir)
        / ".tokens"
    )

    try:
        metadata = register_download(
            token=token,
            downloads_dir=downloads_dir,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except PermissionError as exc:
        raise HTTPException(
            status_code=410,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    package_path = Path(
        metadata["package_path"]
    )

    return FileResponse(
        path=package_path,
        filename=package_path.name,
        media_type="application/zip",
    )


app.include_router(
    woocommerce_router,
)