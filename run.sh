#!/bin/bash
#
# Code Fixer - Easy Setup & Run Script
# Usage: ./run.sh fix <file.py> [options]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check Python
check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found. Please install Python 3.10+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_info "Using Python $PYTHON_VERSION"
}

# Setup virtual environment
setup_venv() {
    if [ -d "$VENV_DIR" ]; then
        log_info "Virtual environment already exists"
    else
        log_info "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
    
    # Activate venv
    source "$VENV_DIR/bin/activate"
    
    # Install package
    log_info "Installing dependencies..."
    pip install -e . --quiet 2>/dev/null || pip install -e .
    
    # Optional: Install linters
    log_info "Installing optional linters..."
    pip install ruff black mypy pyflakes --quiet 2>/dev/null || true
    
    log_info "Setup complete!"
}

# Interactive setup
setup_config() {
    echo ""
    echo "=========================================="
    echo "  Code Fixer - Setup"
    echo "=========================================="
    echo ""
    
    # Ask for LLM provider
    echo "Select LLM Provider:"
    echo "  1) LM Studio (local - recommended)"
    echo "  2) Ollama (local)"
    echo "  3) OpenAI (cloud)"
    echo "  4) Anthropic Claude (cloud)"
    echo "  5) Google Gemini (cloud)"
    echo ""
    read -p "Enter choice (1-5): " choice
    
    # Default model suggestions
    case $choice in
        1)
            PROVIDER="lmstudio"
            DEFAULT_MODEL="qwen2.5-coder-14b"
            BASE_URL="http://localhost:1234/v1"
            echo ""
            echo "Recommended models for LM Studio:"
            echo "  - qwen2.5-coder-14b (code generation)"
            echo "  - deepseek-coder-v2-16b"
            echo "  - llama3.1:8b"
            ;;
        2)
            PROVIDER="ollama"
            DEFAULT_MODEL="qwen2.5-coder:14b"
            BASE_URL="http://localhost:11434/v1"
            echo ""
            echo "Recommended models for Ollama:"
            echo "  - qwen2.5-coder:14b"
            echo "  - codellama:7b"
            echo "  - llama3.1:8b"
            ;;
        3)
            PROVIDER="openai"
            DEFAULT_MODEL="gpt-4o"
            BASE_URL=""
            echo ""
            echo "Available OpenAI models:"
            echo "  - gpt-4o (recommended)"
            echo "  - gpt-4o-mini"
            echo "  - gpt-4-turbo"
            ;;
        4)
            PROVIDER="anthropic"
            DEFAULT_MODEL="claude-3-5-sonnet-20241022"
            BASE_URL=""
            echo ""
            echo "Available Claude models:"
            echo "  - claude-3-5-sonnet-20241022 (recommended)"
            echo "  - claude-3-opus-20240229"
            echo "  - claude-3-haiku-20240307"
            ;;
        5)
            PROVIDER="google"
            DEFAULT_MODEL="gemini-2.0-flash"
            BASE_URL=""
            echo ""
            echo "Available Google models:"
            echo "  - gemini-2.0-flash (recommended)"
            echo "  - gemini-1.5-pro"
            echo "  - gemini-1.5-flash"
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac
    
    echo ""
    read -p "Model (press Enter for default: $DEFAULT_MODEL): " MODEL
    MODEL=${MODEL:-$DEFAULT_MODEL}
    echo "  → Using: $MODEL"
    
    # Ask for temperature
    echo ""
    read -p "Temperature (0.0-1.0, default 0.2): " TEMP
    TEMP=${TEMP:-0.2}
    
    # Write config
    cat > "$SCRIPT_DIR/config.yaml" << EOF
llm:
  provider: $PROVIDER
  model: $MODEL
  temperature: $TEMP
  base_url: $BASE_URL

rule_engine:
  enabled: true
  linters:
    - ruff
    - black
    - mypy
    - pyflakes
EOF
    
    echo ""
    log_info "Configuration saved to config.yaml"
    
    if [ "$PROVIDER" = "openai" ] || [ "$PROVIDER" = "anthropic" ] || [ "$PROVIDER" = "google" ]; then
        echo ""
        echo "⚠️  Please set your API key:"
        echo ""
        if [ "$PROVIDER" = "openai" ]; then
            echo "  export OPENAI_API_KEY=your-api-key"
        elif [ "$PROVIDER" = "anthropic" ]; then
            echo "  export ANTHROPIC_API_KEY=your-api-key"
        elif [ "$PROVIDER" = "google" ]; then
            echo "  export GOOGLE_API_KEY=your-api-key"
        fi
        echo ""
    else
        echo ""
        echo "💡 Make sure your local LLM server is running:"
        if [ "$PROVIDER" = "lmstudio" ]; then
            echo "  - Open LM Studio → Load a model → Click 'Start Server'"
        elif [ "$PROVIDER" = "ollama" ]; then
            echo "  - Run: ollama serve"
        fi
        echo ""
    fi
}

# Ensure config exists
ensure_config() {
    if [ ! -f "$SCRIPT_DIR/config.yaml" ]; then
        if [ -f "$SCRIPT_DIR/config.yaml.example" ]; then
            log_info "Creating config.yaml from example..."
            cp "$SCRIPT_DIR/config.yaml.example" "$SCRIPT_DIR/config.yaml"
            log_warn "Please edit config.yaml and set your LLM provider/API key"
        fi
    fi
}

# Main
check_python
setup_venv

# Run the command
if [ "$1" = "setup" ]; then
    setup_config
    exit 0
fi

if [ "$1" = "config" ]; then
    # Show current config
    if [ -f "$SCRIPT_DIR/config.yaml" ]; then
        echo ""
        echo "Current Configuration:"
        echo "======================"
        cat "$SCRIPT_DIR/config.yaml"
        echo ""
        read -p "Re-run setup? (y/n): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            setup_config
        fi
    else
        echo "No config found. Running setup..."
        setup_config
    fi
    exit 0
fi

if [ "$1" = "test" ]; then
    echo ""
    log_info "Running tests..."
    echo ""
    pytest tests/ -v
    exit $?
fi

if [ "$1" = "lint" ]; then
    echo ""
    log_info "Running linter..."
    echo ""
    ruff check src/
    exit $?
fi

if [ $# -eq 0 ]; then
    echo ""
    echo "Usage: ./run.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  setup          Interactive setup (first time)"
    echo "  config         View/reconfigure model settings"
    echo "  fix <file>    Fix a Python file"
    echo "  test          Run tests"
    echo "  lint          Run linter"
    echo ""
    echo "First Time Setup:"
    echo "  ./run.sh setup"
    echo ""
    echo "Examples:"
    echo "  ./run.sh setup"
    echo "  ./run.sh config"
    echo "  ./run.sh fix path/to/file.py"
    echo "  ./run.sh test"
    echo ""
else
    export FORCE_COLOR=1
    export TERM=xterm-256color
    exec code-fixer "$@"
fi
