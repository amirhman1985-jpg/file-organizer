import argparse
import sys
from pathlib import Path

from file_organizer.config import load_config, build_extension_mapping
from file_organizer.organizer import organize_files
from file_organizer import __version__


EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_OPERATION_ERROR = 2


def get_default_config_path() -> Path:
    """
    Returns the default config path.

    During normal development:
        current working directory / config.json

    During PyInstaller executable mode:
        directory containing the executable / config.json
    """

    if getattr(sys, "frozen", False):
        return (
            Path(sys.executable).resolve().parent
            / "config.json"
        )

    return Path("config.json").resolve()


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
) -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Organize files into folders "
            "based on their extensions."
        )
    )

    parser.add_argument(
        "folder",
        type=Path,
        nargs="?",
        help=(
            "Path to the folder "
            "that should be organized"
        ),
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=get_default_config_path(),
        help=(
            "Path to configuration file "
            "(default: config.json)"
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Preview changes "
            "without moving files"
        ),
    )

    parser.add_argument(
        "--recursive",
        action="store_true",
        help=(
            "Include files inside "
            "subdirectories"
        ),
    )

    parser.add_argument(
        "--on-conflict",
        choices=[
            "rename",
            "skip",
        ],
        default="rename",
        help=(
            "How to handle files "
            "with an existing destination"
        ),
    )

    parser.add_argument(
        "--list-categories",
        action="store_true",
        help=(
            "List configured categories "
            "and extensions"
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args(argv)

    # --------------------------------
    # Load and validate configuration
    # --------------------------------

    try:
        config = load_config(
            args.config
        )

        categories = build_extension_mapping(
            config
        )

    except (
        OSError,
        ValueError,
    ) as error:

        print(
            f"Error: {error}",
            file=sys.stderr,
        )

        return EXIT_CONFIG_ERROR

    # --------------------------------
    # List categories mode
    # --------------------------------

    if args.list_categories:
        print_categories(
            config["categories"]
        )

        return EXIT_OK

    # --------------------------------
    # Folder is required in normal mode
    # --------------------------------

    if args.folder is None:
        print(
            "Error: folder is required "
            "unless --list-categories is used.",
            file=sys.stderr,
        )

        return EXIT_CONFIG_ERROR

    # --------------------------------
    # Validate folder
    # --------------------------------

    if not args.folder.exists():
        print(
            f"Error: Folder does not exist: "
            f"{args.folder}",
            file=sys.stderr,
        )

        return EXIT_CONFIG_ERROR

    if not args.folder.is_dir():
        print(
            f"Error: Path is not a directory: "
            f"{args.folder}",
            file=sys.stderr,
        )

        return EXIT_CONFIG_ERROR

    # --------------------------------
    # Run organizer
    # --------------------------------

    result = organize_files(
        args.folder,
        categories,
        dry_run=args.dry_run,
        recursive=args.recursive,
        on_conflict=args.on_conflict,
        exclude_paths={
            args.config.resolve()
        },
    )

    # --------------------------------
    # Display result
    # --------------------------------

    print(
        f"Moved   : {result.moved}"
    )

    print(
        f"Skipped : {result.skipped}"
    )

    print(
        f"Failed  : {result.failed}"
    )

    # --------------------------------
    # Exit code
    # --------------------------------

    if result.failed > 0:
        return EXIT_OPERATION_ERROR

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())