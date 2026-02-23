"""CLI interface for code-fixer."""

import os
import sys
from pathlib import Path

import click

os.environ["FORCE_COLOR"] = "1"
from rich.console import Console
from rich.theme import Theme

from .agent import Agent
from .config import Config, get_config

LOCAL_MODELS = [
    "nomic-embed-text-v1.5",
    "qwen/qwen2.5-coder-14b",
    "google/gemma-3-4b",
    "deepseek/deepseek-r1-0528-qwen3-8b",
    "qwen/qwen3-4b-thinking-2507",
]

LOCAL_MODELS_STR = ", ".join(LOCAL_MODELS)

import os
console = Console(force_terminal=True, color_system="256")


def show_git_like_diff(original: str, fixed: str, file_path: str) -> None:
    """Show a git-like side-by-side diff view with line numbers."""
    from rich.panel import Panel
    from rich.table import Table
    
    original_lines = original.splitlines()
    fixed_lines = fixed.splitlines()
    
    import difflib
    diff = list(difflib.unified_diff(
        original_lines, 
        fixed_lines, 
        fromfile="a/" + file_path, 
        tofile="b/" + file_path,
        lineterm=""
    ))
    
    if not diff:
        console.print("[green]No changes to show.[/green]")
        return
    
    left_lines = []
    right_lines = []
    left_line_nums = []
    right_line_nums = []
    
    old_line = 1
    new_line = 1
    
    for line in diff:
        if line.startswith("---"):
            left_lines.append(f"[dim]---\na/{file_path}[/dim]")
            right_lines.append(f"[dim]---\na/{file_path}[/dim]")
            left_line_nums.append("")
            right_line_nums.append("")
        elif line.startswith("+++"):
            left_lines.append(f"[dim]+++\nb/{file_path}[/dim]")
            right_lines.append(f"[dim]+++\nb/{file_path}[/dim]")
            left_line_nums.append("")
            right_line_nums.append("")
        elif line.startswith("@@"):
            parts = line.split(" ")
            hunk_info = parts[1] if len(parts) > 1 else ""
            left_lines.append(f"[bold yellow]{line}[/bold yellow]")
            right_lines.append(f"[bold yellow]{line}[/bold yellow]")
            left_line_nums.append("")
            right_line_nums.append("")
            
            import re
            match = re.search(r'-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?', hunk_info)
            if match:
                old_line = int(match.group(1))
                new_line = int(match.group(3))
        elif line.startswith("-"):
            left_lines.append(("[red]" + line[1:] + "[/red]"))
            right_lines.append("")
            left_line_nums.append(str(old_line))
            right_line_nums.append("")
            old_line += 1
        elif line.startswith("+"):
            left_lines.append("")
            right_lines.append(("[green]" + line[1:] + "[/green]"))
            left_line_nums.append("")
            right_line_nums.append(str(new_line))
            new_line += 1
        else:
            left_lines.append(line)
            right_lines.append(line)
            left_line_nums.append(str(old_line))
            right_line_nums.append(str(new_line))
            old_line += 1
            new_line += 1
    
    # Apply styling - white for unchanged lines, keep red/green for changes
    styled_left = []
    styled_right = []
    
    for left, right in zip(left_lines, right_lines):
        if left.startswith("[red]"):
            styled_left.append(left)
            styled_right.append("")
        elif left.startswith("[bold yellow]"):
            styled_left.append(left)
            styled_right.append(right)
        elif left.startswith("[dim]"):
            styled_left.append(left)
            styled_right.append(right)
        elif left and right and left == right:
            # Unchanged line - use white
            styled_left.append(left)
            styled_right.append(right)
        elif left:
            styled_left.append(left)
            styled_right.append("")
        elif right:
            styled_left.append("")
            styled_right.append(right)
        else:
            styled_left.append("")
            styled_right.append("")
    
    left_lines = styled_left
    right_lines = styled_right
    
    max_lines = max(len(left_lines), len(right_lines))
    left_lines.extend([""] * (max_lines - len(left_lines)))
    right_lines.extend([""] * (max_lines - len(right_lines)))
    left_line_nums.extend([""] * (max_lines - len(left_line_nums)))
    right_line_nums.extend([""] * (max_lines - len(right_line_nums)))
    
    table = Table(show_header=True, box=None, padding=(0, 0, 0, 0), collapse_padding=True)
    table.add_column("old_ln", width=4, justify="right", style="dim")
    table.add_column("old", width=45, style="white")
    table.add_column("sep", width=1, style="dim")
    table.add_column("new_ln", width=4, justify="right", style="dim")
    table.add_column("new", width=45, style="white")
    
    for i in range(max_lines):
        ln_left = left_line_nums[i] if left_line_nums[i] else ""
        ln_right = right_line_nums[i] if right_line_nums[i] else ""
        
        if left_lines[i] and right_lines[i]:
            if left_lines[i].startswith("[bold yellow]"):
                table.add_row("", left_lines[i], "", "", right_lines[i])
            else:
                table.add_row(ln_left, left_lines[i], "│", ln_right, right_lines[i])
        elif left_lines[i]:
            table.add_row(ln_left, left_lines[i], "│", "", "")
        elif right_lines[i]:
            table.add_row("", "", "│", ln_right, right_lines[i])
    
    console.print(table)


