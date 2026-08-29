#!/usr/bin/env python3
"""Static, dependency-free structural auditing for Python source files."""

from __future__ import annotations

import argparse
import ast
import builtins
import fnmatch
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

STDLIB_MODULES: Set[str] = set(getattr(sys, "stdlib_module_names", set()))


@dataclass
class Finding:
    kind: str
    severity: str
    location: str
    line: int
    detail: str
    extra: Dict[str, int] = field(default_factory=dict)


@dataclass
class AuditReport:
    findings: List[Finding] = field(default_factory=list)
    call_graph: Dict[str, List[str]] = field(default_factory=dict)
    functions: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    grid: Dict[str, Dict[str, int]] = field(default_factory=dict)

    @property
    def clean(self) -> bool:
        return not any(item.severity == "block" for item in self.findings)

    def to_machine_json(self) -> str:
        counts = {
            severity: sum(item.severity == severity for item in self.findings)
            for severity in ("block", "warn", "info")
        }
        return json.dumps(
            {
                "findings": [asdict(item) for item in self.findings],
                "call_graph": self.call_graph,
                "functions": self.functions,
                "entry_points": self.entry_points,
                "grid": self.grid,
                "block_count": counts["block"],
                "warn_count": counts["warn"],
                "info_count": counts["info"],
                "clean": self.clean,
            },
            ensure_ascii=False,
            indent=2,
        )

    def to_human_summary(self) -> str:
        groups = {
            severity: [item for item in self.findings if item.severity == severity]
            for severity in ("block", "warn", "info")
        }
        lines = [
            f"Audit: {len(groups['block'])} blocking, "
            f"{len(groups['warn'])} warning, {len(groups['info'])} info."
        ]
        if not self.findings:
            lines.append(
                "No structural issues found. This does NOT mean the business logic is "
                "correct — that requires execution or human review of intent."
            )
        for item in groups["block"] + groups["warn"] + groups["info"]:
            depth = (
                f" (depth {item.extra.get('cycle_depth', '?')})"
                if item.kind == "cycle" and item.extra
                else ""
            )
            lines.append(
                f"  [{item.severity.upper()}] {item.kind} @ "
                f"{item.location}:{item.line}{depth} → {item.detail}"
            )
        return "\n".join(lines)


