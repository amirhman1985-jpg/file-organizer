from file_organizer.cli import main as cli_main


def main(argv: list[str] | None = None) -> int:
    return cli_main(argv, edition="free")


if __name__ == "__main__":
    raise SystemExit(main())