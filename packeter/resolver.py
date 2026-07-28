# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Orchestrate multi-stage script analysis, download, and rewrite."""

import json
import platform
import re
import shutil
import urllib.request
from pathlib import Path
from typing import Callable

from .analyzer import analyze_script, ScriptAnalysis

ARCH_MAP = {
    "x86_64": "amd64",
    "AMD64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
    "i386": "386",
    "i686": "386",
}


def _system_vars() -> dict:
    """Detect system variables for URL resolution."""
    uname_m = platform.machine()
    uname_s = platform.system().lower()
    return {
        "ARCH": ARCH_MAP.get(uname_m, uname_m),
        "UNAME_M": uname_m,
        "UNAME_S": uname_s,
        "OS": uname_s,
        "HOSTTYPE": uname_m,
    }


def _resolve_url(url: str, system_vars: dict) -> str:
    """Resolve remaining ${VAR} and $VAR patterns in a URL using system_vars."""
    resolved = url
    for k, v in system_vars.items():
        resolved = resolved.replace("${" + k + "}", v)
        resolved = resolved.replace("$" + k, v)
    # Strip bash parameter expansions like ${VAR:+suffix} if var is empty
    resolved = re.sub(r'\$\{\w+:\+\?[^}]*\}', '', resolved)
    return resolved


def _url_to_filename(url: str) -> str:
    """Convert a URL to a safe filename."""
    path = url.rstrip("/").rsplit("/", 1)[-1]
    # Remove query params
    path = path.split("?")[0]
    # Remove fragment
    path = path.split("#")[0]
    if not path or len(path) < 2:
        path = "download"
    return path


def _download_file(url: str, dest: Path, emit) -> bool:
    """Download a file from URL to dest. Returns True on success."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Packeter/0.1"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(dest, "wb") as f:
                shutil.copyfileobj(resp, f)
        return True
    except Exception as e:
        emit("warning", f"Failed to download {url}: {e}")
        return False


def resolve_script(
    script_path: Path,
    output_dir: Path,
    emit,
    max_depth: int = 3,
    current_depth: int = 0,
) -> dict:
    """Analyze a script, download its dependencies, and rewrite it.

    Returns a dict with:
        - original_path: Path to original script
        - rewritten_path: Path to rewritten script (or None)
        - url_map: {original_url: local_relative_path}
        - downloads: list of downloaded file info
        - analysis: ScriptAnalysis object
    """
    result = {
        "original_path": str(script_path),
        "rewritten_path": None,
        "url_map": {},
        "downloads": [],
        "analysis": None,
    }

    if current_depth >= max_depth:
        emit("warning", f"Max recursion depth ({max_depth}) reached, stopping analysis")
        return result

    # Read the script
    try:
        content = script_path.read_text(errors="replace")
    except Exception as e:
        emit("error", f"Failed to read script: {e}")
        return result

    # Analyze
    analysis = analyze_script(content)
    result["analysis"] = analysis

    if not analysis.downloads:
        emit("info", "No download dependencies found in script")
        return result

    emit("info", f"Found {len(analysis.downloads)} download(s) in script (depth={current_depth})")

    system_vars = _system_vars()

    # Create downloads directory alongside the script
    downloads_dir = script_path.parent
    url_map = {}

    for ref in analysis.downloads:
        original_url = ref.url
        resolved_url = _resolve_url(original_url, system_vars)

        # Handle pip/npm/apt package references
        if resolved_url.startswith("pip:") or resolved_url.startswith("npm:") or resolved_url.startswith("apt:"):
            emit("info", f"  Package reference: {resolved_url} (will be in install hints)")
            url_map[original_url] = resolved_url
            continue

        # Skip URLs that still have unresolved vars
        if "${" in resolved_url or re.search(r'\$\w+', resolved_url):
            emit("info", f"  Skipping unresolved URL: {resolved_url}")
            continue

        # Download HTTP URLs
        filename = _url_to_filename(resolved_url)
        local_path = downloads_dir / filename

        if local_path.exists():
            emit("info", f"  Already exists: {filename}")
        else:
            emit("info", f"  Downloading: {filename}")
            if not _download_file(resolved_url, local_path, emit):
                continue

        size = local_path.stat().st_size
        if size > 1_048_576:
            size_str = f"{size / 1_048_576:.1f} MB"
        elif size > 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} B"

        emit("success", f"  Downloaded {filename} ({size_str})")

        # Relative path from the script's directory to the file
        rel_path = local_path.relative_to(downloads_dir)
        url_map[original_url] = str(rel_path)

        result["downloads"].append({
            "url": resolved_url,
            "original_url": original_url,
            "local_path": str(local_path),
            "relative_path": str(rel_path),
            "filename": filename,
            "size": size,
        })

        # If the downloaded file is also a script, recurse
        if _is_script(local_path) and current_depth + 1 < max_depth:
            emit("info", f"  Analyzing downloaded script: {filename} ...")
            sub_result = resolve_script(
                local_path, output_dir, emit,
                max_depth=max_depth,
                current_depth=current_depth + 1,
            )
            # Merge sub-result url_map
            url_map.update(sub_result.get("url_map", {}))
            result["downloads"].extend(sub_result.get("downloads", []))

    result["url_map"] = url_map

    # Build call-site map and func_local_map for the rewriter
    call_site_map = {}
    resolved_to_local = {}
    for d in result["downloads"]:
        if "original_url" in d:
            resolved_to_local[d["url"]] = d["relative_path"]
        else:
            resolved_to_local[d["url"]] = d["relative_path"]

    func_local_map = {}  # func_name → [{args, local_paths}]
    for cs in analysis.call_sites:
        local_paths = []
        for rurl in cs["resolved_urls"]:
            rurl_resolved = _resolve_url(rurl, system_vars)
            lp = resolved_to_local.get(rurl_resolved) or resolved_to_local.get(rurl)
            if lp:
                local_paths.append(lp)
        if local_paths:
            call_site_map[cs["line_num"]] = {
                "func_name": cs["func_name"],
                "args": cs["args"],
                "local_paths": local_paths,
            }
            fn = cs["func_name"]
            if fn not in func_local_map:
                func_local_map[fn] = []
            func_local_map[fn].append({
                "args": cs["args"],
                "local_paths": local_paths,
            })

    # Rewrite the script
    try:
        from .rewriter import rewrite_script
        rewritten = rewrite_script(content, url_map, output_dir, call_site_map, func_local_map)
        rewritten_path = script_path.with_suffix(".rewritten.sh")
        rewritten_path.write_text(rewritten)
        rewritten_path.chmod(0o755)
        result["rewritten_path"] = str(rewritten_path)
        emit("success", f"Rewritten script: {rewritten_path.name}")
    except Exception as e:
        emit("error", f"Failed to rewrite script: {e}")

    # Save analysis metadata
    meta_path = script_path.with_suffix(".urls.json")
    meta = {
        "original": str(script_path),
        "rewritten": result["rewritten_path"],
        "url_map": url_map,
        "downloads": result["downloads"],
        "os_arch_dep": analysis.os_arch_dep,
    }
    meta_path.write_text(json.dumps(meta, indent=2))

    return result


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
