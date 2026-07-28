# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Go install handler — downloads Go modules for offline use."""

import json
import shutil
import subprocess
from pathlib import Path

from ..parsers import ParsedCommand, ToolType


class GoHandler:
    TOOL = ToolType.GO

    @staticmethod
    def is_available() -> bool:
        return shutil.which("go") is not None

    @staticmethod
    def run(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        spec, name = cmd.args
        dest = output_dir / "go" / name
        dest.mkdir(parents=True, exist_ok=True)

        emit("info", f"Downloading Go module: {spec} ...")
        try:
            proc = subprocess.run(
                ["go", "mod", "download", "-json", spec],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if proc.returncode != 0:
                emit("error", proc.stderr.strip() or "go mod download failed")
                return {"success": False, "path": str(dest), "error": proc.stderr.strip(),
                        "install_hint_sh": f"go install {spec}",
                        "install_hint_bat": f"go install {spec}"}

            info = json.loads(proc.stdout)
            mod_cache = info.get("Dir", "")
            version = info.get("Version", "latest")

            # Copy module files to output
            if mod_cache and Path(mod_cache).exists():
                import shutil as sh
                sh.copytree(mod_cache, dest, dirs_exist_ok=True)

            emit("success", f"Downloaded {spec}@{version} to {dest}")
            return {"success": True, "path": str(dest),
                    "install_hint_sh": f"go install {spec}@{version}",
                    "install_hint_bat": f"go install {spec}@{version}"}
        except FileNotFoundError:
            emit("error", "go not found. Install Go first.")
            return {"success": False, "path": str(dest), "error": "go not found",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except subprocess.TimeoutExpired:
            emit("error", "go mod download timed out (300s)")
            return {"success": False, "path": str(dest), "error": "timeout",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except json.JSONDecodeError:
            emit("error", "Failed to parse go mod output")
            return {"success": False, "path": str(dest), "error": "json decode error",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except Exception as e:
            emit("error", str(e))
            return {"success": False, "path": str(dest), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
