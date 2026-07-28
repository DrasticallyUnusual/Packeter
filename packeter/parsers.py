# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Parse source commands to identify tool and extract arguments."""

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class ToolType(Enum):
    GIT = "git"
    NPM = "npm"
    PIP = "pip"
    CARGO = "cargo"
    URL = "url"
    WINGET = "winget"
    CHOCO = "choco"
    GO = "go"
    GEM = "gem"
    DOCKER = "docker"
    COMPOSER = "composer"
    APT = "apt"
    DNF = "dnf"
    WSL = "wsl"
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    tool: ToolType
    raw: str
    args: list[str]
    label: str


_GIT_CLONE_RE = re.compile(
    r"^git\s+clone\s+(.+?)(?:\s+--(?:depth|branch|single-branch).*)*$",
    re.IGNORECASE,
)

_NPM_INSTALL_RE = re.compile(
    r"^npm\s+(?:install|i)\s+(.+)$",
    re.IGNORECASE,
)

_PIP_INSTALL_RE = re.compile(
    r"^pip(?:3)?\s+(?:install|download)\s+(.+?)(?:\s+--(?:target|dest|d).*)*$",
    re.IGNORECASE,
)

_CARGO_INSTALL_RE = re.compile(
    r"^cargo\s+install\s+(.+?)(?:\s+--.*)*$",
    re.IGNORECASE,
)

_WINGET_INSTALL_RE = re.compile(
    r"^winget\s+install\s+(.+?)(?:\s+--.*)*$",
    re.IGNORECASE,
)

_CHOCO_INSTALL_RE = re.compile(
    r"^choco\s+install\s+(.+?)(?:\s+--.*)*$",
    re.IGNORECASE,
)

_GO_INSTALL_RE = re.compile(
    r"^go\s+install\s+(.+?)(?:@.+)?(?:\s+--.*)?$",
    re.IGNORECASE,
)

_GEM_INSTALL_RE = re.compile(
    r"^gem\s+install\s+(.+?)(?:\s+--.*)*$",
    re.IGNORECASE,
)

_DOCKER_PULL_RE = re.compile(
    r"^docker\s+pull\s+(.+?)(?:\s+--.*)*$",
    re.IGNORECASE,
)

_COMPOSER_REQUIRE_RE = re.compile(
    r"^composer\s+(?:require|install)\s+(.+?)(?:\s+--.*)*$",
    re.IGNORECASE,
)

_APT_DOWNLOAD_RE = re.compile(
    r"^apt(?:-get)?\s+download\s+(.+?)(?:\s+--.*)*$",
    re.IGNORECASE,
)

_DNF_DOWNLOAD_RE = re.compile(
    r"^dnf\s+download\s+(.+?)(?:\s+--.*)*$",
    re.IGNORECASE,
)

_WSL_INSTALL_RE = re.compile(
    r"^wsl(?:\.exe)?\s+--install(?:\s+--web-download)?(?:\s+-d\s+(\S+))?(?:\s+.*)?$",
    re.IGNORECASE,
)

_WSL_UPDATE_RE = re.compile(
    r"^wsl(?:\.exe)?\s+--update(?:\s+--pre-release)?(?:\s+.*)?$",
    re.IGNORECASE,
)

_WSL_DOWNLOAD_RE = re.compile(
    r"^wsl(?:\.exe)?\s+--install\s+--download\s+(\S+)(?:\s+.*)?$",
    re.IGNORECASE,
)

# curl/wget ... URL | sh/bash  (pipe install scripts)
_CURL_PIPE_RE = re.compile(
    r"^curl\s+(?:-[a-zA-Z]+\s+)*?(https?://\S+)\s*\|\s*(?:sudo\s+)?(?:ba)?sh",
    re.IGNORECASE,
)
_WGET_PIPE_RE = re.compile(
    r"^wget\s+(?:-[a-zA-Z]+\s+)*?(?:-\S+\s+)*?(https?://\S+)(?:\s+[^|]*)?\s*\|\s*(?:sudo\s+)?(?:ba)?sh",
    re.IGNORECASE,
)


def _extract_repo_name(url: str) -> str:
    """Extract repo name from a git URL."""
    url = url.strip().rstrip("/")
    url = re.sub(r"\.git$", "", url)
    return url.rsplit("/", 1)[-1] if "/" in url else url


def _extract_package_name(spec: str) -> str:
    """Extract package name from npm/pip/cargo spec like 'pkg@1.0' or 'pkg[extra]'."""
    name = spec.split("@")[0] if "@" in spec else spec
    name = name.split("[")[0]
    name = name.strip().strip('"').strip("'")
    return name


def _extract_docker_image_name(spec: str) -> str:
    """Extract image name from docker pull spec like 'nginx:latest'."""
    name = spec.split(":")[0]
    name = name.strip().strip('"').strip("'")
    # For registry paths like docker.io/library/nginx, take last part
    return name.rsplit("/", 1)[-1] if "/" in name else name


