# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Winget install handler — downloads packages via Windows Package Manager."""

import shutil
import subprocess
from pathlib import Path

from ..parsers import ParsedCommand, ToolType


class WingetHandler:
    TOOL = ToolType.WINGET

    @staticmethod
    def is_available() -> bool:
        return shutil.which("winget") is not None

    @staticmethod
    def run(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        spec, name = cmd.args
        dest = output_dir / "winget" / name
        dest.mkdir(parents=True, exist_ok=True)

        emit("info", f"Downloading winget package: {spec} ...")
        try:
            proc = subprocess.run(
                ["winget", "download", spec, "--download-directory", str(dest),
                 "--accept-package-agreements", "--accept-source-agreements"],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if proc.returncode != 0:
                emit("error", proc.stderr.strip() or "winget download failed")
                return {"success": False, "path": str(dest), "error": proc.stderr.strip(),
                        "install_hint_sh": f"echo 'Use .bat script on Windows for {name}'",
                        "install_hint_bat": f"winget install --source \"{dest}\""}

            files = list(dest.rglob("*"))
            emit("success", f"Downloaded {len(files)} file(s) to {dest}")
            return {"success": True, "path": str(dest),
                    "install_hint_sh": f"echo 'Use .bat script on Windows for {name}'",
                    "install_hint_bat": f"winget install --source \"{dest}\""}
        except FileNotFoundError:
            emit("error", "winget not found. Requires Windows Package Manager.")
            return {"success": False, "path": str(dest), "error": "winget not found",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except subprocess.TimeoutExpired:
            emit("error", "winget download timed out (600s)")
            return {"success": False, "path": str(dest), "error": "timeout",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except Exception as e:
            emit("error", str(e))
            return {"success": False, "path": str(dest), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
