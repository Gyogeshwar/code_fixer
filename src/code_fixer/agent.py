"""Main agent orchestrator for code fixing."""

import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import Config, get_config
from .llm_engine import LLMEngine
from .rule_engine import RuleEngine


@dataclass
class FixResult:
    """Result of a code fix operation."""
    file_path: Path
    success: bool
    original_code: str
    fixed_code: str
    explanation: str
    linter_results: list
    issues_before: list[str]
    issues_after: list[str]
    backup_path: Optional[Path] = None
    error: Optional[str] = None


class Agent:
    """Main agent for fixing code in single files."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.rule_engine = RuleEngine(
            enabled=self.config.linters_enabled,
            linters=self.config.linters,
        )
        self.llm_engine = LLMEngine(
            provider=self.config.llm_provider,
            model=self.config.llm_model,
            temperature=self.config.llm_temperature,
            api_key=self.config.llm_api_key,
            base_url=self.config.llm_base_url,
        )

    def fix(
        self,
        file_path: Path,
        dry_run: bool = False,
        skip_llm: bool = False,
    ) -> FixResult:
        """
        Fix a single file.
        
        Args:
            file_path: Path to the file to fix
            dry_run: If True, don't write changes to disk
            skip_llm: If True, only use rule-based fixes
            
        Returns:
            FixResult with details of the fix operation
        """
        file_path = Path(file_path).resolve()
        
        if not file_path.exists():
            return FixResult(
                file_path=file_path,
                success=False,
                original_code="",
                fixed_code="",
                explanation="",
                linter_results=[],
                issues_before=[],
                issues_after=[],
                error=f"File not found: {file_path}",
            )

        try:
            original_code = file_path.read_text()
        except Exception as e:
            return FixResult(
                file_path=file_path,
                success=False,
                original_code="",
                fixed_code="",
                explanation="",
                linter_results=[],
                issues_before=[],
                issues_after=[],
                error=f"Could not read file: {e}",
            )

        linter_results = self.rule_engine.check(file_path)
        issues_before = self.rule_engine.get_all_issues(linter_results)

        fixed_code = original_code
        explanation = ""
        
        # Always run LLM to get fixes (even in dry-run mode)
        if not skip_llm:
            llm_response = self.llm_engine.fix_code(
                code=original_code,
                file_path=file_path,
                issues=issues_before,
            )
            fixed_code = llm_response.fixed_code
            explanation = llm_response.explanation

        if not dry_run and fixed_code != original_code:
            backup_path = self._create_backup(file_path)
            try:
                file_path.write_text(fixed_code)
            except Exception as e:
                if backup_path and backup_path.exists():
                    shutil.move(str(backup_path), str(file_path))
                return FixResult(
                    file_path=file_path,
                    success=False,
                    original_code=original_code,
                    fixed_code="",
                    explanation=explanation,
                    linter_results=linter_results,
                    issues_before=issues_before,
                    issues_after=[],
                    error=f"Could not write file: {e}",
                )

        linter_results_after = self.rule_engine.check(file_path)
        issues_after = self.rule_engine.get_all_issues(linter_results_after)

        return FixResult(
            file_path=file_path,
            success=True,
            original_code=original_code,
            fixed_code=fixed_code,
            explanation=explanation,
            linter_results=linter_results,
            issues_before=issues_before,
            issues_after=issues_after,
        )

    def _create_backup(self, file_path: Path) -> Optional[Path]:
        """Create a backup of the original file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = file_path.parent / ".code_fixer_backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"{file_path.name}.{timestamp}.bak"
        shutil.copy2(file_path, backup_path)
        return backup_path

    def get_diff(self, original: str, fixed: str) -> str:
        """Generate a unified diff between original and fixed code."""
        import difflib
        original_lines = original.splitlines(keepends=True)
        fixed_lines = fixed.splitlines(keepends=True)
        diff = difflib.unified_diff(original_lines, fixed_lines, lineterm="")
        return "".join(diff)
