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