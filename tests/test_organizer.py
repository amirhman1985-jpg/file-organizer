from file_organizer.organizer import get_category, organize_files
def test_jpg_category():
    assert get_category(".jpg") == "Images"

def test_ai_category():
    assert get_category(".ai") == "Vectors"

def test_unknown_category():
    assert get_category(".xyz") == "Others"

def test_organize_jpg(tmp_path):
    file = tmp_path / "photo.jpg"
    file.touch()

    moved, failed = organize_files(tmp_path)

    assert moved == 1
    assert failed == 0
    assert (tmp_path / "Images" / "photo.jpg").exists()

def test_dry_run(tmp_path):
    file = tmp_path / "photo.jpg"
    file.touch()

    moved, failed = organize_files(tmp_path, dry_run=True)

    assert moved == 0
    assert failed == 0
    assert file.exists()
    assert not (tmp_path / "Images" / "photo.jpg").exists()

def test_dry_run_multiple_files(tmp_path):
    files = [
        tmp_path / "photo.jpg",
        tmp_path / "book.pdf",    
        tmp_path / "design.ai"
    ]
    for file in files:
        file.touch()
        
    moved, failed = organize_files(tmp_path, dry_run=True)

    assert moved == 0
    assert failed == 0

    for file in files:
        assert file.exists()

    assert not (tmp_path / "Images" / "photo.jpg").exists()
    assert not (tmp_path / "Documents" / "book.pdf").exists()
    assert not (tmp_path / "Vectors" / "design.ai").exists()