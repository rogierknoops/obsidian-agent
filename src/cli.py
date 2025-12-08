"""
CLI interface for the Obsidian Vault Agent.
"""

import os
import sys
import subprocess
import click
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.theme import Theme
from dotenv import load_dotenv

from .agent import VaultAgent
from .vault import VaultManager


# Custom theme for rich output
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow", 
    "error": "red bold",
    "success": "green",
    "prompt": "magenta bold",
})

console = Console(theme=custom_theme)


def get_config():
    """Load configuration from environment."""
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
    
    return api_key, vault_path


def maybe_backup_repo(vault_path: Path, default_message: str):
    """Optionally create a git commit before edits."""
    git_dir = vault_path / ".git"
    if not git_dir.exists():
        console.print("[warning]Skipping backup: no .git repository found in vault[/warning]")
        return

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=vault_path,
        capture_output=True,
        text=True,
    )
    if status.returncode != 0:
        console.print(f"[warning]Skipping backup: git status failed ({status.stderr.strip()})[/warning]")
        return

    changes = status.stdout.strip().splitlines()
    if not changes:
        console.print("[info]Vault clean: no changes to commit[/info]")
        return

    console.print(Panel("\n".join(changes), title="Pending changes", border_style="yellow"))
    commit_message = Prompt.ask("Commit message", default=default_message)
    if not commit_message.strip():
        console.print("[warning]No commit created (empty message).[/warning]")
        return

    if not Confirm.ask("Create commit now?", default=True):
        console.print("[info]Backup skipped at your request.[/info]")
        return

    add = subprocess.run(["git", "add", "."], cwd=vault_path, capture_output=True, text=True)
    if add.returncode != 0:
        console.print(f"[error]git add failed: {add.stderr.strip()}[/error]")
        return

    commit = subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=vault_path,
        capture_output=True,
        text=True,
    )
    if commit.returncode != 0:
        console.print(f"[error]git commit failed: {commit.stderr.strip()}[/error]")
        return

    console.print("[success]✓ Backup commit created[/success]")
    console.print("[dim]Review then push when ready: git push[/dim]")


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """🗃️  Obsidian Vault Agent - AI-powered note management"""
    pass


@cli.command()
@click.option("--vault", "-v", help="Path to your Obsidian vault")
@click.option("--api-key", "-k", envvar="OPENAI_API_KEY", help="OpenAI API key")
@click.option(
    "--auto-backup/--no-auto-backup",
    default=False,
    help="Create a git commit of the vault before starting (no push).",
)
@click.option(
    "--backup-message",
    default="Add a description of the changes",
    show_default=True,
    help="Commit message to use if auto-backup is enabled.",
)
def chat(vault: str, api_key: str, auto_backup: bool, backup_message: str):
    """Start an interactive chat session with your vault."""
    
    # Load defaults from env
    env_api_key, env_vault = get_config()
    api_key = api_key or env_api_key
    vault = vault or env_vault
    
    # Validate configuration
    if not api_key:
        console.print("[error]Error: No API key provided.[/error]")
        console.print("Set OPENAI_API_KEY environment variable or use --api-key flag")
        sys.exit(1)
    
    if not vault:
        console.print("[error]Error: No vault path provided.[/error]")
        console.print("Set OBSIDIAN_VAULT_PATH environment variable or use --vault flag")
        sys.exit(1)
    
    vault_path = Path(vault).expanduser().resolve()
    if not vault_path.exists():
        console.print(f"[error]Error: Vault path does not exist: {vault_path}[/error]")
        sys.exit(1)
    
    if auto_backup:
        maybe_backup_repo(vault_path, backup_message)

    # Initialize agent
    try:
        agent = VaultAgent(str(vault_path), api_key)
    except Exception as e:
        console.print(f"[error]Error initializing agent: {e}[/error]")
        sys.exit(1)
    
    # Welcome message
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🗃️  Obsidian Vault Agent[/bold cyan]\n\n"
        f"[dim]Connected to:[/dim] {vault_path.name}/\n"
        f"[dim]Model:[/dim] GPT-5.1\n\n"
        "[dim]Commands:[/dim]\n"
        "  • Type your questions or instructions\n"
        "  • [bold]/tree[/bold] - Show vault structure\n"
        "  • [bold]/files[/bold] - List all files\n"
        "  • [bold]/reset[/bold] - Clear conversation\n"
        "  • [bold]/quit[/bold] or [bold]Ctrl+C[/bold] - Exit",
        border_style="cyan"
    ))
    console.print()
    
    # Main loop
    while True:
        try:
            user_input = Prompt.ask("[prompt]You[/prompt]")
            
            if not user_input.strip():
                continue
            
            # Handle special commands
            if user_input.strip().lower() in ["/quit", "/exit", "/q"]:
                console.print("\n[dim]Goodbye! 👋[/dim]\n")
                break
            
            if user_input.strip().lower() == "/reset":
                agent.reset_conversation()
                console.print("[success]✓ Conversation cleared[/success]\n")
                continue
            
            if user_input.strip().lower() == "/tree":
                tree = agent.vault.get_file_tree()
                console.print(Panel(tree, title="Vault Structure", border_style="blue"))
                continue
            
            if user_input.strip().lower() == "/files":
                files = agent.vault.list_files()
                if files:
                    file_list = "\n".join(f"• {f.relative_path}" for f in files)
                    console.print(Panel(file_list, title=f"Files ({len(files)})", border_style="blue"))
                else:
                    console.print("[warning]No markdown files found in vault[/warning]")
                continue
            
            # Send to agent
            console.print()
            with console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
                response = agent.chat(user_input)
            
            # Display response
            console.print(Panel(
                Markdown(response),
                title="[bold]Agent[/bold]",
                border_style="green",
                padding=(1, 2)
            ))
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n\n[dim]Goodbye! 👋[/dim]\n")
            break
        except Exception as e:
            console.print(f"[error]Error: {e}[/error]\n")