def parse(source: str) -> ParsedCommand:
    source = source.strip()
    if not source:
        return ParsedCommand(ToolType.UNKNOWN, source, [], "empty")

    # git clone
    m = _GIT_CLONE_RE.match(source)
    if m:
        url = m.group(1).strip().strip('"').strip("'")
        name = _extract_repo_name(url)
        return ParsedCommand(ToolType.GIT, source, [url, name], name)

    # npm install
    m = _NPM_INSTALL_RE.match(source)
    if m:
        spec = m.group(1).strip()
        name = _extract_package_name(spec)
        return ParsedCommand(ToolType.NPM, source, [spec, name], name)

    # pip install / pip download
    m = _PIP_INSTALL_RE.match(source)
    if m:
        spec = m.group(1).strip()
        name = _extract_package_name(spec)
        return ParsedCommand(ToolType.PIP, source, [spec, name], name)

    # cargo install
    m = _CARGO_INSTALL_RE.match(source)
    if m:
        spec = m.group(1).strip()
        name = _extract_package_name(spec)
        return ParsedCommand(ToolType.CARGO, source, [spec, name], name)

    # winget install
    m = _WINGET_INSTALL_RE.match(source)
    if m:
        spec = m.group(1).strip()
        name = _extract_package_name(spec)
        return ParsedCommand(ToolType.WINGET, source, [spec, name], name)

    # choco install
    m = _CHOCO_INSTALL_RE.match(source)
    if m:
        spec = m.group(1).strip()
        name = _extract_package_name(spec)
        return ParsedCommand(ToolType.CHOCO, source, [spec, name], name)

    # go install
    m = _GO_INSTALL_RE.match(source)
    if m:
        spec = m.group(1).strip()
        name = _extract_package_name(spec)
        return ParsedCommand(ToolType.GO, source, [spec, name], name)

    # gem install
    m = _GEM_INSTALL_RE.match(source)
    if m:
        spec = m.group(1).strip()
        name = _extract_package_name(spec)
        return ParsedCommand(ToolType.GEM, source, [spec, name], name)

    # docker pull
    m = _DOCKER_PULL_RE.match(source)
    if m:
        spec = m.group(1).strip()
        name = _extract_docker_image_name(spec)
        return ParsedCommand(ToolType.DOCKER, source, [spec, name], name)

    # composer require / composer install
    m = _COMPOSER_REQUIRE_RE.match(source)
    if m:
        spec = m.group(1).strip()
        name = _extract_package_name(spec)
        return ParsedCommand(ToolType.COMPOSER, source, [spec, name], name)

    # apt download
    m = _APT_DOWNLOAD_RE.match(source)
    if m:
        spec = m.group(1).strip()
        name = _extract_package_name(spec)
        return ParsedCommand(ToolType.APT, source, [spec, name], name)

    # dnf download
    m = _DNF_DOWNLOAD_RE.match(source)
    if m:
        spec = m.group(1).strip()
        name = _extract_package_name(spec)
        return ParsedCommand(ToolType.DNF, source, [spec, name], name)

    # wsl --install --download <distro>
    m = _WSL_DOWNLOAD_RE.match(source)
    if m:
        distro = m.group(1).strip()
        return ParsedCommand(ToolType.WSL, source, ["download", distro], f"wsl-{distro}")

    # wsl --install [-d distro]
    m = _WSL_INSTALL_RE.match(source)
    if m:
        distro = m.group(1)
        if distro:
            distro = distro.strip()
            return ParsedCommand(ToolType.WSL, source, ["install", distro], f"wsl-{distro}")
        return ParsedCommand(ToolType.WSL, source, ["install"], "wsl")

    # wsl --update [--pre-release]
    m = _WSL_UPDATE_RE.match(source)
    if m:
        pre_release = "--pre-release" in source
        args = ["update", "--pre-release"] if pre_release else ["update"]
        return ParsedCommand(ToolType.WSL, source, args, "wsl-update")

    # curl/wget ... URL | sh/bash  (pipe install scripts -> download the script)
    m = _CURL_PIPE_RE.match(source)
    if m:
        url = m.group(1)
        script_name = url.rsplit("/", 1)[-1] if "/" in url else "install.sh"
        return ParsedCommand(ToolType.URL, source, [url, script_name], script_name)

    m = _WGET_PIPE_RE.match(source)
    if m:
        url = m.group(1)
        script_name = url.rsplit("/", 1)[-1] if "/" in url else "install.sh"
        return ParsedCommand(ToolType.URL, source, [url, script_name], script_name)

    # Direct URL
    parsed = urlparse(source)
    if parsed.scheme in ("http", "https"):
        path = parsed.path.rstrip("/")
        name = path.rsplit("/", 1)[-1] if "/" in path else "download"
        return ParsedCommand(ToolType.URL, source, [source, name], name)

    return ParsedCommand(ToolType.UNKNOWN, source, [], source[:60] or "unknown")
