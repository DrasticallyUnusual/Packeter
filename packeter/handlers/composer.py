# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Composer handler — downloads PHP packages via Composer."""

import shutil
import subprocess
from pathlib import Path

from ..parsers import ParsedCommand, ToolType


class ComposerHandler:
    TOOL = ToolType.COMPOSER

    @staticmethod
    def is_available() -> bool:
        return shutil.which("composer") is not None

    @staticmethod
    def run(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        spec, name = cmd.args
        dest = output_dir / "composer" / name
        dest.mkdir(parents=True, exist_ok=True)

        emit("info", f"Downloading Composer package: {spec} ...")
        try:
            # Create a temp composer project to download the package
            proc = subprocess.run(
                ["composer", "create-project", "--prefer-dist",
                 "--no-dev", "--no-install", spec, str(dest)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if proc.returncode != 0:
                # Fallback: try require in existing project
                emit("info", "Trying alternative download method ...")
                proc = subprocess.run(
                    ["composer", "require", spec, "--prefer-dist",
                     "--no-dev", "--no-interaction", "--working-dir", str(dest)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if proc.returncode != 0:
                    emit("error", proc.stderr.strip() or "composer failed")
                    return {"success": False, "path": str(dest), "error": proc.stderr.strip(),
                            "install_hint_sh": f"cd ./composer/{name} && composer install --no-dev",
                            "install_hint_bat": f"cd .\\composer\\{name} && composer install --no-dev"}

            emit("success", f"Downloaded {name} to {dest}")
            return {"success": True, "path": str(dest),
                    "install_hint_sh": f"cd ./composer/{name} && composer install --no-dev",
                    "install_hint_bat": f"cd .\\composer\\{name} && composer install --no-dev"}
        except FileNotFoundError:
            emit("error", "composer not found. Install PHP Composer first.")
            return {"success": False, "path": str(dest), "error": "composer not found",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except subprocess.TimeoutExpired:
            emit("error", "composer timed out (300s)")
            return {"success": False, "path": str(dest), "error": "timeout",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except Exception as e:
            emit("error", str(e))
            return {"success": False, "path": str(dest), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
