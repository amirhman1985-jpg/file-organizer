from file_organizer.config import (
    load_config,
    build_extension_mapping,
    validate_config,
)
import pytest


def test_load_config(tmp_path):
    config_file = tmp_path / "config.json"

    config_file.write_text(
        """
        {
            "categories": {
                "Images": [".jpg", ".png"]
            }
        }
        """,
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert "categories" in config
    assert config["categories"]["Images"] == [".jpg", ".png"]

def test_build_extension_mapping():
    config = {
        "categories": {
            "Images": [".jpg", ".png"],
            "Documents": [".pdf"]
        }
    }

    mapping = build_extension_mapping(config)

    assert mapping[".jpg"] == "Images"
    assert mapping[".png"] == "Images"
    assert mapping[".pdf"] == "Documents"

def test_build_extension_mapping_custom_category():
    config = {
        "categories": {
            "Images": [".jpg"],
            "Design": [".psd", ".fig"],
        }
    }

    mapping = build_extension_mapping(config)

    assert mapping[".psd"] == "Design"
    assert mapping[".fig"] == "Design"

def test_invalid_config_missing_categories():
    with pytest.raises(ValueError):
        validate_config({})

def test_invalid_config_categories_not_dict():
    with pytest.raises(ValueError):
        validate_config({"categories": []})

def test_invalid_extension():
    with pytest.raises(ValueError):
        validate_config({
            "categories": {
                "Images": ["jpg"]
            }
        })

def test_invalid_extensions_type():
    with pytest.raises(ValueError):
        validate_config({
            "categories": {
                "Images": ".jpg"
            }
        })
