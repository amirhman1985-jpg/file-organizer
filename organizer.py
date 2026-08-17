from pathlib import Path
import shutil

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

def organize_files(folder: Path) -> int:
    if  not folder.exists():
        print("Folder does not exist")
        return 0
    if not folder.is_dir():
        print("The path is not a directory")
        return 0
    moved_count = 0
    for item in folder.iterdir():
        if item.is_file():
            suffix = item.suffix
            category = FILE_CATEGORIES.get(suffix, "Others")
            destination = folder / category
            destination.mkdir(exist_ok=True)
            shutil.move(item, destination)
            print(item.name, "->", category)
            moved_count += 1
    return moved_count

count = organize_files(Path("test_files_2"))
print("Total Files Moved:", count)