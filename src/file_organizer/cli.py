import argparse
import sys
from pathlib import Path

from .config import build_extension_mapping, load_config
from .organizer import organize_files


EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_OPERATION_ERROR = 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Organize files into folders based on their extensions."
    )

    parser.add_argument(
        "folder",
        type=Path,
        help="Path to the folder that should be organized",
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.json"),
        help="Path to configuration file (default: config.json)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without moving files",
    )

    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Include files inside subdirectories",
    )

    parser.add_argument(
        "--on-conflict",
        choices=["rename", "skip"],
        default="rename",
        help="How to handle files with an existing destination",
    )

    args = parser.parse_args(argv)

    # Validate input folder before starting the organizer.
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

    # Load and validate configuration.
    try:
        config = load_config(args.config)
        categories = build_extension_mapping(config)

    except (OSError, ValueError) as error:
        print(
            f"Error: {error}",
            file=sys.stderr,
        )
        return EXIT_CONFIG_ERROR

    # Run the organizer.
    result = organize_files(
        args.folder,
        categories,
        dry_run=args.dry_run,
        recursive=args.recursive,
        on_conflict=args.on_conflict,
        exclude_paths={args.config.resolve()},
    )

    print(f"Moved   : {result.moved}")
    print(f"Skipped : {result.skipped}")
    print(f"Failed  : {result.failed}")

    if result.failed > 0:
        return EXIT_OPERATION_ERROR

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())