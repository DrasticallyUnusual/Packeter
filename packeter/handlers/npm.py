# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""NPM install handler — uses npm pack to download without installing."""

import shutil
import subprocess
from pathlib import Path

from ..parsers import ParsedCommand, ToolType


class NpmHandler:
    TOOL = ToolType.NPM

    @staticmethod
    def is_available() -> bool:
        return shutil.which("npm") is not None

    @staticmethod
    def run(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        spec, name = cmd.args
        dest = output_dir / "npm" / name
        dest.mkdir(parents=True, exist_ok=True)

        emit("info", f"Downloading npm package: {spec} ...")
        try:
            proc = subprocess.run(
                ["npm", "pack", spec, "--pack-destination", str(dest)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if proc.returncode != 0:
                emit("error", proc.stderr.strip() or "npm pack failed")
                return {"success": False, "path": str(dest), "error": proc.stderr.strip(),
                        "install_hint_sh": "", "install_hint_bat": ""}

            tarball = list(dest.glob("*.tgz"))
            if tarball:
                emit("success", f"Downloaded {tarball[0].name} to {dest}")
            else:
                emit("success", f"Package downloaded to {dest}")
            return {"success": True, "path": str(dest),
                    "install_hint_sh": f"npm install ./npm/{name}/*.tgz",
                    "install_hint_bat": f"npm install .\\npm\\{name}\\*.tgz"}
        except FileNotFoundError:
            emit("error", "npm not found. Install Node.js first.")
            return {"success": False, "path": str(dest), "error": "npm not found",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except subprocess.TimeoutExpired:
            emit("error", "npm pack timed out (300s)")
            return {"success": False, "path": str(dest), "error": "timeout",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except Exception as e:
            emit("error", str(e))
            return {"success": False, "path": str(dest), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
