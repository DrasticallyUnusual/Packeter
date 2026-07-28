# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Pip download handler — uses pip download to fetch packages without installing."""

import shutil
import subprocess
import sys
from pathlib import Path

from ..parsers import ParsedCommand, ToolType


class PipHandler:
    TOOL = ToolType.PIP

    @staticmethod
    def is_available() -> bool:
        return shutil.which("pip3") is not None or shutil.which("pip") is not None

    @staticmethod
    def _pip_cmd() -> str:
        return "pip3" if shutil.which("pip3") else "pip"

    @staticmethod
    def run(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        spec, name = cmd.args
        dest = output_dir / "pip" / name
        dest.mkdir(parents=True, exist_ok=True)

        pip = PipHandler._pip_cmd()
        emit("info", f"Downloading pip package: {spec} ...")
        try:
            proc = subprocess.run(
                [pip, "download", spec, "-d", str(dest), "--no-deps"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if proc.returncode != 0:
                emit("error", proc.stderr.strip() or "pip download failed")
                return {"success": False, "path": str(dest), "error": proc.stderr.strip(),
                        "install_hint_sh": "", "install_hint_bat": ""}

            files = list(dest.iterdir())
            emit("success", f"Downloaded {len(files)} file(s) to {dest}")
            return {"success": True, "path": str(dest),
                    "install_hint_sh": f"pip install ./pip/{name}/*.whl",
                    "install_hint_bat": f"pip install .\\pip\\{name}\\*.whl"}
        except FileNotFoundError:
            emit("error", f"{pip} not found. Install Python first.")
            return {"success": False, "path": str(dest), "error": f"{pip} not found",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except subprocess.TimeoutExpired:
            emit("error", "pip download timed out (300s)")
            return {"success": False, "path": str(dest), "error": "timeout",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except Exception as e:
            emit("error", str(e))
            return {"success": False, "path": str(dest), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
