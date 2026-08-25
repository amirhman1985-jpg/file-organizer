from __future__ import annotations

import argparse
import re
import sys
import tempfile
import zipfile
from pathlib import Path

from file_organizer import PRODUCT_NAME, PUBLISHER, __version__
from file_organizer.license import LicenseError, load_license


DEFAULT_PRO_ZIP = Path(
    f"release/"
    f"FileOrganizer-Pro-v{__version__}-Windows-x64.zip"
)


def safe_customer_name(customer: str) -> str:
    """
    Convert a customer name into a safe filename component.
    """
    value = customer.strip()

    if not value:
        return "Customer"

    value = re.sub(
        r"[^A-Za-z0-9_-]+",
        "-",
        value,
    )

    value = value.strip("-_")

    return value or "Customer"


def validate_license(
    license_path: Path,
) -> None:
    """
    Ensure the license is valid before packaging it.
    """
    try:
        license_data = load_license(
            license_path
        )
    except LicenseError as exc:
        raise ValueError(
            f"Invalid license: {exc}"
        ) from exc

    if license_data.edition != "pro":
        raise ValueError(
            "Only Pro licenses can be packaged."
        )


def create_customer_package(
    pro_zip_path: Path,
    license_path: Path,
    customer: str,
    output_dir: Path,
) -> Path:
    """
    Create a customer-specific Pro package.

    The source Pro ZIP is never modified.
    The customer's license is added as license.json.
    """
    if not pro_zip_path.exists():
        raise FileNotFoundError(
            f"Pro package not found: {pro_zip_path}"
        )

    if not license_path.exists():
        raise FileNotFoundError(
            f"License not found: {license_path}"
        )

    validate_license(
        license_path
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_name = safe_customer_name(
        customer
    )

    output_path = (
        output_dir
        / (
            f"FileOrganizer-Pro-v"
            f"{__version__}-"
            f"{safe_name}.zip"
        )
    )

    with tempfile.TemporaryDirectory(
        prefix="file-organizer-delivery-"
    ) as temp_dir:
        temp_root = Path(temp_dir)
        extracted_root = (
            temp_root / "package"
        )

        extracted_root.mkdir()

        # Extract the public package.
        with zipfile.ZipFile(
            pro_zip_path,
            "r",
        ) as archive:
            archive.extractall(
                extracted_root
            )

        # Locate the actual package directory.
        package_dirs = [
            path
            for path in extracted_root.iterdir()
            if path.is_dir()
        ]

        if len(package_dirs) != 1:
            raise ValueError(
                "Pro ZIP must contain exactly "
                "one top-level directory."
            )

        package_root = package_dirs[0]

        # Never allow private key material
        # to enter a customer package.
        forbidden_names = {
            "license_private.key",
        }

        for path in package_root.rglob("*"):
            if path.is_file():
                if path.name in forbidden_names:
                    raise ValueError(
                        "Private key material detected "
                        "inside Pro package."
                    )

                if "keys" in path.parts:
                    raise ValueError(
                        "Key material detected "
                        "inside Pro package."
                    )

        # Every customer package gets the standard
        # filename license.json.
        destination_license = (
            package_root / "license.json"
        )

        destination_license.write_bytes(
            license_path.read_bytes()
        )

        # Re-create the ZIP from the extracted package.
        with zipfile.ZipFile(
            output_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for path in package_root.rglob("*"):
                if path.is_file():
                    archive.write(
                        path,
                        path.relative_to(
                            extracted_root
                        ),
                    )

    return output_path


def inspect_package(
    package_path: Path,
) -> None:
    """
    Inspect the contents of a customer package.
    """
    if not package_path.exists():
        raise FileNotFoundError(
            f"Package not found: {package_path}"
        )

    with zipfile.ZipFile(
        package_path,
        "r",
    ) as archive:
        names = archive.namelist()

    print(
        f"Package : {package_path}"
    )
    print(
        f"Files   : {len(names)}"
    )

    if any(
        name.endswith("/license.json")
        or name == "license.json"
        for name in names
    ):
        print("License : Present")
    else:
        print("License : Missing")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "TechYarman delivery manager "
            "for File Organizer Pro."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    package_parser = subparsers.add_parser(
        "package",
        help=(
            "Create a customer-specific "
            "Pro package."
        ),
    )

    package_parser.add_argument(
        "--pro-zip",
        type=Path,
        default=DEFAULT_PRO_ZIP,
        help=(
            "Path to the public Pro ZIP."
        ),
    )

    package_parser.add_argument(
        "--license",
        required=True,
        type=Path,
        help="Path to the customer's license.json.",
    )

    package_parser.add_argument(
        "--customer",
        required=True,
        help="Customer name.",
    )

    package_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("deliveries"),
        help="Directory for generated packages.",
    )

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect a delivery package.",
    )

    inspect_parser.add_argument(
        "package",
        type=Path,
        help="Path to customer package.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "package":
        try:
            output = create_customer_package(
                pro_zip_path=args.pro_zip,
                license_path=args.license,
                customer=args.customer,
                output_dir=args.output_dir,
            )
        except (
            FileNotFoundError,
            ValueError,
            zipfile.BadZipFile,
        ) as exc:
            print(
                f"Delivery error: {exc}",
                file=sys.stderr,
            )
            return 1

        print(
            "Customer package created successfully"
        )
        print(
            f"Product   : {PRODUCT_NAME}"
        )
        print(
            f"Publisher : {PUBLISHER}"
        )
        print(
            f"Customer  : {args.customer}"
        )
        print(
            f"Package   : {output}"
        )

        return 0

    if args.command == "inspect":
        try:
            inspect_package(
                args.package
            )
        except (
            FileNotFoundError,
            zipfile.BadZipFile,
        ) as exc:
            print(
                f"Delivery error: {exc}",
                file=sys.stderr,
            )
            return 1

        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())