@cli.command()
@click.option("--vault", "-v", help="Path to your Obsidian vault")
@click.argument("prompt")
@click.option("--api-key", "-k", envvar="OPENAI_API_KEY", help="OpenAI API key")
@click.option(
    "--auto-backup/--no-auto-backup",
    default=False,
    help="Create a git commit of the vault before running (no push).",
)
@click.option(
    "--backup-message",
    default="Add a description of the changes",
    show_default=True,
    help="Commit message to use if auto-backup is enabled.",
)
def ask(vault: str, api_key: str, prompt: str, auto_backup: bool, backup_message: str):
    """Send a single prompt to the agent."""
    
    env_api_key, env_vault = get_config()
    api_key = api_key or env_api_key
    vault = vault or env_vault
    
    if not api_key:
        console.print("[error]Error: No API key provided.[/error]")
        sys.exit(1)
    
    if not vault:
        console.print("[error]Error: No vault path provided.[/error]")
        sys.exit(1)
    
    vault_path = Path(vault).expanduser().resolve()
    if auto_backup:
        maybe_backup_repo(vault_path, backup_message)

    try:
        agent = VaultAgent(str(vault_path), api_key)
        with console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
            response = agent.chat(prompt)
        console.print(Markdown(response))
    except Exception as e:
        console.print(f"[error]Error: {e}[/error]")
        sys.exit(1)


@cli.command()
@click.option("--vault", "-v", help="Path to your Obsidian vault")
def tree(vault: str):
    """Show the vault folder structure."""
    
    _, env_vault = get_config()
    vault = vault or env_vault
    
    if not vault:
        console.print("[error]Error: No vault path provided.[/error]")
        sys.exit(1)
    
    try:
        vm = VaultManager(vault)
        console.print(Panel(vm.get_file_tree(), title="Vault Structure", border_style="cyan"))
    except Exception as e:
        console.print(f"[error]Error: {e}[/error]")
        sys.exit(1)


@cli.command()
@click.option("--vault", "-v", help="Path to your Obsidian vault")
@click.option("--pattern", "-p", help="Glob pattern to filter files")
def files(vault: str, pattern: str):
    """List all files in the vault."""
    
    _, env_vault = get_config()
    vault = vault or env_vault
    
    if not vault:
        console.print("[error]Error: No vault path provided.[/error]")
        sys.exit(1)
    
    try:
        vm = VaultManager(vault)
        file_list = vm.list_files(pattern)
        
        if not file_list:
            console.print("[warning]No files found[/warning]")
            return
        
        console.print(f"\n[info]Found {len(file_list)} file(s):[/info]\n")
        for f in file_list:
            console.print(f"  📄 {f.relative_path}")
        console.print()
    except Exception as e:
        console.print(f"[error]Error: {e}[/error]")
        sys.exit(1)


@cli.command()
@click.option("--vault", "-v", help="Path to your Obsidian vault")
@click.argument("query")
def search(vault: str, query: str):
    """Search for files containing specific text."""
    
    _, env_vault = get_config()
    vault = vault or env_vault
    
    if not vault:
        console.print("[error]Error: No vault path provided.[/error]")
        sys.exit(1)
    
    try:
        vm = VaultManager(vault)
        results = vm.search_content(query)
        
        if not results:
            console.print(f"[warning]No files found containing: {query}[/warning]")
            return
        
        console.print(f"\n[info]Found {len(results)} file(s) containing '{query}':[/info]\n")
        for f in results:
            console.print(f"  📄 {f.relative_path}")
        console.print()
    except Exception as e:
        console.print(f"[error]Error: {e}[/error]")
        sys.exit(1)


def main():
    """Entry point."""
    cli()


if __name__ == "__main__":
    main()
