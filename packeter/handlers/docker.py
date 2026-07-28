# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Docker pull handler — saves Docker images as tar for offline use."""

import shutil
import subprocess
from pathlib import Path

from ..parsers import ParsedCommand, ToolType


class DockerHandler:
    TOOL = ToolType.DOCKER

    @staticmethod
    def is_available() -> bool:
        return shutil.which("docker") is not None

    @staticmethod
    def run(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        spec, name = cmd.args
        dest = output_dir / "docker"
        dest.mkdir(parents=True, exist_ok=True)
        tarball = dest / f"{name}.tar"

        emit("info", f"Pulling Docker image: {spec} ...")
        try:
            # Pull the image
            proc = subprocess.run(
                ["docker", "pull", spec],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if proc.returncode != 0:
                emit("error", proc.stderr.strip() or "docker pull failed")
                return {"success": False, "path": str(dest), "error": proc.stderr.strip(),
                        "install_hint_sh": f"docker load -i ./docker/{name}.tar",
                        "install_hint_bat": f"docker load -i .\\docker\\{name}.tar"}

            # Save the image as tar
            emit("info", f"Saving image as {name}.tar ...")
            proc = subprocess.run(
                ["docker", "save", spec, "-o", str(tarball)],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if proc.returncode != 0:
                emit("error", proc.stderr.strip() or "docker save failed")
                return {"success": False, "path": str(dest), "error": proc.stderr.strip(),
                        "install_hint_sh": "", "install_hint_bat": ""}

            size = tarball.stat().st_size
            if size > 1_048_576:
                size_str = f"{size / 1_048_576:.1f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"

            emit("success", f"Saved {name}.tar ({size_str}) to {dest}")
            return {"success": True, "path": str(tarball),
                    "install_hint_sh": f"docker load -i ./docker/{name}.tar",
                    "install_hint_bat": f"docker load -i .\\docker\\{name}.tar"}
        except FileNotFoundError:
            emit("error", "docker not found. Install Docker first.")
            return {"success": False, "path": str(dest), "error": "docker not found",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except subprocess.TimeoutExpired:
            emit("error", "Docker operation timed out (600s)")
            return {"success": False, "path": str(dest), "error": "timeout",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except Exception as e:
            emit("error", str(e))
            return {"success": False, "path": str(dest), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
