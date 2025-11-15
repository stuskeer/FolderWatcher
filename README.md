# FolderWatcher

Python folder watcher that logs when new files appear in a directory and delegates file processing (move / clean) to a small processor module.

## What this repo contains

- `watcher.py` — main watcher. Uses `watchdog` to watch a directory, waits for files to settle, logs events, and calls the processor.
- `processors/file_processor.py` — small processing hook (moves files to the configured processed directory). Extend this for cleaning, validation, uploads, etc.
- `tests/` — comprehensive unit tests for the watcher and file processor.
- `requirements.txt` — runtime dependencies (`watchdog`, `pytest`).
- `.gitignore` — ignores the `.venv/` directory.

## Defaults

- Watched directory (default): `D:\Data Engineering\Data\DataIn`
- Processed directory (default): `D:\Data Engineering\Data\Processed`
- Log directory (default): `D:\Data Engineering\Data\Logs`
- Log file: `D:\Data Engineering\Data\Logs\folder_watcher.log`

These defaults are set as constants at the top of `watcher.py`. You can edit those values if you prefer to hardcode paths instead of passing CLI arguments.

## Setup (Windows PowerShell)

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks script activation, allow local scripts once (administrator not required for CurrentUser scope):

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

2. Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Running the watcher

Run with the defaults (paths defined in `watcher.py`):

```powershell
python watcher.py
```

Or override any path from the command line:

```powershell
python watcher.py --path "D:\Data Engineering\Data\DataIn" --logdir "D:\Data Engineering\Data\Logs" --processed "D:\Data Engineering\Data\Processed"
```

## Running tests

The project includes a comprehensive test suite covering both the watcher and file processor modules.

**Run all tests:**

```powershell
pytest
```

**Run tests with verbose output:**

```powershell
pytest -v
```

**Run a specific test file:**

```powershell
pytest tests/test_watcher.py -v
pytest tests/test_file_processor.py -v
```

**Run a specific test class:**

```powershell
pytest tests/test_watcher.py::TestSetupLogger -v
```

**Run a specific test:**

```powershell
pytest tests/test_watcher.py::TestSetupLogger::test_setup_logger_creates_file -v
```

**Run tests with coverage report:**

```powershell
pip install pytest-cov
pytest --cov=. --cov-report=html
```

The test suite includes 24 tests covering:
- File processor logic (moves, duplicates, extensions, errors)
- Logger configuration and rotation
- Argument parsing
- File stability detection
- Error handling and edge cases

## How processing works

The watcher delegates processing to `processors.file_processor.process_new_file(path, processed_dir, logger)` once the file appears to be stable. Current behavior:

- `process_new_file` creates the `processed_dir` (if needed) and moves the file there.
- If a file with the same name already exists in `processed_dir`, it appends a numeric suffix (`-1`, `-2`, ...) to avoid overwriting.

Keep processing logic in `processors/file_processor.py`. That keeps the watcher small and makes it easy to add cleaning, validation, or uploads later.

## Notes & common pitfalls

- If `processed_dir` is a subdirectory of the watched directory, the move operation may trigger another event. To avoid this either:
  - Put `processed_dir` outside the watched path (recommended), or
  - Add logic to ignore events originating from `processed_dir` (easy to add in the handler).
- The watcher uses a basic "settle" heuristic (checks file size repeatedly) to avoid handling partially-written files. You can tune `--settle` and `--tries` on the CLI.
- Logs are rotated with `RotatingFileHandler` to prevent unbounded growth.

## Troubleshooting

- Missing `watchdog`: install with:

```powershell
python -m pip install watchdog
```
- Missing `pytest`: install with:

```powershell
python -m pip install pytest
```
- Permissions: Ensure the account running the watcher has read/write/delete access to the watched and processed directories.
