"""File processing utilities for FolderWatcher.

This module exposes a single function `process_new_file` that moves a completed
file to a configured processed directory and returns the destination path.

Extend this file to add cleaning, validation, parsing, or upload logic.
"""
from __future__ import annotations

import os
import shutil
from typing import Optional


def process_new_file(path: str, processed_dir: str, logger: Optional[object] = None) -> str:
    """Move `path` into `processed_dir` and return the destination path.

    - Creates `processed_dir` if needed.
    - Avoids overwriting existing files by adding a numeric suffix when necessary.
    - Logs via `logger` if provided.
    """
    os.makedirs(processed_dir, exist_ok=True)
    dest = os.path.join(processed_dir, os.path.basename(path))

    # Avoid overwrite by adding numeric suffix
    if os.path.exists(dest):
        base, ext = os.path.splitext(dest)
        i = 1
        while True:
            candidate = f"{base}-{i}{ext}"
            if not os.path.exists(candidate):
                dest = candidate
                break
            i += 1

    shutil.move(path, dest)

    if logger:
        try:
            logger.info("Moved file to processed dir: %s", dest)
        except Exception:
            # Keep processing tolerant to logger failures
            pass

    return dest
