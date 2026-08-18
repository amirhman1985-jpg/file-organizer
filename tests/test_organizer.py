from file_organizer.organizer import get_category, organize_files, get_unique_destination, resolve_destination
import pytest
def test_jpg_category():
    assert get_category(".jpg") == "Images"

def test_ai_category():
    assert get_category(".ai") == "Vectors"

def test_unknown_category():
    assert get_category(".xyz") == "Others"

def test_organize_jpg(tmp_path):
    file = tmp_path / "photo.jpg"
    file.touch()

    result = organize_files(tmp_path)

    assert result.moved == 1
    assert result.failed == 0
    assert result.skipped == 0
    assert (tmp_path / "Images" / "photo.jpg").exists()

def test_dry_run(tmp_path):
    file = tmp_path / "photo.jpg"
    file.touch()

    result = organize_files(tmp_path, dry_run=True)

    assert result.moved == 0
    assert result.failed == 0
    assert result.skipped == 0

def test_dry_run_multiple_files(tmp_path):
    files = [
        tmp_path / "photo.jpg",
        tmp_path / "book.pdf",    
        tmp_path / "design.ai"
    ]
    for file in files:
        file.touch()
        
    result = organize_files(tmp_path, dry_run=True)

    assert result.moved == 0
    assert result.failed == 0
    assert result.skipped == 0

    for file in files:
        assert file.exists()

    assert not (tmp_path / "Images" / "photo.jpg").exists()
    assert not (tmp_path / "Documents" / "book.pdf").exists()
    assert not (tmp_path / "Vectors" / "design.ai").exists()

def test_recursive_organize(tmp_path):
    projects = tmp_path / "Projects"
    backup = tmp_path / "Backup"

    projects.mkdir()
    backup.mkdir()

    files = [
        tmp_path / "photo.jpg",
        projects / "design.ai",
        projects / "report.pdf",
        backup / "archive.zip",
    ]

    for file in files:
        file.touch()

    result = organize_files(
        tmp_path,
        recursive=True
    )

    assert result.moved == 4
    assert result.failed == 0
    assert result.skipped == 0

    assert (tmp_path / "Images" / "photo.jpg").exists()
    assert (tmp_path / "Vectors" / "design.ai").exists()
    assert (tmp_path / "Documents" / "report.pdf").exists()
    assert (tmp_path / "Archives" / "archive.zip").exists()

def test_unique_destination_when_file_exists(tmp_path):
    destination = tmp_path / "Images"
    destination.mkdir()

    existing = destination / "photo.jpg"
    existing.touch()

    result = get_unique_destination(destination, "photo.jpg")

    assert result == destination / "photo_1.jpg"


def test_unique_destination_when_multiple_files_exist(tmp_path):
    destination = tmp_path / "Images"
    destination.mkdir()

    (destination / "photo.jpg").touch()
    (destination / "photo_1.jpg").touch()
    (destination / "photo_2.jpg").touch()

    result = get_unique_destination(destination, "photo.jpg")

    assert result == destination / "photo_3.jpg"

def test_organize_duplicate_file(tmp_path):
    image_dir = tmp_path / "Images"
    image_dir.mkdir()

    existing = image_dir / "photo.jpg"
    existing.touch()

    new_file = tmp_path / "photo.jpg"
    new_file.touch()

    result = organize_files(tmp_path)

    assert result.moved == 1
    assert result.failed == 0
    assert result.skipped == 0
    assert (image_dir / "photo.jpg").exists()
    assert (image_dir / "photo_1.jpg").exists()

def test_conflict_rename(tmp_path):
    destination = tmp_path / "Images"
    destination.mkdir()

    existing = destination / "photo.jpg"
    existing.touch()

    new_file = tmp_path / "photo.jpg"
    new_file.touch()

    result = organize_files(
        tmp_path,
        on_conflict="rename"
    )

    assert result.moved == 1
    assert result.failed == 0
    assert result.skipped == 0
    assert (destination / "photo.jpg").exists()
    assert (destination / "photo_1.jpg").exists()


def test_conflict_skip(tmp_path):
    destination = tmp_path / "Images"
    destination.mkdir()

    existing = destination / "photo.jpg"
    existing.touch()

    new_file = tmp_path / "photo.jpg"
    new_file.touch()

    result = organize_files(
        tmp_path,
        on_conflict="skip"
    )

    assert result.moved == 0
    assert result.failed == 0
    assert result.skipped == 1
    assert existing.exists()
    assert new_file.exists()

def test_invalid_conflict_policy(tmp_path):
    destination = tmp_path / "Images"
    destination.mkdir()

    with pytest.raises(ValueError):
        resolve_destination(
            destination,
            "photo.jpg",
            "invalid"
        )