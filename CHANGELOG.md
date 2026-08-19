# Changelog

All notable changes to File Organizer are documented in this file.

## [0.2.0] - 2026-08-19

### Added

* Windows executable build with PyInstaller
* Command-line interface
* `--dry-run` preview mode
* Recursive file organization with `--recursive`
* Conflict handling with `rename` and `skip` policies
* Automatic duplicate filename handling
* JSON-based configuration
* Custom file extension categories
* Configuration validation
* `--config` option for custom configuration files
* `--list-categories` command
* `--version` command
* CLI error handling and exit codes
* File operation logging
* Automated test suite with pytest
* Windows release package

### Improved

* Separated CLI, configuration, and file organization logic
* Added `OrganizeResult` for tracking moved, skipped, and failed files
* Prevented configuration files and destination directories from being reprocessed
* Added type hints and structured project packaging with `pyproject.toml`

### Testing

* 33 automated tests passing
* Tested packaged Windows executable independently from the development environment

### Release

* Version: `0.2.0`
* Platform: Windows x64
* Packaging: PyInstaller `--onedir`
