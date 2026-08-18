import argparse
from pathlib import Path
from .organizer import organize_files
def main():
    parser = argparse.ArgumentParser(
        description="Organize files into folders based on their extensions."
    )

    parser.add_argument(
        "folder",
        help="Path to the folder that should be organized",
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

    args = parser.parse_args()

    folder = Path(args.folder)

    result = organize_files(
        folder,
        dry_run=args.dry_run,
        recursive=args.recursive,
        on_conflict=args.on_conflict,
    )

    print(f"Moved   : {result.moved}")
    print(f"Skipped : {result.skipped}")
    print(f"Failed  : {result.failed}")
if __name__ == "__main__":
    main()