# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Gem install handler — fetches Ruby gems for offline install."""

import shutil
import subprocess
from pathlib import Path

from ..parsers import ParsedCommand, ToolType


class GemHandler:
    TOOL = ToolType.GEM

    @staticmethod
    def is_available() -> bool:
        return shutil.which("gem") is not None

    @staticmethod
    def run(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        spec, name = cmd.args
        dest = output_dir / "gem" / name
        dest.mkdir(parents=True, exist_ok=True)

        emit("info", f"Fetching gem: {spec} ...")
        try:
            proc = subprocess.run(
                ["gem", "fetch", spec, "--output", str(dest)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if proc.returncode != 0:
                emit("error", proc.stderr.strip() or "gem fetch failed")
                return {"success": False, "path": str(dest), "error": proc.stderr.strip(),
                        "install_hint_sh": f"gem install {dest}/*.gem",
                        "install_hint_bat": f"gem install .\\gem\\{name}\\*.gem"}

            gems = list(dest.glob("*.gem"))
            if gems:
                emit("success", f"Downloaded {gems[0].name} to {dest}")
            else:
                emit("success", f"Gem downloaded to {dest}")
            return {"success": True, "path": str(dest),
                    "install_hint_sh": f"gem install ./gem/{name}/*.gem",
                    "install_hint_bat": f"gem install .\\gem\\{name}\\*.gem"}
        except FileNotFoundError:
            emit("error", "gem not found. Install Ruby first.")
            return {"success": False, "path": str(dest), "error": "gem not found",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except subprocess.TimeoutExpired:
            emit("error", "gem fetch timed out (300s)")
            return {"success": False, "path": str(dest), "error": "timeout",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except Exception as e:
            emit("error", str(e))
            return {"success": False, "path": str(dest), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
