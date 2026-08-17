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
def organize_files(folder: Path, dry_run: bool = False) -> tuple[int, int]:
    logging.info("File Organizer started")
    if  not folder.exists():
        logging.error("Folder does not exist")
        return 0, 0
    if not folder.is_dir():
        logging.error("The path is not a directory")
        return 0, 0
    moved_count = 0
    failed_count = 0
    for item in folder.iterdir():
        if item.is_file():
            category = get_category(item.suffix)

            if dry_run:
                print(f"Would move {item.name} -> {category}")
                logging.info(f"DRY RUN | Would move {item.name} -> {category}")
                continue
            destination = folder / category
            destination.mkdir(exist_ok=True)
            try:
                shutil.move(item, destination)
                logging.info(f"Moved {item.name} -> {category}")
                moved_count += 1
            except Exception as e:
                logging.error(f"Could not move {item.name}: {e}")
                failed_count += 1
    if dry_run:
        print("Dry run completed. No files were moved.")
    logging.info(f"Finished. Moved {moved_count}, Failed {failed_count}")
    return moved_count, failed_count