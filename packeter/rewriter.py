# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Rewrite shell scripts to replace remote downloads with local file operations."""

import re
from pathlib import Path


def rewrite_script(
    original_content: str,
    url_map: dict[str, str],
    output_dir: Path,
    call_site_map: dict[int, dict] | None = None,
    func_local_map: dict[str, list] | None = None,
) -> str:
    """Rewrite a shell script, replacing remote URLs with local paths.

    call_site_map: {line_num (1-indexed): {func_name, args, local_paths}}
    func_local_map: {func_name: [{args: [...], local_paths: [...]}]}
    """
    if call_site_map is None:
        call_site_map = {}
    if func_local_map is None:
        func_local_map = {}

    lines = original_content.split("\n")

    # Join continuation lines, tracking original line numbers
    joined = []  # [(joined_text, first_original_line_num)]
    buf = ""
    buf_start = 1
    for i, line in enumerate(lines, 1):
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            if not buf:
                buf_start = i
            buf += stripped[:-1] + " "
        else:
            buf += stripped
            joined.append((buf, buf_start if buf else i))
            buf = ""
            buf_start = i + 1
    if buf:
        joined.append((buf, buf_start))

    rewritten = []
    rewritten.append("#!/bin/bash")
    rewritten.append("# =============================================================")
    rewritten.append("# Packeter REWRITTEN installer -- all downloads replaced with local files")
    rewritten.append("# Original script has been analyzed and modified for offline use.")
    rewritten.append("# =============================================================")
    rewritten.append("")
    rewritten.append('_PACKETER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"')
    rewritten.append("")

    # Inject local file overrides for traced functions
    if func_local_map:
        rewritten.append("# --- Packeter: local file overrides ---")
        for func_name, call_list in func_local_map.items():
            rewritten.append(f"{func_name}() {{")
            rewritten.append(f'    local url_base="$1" dest_dir="$2" filename="$3"')
            rewritten.append(f'    local _local_file')
            # Collect unique local file basenames
            seen = set()
            for ci in call_list:
                for lp in ci["local_paths"]:
                    basename = Path(lp).name
                    if basename in seen:
                        continue
                    seen.add(basename)
                    rewritten.append(
                        f'    _local_file="$_PACKETER_DIR/{lp}"'
                    )
                    rewritten.append(
                        f'    if [ -f "$_local_file" ]; then'
                    )
                    rewritten.append(
                        f'        echo "Packeter: using local {lp}"'
                    )
                    rewritten.append(
                        f'        local _ext="${{filename##*.}}"'
                    )
                    rewritten.append(
                        f'        case "$_ext" in'
                    )
                    rewritten.append(
                        f'            zst) zstd -dc "$_local_file" | tar -xf - -C "$dest_dir" --no-same-owner ;;'
                    )
                    rewritten.append(
                        f'            tgz|tar.gz) tar -xzf "$_local_file" -C "$dest_dir" --no-same-owner ;;'
                    )
                    rewritten.append(
                        f'            tar.xz) tar -xJf "$_local_file" -C "$dest_dir" --no-same-owner ;;'
                    )
                    rewritten.append(
                        f'            zip) unzip -o "$_local_file" -d "$dest_dir" ;;'
                    )
                    rewritten.append(
                        f'            *) cp "$_local_file" "$dest_dir/" ;;'
                    )
                    rewritten.append(
                        f'        esac; return 0; fi'
                    )
            rewritten.append(f'    command {func_name} "$@"')
            rewritten.append(f"}}")
        rewritten.append("# --- End Packeter overrides ---")
        rewritten.append("")

    for joined_text, orig_line in joined:
        new_lines = _rewrite_line(joined_text, url_map, output_dir)
        rewritten.append(new_lines)

    return "\n".join(rewritten)


def _rewrite_line(
    line: str,
    url_map: dict[str, str],
    output_dir: Path,
) -> str:
    """Rewrite a single line, replacing URLs with local paths."""
    stripped = line.strip()

    if not stripped or stripped.startswith("#"):
        return line

    # curl [flags] URL [-o file] [> file]
    m = re.match(
        r'^(\s*)(curl\s+(?:-[a-zA-Z]+\s+)*)(https?://\S+)(\s+[^>\n]*?>\s*\S+)?(?:\s+-o\s+(\S+))?',
        stripped,
    )
    if m:
        indent = m.group(1)
        url = m.group(3).strip('"').strip("'")
        dest = m.group(5)
        if dest:
            dest = dest.strip('"').strip("'")
        local = url_map.get(url)
        if local:
            if dest:
                return (
                    f'{indent}# [Packeter] Original: curl ... {url} -o {dest}\n'
                    f'{indent}mkdir -p "$(dirname "{dest}")" 2>/dev/null\n'
                    f'{indent}cp "$_PACKETER_DIR/{local}" "{dest}"'
                )
            else:
                return (
                    f'{indent}# [Packeter] Original: curl ... {url}\n'
                    f'{indent}bash "$_PACKETER_DIR/{local}"'
                )

    # wget [flags] URL [-O file]
    m = re.match(
        r'^(\s*)(wget\s+(?:-[a-zA-Z]+\s+)*)(https?://\S+)(?:\s+-O\s+(\S+))?',
        stripped,
    )
    if m:
        indent = m.group(1)
        url = m.group(3).strip('"').strip("'")
        dest = m.group(4)
        if dest:
            dest = dest.strip('"').strip("'")
        local = url_map.get(url)
        if local:
            if dest:
                return (
                    f'{indent}# [Packeter] Original: wget ... {url} -O {dest}\n'
                    f'{indent}mkdir -p "$(dirname "{dest}")" 2>/dev/null\n'
                    f'{indent}cp "$_PACKETER_DIR/{local}" "{dest}"'
                )
            else:
                return (
                    f'{indent}# [Packeter] Original: wget ... {url}\n'
                    f'{indent}bash "$_PACKETER_DIR/{local}"'
                )

    # pip install pkg
    m = re.match(r'^(\s*)(pip(?:3)?\s+install\s+)([a-zA-Z0-9_\-\[\]@.>=<]+)(.*)', stripped)
    if m:
        indent = m.group(1)
        cmd = m.group(2)
        pkg = m.group(3)
        rest = m.group(4)
        local = url_map.get(f"pip:{pkg}")
        if local:
            return (
                f'{indent}# [Packeter] Original: pip install {pkg}\n'
                f'{indent}{cmd}"$_PACKETER_DIR/{local}"{rest}'
            )

    # npm install -g pkg
    m = re.match(r'^(\s*)(npm\s+(?:install|i)\s+(?:-[a-zA-Z]+\s+)*)([a-zA-Z0-9_\-@/]+)(.*)', stripped)
    if m:
        indent = m.group(1)
        cmd = m.group(2)
        pkg = m.group(3)
        rest = m.group(4)
        local = url_map.get(f"npm:{pkg}")
        if local:
            return (
                f'{indent}# [Packeter] Original: npm install {pkg}\n'
                f'{indent}{cmd}"$_PACKETER_DIR/{local}"{rest}'
            )

    return line
