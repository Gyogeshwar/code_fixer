"""Rule-based engine for running linters and formatters."""

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class LinterIssue:
    """Represents a linter issue."""
    linter: str
    line: int
    column: int
    message: str
    code: Optional[str] = None


@dataclass
class LinterResult:
    """Result from running a linter."""
    linter: str
    success: bool
    issues: list[LinterIssue]
    stdout: str
    stderr: str


class RuleEngine:
    """Engine for running rule-based tools (linters, formatters)."""

    LINTER_COMMANDS = {
        "ruff": ["ruff", "check", "--output-format=json"],
        "ruff-format": ["ruff", "format"],
        "black": ["black", "--check", "--diff"],
        "mypy": ["mypy", "--no-error-summary", "--output-format=json"],
        "pyflakes": ["pyflakes"],
    }

    FIX_COMMANDS = {
        "ruff": ["ruff", "check", "--fix"],
        "ruff-format": ["ruff", "format"],
        "black": ["black"],
    }

    def __init__(self, enabled: bool = True, linters: Optional[list] = None):
        self.enabled = enabled
        self.linters = linters or ["ruff"]

    def check(self, file_path: Path) -> list[LinterResult]:
        """Run all enabled linters on a file."""
        if not self.enabled:
            return []

        results = []
        for linter in self.linters:
            if linter in self.LINTER_COMMANDS:
                result = self._run_linter(linter, file_path)
                results.append(result)
        return results

    def fix(self, file_path: Path) -> dict[str, bool]:
        """Apply auto-fixes from linters."""
        if not self.enabled:
            return {}

        results = {}
        for linter in self.linters:
            if linter in self.FIX_COMMANDS:
                success = self._run_fix(linter, file_path)
                results[linter] = success
        return results

    def _run_linter(self, linter: str, file_path: Path) -> LinterResult:
        """Run a specific linter."""
        cmd = self.LINTER_COMMANDS.get(linter, [])
        if not cmd:
            return LinterResult(linter=linter, success=True, issues=[], stdout="", stderr="")

        try:
            result = subprocess.run(
                cmd + [str(file_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            issues = self._parse_output(linter, result.stdout, result.stderr)
            return LinterResult(
                linter=linter,
                success=result.returncode == 0,
                issues=issues,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except FileNotFoundError:
            return LinterResult(
                linter=linter,
                success=False,
                issues=[],
                stdout="",
                stderr=f"{linter} not found. Install with: pip install {linter}",
            )
        except subprocess.TimeoutExpired:
            return LinterResult(
                linter=linter,
                success=False,
                issues=[],
                stdout="",
                stderr=f"{linter} timed out",
            )
        except Exception as e:
            return LinterResult(
                linter=linter,
                success=False,
                issues=[],
                stdout="",
                stderr=str(e),
            )

    def _run_fix(self, linter: str, file_path: Path) -> bool:
        """Run auto-fix for a linter."""
        cmd = self.FIX_COMMANDS.get(linter, [])
        if not cmd:
            return False

        try:
            result = subprocess.run(
                cmd + [str(file_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _parse_output(self, linter: str, stdout: str, stderr: str) -> list[LinterIssue]:
        """Parse linter output into structured issues."""
        issues = []

        if linter == "ruff" and stdout:
            try:
                data = json.loads(stdout)
                for item in data:
                    issues.append(LinterIssue(
                        linter="ruff",
                        line=item.get("location", {}).get("row", 0),
                        column=item.get("location", {}).get("column", 0),
                        message=item.get("message", ""),
                        code=item.get("code", ""),
                    ))
            except json.JSONDecodeError:
                for line in stdout.strip().split("\n"):
                    if line.strip():
                        issues.append(LinterIssue(
                            linter="ruff",
                            line=0,
                            column=0,
                            message=line,
                        ))

        elif linter == "mypy" and stdout:
            try:
                data = json.loads(stdout)
                for item in data:
                    issues.append(LinterIssue(
                        linter="mypy",
                        line=item.get("line", 0),
                        column=item.get("column", 0),
                        message=item.get("message", ""),
                    ))
            except json.JSONDecodeError:
                for line in stdout.strip().split("\n"):
                    if line.strip():
                        issues.append(LinterIssue(
                            linter="mypy",
                            line=0,
                            column=0,
                            message=line,
                        ))

        elif linter in ("black", "pyflakes"):
            output = stdout + stderr
            for line in output.strip().split("\n"):
                if line.strip() and not line.startswith("---"):
                    issues.append(LinterIssue(
                        linter=linter,
                        line=0,
                        column=0,
                        message=line,
                    ))

        return issues

    def get_all_issues(self, results: list[LinterResult]) -> list[str]:
        """Get a flat list of all issue messages."""
        issues = []
        for result in results:
            for issue in result.issues:
                if issue.code:
                    issues.append(f"[{issue.code}] {issue.message}")
                else:
                    issues.append(issue.message)
        return issues

    @staticmethod
    def is_available(linter: str) -> bool:
        """Check if a linter is installed."""
        try:
            subprocess.run(
                ["which", linter],
                capture_output=True,
                timeout=5,
            )
            return True
        except Exception:
            return False
