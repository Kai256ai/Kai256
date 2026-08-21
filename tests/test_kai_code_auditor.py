import json
import tempfile
import unittest
from pathlib import Path

from kai_code_auditor import KaiCodeAuditor, main


class KaiCodeAuditorTests(unittest.TestCase):
    def test_known_bad_source_reports_each_structural_problem(self):
        source = """
import imaginary_library
class Broken:
    def __init__(self):
        self.ready = True
    def run(self):
        return missing() + self.counter
    def orphan(self):
        return 42
"""
        report = KaiCodeAuditor().audit_source(source)
        kinds = {finding.kind for finding in report.findings}
        self.assertTrue({"unresolved_import", "undefined_reference", "unreachable_function", "uninitialized_attribute"} <= kinds)
        self.assertFalse(report.clean)
        self.assertFalse(json.loads(report.to_machine_json())["clean"])

    def test_call_graph_reachability_cycle_and_async_functions(self):
        source = """
async def run():
    await first()
def first():
    return second()
def second():
    return first()
"""
        report = KaiCodeAuditor().audit_source(source)
        self.assertEqual(report.call_graph["run"], ["first"])
        self.assertFalse(any(item.kind == "unreachable_function" for item in report.findings))
        self.assertEqual(sum(item.kind == "cycle" for item in report.findings), 1)

    def test_wildcard_ignores_and_local_imports(self):
        source = """
import local_module
def run():
    ignored_call()
def test_helper():
    return 1
"""
        auditor = KaiCodeAuditor(
            ignore_functions={"test_*"},
            ignore_undefined={"ignored_*"},
            local_modules={"local_module"},
        )
        self.assertEqual(auditor.audit_source(source).findings, [])

    def test_methods_and_inherited_methods_are_not_data_attributes(self):
        source = """
class Worker:
    @property
    def ready(self):
        return True
    def run(self):
        self.perform()
        return self.ready
    def perform(self):
        return None
"""
        report = KaiCodeAuditor().audit_source(source)
        self.assertFalse(any(item.kind == "uninitialized_attribute" for item in report.findings))

    def test_cli_returns_nonzero_only_for_blocking_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            clean = Path(directory, "clean.py")
            clean.write_text("def run():\n    print('ok')\n", encoding="utf-8")
            broken = Path(directory, "broken.py")
            broken.write_text("import no_such_dependency\n", encoding="utf-8")
            self.assertEqual(main([str(clean), "--json"]), 0)
            self.assertEqual(main([str(broken)]), 1)


if __name__ == "__main__":
    unittest.main()
