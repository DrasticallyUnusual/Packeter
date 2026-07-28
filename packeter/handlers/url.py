# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Direct URL download handler — with auto-analysis for install scripts."""

import shutil
import urllib.request
from pathlib import Path

from ..parsers import ParsedCommand, ToolType


class UrlHandler:
    TOOL = ToolType.URL

    @staticmethod
    def is_available() -> bool:
        return True

    @staticmethod
    def run(cmd: ParsedCommand, output_dir: Path, emit) -> dict:
        url, name = cmd.args
        dest = output_dir / "downloads"
        dest.mkdir(parents=True, exist_ok=True)
        filepath = dest / name

        emit("info", f"Downloading {url} ...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Packeter/0.1"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(filepath, "wb") as f:
                    shutil.copyfileobj(resp, f)

            size = filepath.stat().st_size
            if size > 1_048_576:
                size_str = f"{size / 1_048_576:.1f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"

            emit("success", f"Downloaded {name} ({size_str})")

            result = {
                "success": True,
                "path": str(filepath),
                "install_hint_sh": f'chmod +x ./downloads/{name} && ./downloads/{name}',
                "install_hint_bat": f'echo   -> Run .\\downloads\\{name}',
            }

            # Auto-analyze if it looks like a shell script
            if _is_script(filepath):
                emit("info", "Detected install script — analyzing dependencies ...")
                try:
                    from ..resolver import resolve_script
                    resolution = resolve_script(filepath, output_dir, emit)
                    url_map = resolution.get("url_map", {})
                    rewritten = resolution.get("rewritten_path")
                    downloads = resolution.get("downloads", [])

                    if rewritten:
                        result["rewritten_path"] = rewritten
                        result["install_hint_sh"] = f'chmod +x ./downloads/{Path(rewritten).name} && ./downloads/{Path(rewritten).name}'
                        result["install_hint_bat"] = f'echo   -> Run .\\downloads\\{Path(rewritten).name}'

                    if downloads:
                        emit("success", f"Resolved {len(downloads)} dependency(ies)")
                        result["dependencies"] = downloads
                        result["url_map"] = url_map

                except Exception as e:
                    emit("warning", f"Script analysis failed: {e}")

            return result

        except urllib.error.URLError as e:
            emit("error", f"Download failed: {e}")
            return {"success": False, "path": str(filepath), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}
        except Exception as e:
            emit("error", str(e))
            return {"success": False, "path": str(filepath), "error": str(e),
                    "install_hint_sh": "", "install_hint_bat": ""}


def _is_script(path: Path) -> bool:
    """Check if a file looks like a shell script."""
    if path.suffix in (".sh", ".bash", ".zsh"):
        return True
    try:
        with open(path, "r", errors="replace") as f:
            first_line = f.readline(100)
            return first_line.startswith("#!/") and ("bash" in first_line or "sh" in first_line)
    except Exception:
        return False