class KaiCodeAuditor:
    """Build a conservative structural report from Python's abstract syntax tree."""

    def __init__(
        self,
        extra_allowed_imports: Optional[Set[str]] = None,
        entry_point_names: Optional[Set[str]] = None,
        ignore_functions: Optional[Set[str]] = None,
        ignore_attributes: Optional[Set[str]] = None,
        ignore_imports: Optional[Set[str]] = None,
        ignore_undefined: Optional[Set[str]] = None,
        local_modules: Optional[Set[str]] = None,
    ) -> None:
        self.extra_allowed = extra_allowed_imports or set()
        self.entry_point_names = entry_point_names or {"main", "run", "__init__"}
        self.ignore_functions = ignore_functions or set()
        self.ignore_attributes = ignore_attributes or set()
        self.ignore_imports = ignore_imports or set()
        self.ignore_undefined = ignore_undefined or set()
        self.local_modules = local_modules or set()

    @staticmethod
    def _matches(name: str, patterns: Set[str]) -> bool:
        return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)

    def audit_source(self, source: str, filename: str = "<string>") -> AuditReport:
        report = AuditReport()
        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError as error:
            report.findings.append(
                Finding("syntax_error", "block", filename, error.lineno or 0, str(error))
            )
            return report

        self._check_imports(tree, report)
        functions = self._index_functions(tree)
        report.functions = sorted(functions)
        report.call_graph = self._build_call_graph(functions)
        self._check_undefined_calls(tree, functions, report)
        self._check_reachability(functions, report.call_graph, report)
        self._check_self_attributes(tree, report)
        self._check_cycles(report.call_graph, report)
        self._build_grid(functions, report.call_graph, report)
        return report

    def audit_file(self, path: Path | str) -> AuditReport:
        file_path = Path(path)
        return self.audit_source(file_path.read_text(encoding="utf-8"), str(file_path))

    def _check_imports(self, tree: ast.AST, report: AuditReport) -> None:
        for node in ast.walk(tree):
            names: Iterable[str] = ()
            if isinstance(node, ast.Import):
                names = (alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = (node.module,)
            for module in names:
                root = module.split(".")[0]
                if not self._matches(root, self.ignore_imports):
                    self._verify_module(root, node.lineno, report)

    def _verify_module(self, root: str, line: int, report: AuditReport) -> None:
        allowed = STDLIB_MODULES | self.extra_allowed | self.local_modules | {"__future__"}
        if root not in allowed:
            report.findings.append(
                Finding(
                    "unresolved_import",
                    "block",
                    "module",
                    line,
                    f"'{root}' is not in stdlib, the audited source tree, or "
                    "extra_allowed_imports.",
                )
            )

    def _index_functions(self, tree: ast.AST) -> Dict[str, ast.AST]:
        index: Dict[str, ast.AST] = {}
        auditor = self

        class Visitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.classes: List[str] = []

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                self.classes.append(node.name)
                self.generic_visit(node)
                self.classes.pop()

            def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
                qualified = ".".join(self.classes + [node.name])
                if not auditor._matches(qualified, auditor.ignore_functions) and not auditor._matches(
                    node.name, auditor.ignore_functions
                ):
                    index[qualified] = node
                self.generic_visit(node)

            visit_FunctionDef = _function
            visit_AsyncFunctionDef = _function

        Visitor().visit(tree)
        return index

    def _build_call_graph(self, functions: Dict[str, ast.AST]) -> Dict[str, List[str]]:
        graph = {name: [] for name in functions}
        by_simple: Dict[str, List[str]] = {}
        for name in functions:
            by_simple.setdefault(name.rsplit(".", 1)[-1], []).append(name)
        for caller, node in functions.items():
            targets: Set[str] = set()
            caller_class = caller.rpartition(".")[0]
            for child in self._walk_function_body(node):
                if not isinstance(child, ast.Call):
                    continue
                simple = self._resolve_call_name(child)
                candidates = by_simple.get(simple or "", [])
                same_class = f"{caller_class}.{simple}" if caller_class else ""
                if same_class in candidates:
                    targets.add(same_class)
                elif len(candidates) == 1:
                    targets.add(candidates[0])
            graph[caller] = sorted(targets)
        return graph

    @staticmethod
    def _walk_function_body(node: ast.AST) -> Iterable[ast.AST]:
        """Walk a function without attributing nested function bodies to its caller."""
        stack = list(ast.iter_child_nodes(node))
        while stack:
            child = stack.pop()
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            yield child
            stack.extend(ast.iter_child_nodes(child))

    @staticmethod
    def _resolve_call_name(call: ast.Call) -> Optional[str]:
        if isinstance(call.func, ast.Name):
            return call.func.id
        if isinstance(call.func, ast.Attribute):
            return call.func.attr
        return None

    def _check_undefined_calls(
        self, tree: ast.AST, functions: Dict[str, ast.AST], report: AuditReport
    ) -> None:
        known = {name.rsplit(".", 1)[-1] for name in functions} | set(dir(builtins))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                known.add(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                known.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                known.update(target.id for target in targets if isinstance(target, ast.Name))
        for qualified, node in functions.items():
            parameters = {arg.arg for arg in node.args.args + node.args.kwonlyargs}
            parameters.update(arg.arg for arg in node.args.posonlyargs)
            for child in self._walk_function_body(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    name = child.func.id
                    if (
                        name not in known
                        and name not in parameters
                        and not self._matches(name, self.ignore_undefined)
                    ):
                        report.findings.append(
                            Finding(
                                "undefined_reference",
                                "warn",
                                qualified,
                                child.lineno,
                                f"Call to '{name}()' has no matching def/class/import in this module.",
                            )
                        )

    def _check_reachability(
        self,
        functions: Dict[str, ast.AST],
        graph: Dict[str, List[str]],
        report: AuditReport,
    ) -> None:
        frontier = {
            name
            for name in functions
            if name.rsplit(".", 1)[-1] in self.entry_point_names
            or name.rsplit(".", 1)[-1].startswith("__")
            and name.rsplit(".", 1)[-1].endswith("__")
        }
        report.entry_points = sorted(frontier)
        reachable: Set[str] = set()
        stack = list(frontier)
        while stack:
            current = stack.pop()
            if current not in reachable:
                reachable.add(current)
                stack.extend(graph.get(current, []))
        for name, node in functions.items():
            if name not in reachable:
                report.findings.append(
                    Finding(
                        "unreachable_function",
                        "warn",
                        name,
                        node.lineno,
                        "Defined but never called from a declared entry point; add its simple "
                        "name to entry_point_names when it is an external API.",
                    )
                )

    def _check_self_attributes(self, tree: ast.AST, report: AuditReport) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            assigned: Set[str] = set()
            reads: Dict[str, int] = {}
            methods = {
                statement.name
                for statement in node.body
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            called_attributes = {
                call.func.attr
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == "self"
            }
            for statement in node.body:
                targets = statement.targets if isinstance(statement, ast.Assign) else []
                if isinstance(statement, ast.AnnAssign):
                    targets = [statement.target]
                assigned.update(target.id for target in targets if isinstance(target, ast.Name))
            for child in ast.walk(node):
                if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name):
                    if child.value.id != "self":
                        continue
                    if isinstance(child.ctx, ast.Store):
                        assigned.add(child.attr)
                    elif (
                        isinstance(child.ctx, ast.Load)
                        and child.attr not in methods
                        and child.attr not in called_attributes
                        and not self._matches(child.attr, self.ignore_attributes)
                    ):
                        reads.setdefault(child.attr, child.lineno)
            for attribute, line in reads.items():
                if attribute not in assigned:
                    report.findings.append(
                        Finding(
                            "uninitialized_attribute",
                            "block",
                            node.name,
                            line,
                            f"self.{attribute} is read but never assigned in class '{node.name}'.",
                        )
                    )

    def _check_cycles(self, graph: Dict[str, List[str]], report: AuditReport) -> None:
        color = {name: 0 for name in graph}
        path: List[str] = []
        seen: Set[frozenset[str]] = set()

        def visit(name: str) -> None:
            color[name] = 1
            path.append(name)
            for neighbour in graph.get(name, []):
                if color.get(neighbour) == 1:
                    cycle = path[path.index(neighbour) :] + [neighbour]
                    identity = frozenset(cycle)
                    if identity not in seen:
                        seen.add(identity)
                        report.findings.append(
                            Finding(
                                "cycle",
                                "info",
                                name,
                                0,
                                f"Cyclic call chain: {' → '.join(cycle)}",
                                {"cycle_depth": len(cycle) - 1},
                            )
                        )
                elif color.get(neighbour) == 0:
                    visit(neighbour)
            path.pop()
            color[name] = 2

        for name in graph:
            if color[name] == 0:
                visit(name)

    @staticmethod
    def _build_grid(
        functions: Dict[str, ast.AST], graph: Dict[str, List[str]], report: AuditReport
    ) -> None:
        blocked = {item.location for item in report.findings if item.severity == "block"}
        for name in functions:
            report.grid[name] = {
                "is_called_by_others": int(any(name in values for values in graph.values())),
                "calls_others": int(bool(graph[name])),
                "is_entry_point": int(name in report.entry_points),
                "has_blocking_finding": int(name in blocked or name.rpartition(".")[0] in blocked),
            }


def _python_files(paths: List[str]) -> List[Path]:
    files: Set[Path] = set()
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            files.update(item for item in path.rglob("*.py") if ".git" not in item.parts)
        elif path.suffix == ".py":
            files.add(path)
    return sorted(files)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Python source structure with the AST.")
    parser.add_argument("paths", nargs="+", help="Python files or directories")
    parser.add_argument("--json", action="store_true", help="emit a JSON object keyed by path")
    parser.add_argument("--allow-import", action="append", default=[], metavar="MODULE")
    parser.add_argument("--entry-point", action="append", default=[], metavar="NAME")
    args = parser.parse_args(argv)
    files = _python_files(args.paths)
    if not files:
        parser.error("no Python files found")
    local_modules = {path.stem for path in files}
    entries = set(args.entry_point) or None
    auditor = KaiCodeAuditor(set(args.allow_import), entries, local_modules=local_modules)
    reports = {str(path): auditor.audit_file(path) for path in files}
    if args.json:
        print(json.dumps({path: json.loads(report.to_machine_json()) for path, report in reports.items()}, ensure_ascii=False, indent=2))
    else:
        for path, report in reports.items():
            print(f"=== {path} ===\n{report.to_human_summary()}")
    return int(any(not report.clean for report in reports.values()))


if __name__ == "__main__":
    raise SystemExit(main())
