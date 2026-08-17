import argparse
from pathlib import Path
from .organizer import organize_files
def main():
    parser = argparse.ArgumentParser(
        description="Organize files into folders based on their extensions."
    )
    parser.add_argument(
        "folder",
        help="Path to the folder that should be organized"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without moving files"
    )
    args = parser.parse_args()
    folder = Path(args.folder)
    moved, failed = organize_files(
        folder,
        dry_run=args.dry_run
        )
    print(f"Moved : {moved}")
    print(f"Failed : {failed}")
if __name__ == "__main__":
    main()