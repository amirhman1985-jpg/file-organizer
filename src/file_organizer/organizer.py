from pathlib import Path
from dataclasses import dataclass
import shutil
import logging

logging.basicConfig(
    filename="File_organizer.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

@dataclass
class OrganizeResult:
    moved: int = 0
    skipped: int = 0
    failed: int = 0

def get_category(
        suffix: str,
        categoreis:dict[str, str],
) -> str:
    return categoreis.get(suffix.lower(), "Others" )

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

def resolve_destination(
    destination: Path,
    filename: str,
    on_conflict: str
) -> Path | None:
    if on_conflict not in {"rename", "skip"}:
        raise ValueError(
            f"Unsupported conflict policy: {on_conflict}"
        )

    target = destination / filename

    if not target.exists():
        return target

    if on_conflict == "rename":
        return get_unique_destination(destination, filename)

    return None

def organize_files(
    folder: Path,
    categories: dict[str, str],
    dry_run: bool = False,
    recursive: bool = False,
    on_conflict: str = "rename",
    exclude_paths: set[Path] | None = None,
) -> OrganizeResult:

    excluded = {
    path.resolve()
    for path in (exclude_paths or set())
}

    logging.info("File Organizer started")

    if not folder.exists():
        logging.error("Folder does not exist")
        return OrganizeResult()

    if not folder.is_dir():
        logging.error("The path is not a directory")
        return OrganizeResult()

    result = OrganizeResult()

    destination_dirs = {
        folder / category
        for category in set(categories.values()) | {"Others"}
    }

    if recursive:
        items = list(folder.rglob("*"))
    else:
        items = list(folder.iterdir())

    for item in items:
        if not item.is_file():
            continue
        if item.resolve() in excluded:
            logging.info(f"Excluded {item}")
            continue

        if any(
            destination_dir in item.parents
            for destination_dir in destination_dirs
        ):
            continue

        category = get_category(item.suffix, categories)

        if dry_run:
            print(f"Would move {item} -> {category}")
            logging.info(
                f"DRY RUN | Would move {item} -> {category}"
            )
            continue

        destination = folder / category
        destination.mkdir(exist_ok=True)

        try:
            target = resolve_destination(
                destination,
                item.name,
                on_conflict,
            )

            if target is None:
                logging.info(f"Skipped {item}")
                result.skipped += 1
                continue

            shutil.move(item, target)

            logging.info(f"Moved {item} -> {target}")
            result.moved += 1

        except Exception as e:
            logging.error(f"Could not move {item}: {e}")
            result.failed += 1

    if dry_run:
        print("Dry run completed. No files were moved.")

    logging.info(
        f"Finished. Moved {result.moved}, "
        f"Skipped {result.skipped}, "
        f"Failed {result.failed}"
    )

    return result
