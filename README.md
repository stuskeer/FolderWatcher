# FolderWatcher

Simple Python folder watcher that logs when new files appear in a directory.

Defaults
- Watched directory: `D:\Data Engineering\Data\DataIn`
- Log directory: `D:\Data Engineering\Data\Logs`
- Log file: `D:\Data Engineering\Data\Logs\folder_watcher.log`

Setup (Windows PowerShell)

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution you can allow local scripts once:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

2. Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Run the watcher (example):

```powershell
python watcher.py
```

Notes
- The script uses `watchdog` to get efficient filesystem events.
- It includes a small heuristic that waits for the new file size to stabilize before logging, to reduce false positives from partially written files.
- The watcher creates the watch and log directories if they don't exist.

Troubleshooting
- If you see the message about `watchdog` missing, install it with:

```powershell
python -m pip install watchdog
```
