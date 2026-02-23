"""Configuration management for code-fixer."""

import os
from pathlib import Path
from typing import Optional

import yaml


class Config:
    """Application configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self._default_config_path()
        self._config = self._load_config()

    def _default_config_path(self) -> Path:
        return Path.cwd() / "config.yaml"

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            return self._default_config()
        with open(self.config_path) as f:
            return yaml.safe_load(f) or {}

    def _default_config(self) -> dict:
        return {
            "llm": {
                "provider": "openai",
                "model": "gpt-4o",
                "temperature": 0.2,
            },
            "rule_engine": {
                "enabled": True,
                "linters": ["ruff", "black", "mypy", "pyflakes"],
            },
        }

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    @property
    def llm_provider(self) -> str:
        return self.get("llm.provider", "openai")

    @property
    def llm_model(self) -> str:
        return self.get("llm.model", self._default_model)

    @property
    def _default_model(self) -> str:
        defaults = {
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-20241022",
            "google": "gemini-2.0-flash",
            "lmstudio": "qwen2.5-coder-14b",
            "ollama": "qwen2.5-coder-14b",
            "local": "qwen2.5-coder-14b",
        }
        return defaults.get(self.llm_provider, "gpt-4o")

    @property
    def llm_temperature(self) -> float:
        return self.get("llm.temperature", 0.2)

    @property
    def llm_api_key(self) -> Optional[str]:
        key = f"{self.llm_provider.upper()}_API_KEY"
        return os.environ.get(key)

    @property
    def llm_base_url(self) -> Optional[str]:
        return self.get("llm.base_url")

    @property
    def linters_enabled(self) -> bool:
        return self.get("rule_engine.enabled", True)

    @property
    def linters(self) -> list:
        return self.get("rule_engine.linters", ["ruff"])


_config: Optional[Config] = None


def get_config(config_path: Optional[Path] = None) -> Config:
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reset_config():
    global _config
    _config = None
