# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Cargo install handler — downloads crate source tarballs."""

import json
import shutil
import urllib.request
from pathlib import Path

from ..parsers import ParsedCommand, ToolType


class CargoHandler:
    TOOL = ToolType.CARGO

    @staticmethod
    def is_available() -> bool:
        return shutil.which("cargo") is not None

    @staticmethod
    def run(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        crate_name, name = cmd.args
        dest = output_dir / "cargo" / name
        dest.mkdir(parents=True, exist_ok=True)

        emit("info", f"Fetching crate info for {crate_name} ...")
        try:
            api_url = f"https://crates.io/api/v1/crates/{crate_name}"
            req = urllib.request.Request(api_url, headers={"User-Agent": "Packeter/0.1"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())

            version = data["crate"]["newest_version"]
            dl_url = f"https://crates.io/api/v1/crates/{crate_name}/{version}/download"
            tarball = dest / f"{crate_name}-{version}.tar.gz"

            emit("info", f"Downloading {crate_name} v{version} ...")
            urllib.request.urlretrieve(dl_url, str(tarball))

            emit("success", f"Downloaded {tarball.name} to {dest}")
            return {"success": True, "path": str(dest),
                    "install_hint_sh": f"tar -xf ./cargo/{name}/{crate_name}-{version}.tar.gz -C ./cargo/{name}/ && cargo install --path ./cargo/{name}/{crate_name}-{version}",
                    "install_hint_bat": f'tar -xf ".\\cargo\\{name}\\{crate_name}-{version}.tar.gz" -C ".\\cargo\\{name}\\" && cargo install --path ".\\cargo\\{name}\\{crate_name}-{version}"'}
        except urllib.error.URLError as e:
            emit("error", f"Network error: {e}")
            return {"success": False, "path": str(dest), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
        except KeyError:
            emit("error", f"Crate '{crate_name}' not found on crates.io")
            return {"success": False, "path": str(dest), "error": "crate not found",
                    "install_hint_sh": "", "install_hint_bat": ""}
        except Exception as e:
            emit("error", str(e))
            return {"success": False, "path": str(dest), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
