# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Analyze shell scripts to extract download URLs and install commands.

Handles:
- Direct curl/wget URLs
- Variable assignments: VAR="https://..."
- Function definitions containing downloads
- Function calls with URL arguments
- URL construction: "${base}/${file}.tar.zst"
"""

import re
from dataclasses import dataclass, field


@dataclass
class DownloadRef:
    """A reference to a file that needs to be downloaded."""
    url: str
    dest_path: str = ""
    tool: str = "curl"
    line_num: int = 0
    raw_line: str = ""
    context: str = ""  # function name or "global"


@dataclass
class ScriptAnalysis:
    """Result of analyzing a shell script."""
    downloads: list[DownloadRef] = field(default_factory=list)
    urls_found: list[str] = field(default_factory=list)
    url_vars: dict[str, str] = field(default_factory=dict)
    functions: dict[str, str] = field(default_factory=dict)  # name → body
    call_sites: list[dict] = field(default_factory=list)  # function call rewrite info
    is_install_script: bool = False
    os_arch_dep: bool = False


# --- Regex patterns ---

_VAR_ASSIGN_RE = re.compile(
    r'^([A-Z_][A-Z0-9_]*)="(.*?)"'
)

_VAR_ASSIGN_SINGLE_RE = re.compile(
    r"^([A-Z_][A-Z0-9_]*)='(.*?)'"
)

# curl with -o flag: curl [flags] URL -o file
_CURL_O_RE = re.compile(
    r'curl\s+[^|;\n]*?(https?://\S+)[^|;\n]*?-o\s+([^\s;|]+)'
)

# curl with redirect: curl [flags] URL > file
_CURL_GT_RE = re.compile(
    r'curl\s+[^|;\n]*?(https?://\S+)[^|;\n]*?>\s*(\S+)'
)

# curl piped: curl [flags] URL | ...
_CURL_PIPE_RE = re.compile(
    r'curl\s+[^|;\n]*?(https?://\S+)\s*\|'
)

# wget URL -O file
_WGET_RE = re.compile(
    r'wget\s+[^|;\n]*?(https?://\S+)[^|;\n]*?-O\s+([^\s;|]+)'
)

# wget URL (no -O)
_WGETPlain_RE = re.compile(
    r'wget\s+(?:-[a-zA-Z]+\s+)*?(https?://\S+)'
)

# pip install
_PIP_RE = re.compile(r'pip(?:3)?\s+install\s+([a-zA-Z0-9_\-\[\]@.>=<]+)')

# npm install
_NPM_RE = re.compile(r'npm\s+(?:install|i)\s+(?:-[a-zA-Z]+\s+)*([a-zA-Z0-9_\-@/]+)')

# apt install
_APT_RE = re.compile(r'apt(?:-get)?\s+install\s+(?:-[a-zA-Z]+\s+)*([a-zA-Z0-9_\-.]+)')

# Bare URL
_URL_RE = re.compile(r'https?://[^\s"\'<>|)]+')

# Function definition: name() { ... }
_FUNC_DEF_RE = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\)\s*\{')

# Function call with string args
_FUNC_CALL_RE = re.compile(
    r'^([a-zA-Z_][a-zA-Z0-9_]*)\s+(".*?"|\S+)'
)

_OS_ARCH_PATTERNS = [
    re.compile(r'uname\s+-m'),
    re.compile(r'uname\s+-s'),
    re.compile(r'\bARCH\b'),
    re.compile(r'\bOS\b.*=.*uname'),
]


def _clean(s: str) -> str:
    return s.strip().strip('"').strip("'")


def _resolve_var(name: str, vars_map: dict) -> str:
    """Resolve a variable reference like ${VAR} or $VAR."""
    val = vars_map.get(name, "")
    # Resolve nested refs like ${OLLAMA_VERSION:+?version=$OLLAMA_VERSION}
    if "${" in val:
        for vname, vval in vars_map.items():
            val = val.replace(f"${{{vname}}}", vval)
            val = val.replace(f"${vname}", vval)
    return val


def _resolve_url_template(template: str, vars_map: dict) -> str:
    """Resolve a URL template like "${base}/${file}.tar.zst"."""
    result = template
    # Replace ${VAR} patterns
    for vname, vval in vars_map.items():
        result = result.replace(f"${{{vname}}}", vval)
        result = result.replace(f"${vname}", vval)
    # Clean up any remaining ${...} that look like shell params ($1, $2)
    result = re.sub(r'\$\{?\d+\}?', '', result)
    return _clean(result)


def _extract_function_body(lines: list, start_idx: int) -> tuple[str, int]:
    """Extract a function body starting from the line with '{'."""
    depth = 0
    body_lines = []
    i = start_idx
    while i < len(lines):
        line = lines[i]
        depth += line.count("{") - line.count("}")
        body_lines.append(line)
        if depth <= 0:
            break
        i += 1
    return "\n".join(body_lines), i


def _analyze_function_body(
    func_name: str,
    body: str,
    vars_map: dict,
    call_args: dict | None = None,
) -> list[DownloadRef]:
    """Analyze a function body for download references."""
    refs = []
    local_vars = dict(vars_map)
    if call_args:
        local_vars.update(call_args)

    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Track local variable assignments
        m = _VAR_ASSIGN_RE.match(stripped)
        if m:
            local_vars[m.group(1)] = m.group(2)
            continue
        m = _VAR_ASSIGN_SINGLE_RE.match(stripped)
        if m:
            local_vars[m.group(1)] = m.group(2)
            continue

        # curl -o
        m = _CURL_O_RE.search(stripped)
        if m:
            url = _resolve_url_template(m.group(1), local_vars)
            dest = _resolve_url_template(m.group(2), local_vars)
            if url.startswith("http"):
                refs.append(DownloadRef(
                    url=url, dest_path=dest, tool="curl",
                    context=func_name, raw_line=stripped,
                ))
            continue

        # curl | (piped download)
        m = _CURL_PIPE_RE.search(stripped)
        if m:
            url = _resolve_url_template(m.group(1), local_vars)
            if url.startswith("http"):
                refs.append(DownloadRef(
                    url=url, dest_path="", tool="curl",
                    context=func_name, raw_line=stripped,
                ))
            continue

        # wget -O
        m = _WGET_RE.search(stripped)
        if m:
            url = _resolve_url_template(m.group(1), local_vars)
            dest = _resolve_url_template(m.group(2), local_vars)
            if url.startswith("http"):
                refs.append(DownloadRef(
                    url=url, dest_path=dest, tool="wget",
                    context=func_name, raw_line=stripped,
                ))
            continue

        # Any http URL
        if "http" in stripped:
            for m in _URL_RE.finditer(stripped):
                url = _clean(m.group(0))
                if url.startswith("http") and url not in [r.url for r in refs]:
                    refs.append(DownloadRef(
                        url=url, dest_path="", tool="url",
                        context=func_name, raw_line=stripped,
                    ))

    return refs


def analyze_script(content: str) -> ScriptAnalysis:
    """Analyze a shell script with variable resolution and function tracing."""
    analysis = ScriptAnalysis()
    lines = content.split("\n")
    vars_map = {}
    functions = {}

    # Pass 1: collect variable assignments
    for line in lines:
        m = _VAR_ASSIGN_RE.match(line.strip())
        if m:
            vars_map[m.group(1)] = m.group(2)
        m = _VAR_ASSIGN_SINGLE_RE.match(line.strip())
        if m:
            vars_map[m.group(1)] = m.group(2)

    # Pass 2: extract function definitions
    i = 0
    while i < len(lines):
        m = _FUNC_DEF_RE.match(lines[i].strip())
        if m:
            func_name = m.group(1)
            body, end_i = _extract_function_body(lines, i)
            functions[func_name] = body
            analysis.functions[func_name] = body
        i += 1

    # Pass 3: analyze global scope and function calls
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Update vars as we go
        m = _VAR_ASSIGN_RE.match(stripped)
        if m:
            vars_map[m.group(1)] = m.group(2)
            continue

        # OS/arch detection
        for pat in _OS_ARCH_PATTERNS:
            if pat.search(stripped):
                analysis.os_arch_dep = True
                break

        # Function call with URL argument — trace into it
        m = _FUNC_CALL_RE.match(stripped)
        if m:
            func_name = m.group(1)
            arg_raw = m.group(2)
            if func_name in functions:
                # Parse call args
                call_args = {}
                # Match: func "arg1" "arg2" "arg3"
                call_arg_matches = re.findall(r'"([^"]*)"', stripped)
                if not call_arg_matches:
                    call_arg_matches = stripped.split()[1:]

                # The function likely takes url_base, dest_dir, filename
                body = functions[func_name]
                # Find what parameter names the function uses
                param_re = re.compile(r'\$(\d+)')
                params = set(param_re.findall(body))
                for idx, p in enumerate(sorted(params, key=int)):
                    pnum = int(p)
                    if 0 < pnum <= len(call_arg_matches):
                        val = call_arg_matches[pnum - 1]
                        val = _resolve_url_template(val, vars_map)
                        call_args[f"${p}"] = val

                local_var_re = re.compile(r'local\s+(\w+)="\$(\d+)"')
                for vm in local_var_re.finditer(body):
                    lname = vm.group(1)
                    pnum = int(vm.group(2))
                    if 0 < pnum <= len(call_arg_matches):
                        val = call_arg_matches[pnum - 1]
                        val = _resolve_url_template(val, vars_map)
                        call_args["${" + lname + "}"] = val
                        call_args[lname] = val

                # Resolve URL templates in function body
                body_resolved = body
                # First pass: resolve named local vars
                for k, v in call_args.items():
                    if not k.startswith("$"):
                        body_resolved = body_resolved.replace("${" + k + "}", v)
                        body_resolved = body_resolved.replace("$" + k, v)
                # Second pass: resolve positional params $1, $2, etc.
                for k, v in call_args.items():
                    if k.startswith("$"):
                        varname = k.lstrip("${")
                        body_resolved = body_resolved.replace("${" + varname + "}", v)
                        body_resolved = body_resolved.replace("$" + varname, v)
                # Third pass: resolve global vars (ARCH, VER_PARAM, etc.)
                for k, v in vars_map.items():
                    body_resolved = body_resolved.replace("${" + k + "}", v)
                    body_resolved = body_resolved.replace("$" + k, v)

                func_refs = _analyze_function_body(
                    func_name, body_resolved, vars_map, call_args
                )
                resolved_urls = []
                for ref in func_refs:
                    ref.line_num = i
                    if ref.url not in [r.url for r in analysis.downloads]:
                        analysis.downloads.append(ref)
                        if ref.url not in analysis.urls_found:
                            analysis.urls_found.append(ref.url)
                        analysis.is_install_script = True
                        resolved_urls.append(ref.url)

                # Record call-site info for the rewriter
                if resolved_urls:
                    call_raw_args = re.findall(r'"([^"]*)"', stripped)
                    analysis.call_sites.append({
                        "line_num": i,
                        "func_name": func_name,
                        "raw_line": stripped,
                        "args": call_raw_args,
                        "resolved_urls": resolved_urls,
                    })
                continue

        # Direct curl
        m = _CURL_O_RE.search(stripped)
        if m:
            url = _resolve_url_template(m.group(1), vars_map)
            dest = _resolve_url_template(m.group(2), vars_map)
            if url.startswith("http"):
                analysis.downloads.append(DownloadRef(
                    url=url, dest_path=dest, tool="curl",
                    line_num=i, raw_line=stripped,
                ))
                if url not in analysis.urls_found:
                    analysis.urls_found.append(url)
                analysis.is_install_script = True
                continue

        m = _CURL_PIPE_RE.search(stripped)
        if m:
            url = _resolve_url_template(m.group(1), vars_map)
            if url.startswith("http"):
                analysis.downloads.append(DownloadRef(
                    url=url, tool="curl",
                    line_num=i, raw_line=stripped,
                ))
                if url not in analysis.urls_found:
                    analysis.urls_found.append(url)
                analysis.is_install_script = True
                continue

        # Direct wget
        m = _WGET_RE.search(stripped)
        if m:
            url = _resolve_url_template(m.group(1), vars_map)
            dest = _resolve_url_template(m.group(2), vars_map)
            if url.startswith("http"):
                analysis.downloads.append(DownloadRef(
                    url=url, dest_path=dest, tool="wget",
                    line_num=i, raw_line=stripped,
                ))
                if url not in analysis.urls_found:
                    analysis.urls_found.append(url)
                analysis.is_install_script = True
                continue

        # pip/npm/apt
        m = _PIP_RE.search(stripped)
        if m:
            analysis.downloads.append(DownloadRef(
                url=f"pip:{m.group(1)}", tool="pip", line_num=i, raw_line=stripped,
            ))
            analysis.is_install_script = True
            continue
        m = _NPM_RE.search(stripped)
        if m:
            analysis.downloads.append(DownloadRef(
                url=f"npm:{m.group(1)}", tool="npm", line_num=i, raw_line=stripped,
            ))
            analysis.is_install_script = True
            continue
        m = _APT_RE.search(stripped)
        if m:
            analysis.downloads.append(DownloadRef(
                url=f"apt:{m.group(1)}", tool="apt", line_num=i, raw_line=stripped,
            ))
            analysis.is_install_script = True
            continue

        # Bare URLs
        if "http" in stripped:
            for m in _URL_RE.finditer(stripped):
                url = _clean(m.group(0))
                if url.startswith("http") and url not in analysis.urls_found:
                    analysis.urls_found.append(url)

    # Deduplicate downloads
    seen = set()
    unique = []
    for ref in analysis.downloads:
        if ref.url not in seen:
            seen.add(ref.url)
            unique.append(ref)
    analysis.downloads = unique

    return analysis
