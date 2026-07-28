# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Download handlers for all supported tool types."""

from .apt import AptHandler
from .cargo import CargoHandler
from .choco import ChocoHandler
from .composer import ComposerHandler
from .docker import DockerHandler
from .dnf import DnfHandler
from .gem import GemHandler
from .git import GitHandler
from .go import GoHandler
from .npm import NpmHandler
from .pip import PipHandler
from .url import UrlHandler
from .winget import WingetHandler
from .wsl import WslHandler

__all__ = [
    "GitHandler",
    "NpmHandler",
    "PipHandler",
    "CargoHandler",
    "UrlHandler",
    "WingetHandler",
    "ChocoHandler",
    "GoHandler",
    "GemHandler",
    "DockerHandler",
    "ComposerHandler",
    "AptHandler",
    "DnfHandler",
    "WslHandler",
]
