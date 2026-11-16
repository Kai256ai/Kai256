"""KaiContinuity: engine-agnostic continuity primitives for Python Zero.

Standalone reference module. Does not install or alter an existing router.
No external dependencies, no model provider required.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Any


@dataclass(frozen=True)
class ContinuityConfig:
    state_dir: Path = Path.home() / ".python_zero" / "continuity"
    # Only adapters explicitly registered by the application can be selected.
    allow_remote: bool = False


class NoEngineAvailable(RuntimeError):
    pass


class EngineRouter:
    """Fail over across registered adapters; never silently enable remote APIs."""

    def __init__(self, config: ContinuityConfig | None = None):
        self.config = config or ContinuityConfig()
        self._engines: list[tuple[str, Callable[[str], str], bool]] = []

    def register(self, name: str, respond: Callable[[str], str], *, remote: bool = False) -> None:
        if not name or any(existing == name for existing, _, _ in self._engines):
            raise ValueError("Engine name must be unique and nonempty")
        self._engines.append((name, respond, remote))

    def respond(self, prompt: str) -> dict[str, str]:
        failures: list[str] = []
        for name, engine, remote in self._engines:
            if remote and not self.config.allow_remote:
                continue
            try:
                return {"engine": name, "response": engine(prompt)}
            except Exception as exc:
                failures.append(f"{name}: {type(exc).__name__}")
        raise NoEngineAvailable("No permitted engine succeeded: " + ", ".join(failures))


class LocalJournal:
    """Append-only local JSONL with content hashes for corruption detection.

    Hashes detect accidental changes, not malicious tampering. Keep separate
    encrypted, versioned backups; never commit private conversation archives.
    """

    def __init__(self, config: ContinuityConfig | None = None):
        self.config = config or ContinuityConfig()
        self.config.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.config.state_dir / "events.jsonl"

    def append(self, kind: str, payload: dict[str, Any]) -> str:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "payload": payload,
        }
        serialized = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        record = json.dumps({"event": event, "sha256": digest}, ensure_ascii=False)
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as stream:
            stream.write(record + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return digest

    def verify(self) -> bool:
        if not self.path.exists():
            return True
        with self.path.open(encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                serialized = json.dumps(record["event"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                if hashlib.sha256(serialized.encode("utf-8")).hexdigest() != record["sha256"]:
                    return False
        return True
