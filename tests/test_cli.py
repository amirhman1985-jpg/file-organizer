import base64
import json

import pytest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from file_organizer import license as license_module
from file_organizer.cli import (
    EXIT_CONFIG_ERROR,
    EXIT_LICENSE_ERROR,
    EXIT_OK,
    EXIT_OPERATION_ERROR,
    main,
)


@pytest.fixture
def test_license(tmp_path, monkeypatch):
    """
    Create a valid signed Pro license for CLI tests.
    """

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    public_key_b64 = base64.b64encode(
        public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode("ascii")

    license_data = {
        "license_id": "TEST-001",
        "product": "File Organizer",
        "publisher": "TechYarman",
        "customer": "Test User",
        "edition": "pro",
        "expires_at": None,
    }

    payload = json.dumps(
        license_data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    signature = private_key.sign(payload)

    license_data["signature"] = base64.b64encode(
        signature
    ).decode("ascii")

    license_file = tmp_path / "license.json"

    license_file.write_text(
        json.dumps(license_data),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        license_module,
        "PUBLIC_KEY_B64",
        public_key_b64,
    )

    return license_file

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
                "categories": categories,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_cli_success(
    tmp_path,
    capsys,
    test_license,
):
    config_file = tmp_path / "config.json"

    create_config(config_file)

    photo = tmp_path / "photo.jpg"
    photo.touch()

    result = main([
        str(tmp_path),
        "--config",
        str(config_file),
        "--license",
        str(test_license),
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
    test_license,
):
    config_file = tmp_path / "config.json"

    create_config(config_file)

    missing_folder = (
        tmp_path / "does_not_exist"
    )

    result = main([
        str(missing_folder),
        "--config",
        str(config_file),
        "--license",
        str(test_license),
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
    test_license,
):
    config_file = tmp_path / "config.json"

    create_config(config_file)

    result = main([
        "--config",
        str(config_file),
        "--license",
        str(test_license),
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
    test_license,
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
        "--license",
        str(test_license),
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
    test_license,
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
        "--license",
        str(test_license),
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
    test_license,
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
        "--license",
        str(test_license),
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
    test_license,
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
        "--license",
        str(test_license),
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
    test_license,
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
        "--license",
        str(test_license),
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
    test_license,
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
        "--license",
        str(test_license),
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
    assert "0.3.1" in captured.out


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

    assert result == EXIT_OK
    assert (
        tmp_path
        / "Images"
        / "photo.jpg"
    ).exists()


def test_free_rejects_custom_config(tmp_path):
    config = tmp_path / "custom.json"
    config.write_text(
        "{}",
        encoding="utf-8",
    )

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
        main(
            ["--version"],
            edition="free",
        )

    assert exc_info.value.code == 0

    captured = capsys.readouterr()

    assert (
        "FileOrganizer Free 0.3.1"
        in captured.out
    )


def test_free_rejects_recursive():
    with pytest.raises(SystemExit) as exc_info:
        main(
            ["--recursive"],
            edition="free",
        )

    assert exc_info.value.code == 2


def test_free_rejects_dry_run():
    with pytest.raises(SystemExit) as exc_info:
        main(
            ["--dry-run"],
            edition="free",
        )

    assert exc_info.value.code == 2


def test_pro_accepts_recursive(
    tmp_path,
    test_license,
):
    result = main(
        [
            str(tmp_path),
            "--recursive",
            "--license",
            str(test_license),
        ],
        edition="pro",
    )

    assert result == EXIT_OK


def test_pro_accepts_dry_run(
    tmp_path,
    test_license,
):
    result = main(
        [
            str(tmp_path),
            "--dry-run",
            "--license",
            str(test_license),
        ],
        edition="pro",
    )

    assert result == EXIT_OK


def test_pro_requires_license(
    tmp_path,
    capsys,
):
    result = main(
        [str(tmp_path)],
        edition="pro",
    )

    captured = capsys.readouterr()

    assert result == EXIT_LICENSE_ERROR
    assert "License error" in captured.err
