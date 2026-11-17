"""Canvas Integrity: offline dependency and file-integrity gate for Python Zero.

No network, code execution, telemetry, or automatic repair.
Manifest hashes are a consistency check, not proof of authorship or intent.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class IntegrityError(RuntimeError):
    """A required component failed an integrity check."""


@dataclass(frozen=True)
class IntegrityReport:
    ok: bool
    errors: tuple[str, ...]

    def require_ok(self) -> None:
        if not self.ok:
            raise IntegrityError("; ".join(self.errors))


class CanvasIntegrity:
    """Verify a declared local component graph before activation.

    Manifest example:
      {"schema": "canvas-integrity/v1",
       "components": {"core": {"path": "core.py", "sha256": "...",
                                "requires": ["memory"]},
                      "memory": {"path": "memory.py", "sha256": "...",
                                 "requires": []}}}

    Treat the manifest as trusted configuration. Keep it and its signatures
    under owner control. Hashes alone cannot prevent malicious replacement
    of both a file and its manifest.
    """

    def __init__(self, root: str | Path, manifest: Mapping):
        self.root = Path(root).expanduser().resolve()
        self.manifest = manifest

    @classmethod
    def from_file(cls, root: str | Path, manifest_path: str | Path) -> "CanvasIntegrity":
        path = Path(manifest_path).expanduser().resolve()
        return cls(root, json.loads(path.read_text(encoding="utf-8")))

    def verify(self, selected: tuple[str, ...] | None = None) -> IntegrityReport:
        errors: list[str] = []
        if self.manifest.get("schema") != "canvas-integrity/v1":
            return IntegrityReport(False, ("Unsupported manifest schema",))
        components = self.manifest.get("components")
        if not isinstance(components, dict):
            return IntegrityReport(False, ("Invalid components mapping",))
        names = selected if selected is not None else tuple(components)
        visited: set[str] = set()
        visiting: set[str] = set()

        def check(name: str) -> None:
            if name in visiting:
                errors.append(f"Cyclic dependency: {name}")
                return
            if name in visited:
                return
            component = components.get(name)
            if not isinstance(component, dict):
                errors.append(f"Missing component: {name}")
                return
            visiting.add(name)
            dependencies = component.get("requires", [])
            if not isinstance(dependencies, list) or not all(isinstance(x, str) for x in dependencies):
                errors.append(f"Invalid dependencies: {name}")
            else:
                for dependency in dependencies:
                    check(dependency)
            visiting.remove(name)
            visited.add(name)
            relative = component.get("path")
            expected = component.get("sha256")
            if not isinstance(relative, str) or not relative or not isinstance(expected, str) or len(expected) != 64:
                errors.append(f"Invalid file specification: {name}")
                return
            target = (self.root / relative).resolve()
            if not target.is_relative_to(self.root) or not target.is_file():
                errors.append(f"Missing or unsafe file: {name}")
                return
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            if digest != expected.lower():
                errors.append(f"Integrity mismatch: {name}")

        for name in names:
            check(name)
        return IntegrityReport(not errors, tuple(errors))

    def require_ready(self, selected: tuple[str, ...] | None = None) -> None:
        """Fail closed: caller must invoke this before enabling protected modules."""
        self.verify(selected).require_ok()
