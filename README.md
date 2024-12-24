# GitHub Release Notes Fetcher

A Python tool to fetch and organize release notes from GitHub repositories. Automatically detects and organizes releases for monorepos and single repositories.

## Features

- Fetches latest stable and pre-release notes from GitHub repositories
- Automatically detects monorepo artifacts from release tags
- Organizes release notes in a clean directory structure
- Configurable through environment variables, command line arguments, or config file
- Supports fetching complete release history
- Handles GitHub API rate limiting gracefully
- Avoids rewriting existing release notes

## Installation

1. Clone the repository:

```bash
git clone https://github.com/argakiig/pyMon.git
cd pyMon
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

The tool can be configureed in three ways(in order of priority):

1. Environment variables
2. Command line arguments
3. Configuration file

## Environment variables

### Required:
```bash
export GITHUB_REPOS="owner1/repo1,owner2/repo2"

```

### Optional:
```bash
export GITHUB_TOKEN=<your-github-token>
export GITHUB_RELEASES_DEBUG="true"
export GITHUB_RELEASES_HISTORY="true"
export ARTIFACTS_PATH="./artifacts"
```

## Command line arguments

```bash
python get_latest_releases.py \
--repos owner1/repo1,owner2/repo2 \
--artifacts-path ./release-notes \
--debug \
--history
```

## Configuration file

```bash
[repositories]
repos = owner1/repo1,owner2/repo2

[artifacts]
path = artifacts
history = true

[settings]
debug = true
```

## Usage

### Basic usage

#### Command line
```bash
python get_latest_releases.py \
--repos owner1/repo1,owner2/repo2
```

#### Configuration file

```bash
python get_latest_releases.py
```

#### Environment variables

```bash
export GITHUB_REPOS="owner1/repo1,owner2/repo2"
python get_latest_releases.py
```

### Output Structure

```bash
artifacts/
├── owner1/
│   ├── repo1/
│   │   ├── v0.0.1.md
│   │   ├── v0.0.1-rc.1.md
├── owner2/
│   ├── monorepo/
│   │   ├── artifacts1/
│   │   │   ├── v0.0.1.md
│   │   │   ├── v0.0.1-rc.1.md
│   │   ├── artifacts2/
│   │   │   ├── v0.0.1.md
│   │   │   ├── v0.0.1-rc.1.md
```

Each markdown file contains:
- Repo and Release info
- Release Type
- Complete Release Notes

### Artifact Detection

The tool automatically detects artifacts in monorepos by:
1. Analyzing release tag patterns (e.g., "artifact/v0.0.1-rc.1")
2. Creating appropriate directory Structures
3. Organizing release notes into the appropriate directories

No manual configuration is required for monorepos.

## Testing

The project includes a comprehensive test suite using pytest. Tests cover all major functionality including:
- Release fetching and parsing
- File operations
- Monorepo artifact detection
- Configuration handling
- Error cases

### Running Tests

1. Install test dependencies:
```bash
pip install pytest
```

2. Run the test suite:
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest test_release_fetcher.py

# Run specific test
pytest test_release_fetcher.py::test_history_mode
```

### Test Coverage

The test suite includes:
- Unit tests for core functionality
- Integration tests for file operations
- Parameterized tests for different release formats
- Mocked GitHub API responses to avoid rate limiting
- Temporary directory fixtures for safe file operations

### Adding New Tests

When adding new features, please ensure:
1. Test coverage for new functionality
2. Mocked external dependencies
3. Use of appropriate fixtures
4. Clear test documentation

## Notes

- Release notes are saved in markdown format
- Files are only written if they don't already exist
- Debug logging can be enabled for troubleshooting
- Artifacts are automatically detected from release tags
- Historical releases can be fetched with the `--history` flag or `history = true` setting