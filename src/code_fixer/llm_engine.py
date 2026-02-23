"""LLM engine for AI-powered code fixes."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from openai import OpenAI
from anthropic import Anthropic
from google import genai


@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    fixed_code: str
    explanation: str


class LLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def fix_code(
        self,
        code: str,
        file_path: Path,
        issues: list[str],
        model: str,
        temperature: float,
    ) -> LLMResponse:
        """Generate code fixes using LLM."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY env var.")
        self.client = OpenAI(api_key=self.api_key)

    def fix_code(
        self,
        code: str,
        file_path: Path,
        issues: list[str],
        model: str,
        temperature: float,
    ) -> LLMResponse:
        issues_text = "\n".join(f"- {issue}" for issue in issues) if issues else "No specific issues detected"
        
        system_prompt = f"""You are an expert code fixing assistant. Fix issues in this Python file: {file_path.name}

Issues to fix:
{issues_text}

Return format:
FIXED_CODE:
<the fixed code>

EXPLANATION:
<brief explanation>"""

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": code},
            ],
            temperature=temperature,
        )

        content = response.choices[0].message.content
        return LLMEngine._parse_response(content)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY env var.")
        self.client = Anthropic(api_key=self.api_key)

    def fix_code(
        self,
        code: str,
        file_path: Path,
        issues: list[str],
        model: str,
        temperature: float,
    ) -> LLMResponse:
        issues_text = "\n".join(f"- {issue}" for issue in issues) if issues else "No specific issues detected"
        
        system_prompt = f"""You are an expert code fixing assistant. Fix issues in this Python file: {file_path.name}

Issues to fix:
{issues_text}

Return format:
FIXED_CODE:
<the fixed code>

EXPLANATION:
<brief explanation>"""

        response = self.client.messages.create(
            model=model,
            max_tokens=8192,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": code}],
        )

        content = response.content[0].text
        return LLMEngine._parse_response(content)


class LocalProvider(LLMProvider):
    """Local LLM provider (Ollama, LM Studio, etc.)."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    def fix_code(
        self,
        code: str,
        file_path: Path,
        issues: list[str],
        model: str,
        temperature: float,
    ) -> LLMResponse:
        issues_text = "\n".join(f"- {issue}" for issue in issues) if issues else "No specific issues detected"
        
        system_prompt = f"""You are an expert code fixing assistant. Fix issues in this Python file: {file_path.name}

Issues to fix:
{issues_text}

Return format:
FIXED_CODE:
<the fixed code>

EXPLANATION:
<brief explanation>"""

        client = OpenAI(base_url=self.base_url, api_key="not-needed")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": code},
            ],
            temperature=temperature,
        )

        content = response.choices[0].message.content
        return LLMEngine._parse_response(content)


class LMStudioProvider(LocalProvider):
    """LM Studio provider - runs local LLMs with OpenAI-compatible API."""

    def __init__(self, base_url: str = "http://localhost:1234/v1"):
        super().__init__(base_url)


class OllamaProvider(LocalProvider):
    """Ollama provider - runs local LLMs."""

    def __init__(self, base_url: str = "http://localhost:11434/v1"):
        super().__init__(base_url)


class GoogleProvider(LLMProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key not found. Set GOOGLE_API_KEY env var.")
        self.client = genai.Client(api_key=self.api_key)

    def fix_code(
        self,
        code: str,
        file_path: Path,
        issues: list[str],
        model: str,
        temperature: float,
    ) -> LLMResponse:
        issues_text = "\n".join(f"- {issue}" for issue in issues) if issues else "No specific issues detected"
        
        system_prompt = f"""You are an expert code fixing assistant. Fix issues in this Python file: {file_path.name}

Issues to fix:
{issues_text}

Return format:
FIXED_CODE:
<the fixed code>

EXPLANATION:
<brief explanation>"""

        response = self.client.models.generate_content(
            model=model,
            contents=code,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                max_output_tokens=8192,
            ),
        )

        content = response.text
        return LLMEngine._parse_response(content)


class LLMEngine:
    """LLM engine that routes to the appropriate provider."""

    PROVIDERS = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "local": LocalProvider,
        "lmstudio": LMStudioProvider,
        "ollama": OllamaProvider,
    }

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o",
        temperature: float = 0.2,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.provider_name = provider
        self.model = model
        self.temperature = temperature
        self.base_url = base_url
        self._provider = self._create_provider(provider, api_key, base_url)

    def _create_provider(self, provider: str, api_key: Optional[str], base_url: Optional[str]) -> LLMProvider:
        provider_class = self.PROVIDERS.get(provider)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(self.PROVIDERS.keys())}")
        
        if provider in ("local", "lmstudio", "ollama"):
            return provider_class(base_url=base_url) if base_url else provider_class()
        return provider_class(api_key)

    def fix_code(
        self,
        code: str,
        file_path: Path,
        issues: list[str],
    ) -> LLMResponse:
        return self._provider.fix_code(
            code=code,
            file_path=file_path,
            issues=issues,
            model=self.model,
            temperature=self.temperature,
        )

    @staticmethod
    def _parse_response(content: str) -> LLMResponse:
        """Parse LLM response into fixed code and explanation."""
        import re
        parts = content.split("EXPLANATION:")
        code_part = parts[0].replace("FIXED_CODE:", "").strip()
        
        # Remove markdown code fences like ```python or ```
        code_part = re.sub(r'^```[\w]*\n', '', code_part, flags=re.MULTILINE)
        code_part = re.sub(r'```$', '', code_part, flags=re.MULTILINE)
        
        explanation = parts[1].strip() if len(parts) > 1 else "No explanation provided"
        
        return LLMResponse(
            content=content,
            fixed_code=code_part,
            explanation=explanation,
        )
