from dataclasses import dataclass


@dataclass(frozen=True)
class EditionFeatures:
    name: str
    recursive: bool
    dry_run: bool
    custom_config: bool
    list_categories: bool
    conflict_policies: tuple[str, ...]


FREE_FEATURES = EditionFeatures(
    name="Free",
    recursive=False,
    dry_run=False,
    custom_config=False,
    list_categories=False,
    conflict_policies=("rename",),
)


PRO_FEATURES = EditionFeatures(
    name="Pro",
    recursive=True,
    dry_run=True,
    custom_config=True,
    list_categories=True,
    conflict_policies=("rename", "skip"),
)