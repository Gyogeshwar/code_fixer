# Code Fixer

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Build](https://img.shields.io/badge/Build-Passing-green)](https://github.com/example/code-fixer)

AI-powered code fixing agent for Python files with beautiful terminal UI.

## Features

- **Rich Terminal UI**: Beautiful color-coded output using the Rich library
- **Git-like Diff View**: Side-by-side comparison with line numbers
  - Red highlighting for removed lines
  - Green highlighting for added lines
  - White for unchanged lines
- **Hybrid Fixing**: Combines linters (ruff, black, mypy, pyflakes) with AI-powered fixes
- **Multi-LLM Support**: OpenAI, Anthropic Claude, Google Gemini, or local models (LM Studio, Ollama)
- **Interactive CLI**: Shows diff, explanation, and asks for confirmation before applying changes
- **Backup Support**: Keeps backup of original files

## Quick Start

```bash
# Run setup wizard (first time)
./run.sh setup

# Then fix your files
./run.sh fix path/to/file.py
```

The setup wizard will:
1. Ask to select LLM provider (LM Studio, Ollama, OpenAI, Anthropic, Google)
2. Show recommended models for each provider
3. Allow custom model name or use default
4. Set temperature (0.0-1.0)

The script will automatically:
1. Create a virtual environment
2. Install all dependencies (including Rich for terminal UI)
3. Create config.yaml if needed

## Installation

### Option 1: Easy Setup (Recommended)
```bash
# First time: Run interactive setup
./run.sh setup

# Then fix files
./run.sh fix path/to/file.py
```

### Option 2: Manual Install
```bash
pip install -e .
pip install ruff black mypy pyflakes
```

## Configuration

1. Copy config file:
```bash
cp config.yaml.example config.yaml
```

2. Edit `config.yaml`:
```yaml
llm:
  provider: lmstudio       # openai, anthropic, google, lmstudio, ollama
  model: qwen2.5-coder-14b
  temperature: 0.2
  base_url: http://localhost:1234/v1  # For LM Studio / Ollama

rule_engine:
  enabled: true
  linters:
    - ruff
    - black
    - mypy
    - pyflakes
```

3. Set API key (for cloud providers):
```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=...
```

## Usage

### Basic Commands

```bash
# Fix a file (shows git-like side-by-side diff, asks confirmation)
./run.sh fix path/to/file.py

# Don't show diff of changes
./run.sh fix path/to/file.py --no-diff

# Apply automatically without asking
./run.sh fix path/to/file.py --yes

# Preview changes without applying
./run.sh fix path/to/file.py --dry-run

# Use specific LLM provider
./run.sh fix file.py --provider lmstudio --model qwen2.5-coder-14b

# Use only linters (no LLM)
./run --skip-ll.sh fix file.pym
```

### Diff View Example

When you run `fix` command, you'll see a beautiful side-by-side diff:

```
old     │ new
        │ # Call the function to see the output
        │ hello()
```

- **Red highlight**: Lines removed from original
- **Green highlight**: Lines added in fixed version
- **White**: Unchanged lines (same on both sides)

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--no-diff` | | Don't show diff of changes |
| `--yes` | `-y` | Apply changes without asking |
| `--dry-run` | | Show what would change without applying |
| `--skip-llm` | | Use only linters, skip AI fixes |
| `--provider` | | LLM provider (openai, anthropic, google, lmstudio, ollama) |
| `--model` | | Model name to use |
| `--base-url` | | Custom endpoint for local models |

## Using as a Library

```python
from code_fixer import Agent
from pathlib import Path

agent = Agent()
result = agent.fix(Path("example.py"))

print(result.fixed_code)
print(result.explanation)
```

## Development

### Setup
```bash
# Clone the project
git clone <repo-url>
cd code_fixer

# Run setup script (creates venv, installs deps)
./run.sh --help
```

### Testing
```bash
# Run all tests
./run.sh test

# Or manually:
source .venv/bin/activate
pytest tests/ -v
```

### Linting & Formatting
```bash
# Lint code
ruff check src/

# Format code
ruff format src/

# Type check
mypy src/
```

### Building Package
```bash
# Build package
pip install build
python -m build

# Install locally
pip install dist/code_fixer-*.whl
```

### Project Structure
```
code_fixer/
├── src/code_fixer/
│   ├── agent.py         # Main orchestrator
│   ├── llm_engine.py    # LLM providers
│   ├── rule_engine.py  # Linter integration
│   ├── config.py       # Configuration
│   └── cli.py          # CLI interface with Rich UI
├── tests/              # Test files
├── run.sh             # Easy setup script
└── pyproject.toml     # Package config
```

## How It Works

1. **Scan**: Run linters to detect issues
2. **Analyze**: Send code + issues to LLM
3. **Preview**: Show git-like side-by-side diff with color-coded changes
4. **Confirm**: Ask user before applying
5. **Apply**: Write fixes and verify

## License

MIT
