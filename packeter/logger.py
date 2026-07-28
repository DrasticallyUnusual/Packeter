# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Logging utilities for Packeter — Query.log and Log.log."""

import datetime
from pathlib import Path


def _ts() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _fmt_size(size_bytes: int) -> str:
    if size_bytes > 1_048_576:
        return f"{size_bytes / 1_048_576:.1f} MB"
    if size_bytes > 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


class PacketerLogger:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._query_path = self.output_dir / "Query.log"
        self._log_path = self.output_dir / "Log.log"

    def set_output_dir(self, path: Path):
        self.output_dir = path
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._query_path = self.output_dir / "Query.log"
        self._log_path = self.output_dir / "Log.log"

    def log_query(self, source: str):
        line = f"{_ts()} - {source}\n"
        with open(self._query_path, "a", encoding="utf-8") as f:
            f.write(line)

    def log_download(self, url: str, filename: str, filepath: str):
        size_bytes = 0
        p = Path(filepath)
        if p.exists():
            size_bytes = p.stat().st_size
        size_str = _fmt_size(size_bytes)
        line = f"{url} - {filename} - {size_str} - {filepath} - {_ts()}\n"
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(line)
