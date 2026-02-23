"""Tests for code-fixer."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from code_fixer.agent import Agent, FixResult
from code_fixer.config import Config, get_config
from code_fixer.rule_engine import RuleEngine, LinterResult, LinterIssue
from code_fixer.llm_engine import LLMEngine, LLMResponse


@pytest.fixture
def sample_python_file(tmp_path):
    """Create a sample Python file with issues."""
    file_path = tmp_path / "sample.py"
    file_path.write_text("""def add(a,b):
    return a+b
    
x=1
print(x)
""")
    return file_path


@pytest.fixture
def mock_config():
    """Create a mock config."""
    config = MagicMock(spec=Config)
    config.llm_provider = "openai"
    config.llm_model = "gpt-4o"
    config.llm_temperature = 0.2
    config.llm_api_key = "test-key"
    config.llm_base_url = None
    config.linters_enabled = True
    config.linters = ["ruff"]
    return config


class TestConfig:
    """Tests for configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = get_config()
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4o"
        assert config.linters_enabled is True

    def test_config_from_file(self, tmp_path):
        """Test loading config from file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
llm:
  provider: anthropic
  model: claude-3-5-sonnet
  
rule_engine:
  enabled: false
  linters: []
""")
        from code_fixer.config import Config
        config = Config(config_file)
        assert config.llm_provider == "anthropic"
        assert config.linters_enabled is False


class TestRuleEngine:
    """Tests for rule engine."""

    def test_parse_ruff_output(self):
        """Test parsing ruff JSON output."""
        engine = RuleEngine()
        json_output = '[{"location": {"row": 1, "column": 5}, "message": "F401 imported but unused", "code": "F401"}]'
        
        issues = engine._parse_output("ruff", json_output, "")
        
        assert len(issues) == 1
        assert issues[0].code == "F401"
        assert issues[0].line == 1

    def test_get_all_issues(self):
        """Test aggregating issues from multiple linters."""
        engine = RuleEngine()
        results = [
            LinterResult(
                linter="ruff",
                success=False,
                issues=[
                    LinterIssue(linter="ruff", line=1, column=0, message="F401", code="F401"),
                ],
                stdout="",
                stderr="",
            ),
            LinterResult(
                linter="mypy",
                success=False,
                issues=[
                    LinterIssue(linter="mypy", line=5, column=0, message="Missing type hint"),
                ],
                stdout="",
                stderr="",
            ),
        ]
        
        all_issues = engine.get_all_issues(results)
        
        assert len(all_issues) == 2
        assert "[F401] F401" in all_issues


class TestLLMEngine:
    """Tests for LLM engine."""

    def test_parse_response(self):
        """Test parsing LLM response."""
        response = LLMEngine._parse_response("""FIXED_CODE:
def add(a, b):
    return a + b

EXPLANATION:
Fixed spacing and formatting.""")
        
        assert "def add(a, b):" in response.fixed_code
        assert "Fixed spacing" in response.explanation

    def test_provider_creation(self):
        """Test creating different LLM providers."""
        with pytest.raises(ValueError):
            LLMEngine(provider="unknown")


class TestAgent:
    """Tests for the main agent."""

    def test_fix_nonexistent_file(self, mock_config):
        """Test fixing a file that doesn't exist."""
        agent = Agent(mock_config)
        result = agent.fix(Path("/nonexistent/file.py"))
        
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_fix_read_error(self, tmp_path, mock_config):
        """Test handling file read errors."""
        file_path = tmp_path / "test.py"
        file_path.write_text("test")
        
        # Make file unreadable
        file_path.chmod(0o000)
        
        try:
            agent = Agent(mock_config)
            result = agent.fix(file_path)
            
            assert result.success is False
            assert "read" in result.error.lower()
        finally:
            file_path.chmod(0o644)

    def test_get_diff(self, mock_config):
        """Test diff generation."""
        agent = Agent(mock_config)
        
        original = "def foo():\n    pass\n"
        fixed = "def foo():\n    return None\n"
        
        diff = agent.get_diff(original, fixed)
        
        assert "def foo()" in diff
        assert "-" in diff or "+" in diff


class TestAgentIntegration:
    """Integration tests for the agent."""

    def test_fix_with_rule_engine_only(self, tmp_path, mock_config):
        """Test fixing with only rule engine (no LLM)."""
        file_path = tmp_path / "sample.py"
        file_path.write_text("x=1\n")
        
        mock_config.linters = ["ruff"]
        
        with patch("code_fixer.agent.LLMEngine"):
            agent = Agent(mock_config)
            result = agent.fix(file_path, skip_llm=True)
        
        assert result.success is True

    def test_backup_creation(self, tmp_path, mock_config):
        """Test that backups are created when code changes."""
        file_path = tmp_path / "sample.py"
        file_path.write_text("x = 1\n")
        
        agent = Agent(mock_config)
        
        with patch.object(agent.llm_engine, "fix_code") as mock_llm:
            mock_llm.return_value = LLMResponse(
                content="",
                fixed_code="y = 2\n",
                explanation="Changed variable",
            )
            result = agent.fix(file_path)
        
        assert result.success is True
        assert result.fixed_code != result.original_code
        
        backup_dir = tmp_path / ".code_fixer_backups"
        assert backup_dir.exists()
