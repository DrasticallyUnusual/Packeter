# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""DNF download handler — fetches .rpm packages for offline install."""

import shutil
import subprocess
from pathlib import Path

from ..parsers import ParsedCommand, ToolType


class DnfHandler:
    TOOL = ToolType.DNF

    @staticmethod
    def is_available() -> bool:
        return shutil.which("dnf") is not None or shutil.which("yum") is not None

    @staticmethod
    def _dnf_cmd() -> str:
        return "dnf" if shutil.which("dnf") else "yum"

    @staticmethod
    def run(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        spec, name = cmd.args
        dest = output_dir / "dnf" / name
        dest.mkdir(parents=True, exist_ok=True)

        dnf = DnfHandler._dnf_cmd()
        emit("info", f"Downloading dnf package: {spec} ...")
        try:
            proc = subprocess.run(
                [dnf, "download", spec, "--destdir", str(dest)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if proc.returncode != 0:
                emit("error", proc.stderr.strip() or "dnf download failed")
                return {"success": False, "path": str(dest), "error": proc.stderr.strip(),
                        "install_hint_sh": f"sudo rpm -i ./{dest}/*.rpm",
                        "install_hint_bat": f"rpm -i .\\dnf\\{name}\\*.rpm"}

            rpms = list(dest.glob("*.rpm"))
            if rpms:
                emit("success", f"Downloaded {len(rpms)} .rpm file(s) to {dest}")
            else:
                emit("success", f"Package downloaded to {dest}")
            return {"success": True, "path": str(dest),
                    "install_hint_sh": f"sudo rpm -i ./dnf/{name}/*.rpm",
                    "install_hint_bat": f"rpm -i .\\dnf\\{name}\\*.rpm"}
        except FileNotFoundError:
            emit("error", f"{dnf} not found. Install DNF/YUM first.")
            return {"success": False, "path": str(dest), "error": f"{dnf} not found",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except subprocess.TimeoutExpired:
            emit("error", "dnf download timed out (300s)")
            return {"success": False, "path": str(dest), "error": "timeout",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except Exception as e:
            emit("error", str(e))
            return {"success": False, "path": str(dest), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
