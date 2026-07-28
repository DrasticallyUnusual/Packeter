# Tool: Packeter v1
# Author: A.O
# Date: 25 July 2026
# License: MIT
"""Core download orchestration."""

import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from .handlers import (
    AptHandler,
    CargoHandler,
    ChocoHandler,
    ComposerHandler,
    DockerHandler,
    DnfHandler,
    GemHandler,
    GitHandler,
    GoHandler,
    NpmHandler,
    PipHandler,
    UrlHandler,
    WingetHandler,
    WslHandler,
)
from .parsers import ToolType, parse


class JobStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


_HANDLERS = {
    ToolType.GIT: GitHandler,
    ToolType.NPM: NpmHandler,
    ToolType.PIP: PipHandler,
    ToolType.CARGO: CargoHandler,
    ToolType.URL: UrlHandler,
    ToolType.WINGET: WingetHandler,
    ToolType.CHOCO: ChocoHandler,
    ToolType.GO: GoHandler,
    ToolType.GEM: GemHandler,
    ToolType.DOCKER: DockerHandler,
    ToolType.COMPOSER: ComposerHandler,
    ToolType.APT: AptHandler,
    ToolType.DNF: DnfHandler,
    ToolType.WSL: WslHandler,
}


@dataclass
class Job:
    id: str
    source: str
    status: JobStatus = JobStatus.QUEUED
    result: Optional[dict] = None
    logs: list = field(default_factory=list)


class DownloadManager:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def set_output_dir(self, path: Path):
        self.output_dir = path

    def add_job(self, source: str, emit_fn: Callable) -> str:
        parsed = parse(source)
        job_id = uuid.uuid4().hex[:8]
        job = Job(id=job_id, source=source)

        with self._lock:
            self._jobs[job_id] = job

        thread = threading.Thread(
            target=self._run_job, args=(job, parsed, emit_fn), daemon=True
        )
        thread.start()
        return job_id

    def get_all_jobs(self):
        with self._lock:
            return list(self._jobs.values())

    def get_successful_jobs(self):
        with self._lock:
            return [j for j in self._jobs.values()
                    if j.status == JobStatus.SUCCESS and j.result]

    def _run_job(self, job: Job, parsed, emit_fn: Callable):
        def emit(level: str, message: str):
            entry = {"level": level, "message": message}
            job.logs.append(entry)
            emit_fn(job.id, entry)

        with self._lock:
            job.status = JobStatus.RUNNING
        emit_fn(job.id, {"level": "status", "message": "running"})

        handler = _HANDLERS.get(parsed.tool)
        if handler is None:
            msg = f"Unsupported command: {parsed.raw}"
            emit("error", msg)
            with self._lock:
                job.status = JobStatus.FAILED
                job.result = {"success": False, "error": msg}
            emit_fn(job.id, {"level": "status", "message": "failed"})
            return

        if not handler.is_available():
            tool_name = parsed.tool.value
            msg = f"'{tool_name}' is not installed or not in PATH"
            emit("error", msg)
            with self._lock:
                job.status = JobStatus.FAILED
                job.result = {"success": False, "error": msg}
            emit_fn(job.id, {"level": "status", "message": "failed"})
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)
        result = handler.run(parsed, self.output_dir, emit)

        with self._lock:
            job.result = result
            job.status = (
                JobStatus.SUCCESS if result.get("success") else JobStatus.FAILED
            )

        status_msg = "success" if result.get("success") else "failed"
        emit_fn(job.id, {"level": "status", "message": status_msg})
