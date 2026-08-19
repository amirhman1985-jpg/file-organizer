import json
import pytest

from file_organizer.cli import (
    EXIT_CONFIG_ERROR,
    EXIT_OK,
    EXIT_OPERATION_ERROR,
    main,
)


def create_config(
    path,
    categories=None,
):
    if categories is None:
        categories = {
            "Images": [
                ".jpg",
                ".png",
            ],
            "Documents": [
                ".pdf",
            ],
            "Vectors": [
                ".ai",
            ],
            "Others": [],
        }

    path.write_text(
        json.dumps(
            {
                "categories": categories
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_cli_success(
    tmp_path,
    capsys,
):
    config_file = tmp_path / "config.json"

    create_config(
        config_file
    )

    photo = tmp_path / "photo.jpg"
    photo.touch()

    result = main([
        str(tmp_path),
        "--config",
        str(config_file),
    ])

    captured = capsys.readouterr()

    assert result == EXIT_OK
    assert "Moved   : 1" in captured.out
    assert "Skipped : 0" in captured.out
    assert "Failed  : 0" in captured.out

    assert (
        tmp_path
        / "Images"
        / "photo.jpg"
    ).exists()


def test_cli_missing_folder(
    tmp_path,
    capsys,
):
    config_file = tmp_path / "config.json"

    create_config(
        config_file
    )

    missing_folder = (
        tmp_path / "does_not_exist"
    )

    result = main([
        str(missing_folder),
        "--config",
        str(config_file),
    ])

    captured = capsys.readouterr()

    assert result == EXIT_CONFIG_ERROR

    assert (
        "Folder does not exist"
        in captured.err
    )


def test_cli_missing_folder_argument(
    tmp_path,
    capsys,
):
    config_file = tmp_path / "config.json"

    create_config(
        config_file
    )

    result = main([
        "--config",
        str(config_file),
    ])

    captured = capsys.readouterr()

    assert result == EXIT_CONFIG_ERROR

    assert (
        "folder is required"
        in captured.err
    )


def test_cli_invalid_config(
    tmp_path,
    capsys,
):
    config_file = (
        tmp_path / "broken.json"
    )

    config_file.write_text(
        '{"wrong_key": {}}',
        encoding="utf-8",
    )

    result = main([
        str(tmp_path),
        "--config",
        str(config_file),
    ])

    captured = capsys.readouterr()

    assert result == EXIT_CONFIG_ERROR

    assert (
        "Config must contain 'categories'"
        in captured.err
    )


def test_cli_dry_run(
    tmp_path,
    capsys,
):
    config_file = (
        tmp_path / "config.json"
    )

    create_config(
        config_file
    )

    photo = tmp_path / "photo.jpg"
    photo.touch()

    result = main([
        str(tmp_path),
        "--config",
        str(config_file),
        "--dry-run",
    ])

    captured = capsys.readouterr()

    assert result == EXIT_OK
    assert "Moved   : 0" in captured.out
    assert "Skipped : 0" in captured.out
    assert "Failed  : 0" in captured.out

    assert photo.exists()

    assert not (
        tmp_path
        / "Images"
        / "photo.jpg"
    ).exists()


def test_cli_recursive(
    tmp_path,
    capsys,
):
    config_file = (
        tmp_path / "config.json"
    )

    create_config(
        config_file
    )

    nested = (
        tmp_path / "Projects"
    )

    nested.mkdir()

    design = (
        nested / "design.ai"
    )

    design.touch()

    result = main([
        str(tmp_path),
        "--config",
        str(config_file),
        "--recursive",
    ])

    captured = capsys.readouterr()

    assert result == EXIT_OK
    assert "Moved   : 1" in captured.out

    assert (
        tmp_path
        / "Vectors"
        / "design.ai"
    ).exists()


def test_cli_conflict_skip(
    tmp_path,
    capsys,
):
    config_file = (
        tmp_path / "config.json"
    )

    create_config(
        config_file
    )

    image_dir = (
        tmp_path / "Images"
    )

    image_dir.mkdir()

    existing = (
        image_dir / "photo.jpg"
    )

    existing.touch()

    new_file = (
        tmp_path / "photo.jpg"
    )

    new_file.touch()

    result = main([
        str(tmp_path),
        "--config",
        str(config_file),
        "--on-conflict",
        "skip",
    ])

    captured = capsys.readouterr()

    assert result == EXIT_OK
    assert "Moved   : 0" in captured.out
    assert "Skipped : 1" in captured.out
    assert "Failed  : 0" in captured.out

    assert existing.exists()
    assert new_file.exists()


def test_cli_list_categories(
    tmp_path,
    capsys,
):
    config_file = (
        tmp_path / "config.json"
    )

    create_config(
        config_file,
        {
            "Images": [
                ".jpg",
                ".png",
            ],
            "Design": [
                ".psd",
                ".fig",
            ],
        },
    )

    result = main([
        "--config",
        str(config_file),
        "--list-categories",
    ])

    captured = capsys.readouterr()

    assert result == EXIT_OK

    assert "Images" in captured.out
    assert ".jpg" in captured.out
    assert ".png" in captured.out

    assert "Design" in captured.out
    assert ".psd" in captured.out
    assert ".fig" in captured.out


def test_cli_list_categories_without_folder(
    tmp_path,
    capsys,
):
    config_file = (
        tmp_path / "config.json"
    )

    create_config(
        config_file
    )

    result = main([
        "--config",
        str(config_file),
        "--list-categories",
    ])

    captured = capsys.readouterr()

    assert result == EXIT_OK
    assert "Images" in captured.out


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "0.2.1" in captured.out

def test_cli_invalid_operation_code():
    """
    Placeholder for a future test that
    simulates a failed file operation.
    """

    assert EXIT_OPERATION_ERROR == 2

def test_free_edition(tmp_path):
    file = tmp_path / "photo.jpg"
    file.touch()

    result = main(
        [str(tmp_path)],
        edition="free",
    )

    assert result == 0
    assert (tmp_path / "Images" / "photo.jpg").exists()


def test_free_rejects_custom_config(tmp_path):
    config = tmp_path / "custom.json"
    config.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit):
        main(
            [
                str(tmp_path),
                "--config",
                str(config),
            ],
            edition="free",
        )

def test_free_edition_uses_free_features(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"], edition="free")

    assert exc_info.value.code == 0

    captured = capsys.readouterr()

    assert "FileOrganizer Free 0.2.1" in captured.out

def test_free_rejects_recursive():
    with pytest.raises(SystemExit) as exc_info:
        main(["--recursive"], edition="free")

    assert exc_info.value.code == 2


def test_free_rejects_dry_run():
    with pytest.raises(SystemExit) as exc_info:
        main(["--dry-run"], edition="free")

    assert exc_info.value.code == 2

def test_pro_accepts_recursive(tmp_path):
    result = main(
        [str(tmp_path), "--recursive"],
        edition="pro",
    )

    assert result == 0

def test_pro_accepts_dry_run(tmp_path):
    result = main(
        [str(tmp_path), "--dry-run"],
        edition="pro",
    )

    assert result == 0