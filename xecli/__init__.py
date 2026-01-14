import typer
import requests
import os
import json
import shutil
from pathlib import Path
import platform
from datetime import datetime
import sys
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.style import Style
import subprocess

class AliasTyper(typer.Typer):
    def __call__(self, *args, **kwargs):
        if len(sys.argv) > 1:
            aliases = load_aliases()
            if aliases and sys.argv[1] in aliases:
                original_cmd = sys.argv[1]
                expanded = aliases[original_cmd].split()
                
                if is_debug_mode():
                    console.print(f"[dim]Resolving alias '{original_cmd}' → '{aliases[original_cmd]}'[/]")
                
                sys.argv = [sys.argv[0]] + expanded + sys.argv[2:]
        
        return super().__call__(*args, **kwargs)

app = AliasTyper(
    help="xEclipsity tool manager", add_completion=False)
tools_app = typer.Typer(help="Manage tools: install, update, remove")
config_app = typer.Typer(help="Manage configuration settings")
backup_app = typer.Typer(help="Backup and restore your configuration")
debug_app = typer.Typer(help="Control debug mode")
alias_app = typer.Typer(help="Manage command aliases")

app.add_typer(tools_app, name="tools")
app.add_typer(config_app, name="config")
app.add_typer(backup_app, name="backup")
app.add_typer(debug_app, name="debug")
app.add_typer(alias_app, name="alias")

console = Console()

GITHUB = "xEclipsity"
EXCLUDED_REPOS = [".github"]


def get_base_dir():
    if platform.system() == "Windows":
        return Path(os.environ["LOCALAPPDATA"]) / "xecli"
    else:
        return Path.home() / ".local/share/xecli"


BASE_DIR = get_base_dir()
TOOLS_JSON = BASE_DIR / "tools.json"
CONFIG_JSON = BASE_DIR / "config.json"
ALIASES_JSON = BASE_DIR / "aliases.json"
LOG_FILE = BASE_DIR / "xecli.log"
BACKUP_DIR = BASE_DIR / "backups"


def is_debug_mode():
    config = load_config()
    return config.get("_debug", False)


def log(message: str, level: str = "INFO"):
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] [{level}] {message}\n")


def debug_log(message: str):
    if is_debug_mode():
        console.print(f"[dim]┃ [DEBUG] {message}[/]")
    log(message, "DEBUG")


def echo_log(message: str, level: str = "INFO", err: bool = False):
    icons = {
        "ERROR": "✗",
        "WARNING": "⚠",
        "INFO": "ℹ",
        "SUCCESS": "✓"
    }
    colors = {
        "ERROR": "bold red",
        "WARNING": "bold yellow",
        "INFO": "bold cyan",
        "SUCCESS": "bold green"
    }

    icon = icons.get(level, "•")
    color = colors.get(level, "white")

    console.print(f"[{color}]{icon}[/] {message}")
    log(message, level)


def success_log(message: str):
    console.print(f"[bold green]✓[/] {message}")
    log(message, "SUCCESS")


