# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Chocolatey install handler — downloads packages via Choco."""

import shutil
import subprocess
from pathlib import Path

from ..parsers import ParsedCommand, ToolType


class ChocoHandler:
    TOOL = ToolType.CHOCO

    @staticmethod
    def is_available() -> bool:
        return shutil.which("choco") is not None

    @staticmethod
    def run(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        spec, name = cmd.args
        dest = output_dir / "choco" / name
        dest.mkdir(parents=True, exist_ok=True)

        emit("info", f"Downloading choco package: {spec} ...")
        try:
            proc = subprocess.run(
                ["choco", "install", spec, "--download-only",
                 "--force", "-y", "--out", str(dest)],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if proc.returncode != 0:
                emit("error", proc.stderr.strip() or "choco install --download-only failed")
                return {"success": False, "path": str(dest), "error": proc.stderr.strip(),
                        "install_hint_sh": f"echo 'Use .bat script on Windows for {name}'",
                        "install_hint_bat": f"choco install {spec} --source \"{dest}\" -y"}

            files = list(dest.rglob("*"))
            emit("success", f"Downloaded {len(files)} file(s) to {dest}")
            return {"success": True, "path": str(dest),
                    "install_hint_sh": f"echo 'Use .bat script on Windows for {name}'",
                    "install_hint_bat": f"choco install {spec} --source \"{dest}\" -y"}
        except FileNotFoundError:
            emit("error", "choco not found. Install Chocolatey first.")
            return {"success": False, "path": str(dest), "error": "choco not found",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except subprocess.TimeoutExpired:
            emit("error", "choco timed out (600s)")
            return {"success": False, "path": str(dest), "error": "timeout",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except Exception as e:
            emit("error", str(e))
            return {"success": False, "path": str(dest), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
