"""Unit tests for Canvas Integrity; run with python -m unittest tests.test_canvas_integrity."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from python_zero.canvas_integrity import CanvasIntegrity, IntegrityError


class CanvasIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "memory.py").write_text("ready = True\n", encoding="utf-8")
        (self.root / "core.py").write_text("ready = True\n", encoding="utf-8")
        self.manifest = {
            "schema": "canvas-integrity/v1",
            "components": {
                name: {
                    "path": name + ".py",
                    "sha256": hashlib.sha256((self.root / (name + ".py")).read_bytes()).hexdigest(),
                    "requires": ["memory"] if name == "core" else [],
                }
                for name in ("memory", "core")
            },
        }

    def test_valid_dependency_graph(self):
        CanvasIntegrity(self.root, self.manifest).require_ready(("core",))

    def test_detects_tampering(self):
        (self.root / "memory.py").write_text("ready = False\n", encoding="utf-8")
        report = CanvasIntegrity(self.root, self.manifest).verify(("core",))
        self.assertFalse(report.ok)
        self.assertIn("Integrity mismatch: memory", report.errors)
        with self.assertRaises(IntegrityError):
            CanvasIntegrity(self.root, self.manifest).require_ready(("core",))

    def test_missing_dependency_fails_closed(self):
        self.manifest["components"]["core"]["requires"] = ["unknown"]
        self.assertIn("Missing component: unknown", CanvasIntegrity(self.root, self.manifest).verify(("core",)).errors)

    def test_path_escape_is_rejected(self):
        self.manifest["components"]["core"]["path"] = "../outside.py"
        self.assertIn("Missing or unsafe file: core", CanvasIntegrity(self.root, self.manifest).verify(("core",)).errors)

    def test_cycle_is_rejected(self):
        self.manifest["components"]["memory"]["requires"] = ["core"]
        self.assertIn("Cyclic dependency: core", CanvasIntegrity(self.root, self.manifest).verify(("core",)).errors)


if __name__ == "__main__":
    unittest.main()
