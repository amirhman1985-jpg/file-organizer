from pathlib import Path
import json


def validate_config(config: dict) -> None:
    if "categories" not in config:
        raise ValueError("Config must contain 'categories'")

    categories = config["categories"]

    if not isinstance(categories, dict):
        raise ValueError("'categories' must be an object")

    for category, extensions in categories.items():
        if not isinstance(category, str) or not category.strip():
            raise ValueError(
                "Category names must be non-empty strings"
            )

        if not isinstance(extensions, list):
            raise ValueError(
                f"Extensions for '{category}' must be a list"
            )

        for extension in extensions:
            if not isinstance(extension, str):
                raise ValueError(
                    f"Extension in '{category}' must be a string"
                )

            if not extension.startswith("."):
                raise ValueError(
                    f"Invalid extension: {extension}"
                )


def load_config(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    validate_config(config)

    return config


def build_extension_mapping(config: dict) -> dict[str, str]:
    mapping: dict[str, str] = {}

    for category, extensions in config["categories"].items():
        for extension in extensions:
            mapping[extension.lower()] = category

    return mapping