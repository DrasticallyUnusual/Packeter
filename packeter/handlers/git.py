# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Git clone handler."""

import shutil
import subprocess
from pathlib import Path

from ..parsers import ParsedCommand, ToolType


class GitHandler:
    TOOL = ToolType.GIT

    @staticmethod
    def is_available() -> bool:
        return shutil.which("git") is not None

    @staticmethod
    def run(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        url, name = cmd.args
        dest = output_dir / name

        if dest.exists():
            emit("warning", f"Destination already exists: {dest}")
            return {"success": False, "path": str(dest), "error": "destination exists",
                    "install_hint_sh": "", "install_hint_bat": ""}

        emit("info", f"Cloning {url} ...")
        try:
            proc = subprocess.run(
                ["git", "clone", "--depth", "1", url, str(dest)],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if proc.returncode != 0:
                emit("error", proc.stderr.strip() or "git clone failed")
                return {"success": False, "path": str(dest), "error": proc.stderr.strip(),
                        "install_hint_sh": "", "install_hint_bat": ""}

            emit("success", f"Cloned to {dest}")
            return {"success": True, "path": str(dest),
                    "install_hint_sh": f'echo "  -> Ready at ./{name}"',
                    "install_hint_bat": f'echo   -> Ready at .\\{name}'}
        except subprocess.TimeoutExpired:
            emit("error", "Git clone timed out (600s)")
            return {"success": False, "path": str(dest), "error": "timeout",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except Exception as e:
            emit("error", str(e))
            return {"success": False, "path": str(dest), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