def colorize_diff(text: str) -> str:
    """Apply color codes to diff output using rich."""
    from rich.text import Text
    
    lines = []
    for line in text.split("\n"):
        if line.startswith("---"):
            lines.append(Text(line, style="white"))
        elif line.startswith("+++"):
            lines.append(Text(line, style="white"))
        elif line.startswith("-") and not line.startswith("---"):
            lines.append(Text(line, style="red"))
        elif line.startswith("+") and not line.startswith("+++"):
            lines.append(Text(line, style="green"))
        elif line.startswith("@@"):
            lines.append(Text(line, style="cyan bold"))
        else:
            lines.append(Text(line, style="white"))
    
    return "\n".join(str(line) for line in lines)


@click.group()
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to config file",
)
@click.pass_context
def cli(ctx, config):
    """AI-powered code fixing agent."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = get_config(config) if config else get_config()


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "local", "lmstudio", "ollama"]),
    help="LLM provider to use",
)
@click.option(
    "--model",
    help=f"Model to use. Local models: {LOCAL_MODELS_STR}",
)
@click.option(
    "--base-url",
    help="Base URL for local providers (e.g., http://localhost:1234/v1)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show changes without applying",
)
@click.option(
    "--skip-llm",
    is_flag=True,
    help="Only use rule-based fixes (no LLM)",
)
@click.option(
    "--no-diff",
    is_flag=True,
    help="Don't show diff of changes",
)
@click.option(
    "-y", "--yes",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.pass_context
def fix(ctx, file_path, provider, model, base_url, dry_run, skip_llm, no_diff, yes):
    """Fix code issues in a file."""
    from .config import reset_config
    reset_config()
    
    config = ctx.obj.get("config") or get_config()
    
    if provider:
        config._config.setdefault("llm", {})["provider"] = provider
    if model:
        config._config.setdefault("llm", {})["model"] = model
    if base_url:
        config._config.setdefault("llm", {})["base_url"] = base_url

    agent = Agent(config)
    
    console.print(f"[bold cyan]Fixing:[/bold cyan] {file_path}")
    
    result = agent.fix(file_path, dry_run=True, skip_llm=skip_llm)
    
    if result.error:
        console.print(f"[bold red]Error:[/bold red] {result.error}")
        sys.exit(1)
    
    if result.issues_before:
        console.print(f"\n[bold yellow]Issues found ({len(result.issues_before)}):[/bold yellow]")
        
        if not no_diff:
            for issue in result.issues_before[:15]:
                colored = colorize_diff(issue)
                console.print(f"  {colored}")
            if len(result.issues_before) > 15:
                console.print(f"  [dim]... and {len(result.issues_before) - 15} more[/dim]")
        else:
            for issue in result.issues_before[:10]:
                console.print(f"  - {issue}")
            if len(result.issues_before) > 10:
                console.print(f"  ... and {len(result.issues_before) - 10} more")
    
    if not no_diff and result.fixed_code != result.original_code:
        console.print("\n")
        show_git_like_diff(result.original_code, result.fixed_code, str(file_path))
    
    if result.fixed_code == result.original_code:
        console.print("\n[green]No changes needed.[/green]")
        return
    
    if result.explanation:
        console.print(f"\n[magenta]Explanation:[/magenta] {result.explanation}")
    
    if dry_run:
        console.print("\n[yellow][Dry run] Changes not applied.[/yellow]")
    elif yes or click.confirm("\nApply these changes?"):
        file_path.write_text(result.fixed_code)
        
        result_verify = agent.fix(file_path, dry_run=True, skip_llm=skip_llm)
        
        if result_verify.issues_after:
            console.print(f"\n[yellow]Remaining issues ({len(result_verify.issues_after)}):[/yellow]")
            for issue in result_verify.issues_after[:5]:
                console.print(f"  - {issue}")
        else:
            console.print("\n[green bold]All issues resolved![/green bold]")
        
        console.print("\n[green bold]Fixes applied successfully![/green bold]")
    else:
        console.print("\n[dim]Changes not applied.[/dim]")


@cli.command()
def check():
    """Check a file for issues without fixing."""
    console.print("[dim]Use 'fix' command with --dry-run to check without fixing.[/dim]")


def main():
    """Entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
