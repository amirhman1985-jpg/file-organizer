from pathlib import Path
import shutil
import logging

logging.basicConfig(
    filename="File_organizer.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
FILE_CATEGORIES = {
    ".jpg" : "Images",
    ".png" : "Images",
    ".webp" : "Images",
    ".pdf" : "Documents",
    ".docx" : "Documents",
    ".ai" : "Vectors",
    ".cdr" : "Vectors",
    ".svg" : "Vectors",
    ".zip" : "Archives",
    ".mp4" : "Videos"
}
def get_category(suffix: str) -> str:
    return FILE_CATEGORIES.get(suffix, "Others" )

def get_unique_destination(destination: Path, filename: str) -> Path:
    target = destination / filename

    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    counter = 1

    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_target = destination / new_name

        if not new_target.exists():
            return new_target

        counter += 1

def organize_files(folder: Path,
                   dry_run: bool = False,
                   recursive: bool = False
                ) -> tuple[int, int]:
    logging.info("File Organizer started")

    if  not folder.exists():
        logging.error("Folder does not exist")
        return 0, 0
    
    if not folder.is_dir():
        logging.error("The path is not a directory")
        return 0, 0
    
    moved_count = 0
    failed_count = 0

    destination_dirs = {
        folder / category
        for category in set(FILE_CATEGORIES.values()) | {"Others"}
    }

    if recursive:
        items = list(folder.rglob("*"))
    else:
        items = list(folder.iterdir())

    for item in items:
        if not item.is_file():
            continue

        if any(destination_dirs in item.parents for destination_dir in destination_dirs):
            continue
        
        category = get_category(item.suffix)

        if dry_run:
            print(f"Would move {item} -> {category}")
            logging.info(f"DRY RUN | Would move {item} -> {category}")
            continue

        destination = folder / category
        destination.mkdir(exist_ok=True)

        try:
            target= get_unique_destination(destination, item.name)
            shutil.move(item, target)
            logging.info(f"Moved {item} -> {category}")
            moved_count += 1
        except Exception as e:
            logging.error(f"Could not move {item}: {e}")
            failed_count += 1
    if dry_run:
        print("Dry run completed. No files were moved.")

    logging.info(f"Finished. Moved {moved_count}, Failed {failed_count}")

    return moved_count, failed_count