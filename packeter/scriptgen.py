# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Generate install scripts (.sh or .bat) from completed downloads."""

from datetime import date
from pathlib import Path


def _tool_label(source: str) -> str:
    """Extract a short tool label from the raw source command."""
    s = source.strip().lower()
    if s.startswith("git clone"):
        return "git clone"
    if s.startswith("npm "):
        return "npm"
    if s.startswith("pip"):
        return "pip"
    if s.startswith("cargo "):
        return "cargo"
    if s.startswith("winget "):
        return "winget"
    if s.startswith("choco "):
        return "choco"
    if s.startswith("go "):
        return "go"
    if s.startswith("gem "):
        return "gem"
    if s.startswith("docker "):
        return "docker"
    if s.startswith("composer "):
        return "composer"
    if s.startswith("apt"):
        return "apt"
    if s.startswith("dnf "):
        return "dnf"
    if "|" in s and ("curl" in s or "wget" in s):
        return "curl|sh"
    return "url"


def _get_script_name(result: dict) -> str:
    """Get the best script name from a result — prefer rewritten over original."""
    rewritten = result.get("rewritten_path")
    if rewritten:
        return Path(rewritten).name
    path = result.get("path", "")
    return Path(path).name if path else "download"


def generate_sh(jobs: list, output_dir: Path) -> Path:
    """Generate a bash install.sh script from completed jobs."""
    today = date.today().isoformat()
    lines = [
        "#!/bin/bash",
        f"# Packeter Offline Installer — generated {today}",
        "# This script installs all downloaded packages.",
        "# Run this from the root of the output folder.",
        "",
        "set -e",
        "",
        'echo "Packeter Offline Installer"',
        'echo "========================="',
        "",
    ]

    total = len(jobs)
    for i, job in enumerate(jobs, 1):
        source = job.source
        result = job.result or {}
        tool = _tool_label(source)
        name = result.get("path", "").rsplit("/", 1)[-1] or source[:40]

        lines.append(f'echo "[{i}/{total}] {name} ({tool})"')

        # Use rewritten script if available
        rewritten = result.get("rewritten_path")
        if rewritten:
            script_name = Path(rewritten).name
            lines.append(f'chmod +x "./downloads/{script_name}"')
            lines.append(f'"./downloads/{script_name}"')
        else:
            hint = result.get("install_hint_sh", "")
            if hint:
                lines.append(hint)
            else:
                lines.append(f'echo "  -> Files ready at downloaded location"')

        lines.append("")

    lines.append('echo ""')
    lines.append('echo "All done!"')
    lines.append("")

    script_path = output_dir / "install.sh"
    script_path.write_text("\n".join(lines))
    script_path.chmod(0o755)
    return script_path


def generate_bat(jobs: list, output_dir: Path) -> Path:
    """Generate a Windows install.bat script from completed jobs."""
    today = date.today().isoformat()
    lines = [
        "@echo off",
        f":: Packeter Offline Installer — generated {today}",
        ":: This script installs all downloaded packages.",
        ":: Run this from the root of the output folder.",
        "",
        "echo Packeter Offline Installer",
        "echo =========================",
        "",
    ]

    total = len(jobs)
    for i, job in enumerate(jobs, 1):
        source = job.source
        result = job.result or {}
        tool = _tool_label(source)
        name = result.get("path", "").rsplit("\\", 1)[-1].rsplit("/", 1)[-1] or source[:40]

        lines.append(f"echo [{i}/{total}] {name} ({tool})")

        # Use rewritten script if available
        rewritten = result.get("rewritten_path")
        if rewritten:
            script_name = Path(rewritten).name
            lines.append(f"echo   -> Run .\\downloads\\{script_name}")
            lines.append(f"echo   NOTE: This is a bash script — run on Linux/macOS")
        else:
            hint = result.get("install_hint_bat", "")
            if hint:
                lines.append(hint)
            else:
                lines.append(f"echo   -> Files ready at downloaded location")

        lines.append("")

    lines.append("echo.")
    lines.append("echo All done!")
    lines.append("pause")
    lines.append("")

    script_path = output_dir / "install.bat"
    script_path.write_text("\n".join(lines))
    return script_path