def load_tools():
    if TOOLS_JSON.exists():
        try:
            with open(TOOLS_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            log(f"Failed to parse tools.json: {e}", "ERROR")
            return {}
    return {}


def save_tools(tools_dict):
    try:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        with open(TOOLS_JSON, "w", encoding="utf-8") as f:
            json.dump(tools_dict, f, indent=2)
        debug_log(f"Saved tools.json successfully")
    except Exception as e:
        log(f"Failed to save tools.json: {e}", "ERROR")
        raise


def load_config():
    if CONFIG_JSON.exists():
        try:
            with open(CONFIG_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            log(f"Failed to parse config.json: {e}", "ERROR")
            return {}
    return {}


def save_config(config_dict):
    try:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_JSON, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2)
        debug_log(f"Saved config.json successfully")
    except Exception as e:
        log(f"Failed to save config.json: {e}", "ERROR")
        raise


def load_aliases():
    if ALIASES_JSON.exists():
        try:
            with open(ALIASES_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            log(f"Failed to parse aliases.json: {e}", "ERROR")
            return {}
    return {}


def save_aliases(aliases_dict):
    try:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        with open(ALIASES_JSON, "w", encoding="utf-8") as f:
            json.dump(aliases_dict, f, indent=2)
        debug_log(f"Saved aliases.json successfully")
    except Exception as e:
        log(f"Failed to save aliases.json: {e}", "ERROR")
        raise


def get_download_dir():
    config = load_config()
    download_dir = config.get("download_dir")
    if download_dir:
        return Path(download_dir).expanduser()
    return Path.cwd()


@alias_app.command("set")
def alias_set(shortcut: str, command: str):
    aliases = load_aliases()

    if shortcut in aliases:
        echo_log(
            f"Alias '{shortcut}' already exists: {aliases[shortcut]}", "WARNING")
        response = typer.prompt("Overwrite? [y/n]", default="n").lower()
        if response != "y":
            return

    aliases[shortcut] = command
    save_aliases(aliases)
    success_log(f"Alias created: '{shortcut}' → '{command}'")


@alias_app.command("get")
def alias_get(shortcut: str):
    aliases = load_aliases()

    if shortcut in aliases:
        console.print(
            f"\n[cyan]{shortcut}[/] → [green]{aliases[shortcut]}[/]\n")
    else:
        echo_log(f"Alias '{shortcut}' not found", "WARNING")


@alias_app.command("list")
def alias_list():
    aliases = load_aliases()

    if not aliases:
        echo_log("No aliases configured")
        return

    console.print("\n[bold cyan]Configured Aliases:[/]\n")

    table = Table(show_header=True,
                  header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Shortcut", style="cyan", width=15)
    table.add_column("Command", style="green")

    for shortcut, command in sorted(aliases.items()):
        table.add_row(shortcut, command)

    console.print(table)
    console.print()


@alias_app.command("remove")
def alias_remove(shortcut: str):
    aliases = load_aliases()

    if shortcut not in aliases:
        echo_log(f"Alias '{shortcut}' not found", "WARNING")
        return

    command = aliases.pop(shortcut)
    save_aliases(aliases)
    success_log(f"Removed alias: '{shortcut}' (was: '{command}')")


@alias_app.command("clear")
def alias_clear():
    aliases = load_aliases()

    if not aliases:
        echo_log("No aliases to clear")
        return

    console.print(f"\n[yellow]⚠ About to remove {len(aliases)} alias(es)[/]\n")
    response = typer.prompt("Continue? [y/n]", default="n").lower()

    if response != "y":
        return

    aliases.clear()
    save_aliases(aliases)
    success_log("All aliases removed")


@app.command("help")
def show_help(legacy: bool = typer.Option(False, "--legacy", help="Show legacy help")):
    if legacy:
        show_legacy_help()
        return

    console.print("\n")

    title = Panel(
        "[bold white]xEclipsity Manager[/]\n"
        f"[dim]GitHub: {GITHUB}[/]\n"
        "[dim cyan]A Python CLI to manage xEclipsity tools and releases[/]",
        border_style="bold cyan",
        box=box.DOUBLE,
        padding=(1, 2)
    )
    console.print(title)

    console.print("\n[bold white on blue] QUICK START [/]\n")
    quick_start = Table(show_header=False, box=None,
                        padding=(0, 2), show_edge=False)
    quick_start.add_column("Step", style="bold cyan", width=8)
    quick_start.add_column("Command", style="green", width=30)
    quick_start.add_column("Description", style="dim white")

    quick_start.add_row("1.", "xe setup", "Initialize xecli environment")
    quick_start.add_row("2.", "xe tools list", "Browse available tools")
    quick_start.add_row("3.", "xe tools install <name>",
                        "Install your first tool")
    quick_start.add_row("4.", "xe doctor", "Verify everything works")

    console.print(quick_start)

    console.print("\n[bold white on blue] CORE COMMANDS [/]\n")
    core_table = Table(show_header=True, header_style="bold magenta",
                       box=box.SIMPLE_HEAD, padding=(0, 2))
    core_table.add_column("Command", style="bold green", width=22)
    core_table.add_column("Description", style="white", width=50)
    core_table.add_column("Usage", style="dim cyan")

    core_table.add_row(
        "setup",
        "Initialize xecli (first-time setup)",
        "xe setup"
    )
    core_table.add_row(
        "help",
        "Display this comprehensive help guide",
        "xe help"
    )
    core_table.add_row(
        "doctor",
        "Run diagnostics and health checks",
        "xe doctor"
    )
    core_table.add_row(
        "upgrade-self",
        "Update xecli to the latest version",
        "xe upgrade-self"
    )
    core_table.add_row(
        "uninstall-self",
        "Completely remove xecli from system",
        "xe uninstall-self"
    )
    core_table.add_row(
        "logs",
        "View recent activity logs (debug mode)",
        "xe logs -n 100"
    )

    console.print(core_table)

    console.print("\n[bold white on yellow] TOOLS MANAGEMENT [/]\n")
    tools_table = Table(show_header=True, header_style="bold magenta",
                        box=box.SIMPLE_HEAD, padding=(0, 2))
    tools_table.add_column("Command", style="bold yellow", width=30)
    tools_table.add_column("Description", style="white", width=42)
    tools_table.add_column("Example", style="dim cyan")

    tools_table.add_row(
        "tools list",
        "Show all available tools from GitHub",
        "xe tools list"
    )
    tools_table.add_row(
        "tools install <name>",
        "Install a tool from latest release",
        "xe tools install myapp"
    )
    tools_table.add_row(
        "tools install <name> --branch",
        "Install from specific Git branch",
        "xe tools install test --branch main"
    )
    tools_table.add_row(
        "tools info <name>",
        "Display detailed tool information",
        "xe tools info test"
    )
    tools_table.add_row(
        "tools check <name>",
        "Check if updates are available",
        "xe tools check test"
    )
    tools_table.add_row(
        "tools outdated",
        "List all tools with available updates",
        "xe tools outdated"
    )
    tools_table.add_row(
        "tools update <name>",
        "Update a specific tool to latest",
        "xe tools update test"
    )
    tools_table.add_row(
        "tools update --all",
        "Update all installed tools at once",
        "xe tools update --all"
    )
    tools_table.add_row(
        "tools remove <name>",
        "Uninstall and remove a tool",
        "xe tools remove test"
    )
    tools_table.add_row(
        "tools remove <name> --dry-run",
        "Preview removal without executing",
        "xe tools remove test --dry-run"
    )

    console.print(tools_table)

    console.print("\n[bold white on magenta] CONFIGURATION [/]\n")
    config_table = Table(
        show_header=True, header_style="bold magenta", box=box.SIMPLE_HEAD, padding=(0, 2))
    config_table.add_column("Command", style="bold magenta", width=30)
    config_table.add_column("Description", style="white", width=42)
    config_table.add_column("Example", style="dim cyan")

    config_table.add_row(
        "config set <key> <value>",
        "Set a configuration value",
        "xe config set download_dir ~/tools"
    )
    config_table.add_row(
        "config get <key>",
        "Retrieve a configuration value",
        "xe config get download_dir"
    )
    config_table.add_row(
        "config list",
        "Display all current settings",
        "xe config list"
    )
    config_table.add_row(
        "config delete <key>",
        "Remove a specific configuration",
        "xe config delete download_dir"
    )
    config_table.add_row(
        "config delete --all",
        "Clear all configuration settings",
        "xe config delete --all"
    )

    console.print(config_table)

    console.print("\n[bold white on green] ALIASES [/]\n")
    alias_table = Table(
        show_header=True, header_style="bold magenta", box=box.SIMPLE_HEAD, padding=(0, 2))
    alias_table.add_column("Command", style="bold green", width=30)
    alias_table.add_column("Description", style="white", width=42)
    alias_table.add_column("Example", style="dim cyan")

    alias_table.add_row(
        "alias set <short> <cmd>",
        "Create command shortcut",
        "xe alias set i install"
    )
    alias_table.add_row(
        "alias get <short>",
        "Show alias command",
        "xe alias get i"
    )
    alias_table.add_row(
        "alias list",
        "List all aliases",
        "xe alias list"
    )
    alias_table.add_row(
        "alias remove <short>",
        "Remove an alias",
        "xe alias remove i"
    )
    alias_table.add_row(
        "alias clear",
        "Remove all aliases",
        "xe alias clear"
    )

    console.print(alias_table)

    console.print("\n[bold white on blue] BACKUP & RESTORE [/]\n")
    backup_table = Table(
        show_header=True, header_style="bold magenta", box=box.SIMPLE_HEAD, padding=(0, 2))
    backup_table.add_column("Command", style="bold blue", width=30)
    backup_table.add_column("Description", style="white", width=42)
    backup_table.add_column("Example", style="dim cyan")

    backup_table.add_row(
        "backup create [name]",
        "Create backup (auto-named if omitted)",
        "xe backup create stable-2024"
    )
    backup_table.add_row(
        "backup restore [name]",
        "Restore backup (latest if omitted)",
        "xe backup restore stable-2024"
    )
    backup_table.add_row(
        "backup list",
        "Show all available backups",
        "xe backup list"
    )
    backup_table.add_row(
        "backup delete <name>",
        "Delete a specific backup",
        "xe backup delete old-backup"
    )
    backup_table.add_row(
        "backup delete --all",
        "Remove all backups (with confirm)",
        "xe backup delete --all"
    )

    console.print(backup_table)

    console.print("\n[bold white on red] DEBUG MODE [/]\n")
    debug_table = Table(show_header=True, header_style="bold magenta",
                        box=box.SIMPLE_HEAD, padding=(0, 2))
    debug_table.add_column("Command", style="bold red", width=30)
    debug_table.add_column("Description", style="white", width=42)
    debug_table.add_column("Example", style="dim cyan")

    debug_table.add_row(
        "debug activate",
        "Enable verbose debug logging",
        "xe debug activate"
    )
    debug_table.add_row(
        "debug deactivate",
        "Disable debug logging",
        "xe debug deactivate"
    )
    debug_table.add_row(
        "logs [--lines N]",
        "View recent log entries (debug only)",
        "xe logs --lines 50"
    )

    console.print(debug_table)

    console.print("\n[bold white on cyan] SYSTEM INFORMATION [/]\n")
    info_table = Table(show_header=False, box=box.SIMPLE,
                       padding=(0, 2), show_edge=False)
    info_table.add_column("Label", style="bold cyan", width=25)
    info_table.add_column("Path", style="white")

    info_table.add_row("📁 Base Directory", str(BASE_DIR))
    info_table.add_row("🔧 Tools Configuration", str(TOOLS_JSON))
    info_table.add_row("⚙️ User Configuration", str(CONFIG_JSON))
    info_table.add_row("🔗 Aliases", str(ALIASES_JSON))
    info_table.add_row("📝 Log File", str(LOG_FILE))
    info_table.add_row("💾 Backup Directory", str(BACKUP_DIR))

    console.print(info_table)

    console.print("\n[bold white on green] TIPS & TRICKS [/]\n")
    tips = [
        "[bold cyan]•[/] Create aliases for frequent commands: [dim]xe alias set i install[/]",
        "[bold cyan]•[/] Use dry-run before destructive operations: [dim]xe tools remove test --dry-run[/]",
        "[bold cyan]•[/] Create backups before major updates: [dim]xe backup create pre-update[/]",
        "[bold cyan]•[/] Enable debug mode when troubleshooting: [dim]xe debug activate[/]",
        "[bold cyan]•[/] Run [green]xe doctor[/] regularly to catch issues early",
    ]

    for tip in tips:
        console.print(f"  {tip}")

    console.print(
        f"\n[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")
    console.print(
        f"[dim]For more information, visit: [cyan]https://github.com/{GITHUB}[/][/]")
    console.print(
        f"[dim]Report issues or suggestions: [cyan]https://github.com/{GITHUB}/xecli/issues[/][/]")
    console.print(
        f"[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n")

    log("Displayed help information", "INFO")


def show_legacy_help():
    console.print("\n")

    header = Table.grid(padding=(0, 2))
    header.add_column(style="bold cyan", justify="center")
    header.add_row(
        "╭─────────────────────────────────────────────────────────────╮")
    header.add_row(
        "│                      [bold white]xEclipsity Manager[/]                     │")
    header.add_row(
        f"│                      [dim]GitHub: {GITHUB}[/]                     │")
    header.add_row(
        "╰─────────────────────────────────────────────────────────────╯")
    console.print(Panel(header, border_style="cyan", box=box.ROUNDED))

    commands_table = Table(show_header=False, box=None, padding=(0, 2))
    commands_table.add_column("Command", style="bold green", width=20)
    commands_table.add_column("Description", style="white")

    commands_table.add_row("setup", "Initialize xecli")
    commands_table.add_row("help", "Show this help message")
    commands_table.add_row("doctor", "Run diagnostic checks")
    commands_table.add_row("upgrade-self", "Update xecli to latest version")
    commands_table.add_row("uninstall-self", "Uninstall xecli")
    commands_table.add_row("logs", "View recent logs (debug mode)")

    console.print("\n[bold cyan]COMMANDS[/]")
    console.print(commands_table)

    tools_table = Table(show_header=False, box=None, padding=(0, 2))
    tools_table.add_column("Command", style="bold yellow", width=35)
    tools_table.add_column("Description", style="white")

    tools_table.add_row("tools list", "List all available tools")
    tools_table.add_row("tools install NAME", "Install a specific tool")
    tools_table.add_row("tools install NAME --branch BRANCH",
                        "Install from specific branch")
    tools_table.add_row("tools info NAME", "Show detailed info about a tool")
    tools_table.add_row("tools check NAME", "Check if a tool has updates")
    tools_table.add_row("tools update NAME", "Update a specific tool")
    tools_table.add_row("tools update --all", "Update all installed tools")
    tools_table.add_row("tools outdated", "Show all tools with updates")
    tools_table.add_row("tools remove NAME", "Remove an installed tool")
    tools_table.add_row("tools remove NAME --dry-run", "Preview removal")

    console.print("\n[bold cyan]TOOLS COMMANDS[/]")
    console.print(tools_table)

    config_table = Table(show_header=False, box=None, padding=(0, 2))
    config_table.add_column("Command", style="bold magenta", width=35)
    config_table.add_column("Description", style="white")

    config_table.add_row("config set KEY VALUE", "Set a configuration value")
    config_table.add_row("config get KEY", "Get a configuration value")
    config_table.add_row("config list", "List all configuration values")
    config_table.add_row("config delete KEY", "Delete a configuration key")
    config_table.add_row("config delete --all", "Delete all configuration")

    console.print("\n[bold cyan]CONFIG COMMANDS[/]")
    console.print(config_table)

    alias_table = Table(show_header=False, box=None, padding=(0, 2))
    alias_table.add_column("Command", style="bold green", width=35)
    alias_table.add_column("Description", style="white")

    alias_table.add_row("alias set SHORT CMD", "Create alias")
    alias_table.add_row("alias list", "List all aliases")
    alias_table.add_row("alias remove SHORT", "Remove alias")
    alias_table.add_row("alias clear", "Remove all aliases")

    console.print("\n[bold cyan]ALIAS COMMANDS[/]")
    console.print(alias_table)

    console.print(
        f"\n[dim]For better help, use: [cyan]xe help[/][/]")
    console.print(
        f"[dim]Visit: https://github.com/{GITHUB}[/]\n")
    log("Displayed legacy help information", "INFO")


@app.command("setup")
def setup():
    try:
        console.print()
        console.print(Panel(
            "[bold cyan]Initializing xEclipsity Manager[/]",
            border_style="cyan",
            box=box.ROUNDED
        ))
        console.print()

        BASE_DIR.mkdir(parents=True, exist_ok=True)
        debug_log(f"Created base directory at {BASE_DIR}")

        if not TOOLS_JSON.exists():
            with open(TOOLS_JSON, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)
            success_log(f"Created tools configuration")
        else:
            echo_log(f"Tools configuration already exists", "INFO")

        if not CONFIG_JSON.exists():
            with open(CONFIG_JSON, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)
            success_log(f"Created configuration file")
        else:
            echo_log(f"Configuration file already exists", "INFO")

        if not ALIASES_JSON.exists():
            with open(ALIASES_JSON, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)
            success_log(f"Created aliases file")
        else:
            echo_log(f"Aliases file already exists", "INFO")

        if not LOG_FILE.exists():
            LOG_FILE.touch()
            success_log(f"Created log file")

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        debug_log(f"Created backup directory at {BACKUP_DIR}")

        console.print()
        info_panel = Panel(
            f"[cyan]Base:[/] {BASE_DIR}\n"
            f"[cyan]OS:[/] {platform.system()} ({platform.machine()})\n"
            f"[cyan]Python:[/] {platform.python_version()}",
            title="[bold]System Info[/]",
            border_style="dim cyan",
            box=box.ROUNDED
        )
        console.print(info_panel)
        console.print()
        success_log("Setup complete!")
        console.print()

    except Exception as e:
        echo_log(f"Setup failed: {e}", "ERROR", err=True)
        sys.exit(1)


@app.command("doctor")
def doctor():
    console.print()
    console.print(Panel(
        "[bold cyan]Running System Diagnostics[/]",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()

    issues = []
    checks_passed = 0
    total_checks = 0

    total_checks += 1
    console.print("[bold]━━━ xecli Version Check[/]")
    try:
        current_version = None
        package_manager = None

        try:
            result = subprocess.run(
                ["pip", "show", "xecli"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith("Version:"):
                        current_version = line.split(":", 1)[1].strip()
                        package_manager = "pip"
                        break
        except FileNotFoundError:
            pass

        if not current_version:
            try:
                result = subprocess.run(
                    ["pipx", "list"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and "xecli" in result.stdout:
                    for line in result.stdout.split('\n'):
                        if "xecli" in line and "package xecli" in line:
                            parts = line.split()
                            if len(parts) > 2:
                                current_version = parts[2].strip().rstrip(',')
                                package_manager = "pipx"
                                break
            except FileNotFoundError:
                pass

        if current_version:
            console.print(
                f"  [cyan]Current version:[/] {current_version} [dim]({package_manager})[/]")

            try:
                pypi_url = "https://pypi.org/pypi/xecli/json"
                r = requests.get(pypi_url, timeout=10)
                r.raise_for_status()
                pypi_data = r.json()
                latest_version = pypi_data["info"]["version"]

                current_clean = current_version.strip().rstrip(',')
                latest_clean = latest_version.strip()

                if current_clean == latest_clean:
                    success_log(f"xecli is up to date ({latest_clean})")
                    checks_passed += 1
                else:
                    echo_log(
                        f"Update available: {current_clean} → {latest_clean}", "WARNING")
                    console.print(f"  [dim]Run 'xe upgrade-self' to update[/]")
                    issues.append("xecli outdated")
            except requests.RequestException as e:
                echo_log(f"Could not check PyPI: {e}", "WARNING")
                issues.append("PyPI unreachable")
        else:
            echo_log("xecli not found via pip/pipx", "WARNING")
            issues.append("xecli not found")
    except Exception as e:
        echo_log(f"Version check error: {e}", "ERROR")
        issues.append("version check failed")

    console.print()

    total_checks += 1
    console.print("[bold]━━━ Directory Structure Check[/]")
    if BASE_DIR.exists():
        success_log(f"Base directory exists: {BASE_DIR}")
        checks_passed += 1
    else:
        echo_log(f"Base directory missing: {BASE_DIR}", "ERROR")
        issues.append("Base directory missing")

    total_checks += 1
    console.print()
    console.print("[bold]━━━ Configuration Files Check[/]")

    config_files = {
        "tools.json": TOOLS_JSON,
        "config.json": CONFIG_JSON,
        "aliases.json": ALIASES_JSON,
        "backups/": BACKUP_DIR
    }

    for name, path in config_files.items():
        if path.exists():
            if path.is_dir():
                success_log(f"{name} directory exists")
            else:
                try:
                    with open(path, "r") as f:
                        json.load(f)
                    success_log(f"{name} is valid")
                except json.JSONDecodeError:
                    echo_log(f"{name} is corrupted", "ERROR")
                    issues.append(f"Invalid {name}")
        else:
            echo_log(f"{name} not found", "WARNING")
            issues.append(f"{name} missing")

    if not issues or len(issues) < 2:
        checks_passed += 1

    total_checks += 1
    console.print()
    console.print("[bold]━━━ File Permissions Check[/]")
    try:
        test_file = BASE_DIR / ".test_write"
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        test_file.touch()
        test_file.unlink()
        success_log(f"Read/Write permissions OK")
        checks_passed += 1
    except Exception as e:
        echo_log(f"Permission error: {e}", "ERROR")
        issues.append("Permission error")

    total_checks += 1
    console.print()
    console.print("[bold]━━━ Network Connectivity Check[/]")
    try:
        requests.get("https://www.google.com", timeout=5)
        success_log("Internet connectivity OK")
        checks_passed += 1
    except requests.RequestException:
        echo_log("No internet connection", "ERROR")
        issues.append("No internet")

    total_checks += 1
    console.print()
    console.print("[bold]━━━ GitHub API Check[/]")
    try:
        r = requests.get(f"https://api.github.com/orgs/{GITHUB}", timeout=10)
        r.raise_for_status()

        config = load_config()
        if config.get("github_token"):
            success_log(f"GitHub API reachable (authenticated)")
        else:
            success_log(f"GitHub API reachable")

        rate_limit = r.headers.get('X-RateLimit-Remaining')
        if rate_limit:
            console.print(f"  [dim]Rate limit remaining: {rate_limit}[/]")

        checks_passed += 1
    except requests.RequestException as e:
        echo_log(f"Cannot reach GitHub API: {e}", "ERROR")
        issues.append("GitHub unreachable")

    total_checks += 1
    console.print()
    console.print("[bold]━━━ Installed Tools Check[/]")
    tools = load_tools()

    if tools:
        console.print(f"  [cyan]Found {len(tools)} installed tool(s)[/]")

        missing_files = []
        for tool_name, tool_data in tools.items():
            file_path = Path(tool_data.get("file", ""))
            if not file_path.exists():
                missing_files.append(tool_name)

        if missing_files:
            echo_log(
                f"Missing files for: {', '.join(missing_files)}", "WARNING")
            issues.append("Missing tool files")
        else:
            success_log("All tool files present")
            checks_passed += 1
    else:
        echo_log("No tools installed", "INFO")
        checks_passed += 1

    total_checks += 1
    console.print()
    console.print("[bold]━━━ Python Dependencies Check[/]")

    required_modules = ["requests", "typer", "rich"]
    missing_modules = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    if missing_modules:
        echo_log(f"Missing modules: {', '.join(missing_modules)}", "ERROR")
        issues.append("Missing dependencies")
    else:
        success_log("All required modules installed")
        checks_passed += 1

    total_checks += 1
    console.print()
    console.print("[bold]━━━ Disk Space Check[/]")
    try:
        import shutil
        total, used, free = shutil.disk_usage(BASE_DIR)
        free_gb = free / (1024**3)

        if free_gb < 0.1:
            echo_log(f"Low disk space: {free_gb:.2f} GB free", "WARNING")
            issues.append("Low disk space")
        else:
            success_log(f"Sufficient disk space: {free_gb:.2f} GB free")
            checks_passed += 1
    except Exception as e:
        echo_log(f"Could not check disk space: {e}", "WARNING")

    total_checks += 1
    console.print()
    console.print("[bold]━━━ Log File Check[/]")
    if LOG_FILE.exists():
        log_size = LOG_FILE.stat().st_size / 1024  # KB
        if log_size > 10240:  # 10 MB
            echo_log(f"Large log file: {log_size/1024:.1f} MB", "WARNING")
            console.print(f"  [dim]Consider clearing: rm {LOG_FILE}[/]")
        else:
            success_log(f"Log file OK ({log_size:.1f} KB)")
        checks_passed += 1
    else:
        echo_log("Log file not found", "INFO")

    console.print()
    console.print("[bold]━━━ System Information[/]")

    info_table = Table(show_header=False, box=None, padding=(0, 1))
    info_table.add_column("Property", style="cyan", width=20)
    info_table.add_column("Value", style="white")

    info_table.add_row("Operating System", platform.system())
    info_table.add_row("Architecture", platform.machine())
    info_table.add_row("Python Version", platform.python_version())
    info_table.add_row("Base Directory", str(BASE_DIR))

    config = load_config()
    debug_status = "[green]Enabled[/]" if config.get(
        "_debug") else "[dim]Disabled[/]"
    info_table.add_row("Debug Mode", debug_status)

    console.print(info_table)

    console.print()
    pass_rate = (checks_passed / total_checks) * 100

    summary_panel = Panel(
        f"[bold]Checks Passed:[/] {checks_passed}/{total_checks} ({pass_rate:.0f}%)\n"
        f"[bold]Issues Found:[/] {len(issues)}\n"
        f"[bold]Status:[/] {'[green]Healthy[/]' if pass_rate >= 80 else '[yellow]Needs Attention[/]' if pass_rate >= 50 else '[red]Critical[/]'}",
        title="[bold]Diagnostic Summary[/]",
        border_style="green" if pass_rate >= 80 else "yellow" if pass_rate >= 50 else "red",
        box=box.ROUNDED
    )
    console.print(summary_panel)

    if issues:
        console.print()
        console.print("[yellow]Issues detected:[/]")
        for issue in issues:
            console.print(f"  [yellow]•[/] {issue}")

    console.print()


@app.command("upgrade-self")
def upgrade_self():
    console.print()
    console.print(Panel(
        "[bold cyan]Checking for xecli Updates[/]",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()

    try:
        current_version = None
        package_manager = None

        try:
            result = subprocess.run(
                ["pip", "show", "xecli"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith("Version:"):
                        current_version = line.split(":", 1)[1].strip()
                        package_manager = "pip"
                        break
        except FileNotFoundError:
            pass

        if not current_version:
            try:
                result = subprocess.run(
                    ["pipx", "list"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and "xecli" in result.stdout:
                    for line in result.stdout.split('\n'):
                        if "xecli" in line and "package xecli" in line:
                            parts = line.split()
                            if len(parts) > 2:
                                current_version = parts[2].strip().rstrip(',')
                                package_manager = "pipx"
                                break
            except FileNotFoundError:
                pass

        if not current_version:
            echo_log("xecli not found via pip or pipx", "ERROR")
            echo_log("Install with: pip install xecli", "INFO")
            return

        console.print(f"[cyan]Current version:[/] {current_version}")

        try:
            pypi_url = "https://pypi.org/pypi/xecli/json"
            r = requests.get(pypi_url, timeout=10)
            r.raise_for_status()
            pypi_data = r.json()
            latest_version = pypi_data["info"]["version"]

            console.print(f"[cyan]Latest version:[/] {latest_version}\n")

            current_clean = current_version.strip().rstrip(',')
            latest_clean = latest_version.strip()

            if current_clean == latest_clean:
                success_log("xecli is already up to date!")
                console.print()
                return
            else:
                console.print(
                    f"[yellow]Update available: {current_clean} → {latest_clean}[/]\n")
        except requests.RequestException as e:
            echo_log(f"Failed to check PyPI: {e}", "WARNING")
            console.print("[cyan]Proceeding with upgrade anyway...[/]\n")

        if package_manager == "pip":
            console.print("[cyan]Upgrading via pip...[/]")
            result = subprocess.run(
                ["pip", "install", "--upgrade", "xecli"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                console.print()
                success_log("xecli updated successfully!")
                console.print()
            else:
                echo_log(f"pip upgrade failed: {result.stderr}", "ERROR")

        elif package_manager == "pipx":
            console.print("[cyan]Upgrading via pipx...[/]")
            result = subprocess.run(
                ["pipx", "upgrade", "xecli"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                console.print()
                success_log("xecli updated successfully via pipx!")
                console.print()
            else:
                echo_log(f"pipx upgrade failed: {result.stderr}", "ERROR")

    except FileNotFoundError:
        echo_log("pip/pipx not found. Install manually:", "ERROR")
        echo_log("pip install --upgrade xecli", "INFO")


@app.command("uninstall-self")
def uninstall_self():
    console.print()
    console.print(Panel(
        "[bold red]⚠ Uninstalling xEclipsity Manager[/]",
        border_style="red",
        box=box.ROUNDED
    ))
    console.print()

    try:
        package_manager = None

        try:
            result = subprocess.run(
                ["pip", "show", "xecli"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                package_manager = "pip"
        except FileNotFoundError:
            pass

        if not package_manager:
            try:
                result = subprocess.run(
                    ["pipx", "list"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and "xecli" in result.stdout:
                    package_manager = "pipx"
            except FileNotFoundError:
                pass

        if not package_manager:
            echo_log("xecli not found via pip or pipx", "WARNING")

            response = typer.prompt(
                "\nDelete configuration files? [y/n]", default="n").lower()
            if response == "y":
                try:
                    if BASE_DIR.exists():
                        shutil.rmtree(BASE_DIR)
                        success_log(
                            f"Deleted configuration directory: {BASE_DIR}")
                except Exception as e:
                    echo_log(f"Failed to delete configuration: {e}", "ERROR")
            return

        console.print(f"[cyan]Package manager:[/] {package_manager}\n")

        if package_manager == "pip":
            console.print("[cyan]Uninstalling via pip...[/]")
            result = subprocess.run(
                ["pip", "uninstall", "xecli", "-y"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                console.print()
                success_log("xecli uninstalled successfully!")
            else:
                echo_log(f"pip uninstall failed: {result.stderr}", "ERROR")
                return

        elif package_manager == "pipx":
            console.print("[cyan]Uninstalling via pipx...[/]")
            result = subprocess.run(
                ["pipx", "uninstall", "xecli"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                console.print()
                success_log("xecli uninstalled successfully via pipx!")
            else:
                echo_log(f"pipx uninstall failed: {result.stderr}", "ERROR")
                return

        console.print()
        response = typer.prompt(
            "Delete configuration files? [y/n]", default="n").lower()
        if response == "y":
            try:
                if BASE_DIR.exists():
                    shutil.rmtree(BASE_DIR)
                    success_log(f"Deleted configuration directory")
                    console.print(f"[dim]{BASE_DIR}[/]")
            except Exception as e:
                echo_log(f"Failed to delete configuration: {e}", "ERROR")
        else:
            console.print(f"\n[dim]Configuration preserved at: {BASE_DIR}[/]")

        console.print()

    except Exception as e:
        echo_log(f"Uninstall failed: {e}", "ERROR")
        sys.exit(1)


@tools_app.command("list")
def list_tools():
    url = f"https://api.github.com/orgs/{GITHUB}/repos"

    try:
        console.print()
        console.print(Panel(
            f"[bold cyan]Fetching Tools from {GITHUB}[/]",
            border_style="cyan",
            box=box.ROUNDED
        ))
        console.print()

        debug_log(f"Fetching repos from {url}")
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        repos = r.json()

        filtered_repos = [
            repo for repo in repos if repo['name'] not in EXCLUDED_REPOS]

        if not filtered_repos:
            echo_log("No tools available")
            return

        table = Table(show_header=True,
                      header_style="bold magenta", box=box.ROUNDED)
        table.add_column("Tool", style="cyan", width=25)
        table.add_column("Description", style="white")
        table.add_column("Stars", style="yellow", justify="right", width=8)

        for repo in filtered_repos:
            stars = str(repo.get('stargazers_count', 0))
            table.add_row(
                repo['name'],
                repo.get('description', 'No description'),
                stars
            )

        console.print(table)
        console.print()
        success_log(f"Found {len(filtered_repos)} available tools")
        console.print()
        log(f"Listed {len(filtered_repos)} tools", "INFO")

    except requests.RequestException as e:
        echo_log(f"Failed to fetch tools: {e}", "ERROR", err=True)
        sys.exit(1)
    except Exception as e:
        echo_log(f"Unexpected error: {e}", "ERROR", err=True)
        sys.exit(1)


@tools_app.command("install")
def install(
    name: str,
    branch: str = typer.Option(
        None, "--branch", help="Install from specific branch")
):
    if name in EXCLUDED_REPOS:
        echo_log(
            f"Cannot install {name}: excluded repository", "ERROR", err=True)
        sys.exit(1)

    try:
        console.print()
        console.print(Panel(
            f"[bold cyan]Installing {name}[/]" +
            (f"\n[dim]Branch: {branch}[/]" if branch else ""),
            border_style="cyan",
            box=box.ROUNDED
        ))
        console.print()

        log(f"Installing {name}" +
            (f" from branch {branch}" if branch else ""), "INFO")
        download_update(name, branch=branch)
        console.print()
        success_log(f"{name} installed successfully")
        console.print()
    except Exception as e:
        echo_log(f"Install failed for {name}: {e}", "ERROR", err=True)
        sys.exit(1)


@tools_app.command("info")
def info(name: str):
    tools = load_tools()
    local_data = tools.get(name)

    repo = f"{GITHUB}/{name}"
    url = f"https://api.github.com/repos/{repo}/releases/latest"

    console.print()
    console.print(Panel(
        f"[bold cyan]Tool Information: {name}[/]",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()

    if local_data:
        console.print("[bold]━━━ Local Installation[/]")

        info_table = Table(show_header=False, box=None, padding=(0, 1))
        info_table.add_column("Property", style="cyan", width=15)
        info_table.add_column("Value", style="white")

        info_table.add_row("Version", local_data.get('version', 'unknown'))
        info_table.add_row("Path", local_data.get('file', 'unknown'))
        info_table.add_row("Installed", local_data.get(
            'installed_at', 'unknown'))
        info_table.add_row("OS", local_data.get('os', 'unknown'))
        if 'branch' in local_data:
            info_table.add_row("Branch", local_data.get('branch'))

        console.print(info_table)
    else:
        echo_log("Not installed locally", "WARNING")

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        release = r.json()

        console.print(f"\n[bold]━━━ Remote Information[/]")

        remote_table = Table(show_header=False, box=None, padding=(0, 1))
        remote_table.add_column("Property", style="cyan", width=15)
        remote_table.add_column("Value", style="white")

        remote_table.add_row(
            "Latest Version", release.get('tag_name', 'unknown'))
        remote_table.add_row(
            "Published", release.get('published_at', 'unknown'))

        console.print(remote_table)

        repo_url = f"https://api.github.com/repos/{repo}"
        repo_r = requests.get(repo_url, timeout=10)
        if repo_r.status_code == 200:
            repo_data = repo_r.json()
            console.print(
                f"\n  [dim]{repo_data.get('description', 'No description')}[/]")

        body = release.get('body', '')
        if body:
            console.print(f"\n[bold]━━━ Release Notes[/]")
            console.print(Panel(body, box=box.ROUNDED, border_style="dim"))

    except requests.RequestException as e:
        echo_log(f"Failed to fetch remote info: {e}", "ERROR")

    console.print()


@tools_app.command("check")
def check(name: str):
    tools = load_tools()
    local_version = tools.get(name, {}).get("version")

    repo = f"{GITHUB}/{name}"
    url = f"https://api.github.com/repos/{repo}/releases/latest"

    try:
        console.print()
        debug_log(f"Checking latest release for {name}")
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        release = r.json()
        latest_tag = release.get("tag_name", "latest")

        if not local_version:
            echo_log(f"{name} is not installed locally", "WARNING")
            console.print(f"  [cyan]Latest release:[/] {latest_tag}")
            console.print()
            log(f"{name} not installed, latest is {latest_tag}", "INFO")
            return

        if local_version == latest_tag:
            success_log(f"{name} is up-to-date (version {latest_tag})")
            console.print()
            log(f"{name} is up-to-date at {latest_tag}", "INFO")
        else:
            echo_log(f"Update available for {name}", "WARNING")
            console.print(f"  [yellow]Local:[/] {local_version}")
            console.print(f"  [green]Latest:[/] {latest_tag}")
            console.print(f"  [dim]Run: xe tools update {name}[/]")
            console.print()
            log(f"{name} outdated: {local_version} -> {latest_tag}", "INFO")

    except requests.RequestException as e:
        echo_log(f"Failed to check updates: {e}", "ERROR", err=True)
        sys.exit(1)
    except Exception as e:
        echo_log(f"Unexpected error: {e}", "ERROR", err=True)
        sys.exit(1)


@tools_app.command("outdated")
def outdated():
    tools = load_tools()

    if not tools:
        echo_log("No tools installed")
        return

    console.print()
    console.print(Panel(
        "[bold cyan]Checking for Updates[/]",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()

    table = Table(show_header=True,
                  header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Tool", style="cyan", width=20)
    table.add_column("Local", style="yellow", width=15)
    table.add_column("Remote", style="green", width=15)
    table.add_column("Status", style="white")

    outdated_count = 0

    for tool_name, tool_data in tools.items():
        local_version = tool_data.get("version", "unknown")

        try:
            repo = f"{GITHUB}/{tool_name}"
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            release = r.json()
            remote_version = release.get("tag_name", "unknown")

            if local_version == remote_version:
                status = "[green]✓ up-to-date[/]"
            else:
                status = "[yellow]⚠ update available[/]"
                outdated_count += 1

            table.add_row(tool_name, local_version, remote_version, status)

        except Exception as e:
            table.add_row(tool_name, local_version,
                          "[red]error[/]", f"[red]{str(e)[:20]}...[/]")

    console.print(table)
    console.print()

    if outdated_count > 0:
        console.print(
            f"[yellow]{outdated_count} tool(s) have updates available[/]")
        console.print(
            "[dim]Run 'xe tools update --all' to update all tools[/]\n")
    else:
        success_log("All tools are up-to-date!")
        console.print()


@tools_app.command("update")
def update(
    name: str = typer.Argument(None),
    all: bool = typer.Option(False, "--all", help="Update all installed tools")
):
    tools = load_tools()

    if all:
        if not tools:
            echo_log("No tools installed to update")
            return

        console.print()
        console.print(Panel(
            f"[bold cyan]Updating All Tools ({len(tools)})[/]",
            border_style="cyan",
            box=box.ROUNDED
        ))
        console.print()

        log(f"Updating all {len(tools)} tools", "INFO")
        failed = []

        for i, tool_name in enumerate(tools.keys(), 1):
            console.print(f"[dim]───  {i}/{len(tools)} [/]")
            try:
                update_single(tool_name)
            except Exception as e:
                echo_log(
                    f"Failed to update {tool_name}: {e}", "ERROR", err=True)
                failed.append(tool_name)

        console.print()
        if failed:
            echo_log(f"Failed to update: {', '.join(failed)}", "WARNING")
            console.print()
        else:
            success_log("All tools updated successfully")
            console.print()
    else:
        if not name:
            echo_log("Provide a tool name or use --all", "ERROR", err=True)
            sys.exit(1)

        console.print()
        console.print(Panel(
            f"[bold cyan]Updating {name}[/]",
            border_style="cyan",
            box=box.ROUNDED
        ))
        console.print()

        try:
            update_single(name)
            console.print()
        except Exception as e:
            echo_log(f"Update failed: {e}", "ERROR", err=True)
            sys.exit(1)


@tools_app.command("remove")
def remove(
    name: str,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be removed without actually removing")
):
    tools = load_tools()

    if name not in tools:
        echo_log(f"{name} is not installed", "WARNING")
        return

    file_path = Path(tools[name]["file"])

    if dry_run:
        console.print()
        console.print(Panel(
            f"[bold yellow]DRY RUN: Removing {name}[/]",
            border_style="yellow",
            box=box.ROUNDED
        ))
        console.print()

        console.print("[yellow]The following would be removed:[/]\n")
        console.print(f"  [cyan]Tool:[/] {name}")
        console.print(
            f"  [cyan]Version:[/] {tools[name].get('version', 'unknown')}")
        console.print(f"  [cyan]File:[/] {file_path}")

        if file_path.exists():
            file_size = file_path.stat().st_size / 1024  # KB
            console.print(f"  [cyan]Size:[/] {file_size:.1f} KB")
            console.print(f"\n  [green]✓ File exists and would be deleted[/]")
        else:
            console.print(
                f"\n  [yellow]⚠ File not found (would skip deletion)[/]")

        console.print(f"\n  [cyan]Entry would be removed from tools.json[/]")
        console.print(f"\n[dim]Run without --dry-run to actually remove[/]\n")
        return

    try:
        console.print()
        console.print(Panel(
            f"[bold red]Removing {name}[/]",
            border_style="red",
            box=box.ROUNDED
        ))
        console.print()

        if file_path.exists():
            file_path.unlink()
            success_log(f"Deleted file: {name}")
            debug_log(f"Deleted file {file_path}")
        else:
            echo_log(f"File not found, skipping deletion", "WARNING")

        tools.pop(name)
        save_tools(tools)
        success_log(f"Removed {name} from registry")
        console.print()
        log(f"Removed {name} from tools.json", "INFO")

    except Exception as e:
        echo_log(f"Failed to remove {name}: {e}", "ERROR", err=True)
        sys.exit(1)


ALLOWED_CONFIG_KEYS = ["download_dir"]


@config_app.command("set")
def config_set(key: str, value: str):
    if key not in ALLOWED_CONFIG_KEYS:
        echo_log(f"Invalid config key: {key}", "ERROR", err=True)
        console.print(
            f"\n[cyan]Allowed keys:[/] {', '.join(ALLOWED_CONFIG_KEYS)}\n")
        sys.exit(1)

    config = load_config()
    old_value = config.get(key)
    config[key] = value
    save_config(config)

    if old_value:
        console.print(f"\n[dim]{key}: {old_value} → {value}[/]")
    success_log(f"Set {key} = {value}")
    console.print()


@config_app.command("get")
def config_get(key: str):
    config = load_config()
    value = config.get(key)

    console.print()
    if value is not None:
        console.print(f"[cyan]{key}[/] = [green]{value}[/]")
    else:
        echo_log(f"Key '{key}' not found", "WARNING")
    console.print()


@config_app.command("list")
def config_list():
    config = load_config()

    if not config:
        echo_log("No configuration set")
        return

    console.print()
    console.print(Panel(
        "[bold cyan]Current Configuration[/]",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()

    table = Table(show_header=True,
                  header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Key", style="cyan", width=20)
    table.add_column("Value", style="green")

    for key, value in config.items():
        if not key.startswith("_"):
            table.add_row(key, str(value))

    console.print(table)
    console.print()


@config_app.command("delete")
def config_delete(
    key: str = typer.Argument(None),
    all: bool = typer.Option(False, "--all", help="Delete all configuration")
):
    config = load_config()

    if all:
        if not config:
            echo_log("No configuration to delete")
            return

        console.print()
        console.print(Panel(
            "[bold yellow]⚠ Delete All Configuration[/]",
            border_style="yellow",
            box=box.ROUNDED
        ))
        console.print()

        debug_mode = config.get("_debug", False)
        config.clear()
        if debug_mode:
            config["_debug"] = debug_mode
        save_config(config)
        success_log("Deleted all configuration")
        console.print()
        return

    if not key:
        echo_log("Provide a key or use --all", "ERROR", err=True)
        sys.exit(1)

    if key.startswith("_"):
        echo_log(f"Cannot delete internal key: {key}", "ERROR", err=True)
        sys.exit(1)

    if key not in config:
        echo_log(f"Key '{key}' not found in configuration", "WARNING")
        return

    deleted_value = config.pop(key)
    save_config(config)
    console.print()
    success_log(f"Deleted {key} (was: {deleted_value})")
    console.print()


@backup_app.command("create")
def backup_create(name: str = typer.Argument(None)):
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        if name is None:
            existing_backups = sorted(
                [f.stem for f in BACKUP_DIR.glob("backup_*.json")])
            if existing_backups:
                last_num = max([int(b.split("_")[1])
                               for b in existing_backups if b.split("_")[1].isdigit()])
                name = f"backup_{last_num + 1}"
            else:
                name = "backup_1"

        backup_file = BACKUP_DIR / f"{name}.json"

        if backup_file.exists():
            echo_log(f"Backup '{name}' already exists", "WARNING")
            response = typer.prompt("Overwrite? [y/n]", default="n").lower()
            if response != "y":
                return

        console.print()
        console.print(Panel(
            f"[bold cyan]Creating Backup: {name}[/]",
            border_style="cyan",
            box=box.ROUNDED
        ))
        console.print()

        backup_data = {
            "created_at": datetime.now().isoformat(),
            "tools": load_tools(),
            "config": load_config(),
            "aliases": load_aliases(),
        }

        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2)

        success_log(f"Created backup: {name}")
        console.print(f"  [dim]Location: {backup_file}[/]")
        console.print()
        debug_log(f"Backup saved to {backup_file}")

    except Exception as e:
        echo_log(f"Failed to create backup: {e}", "ERROR", err=True)
        sys.exit(1)


@backup_app.command("restore")
def backup_restore(name: str = typer.Argument(None)):
    try:
        if not BACKUP_DIR.exists() or not list(BACKUP_DIR.glob("*.json")):
            echo_log("No backups found", "WARNING")
            return

        if name is None:
            backups = sorted(BACKUP_DIR.glob("*.json"),
                             key=lambda x: x.stat().st_mtime, reverse=True)
            if not backups:
                echo_log("No backups found", "WARNING")
                return
            backup_file = backups[0]
            name = backup_file.stem
        else:
            backup_file = BACKUP_DIR / f"{name}.json"

        if not backup_file.exists():
            echo_log(f"Backup '{name}' not found", "ERROR", err=True)
            sys.exit(1)

        with open(backup_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        console.print()
        console.print(Panel(
            f"[bold yellow]Restoring Backup: {name}[/]\n"
            f"[dim]Created: {backup_data.get('created_at', 'unknown')}[/]",
            border_style="yellow",
            box=box.ROUNDED
        ))
        console.print()

        response = typer.prompt("Continue? [y/n]", default="y").lower()
        if response != "y":
            return

        console.print()
        if "tools" in backup_data:
            save_tools(backup_data["tools"])
            success_log("Restored tools configuration")

        if "config" in backup_data:
            save_config(backup_data["config"])
            success_log("Restored configuration")

        if "aliases" in backup_data:
            save_aliases(backup_data["aliases"])
            success_log("Restored aliases")

        console.print()
        success_log(f"Backup restored: {name}")
        console.print()

    except Exception as e:
        echo_log(f"Failed to restore backup: {e}", "ERROR", err=True)
        sys.exit(1)


@backup_app.command("list")
def backup_list():
    if not BACKUP_DIR.exists() or not list(BACKUP_DIR.glob("*.json")):
        echo_log("No backups found")
        return

    backups = sorted(BACKUP_DIR.glob("*.json"),
                     key=lambda x: x.stat().st_mtime, reverse=True)

    console.print()
    console.print(Panel(
        "[bold cyan]Available Backups[/]",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()

    table = Table(show_header=True,
                  header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Name", style="cyan", width=25)
    table.add_column("Created", style="white", width=25)
    table.add_column("Size", style="yellow", width=12)

    for backup in backups:
        try:
            with open(backup, "r", encoding="utf-8") as f:
                data = json.load(f)
                created = data.get("created_at", "unknown")
        except:
            created = "unknown"

        size = backup.stat().st_size
        size_str = f"{size / 1024:.1f} KB" if size > 1024 else f"{size} B"

        table.add_row(backup.stem, created, size_str)

    console.print(table)
    console.print()


@backup_app.command("delete")
def backup_delete(
    name: str = typer.Argument(None),
    all: bool = typer.Option(False, "--all", help="Delete all backups")
):
    try:
        if not BACKUP_DIR.exists() or not list(BACKUP_DIR.glob("*.json")):
            echo_log("No backups found")
            return

        if all:
            backups = list(BACKUP_DIR.glob("*.json"))

            console.print()
            console.print(Panel(
                f"[bold yellow]⚠ Delete All Backups ({len(backups)})[/]",
                border_style="yellow",
                box=box.ROUNDED
            ))
            console.print()

            response = typer.prompt("Continue? [y/n]", default="n").lower()
            if response != "y":
                return

            for backup in backups:
                backup.unlink()
                debug_log(f"Deleted backup: {backup.stem}")

            console.print()
            success_log(f"Deleted all {len(backups)} backup(s)")
            console.print()
            return

        if not name:
            echo_log("Provide a backup name or use --all", "ERROR", err=True)
            sys.exit(1)

        backup_file = BACKUP_DIR / f"{name}.json"

        if not backup_file.exists():
            echo_log(f"Backup '{name}' not found", "ERROR", err=True)
            sys.exit(1)

        backup_file.unlink()
        console.print()
        success_log(f"Deleted backup: {name}")
        console.print()
        debug_log(f"Deleted backup file: {backup_file}")

    except Exception as e:
        echo_log(f"Failed to delete backup: {e}", "ERROR", err=True)
        sys.exit(1)


@debug_app.command("activate")
def debug_activate():
    config = load_config()
    config["_debug"] = True
    save_config(config)
    console.print()
    success_log("Debug mode activated")
    console.print(f"  [dim]View logs with: xe logs[/]")
    console.print()


@debug_app.command("deactivate")
def debug_deactivate():
    config = load_config()
    config["_debug"] = False
    save_config(config)
    console.print()
    success_log("Debug mode deactivated")
    console.print()


@app.command("logs")
def show_logs(lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show")):
    if not is_debug_mode():
        echo_log("Debug mode must be enabled to view logs", "ERROR", err=True)
        console.print("\n[dim]Enable debug mode with: xe debug activate[/]\n")
        sys.exit(1)

    if not LOG_FILE.exists():
        echo_log("No log file found", "WARNING")
        return

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()

        recent_lines = all_lines[-lines:] if len(
            all_lines) > lines else all_lines

        console.print()
        console.print(Panel(
            f"[bold cyan]Recent Logs[/] [dim]({len(recent_lines)} entries)[/]",
            border_style="cyan",
            box=box.ROUNDED
        ))
        console.print()

        table = Table(show_header=True, header_style="bold magenta",
                      box=box.ROUNDED, show_lines=False)
        table.add_column("Time", style="dim cyan", width=19)
        table.add_column("Level", style="bold", width=8)
        table.add_column("Message", style="white")

        for line in recent_lines:
            line = line.strip()
            if not line:
                continue

            try:
                parts = line.split("] ", 2)
                if len(parts) >= 3:
                    timestamp = parts[0].replace("[", "")
                    level = parts[1].replace("[", "")
                    message = parts[2]

                    level_style = {
                        "ERROR": "bold red",
                        "WARNING": "bold yellow",
                        "INFO": "bold green",
                        "SUCCESS": "bold green",
                        "DEBUG": "dim"
                    }.get(level, "white")

                    table.add_row(
                        timestamp,
                        f"[{level_style}]{level}[/]",
                        message
                    )
            except:
                table.add_row("", "", line)

        console.print(table)
        console.print(f"\n[dim]Log file: {LOG_FILE}[/]\n")

    except Exception as e:
        echo_log(f"Failed to read logs: {e}", "ERROR", err=True)
        sys.exit(1)


def update_single(name: str):
    tools = load_tools()
    local_version = tools.get(name, {}).get("version")

    repo = f"{GITHUB}/{name}"
    url = f"https://api.github.com/repos/{repo}/releases/latest"

    try:
        debug_log(f"Checking updates for {name}")
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        release = r.json()
        latest_tag = release.get("tag_name", "latest")

        if local_version == latest_tag:
            success_log(f"{name} is already up-to-date ({latest_tag})")
            return

        console.print(
            f"[cyan]Updating {name}: {local_version or 'new'} → {latest_tag}[/]")
        log(f"Updating {name} from {local_version} to {latest_tag}", "INFO")
        download_update(name)
        success_log(f"{name} updated to {latest_tag}")

    except Exception as e:
        log(f"Update failed for {name}: {e}", "ERROR")
        raise


def download_update(name: str, branch: str = None):
    repo = f"{GITHUB}/{name}"

    if branch:
        dl_url = f"https://github.com/{repo}/archive/refs/heads/{branch}.zip"
        file_name = f"{name}-{branch}.zip"
        tag_name = f"branch-{branch}"
    else:
        url = f"https://api.github.com/repos/{repo}/releases/latest"

        try:
            debug_log(f"Fetching release info for {name}")
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            release = r.json()

            tag_name = release.get("tag_name", "latest")
            system = platform.system().lower()
            assets = release.get("assets", [])
            asset_to_download = None

            for a in assets:
                n = a["name"].lower()
                if system == "windows" and n.endswith(".exe"):
                    asset_to_download = a
                    break
                elif system != "windows" and (n.endswith(".tar.gz") or n.endswith(".zip")):
                    asset_to_download = a
                    break

            if asset_to_download:
                dl_url = asset_to_download["browser_download_url"]
                file_name = f"{name}-{tag_name}-{asset_to_download['name']}"
            else:
                dl_url = release.get("zipball_url")
                if not dl_url:
                    raise ValueError(f"Couldn't find releases for: {name}")
                file_name = f"{name}-{tag_name}.zip"

        except requests.RequestException as e:
            log(f"download failed for: {name}: {e}", "ERROR")
            raise
        except Exception as e:
            log(f"Error while downloading: {name}: {e}", "ERROR")
            raise

    download_dir = get_download_dir()
    download_dir.mkdir(parents=True, exist_ok=True)
    dest_path = download_dir / file_name

    debug_log(f"Downloading from {dl_url} to {dest_path}")

    try:
        headers = {}

        with requests.get(dl_url, stream=True, headers=headers, timeout=30) as req:
            req.raise_for_status()
            total_size = int(req.headers.get('content-length', 0))

            with Progress(
                SpinnerColumn(style=Style(color="cyan")),
                TextColumn("[bold cyan]{task.description}"),
                BarColumn(complete_style="green", finished_style="bold green"),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
                transient=False
            ) as progress:
                task = progress.add_task(
                    f"Downloading {name}", total=total_size)

                with open(dest_path, "wb") as f:
                    for chunk in req.iter_content(8192):
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))

        success_log(f"Downloaded {name}")
        debug_log(f"Downloaded to {dest_path}")

        tools = load_tools()
        tools[name] = {
            "version": tag_name,
            "file": str(dest_path),
            "os": platform.system().lower(),
            "installed_at": datetime.now().isoformat()
        }
        if branch:
            tools[name]["branch"] = branch
        save_tools(tools)
        debug_log(f"Updated json for: {name}")

    except requests.RequestException as e:
        log(f"download failed for: {name}: {e}", "ERROR")
        raise
    except Exception as e:
        log(f"Error while downloading: {name}: {e}", "ERROR")
        raise


if __name__ == "__main__":
    app()
