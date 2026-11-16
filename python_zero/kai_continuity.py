"""KaiContinuity: provider-neutral, local-first state checkpoints for Python Zero.

Standard library only. No network calls. No automatic model selection.
This module does not replace a backup of the full conversation archive.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ContinuityError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class KaiContinuity:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory).expanduser().resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "checkpoint.json"
        self.previous = self.directory / "checkpoint.previous.json"

    def save(self, state: dict[str, Any]) -> Path:
        """Save JSON-compatible state atomically, retaining one previous checkpoint."""
        if not isinstance(state, dict):
            raise TypeError("state must be a dictionary")
        payload = {
            "schema": "kai-continuity/v1",
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "state": state,
            "sha256": hashlib.sha256(_canonical(state)).hexdigest(),
        }
        raw = _canonical(payload)
        fd, name = tempfile.mkstemp(prefix=".checkpoint-", suffix=".tmp", dir=self.directory)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            if self.path.exists():
                os.replace(self.path, self.previous)
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        return self.path

    def load(self) -> dict[str, Any]:
        """Load the latest valid checkpoint, falling back to the previous one."""
        for path in (self.path, self.previous):
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                state = payload["state"]
                if payload.get("schema") != "kai-continuity/v1" or not isinstance(state, dict):
                    continue
                if hashlib.sha256(_canonical(state)).hexdigest() != payload.get("sha256"):
                    continue
                return state
            except (OSError, ValueError, KeyError, TypeError):
                continue
        raise ContinuityError("No valid checkpoint available; original archive remains untouched.")
