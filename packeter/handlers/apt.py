# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""APT download handler — fetches .deb packages for offline install."""

import shutil
import subprocess
from pathlib import Path

from ..parsers import ParsedCommand, ToolType


class AptHandler:
    TOOL = ToolType.APT

    @staticmethod
    def is_available() -> bool:
        return shutil.which("apt") is not None or shutil.which("apt-get") is not None

    @staticmethod
    def _apt_cmd() -> str:
        return "apt" if shutil.which("apt") else "apt-get"

    @staticmethod
    def run(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        spec, name = cmd.args
        dest = output_dir / "apt" / name
        dest.mkdir(parents=True, exist_ok=True)

        apt = AptHandler._apt_cmd()
        emit("info", f"Downloading apt package: {spec} ...")
        try:
            proc = subprocess.run(
                [apt, "download", spec],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(dest),
            )
            if proc.returncode != 0:
                emit("error", proc.stderr.strip() or "apt download failed")
                return {"success": False, "path": str(dest), "error": proc.stderr.strip(),
                        "install_hint_sh": f"sudo dpkg -i ./{dest}/*.deb && sudo apt-get install -f",
                        "install_hint_bat": f"dpkg -i .\\apt\\{name}\\*.deb"}

            debs = list(dest.glob("*.deb"))
            if debs:
                emit("success", f"Downloaded {len(debs)} .deb file(s) to {dest}")
            else:
                emit("success", f"Package downloaded to {dest}")
            return {"success": True, "path": str(dest),
                    "install_hint_sh": f"sudo dpkg -i ./apt/{name}/*.deb && sudo apt-get install -f",
                    "install_hint_bat": f"dpkg -i .\\apt\\{name}\\*.deb"}
        except FileNotFoundError:
            emit("error", f"{apt} not found. Install APT first.")
            return {"success": False, "path": str(dest), "error": f"{apt} not found",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except subprocess.TimeoutExpired:
            emit("error", "apt download timed out (300s)")
            return {"success": False, "path": str(dest), "error": "timeout",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except Exception as e:
            emit("error", str(e))
            return {"success": False, "path": str(dest), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
