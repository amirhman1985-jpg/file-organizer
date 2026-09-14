# File Organizer

A lightweight Windows utility for automatically organizing files by extension using configurable rules.

**Official website:** https://techyarman.ir/

**Download:** https://techyarman.ir/download.html

## What it does

File Organizer scans a selected folder and organizes files into category folders based on their file extensions. It is designed for common cleanup tasks such as Downloads, Desktop, and other file-heavy directories.

## Features

- Organize files by extension
- Recursive directory scanning with `--recursive`
- Preview changes safely with `--dry-run`
- Configurable categories and extensions through JSON
- Conflict handling with `rename` or `skip`
- Automatic duplicate filename handling
- List configured categories with `--list-categories`
- Configuration validation
- Operation logging
- Windows x64 executable support
- Automated test suite

## Requirements

### Packaged Windows version

- Windows 10 or Windows 11
- 64-bit Windows (x64)

The packaged release is designed to run without a separate Python installation.

### Development

- Python 3.10+

## Quick start

Download the latest Windows package from the official website:

https://techyarman.ir/download.html

Extract the ZIP and open PowerShell in the extracted folder.

Preview changes before moving anything:

```powershell
.\FileOrganizerPro.exe "C:\Users\YourName\Downloads" --config .\config.json --dry-run
```

Run the organization:

```powershell
.\FileOrganizerPro.exe "C:\Users\YourName\Downloads" --config .\config.json
```

Include files inside subdirectories:

```powershell
.\FileOrganizerPro.exe "C:\Users\YourName\Downloads" --config .\config.json --recursive
```

See all configured categories and extensions:

```powershell
.\FileOrganizerPro.exe --list-categories --config .\config.json
```

## Command-line options

```text
positional arguments:
  folder                Path to the folder that should be organized

options:
  -h, --help             Show help and exit
  --version              Show program's version number and exit
  --about                Show product and publisher information
  --config CONFIG        Path to configuration file
  --dry-run              Preview changes without moving files
  --recursive            Include files inside subdirectories
  --on-conflict {rename,skip}
                         How to handle files with an existing destination
  --list-categories      List configured categories and extensions
  --license LICENSE      Path to Pro license file
```

## Free and Pro

File Organizer is distributed in Free and Pro editions.

See the official website for the current edition details and downloads:

https://techyarman.ir/product.html

## Security and integrity

For release packages, the official website publishes the SHA-256 checksum so you can verify that the downloaded ZIP matches the published release.

Do not run modified executables or packages from unofficial mirrors unless you trust the source.

## License

This repository contains proprietary software by TechYarman. See [`LICENSE.txt`](LICENSE.txt) for the applicable license terms.

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md) for project history.

## Support

For documentation and product information:

https://techyarman.ir/help.html

For the latest download information:

https://techyarman.ir/download.html
