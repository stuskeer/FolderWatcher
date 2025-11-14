from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from processors.file_processor import process_new_file

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except Exception:  # watchdog not available
    print("Required package 'watchdog' is not installed. Install with: python -m pip install watchdog")
    sys.exit(1)


class NewFileHandler(FileSystemEventHandler):
    def __init__(
        self,
        logger: logging.Logger,
        processed_dir: str | None = None,
        settle_seconds: float = 0.5,
        max_tries: int = 10,
    ) -> None:
        super().__init__()
        self.logger = logger
        self.processed_dir = processed_dir
        self.settle_seconds = settle_seconds
        self.max_tries = max_tries

    def on_created(self, event):
        # Ignore directories
        if event.is_directory:
            return

        path = event.src_path

        # Wait for file size to stabilize (basic heuristic to avoid partial-write events)
        prev_size = -1
        stable = False
        for _ in range(self.max_tries):
            try:
                size = os.path.getsize(path)
            except OSError:
                size = -1
            if size == prev_size and size != -1:
                stable = True
                break
            prev_size = size
            time.sleep(self.settle_seconds)

        if not stable:
            # Still log it — better to have the event than miss it entirely
            self.logger.info("New file detected (may be incomplete): %s", path)
        else:
            self.logger.info("New file detected: %s", path)

        # Delegate processing (move/clean) to processors.file_processor
        try:
            if self.processed_dir:
                dest = process_new_file(path, processed_dir=self.processed_dir, logger=self.logger)
                self.logger.info("Processed file: %s", dest)
            else:
                self.logger.info("No processed_dir configured; skipping processing for %s", path)
        except Exception:
            self.logger.exception("Error processing file %s", path)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def setup_logger(logfile: str) -> logging.Logger:
    logger = logging.getLogger("folder_watcher")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    # Rotating file handler to avoid unbounded log growth
    handler = RotatingFileHandler(logfile, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Also log to console for immediate feedback
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


# Edit these defaults as needed (Windows paths)
DEFAULT_WATCH_PATH = r"D:\Data Engineering\Data\DataIn"
DEFAULT_LOG_DIR = r"D:\Data Engineering\Data\Logs"
DEFAULT_PROCESSED_DIR = r"D:\Data Engineering\Data\Processed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch a folder for new files and log events")
    parser.add_argument(
        "--path", "-p",
        default=DEFAULT_WATCH_PATH,
        help=f"Directory to watch (default {DEFAULT_WATCH_PATH})"
    )
    parser.add_argument(
        "--logdir", "-l",
        default=DEFAULT_LOG_DIR,
        help=f"Directory to write logs to (default {DEFAULT_LOG_DIR})"
    )
    parser.add_argument(
        "--processed", "-d",
        default=DEFAULT_PROCESSED_DIR,
        help=f"Directory to move processed files to (default {DEFAULT_PROCESSED_DIR})"
    )
    parser.add_argument("--settle", type=float, default=0.5, help="Seconds to wait between file-size checks for settle heuristic")
    parser.add_argument("--tries", type=int, default=10, help="Number of settle checks before giving up")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    watch_path = os.path.abspath(args.path)
    log_dir = os.path.abspath(args.logdir)
    processed_dir = os.path.abspath(args.processed)

    ensure_dir(watch_path)
    ensure_dir(log_dir)
    ensure_dir(processed_dir)

    logfile = os.path.join(log_dir, "folder_watcher.log")
    logger = setup_logger(logfile)

    logger.info("Starting folder watcher")
    logger.info("Watching: %s", watch_path)
    logger.info("Logging to: %s", logfile)
    logger.info("Processed dir: %s", processed_dir)

    event_handler = NewFileHandler(logger, processed_dir=processed_dir, settle_seconds=args.settle, max_tries=args.tries)
    observer = Observer()
    observer.schedule(event_handler, watch_path, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown requested, stopping observer")
        observer.stop()
    observer.join()
    logger.info("Stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
