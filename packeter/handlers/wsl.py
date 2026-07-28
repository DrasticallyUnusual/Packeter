# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""WSL handler — downloads WSL components and distro packages for offline install."""

import json
import shutil
import urllib.request
from pathlib import Path

from ..parsers import ParsedCommand, ToolType

WSL_MSI_URL = "https://github.com/microsoft/WSL/releases/latest"
WSL_GITHUB_API = "https://api.github.com/repos/microsoft/WSL/releases/latest"

DISTRO_DOWNLOADS = {
    "ubuntu": "https://aka.ms/wslubuntu",
    "ubuntu-24.04": "https://aka.ms/wslubuntu2404",
    "ubuntu-22.04": "https://aka.ms/wslubuntu2204",
    "ubuntu-20.04": "https://aka.ms/wslubuntu2004",
    "debian": "https://aka.ms/wsldebian",
    "kali-linux": "https://aka.ms/wslkali",
    "opensuse-leap-15.6": "https://aka.ms/wslopensuseleap156",
    "sles-15-sp5": "https://aka.ms/wslsles15sp5",
    "oracle-linux-9_4": "https://aka.ms/wsloraclelinux94",
    "ubuntu-pro": "https://aka.ms/wslubuntu-pro",
}


class WslHandler:
    TOOL = ToolType.WSL

    @staticmethod
    def is_available() -> bool:
        return True

    @staticmethod
    def run(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        action = cmd.args[0] if cmd.args else "install"

        if action == "install":
            return WslHandler._handle_install(cmd, output_dir, emit)
        elif action == "update":
            return WslHandler._handle_update(cmd, output_dir, emit)
        elif action == "download":
            return WslHandler._handle_download(cmd, output_dir, emit)
        else:
            emit("error", f"Unknown WSL action: {action}")
            return {"success": False, "error": f"Unknown action: {action}",
                    "install_hint_sh": "", "install_hint_bat": ""}

    @staticmethod
    def _handle_install(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        distro = cmd.args[1] if len(cmd.args) > 1 else None
        dest = output_dir / "wsl"
        dest.mkdir(parents=True, exist_ok=True)

        if distro:
            return WslHandler._download_distro(distro, dest, emit)
        else:
            return WslHandler._download_wsl_msi(dest, emit)

    @staticmethod
    def _handle_update(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        dest = output_dir / "wsl"
        dest.mkdir(parents=True, exist_ok=True)
        return WslHandler._download_wsl_msi(dest, emit)

    @staticmethod
    def _handle_download(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        distro = cmd.args[1] if len(cmd.args) > 1 else None
        if not distro:
            emit("error", "No distro specified for wsl --install --download")
            return {"success": False, "error": "No distro specified",
                    "install_hint_sh": "", "install_hint_bat": ""}
        dest = output_dir / "wsl"
        dest.mkdir(parents=True, exist_ok=True)
        return WslHandler._download_distro(distro, dest, emit)

    @staticmethod
    def _download_wsl_msi(dest: Path, emit) -> dict:
        emit("info", "Fetching latest WSL release info from GitHub ...")
        try:
            req = urllib.request.Request(
                WSL_GITHUB_API,
                headers={"User-Agent": "Packeter/0.1", "Accept": "application/vnd.github.v3+json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())

            msi_url = None
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".msi") and "x64" in name:
                    msi_url = asset["browser_download_url"]
                    msi_name = name
                    break

            if not msi_url:
                emit("error", "Could not find WSL MSI in latest release")
                return {"success": False, "error": "MSI not found",
                        "install_hint_sh": "", "install_hint_bat": ""}

            msi_path = dest / msi_name
            emit("info", f"Downloading {msi_name} ...")
            req2 = urllib.request.Request(msi_url, headers={"User-Agent": "Packeter/0.1"})
            with urllib.request.urlopen(req2, timeout=300) as resp:
                with open(msi_path, "wb") as f:
                    shutil.copyfileobj(resp, f)

            size = msi_path.stat().st_size
            size_str = f"{size / 1_048_576:.1f} MB" if size > 1_048_576 else f"{size / 1024:.0f} KB"
            emit("success", f"Downloaded {msi_name} ({size_str})")

            return {
                "success": True,
                "path": str(msi_path),
                "install_hint_sh": f'echo "Run on Windows as admin:" && echo "  .\\\\wsl\\\\{msi_name}"',
                "install_hint_bat": f"echo   -> Run as admin: .\\wsl\\{msi_name}",
            }

        except Exception as e:
            emit("error", f"Failed to fetch WSL release: {e}")
            return {"success": False, "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}

    @staticmethod
    def _download_distro(distro: str, dest: Path, emit) -> dict:
        distro_key = distro.lower().strip()
        url = DISTRO_DOWNLOADS.get(distro_key)

        if not url:
            emit("warning", f"Unknown distro '{distro}', trying direct download URL ...")
            if distro.startswith("http"):
                url = distro
            else:
                emit("error", f"Unknown distro: {distro}. Available: {', '.join(sorted(DISTRO_DOWNLOADS.keys()))}")
                return {"success": False, "error": f"Unknown distro: {distro}",
                        "install_hint_sh": "", "install_hint_bat": ""}

        safe_name = distro_key.replace(" ", "-")
        emit("info", f"Downloading WSL distro: {distro} ...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Packeter/0.1"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                content_type = resp.headers.get("Content-Type", "")
                final_url = resp.url

                if "text/html" in content_type or "application/json" in content_type:
                    emit("error", f"Got redirect to web page instead of download. Use --web-download flag.")
                    return {"success": False, "error": "Redirected to web page",
                            "install_hint_sh": "", "install_hint_bat": ""}

                ext = ".appx"
                if ".wsl" in final_url.lower():
                    ext = ".wsl"
                elif ".appxbundle" in final_url.lower():
                    ext = ".appxbundle"
                elif ".msixbundle" in final_url.lower():
                    ext = ".msixbundle"

                filename = f"{safe_name}{ext}"
                filepath = dest / filename
                with open(filepath, "wb") as f:
                    shutil.copyfileobj(resp, f)

            size = filepath.stat().st_size
            size_str = f"{size / 1_048_576:.1f} MB" if size > 1_048_576 else f"{size / 1024:.0f} KB"
            emit("success", f"Downloaded {filename} ({size_str})")

            return {
                "success": True,
                "path": str(filepath),
                "install_hint_sh": (
                    f'echo "To install on Windows (run PowerShell as admin):"\n'
                    f'echo "  Add-AppxPackage .\\\\wsl\\\\{filename}"\n'
                    f'echo "Or run: wsl --install -d {distro}"'
                ),
                "install_hint_bat": (
                    f"echo   -> Run PowerShell as admin:\n"
                    f"echo     Add-AppxPackage .\\wsl\\{filename}\n"
                    f"echo   Or run: wsl --install -d {distro}"
                ),
            }

        except Exception as e:
            emit("error", f"Failed to download distro: {e}")
            return {"success": False, "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
