import argparse
import sys
from pathlib import Path

from file_organizer import __version__
from file_organizer.config import load_config, build_extension_mapping
from file_organizer.features import FREE_FEATURES, PRO_FEATURES
from file_organizer.organizer import organize_files
from file_organizer.license import load_license, LicenseError


EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_OPERATION_ERROR = 2
EXIT_LICENSE_ERROR = 3


FREE_CATEGORIES = {
    ".jpg": "Images",
    ".jpeg": "Images",
    ".png": "Images",
    ".webp": "Images",
    ".pdf": "Documents",
    ".docx": "Documents",
    ".txt": "Documents",
    ".ai": "Vectors",
    ".cdr": "Vectors",
    ".svg": "Vectors",
    ".zip": "Archives",
    ".rar": "Archives",
    ".mp4": "Videos",
    ".mkv": "Videos",
}


def get_default_config_path() -> Path:
    """
    Return the default config path.

    In development:
        current working directory / config.json

    In PyInstaller executable mode:
        directory containing the executable / config.json
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "config.json"

    return Path("config.json").resolve()


def get_default_license_path() -> Path:
    """
    Return the default Pro license path.

    In PyInstaller executable mode:
        directory containing the executable / license.json

    In development:
        current working directory / license.json
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "license.json"

    return Path("license.json").resolve()


def print_categories(
    categories: dict[str, list[str]],
) -> None:
    for category, extensions in categories.items():
        print(category)

        for extension in extensions:
            print(f"  {extension}")

        print()


def main(
    argv: list[str] | None = None,
    edition: str = "pro",
) -> int:

    # -----------------------------
    # Select edition
    # -----------------------------
    if edition == "free":
        features = FREE_FEATURES
    elif edition == "pro":
        features = PRO_FEATURES
    else:
        print(
            f"Error: Unsupported edition: {edition}",
            file=sys.stderr,
        )
        return EXIT_CONFIG_ERROR

    # -----------------------------
    # Argument parser
    # -----------------------------
    parser = argparse.ArgumentParser(
        prog=f"FileOrganizer {features.name}",
        description=(
            "Organize files into folders "
            "based on their extensions."
        ),
    )

    # Common argument
    parser.add_argument(
        "folder",
        type=Path,
        nargs="?",
        help="Path to the folder that should be organized",
    )

    # Common argument
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # Pro only
    if features.custom_config:
        parser.add_argument(
            "--config",
            type=Path,
            default=get_default_config_path(),
            help=(
                "Path to configuration file "
                "(default: config.json)"
            ),
        )

    # Pro only
    if features.dry_run:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without moving files",
        )

    # Pro only
    if features.recursive:
        parser.add_argument(
            "--recursive",
            action="store_true",
            help="Include files inside subdirectories",
        )

    # Free + Pro
    parser.add_argument(
        "--on-conflict",
        choices=features.conflict_policies,
        default="rename",
        help="How to handle files with an existing destination",
    )

    # Pro only
    if features.list_categories:
        parser.add_argument(
            "--list-categories",
            action="store_true",
            help="List configured categories and extensions",
        )

    # Pro only
    if edition == "pro":
        parser.add_argument(
            "--license",
            type=Path,
            default=get_default_license_path(),
            help="Path to Pro license file",
        )

    args = parser.parse_args(argv)

    # -----------------------------
    # Validate Pro license
    # -----------------------------
    if edition == "pro":
        try:
            license_data = load_license(args.license)
        except LicenseError as error:
            print(
                f"License error: {error}",
                file=sys.stderr,
            )
            return EXIT_LICENSE_ERROR

        if license_data.edition != "pro":
            print(
                "License error: License is not for Pro edition.",
                file=sys.stderr,
            )
            return EXIT_LICENSE_ERROR

    # -----------------------------
    # Load configuration
    # -----------------------------
    if edition == "free":
        categories = FREE_CATEGORIES
        config = None

    else:
        try:
            config = load_config(args.config)
            categories = build_extension_mapping(config)

        except (OSError, ValueError) as error:
            print(
                f"Error: {error}",
                file=sys.stderr,
            )
            return EXIT_CONFIG_ERROR

    # -----------------------------
    # List categories - Pro only
    # -----------------------------
    if features.list_categories and args.list_categories:
        print_categories(
            config["categories"]
        )
        return EXIT_OK

    # -----------------------------
    # Folder required
    # -----------------------------
    if args.folder is None:
        message = (
            "Error: folder is required "
            "unless --list-categories is used."
            if features.list_categories
            else "Error: folder is required."
        )

        print(
            message,
            file=sys.stderr,
        )
        return EXIT_CONFIG_ERROR

    # -----------------------------
    # Validate folder
    # -----------------------------
    if not args.folder.exists():
        print(
            f"Error: Folder does not exist: {args.folder}",
            file=sys.stderr,
        )
        return EXIT_CONFIG_ERROR

    if not args.folder.is_dir():
        print(
            f"Error: Path is not a directory: {args.folder}",
            file=sys.stderr,
        )
        return EXIT_CONFIG_ERROR

    # -----------------------------
    # Run organizer
    # -----------------------------
    result = organize_files(
        args.folder,
        categories,
        dry_run=(
            args.dry_run
            if features.dry_run
            else False
        ),
        recursive=(
            args.recursive
            if features.recursive
            else False
        ),
        on_conflict=args.on_conflict,
        exclude_paths=(
            {
                args.config.resolve(),
                args.license.resolve(),
            }
            if edition == "pro"
            else set()
        ),
    )

    # -----------------------------
    # Display result
    # -----------------------------
    print(f"Moved   : {result.moved}")
    print(f"Skipped : {result.skipped}")
    print(f"Failed  : {result.failed}")

    # -----------------------------
    # Exit code
    # -----------------------------
    if result.failed > 0:
        return EXIT_OPERATION_ERROR

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())