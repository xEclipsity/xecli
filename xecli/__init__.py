import typer
import requests
import os
import json
from pathlib import Path
import platform
from datetime import datetime
import sys
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn
from rich.table import Table
from rich.panel import Panel
from rich import box
import subprocess

app = typer.Typer()
tools_app = typer.Typer()
config_app = typer.Typer()
app.add_typer(tools_app, name="tools")
app.add_typer(config_app, name="config")

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
LOG_FILE = BASE_DIR / "xecli.log"


def log(message: str, level: str = "INFO"):
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] [{level}] {message}\n")


def echo_log(message: str, level: str = "INFO", err: bool = False):
    if level == "ERROR":
        console.print(f"[bold red][✗][/] {message}")
    elif level == "WARNING":
        console.print(f"[bold yellow][!][/] {message}")
    elif level == "INFO":
        console.print(f"[bold cyan][i][/] {message}")
    else:
        console.print(message)
    log(message, level)


def success_log(message: str):
    console.print(f"[bold green][✓][/] {message}")
    log(message, "INFO")


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
        log(f"Saved tools.json successfully", "DEBUG")
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
        log(f"Saved config.json successfully", "DEBUG")
    except Exception as e:
        log(f"Failed to save config.json: {e}", "ERROR")
        raise


def get_download_dir():
    config = load_config()
    download_dir = config.get("download_dir")
    if download_dir:
        return Path(download_dir).expanduser()
    return Path.cwd()


@app.command("help")
def show_help():
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

    console.print("\n[bold cyan]TOOLS COMMANDS[/]")
    console.print(tools_table)

    config_table = Table(show_header=False, box=None, padding=(0, 2))
    config_table.add_column("Command", style="bold magenta", width=35)
    config_table.add_column("Description", style="white")

    config_table.add_row("config set KEY VALUE", "Set a configuration value")
    config_table.add_row("config get KEY", "Get a configuration value")
    config_table.add_row("config list", "List all configuration values")
    config_table.add_row("config delete KEY", "Delete a configuration key")

    console.print("\n[bold cyan]CONFIG COMMANDS[/]")
    console.print(config_table)

    config_keys_table = Table(show_header=True, box=box.SIMPLE, padding=(0, 2))
    config_keys_table.add_column("Key", style="cyan")
    config_keys_table.add_column("Description", style="white")
    config_keys_table.add_column("Required", style="yellow")

    config_keys_table.add_row(
        "download_dir", "Directory for downloaded tools", "No")

    console.print("\n[bold cyan]CONFIGURATION KEYS[/]")
    console.print(config_keys_table)

    examples = [
        ("xe setup", "First time setup"),
        ("xe doctor", "Run diagnostics"),
        ("xe tools list", "See all available tools"),
        ("xe tools install example", "Install 'example'"),
        ("xe tools install test --branch main", "Install from main branch"),
        ("xe tools info example", "Show tool details"),
        ("xe tools outdated", "Check for updates"),
        ("xe tools update --all", "Update all tools"),
        ("xe config set download_dir ~/tools", "Set download directory"),
        ("xe upgrade-self", "Update xecli itself"),
    ]

    examples_table = Table(show_header=False, box=None, padding=(0, 2))
    examples_table.add_column("Example", style="bold blue", width=45)
    examples_table.add_column("Description", style="dim white")

    for cmd, desc in examples:
        examples_table.add_row(cmd, desc)

    console.print("\n[bold cyan]EXAMPLES[/]")
    console.print(examples_table)

    info_table = Table(show_header=False, box=None, padding=(0, 1))
    info_table.add_column("Label", style="dim cyan", width=20)
    info_table.add_column("Path", style="dim white")

    info_table.add_row("Base Directory:", str(BASE_DIR))
    info_table.add_row("Tools Config:", str(TOOLS_JSON))
    info_table.add_row("Config File:", str(CONFIG_JSON))
    info_table.add_row("Log File:", str(LOG_FILE))

    console.print("\n[bold cyan]CONFIGURATION[/]")
    console.print(info_table)

    console.print(
        f"\n[dim]For more information, visit: https://github.com/{GITHUB}[/]\n")
    log("Displayed help information", "INFO")


@app.command("setup")
def setup():
    try:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        log(f"Created base directory at {BASE_DIR}", "DEBUG")

        if not TOOLS_JSON.exists():
            with open(TOOLS_JSON, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)
            success_log(f"Created tools.json at {TOOLS_JSON}")
        else:
            echo_log(f"tools.json already exists at {TOOLS_JSON}")

        if not CONFIG_JSON.exists():
            with open(CONFIG_JSON, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)
            success_log(f"Created config.json at {CONFIG_JSON}")
        else:
            echo_log(f"config.json already exists at {CONFIG_JSON}")

        if not LOG_FILE.exists():
            LOG_FILE.touch()
            success_log(f"Created log file at {LOG_FILE}")

        echo_log(f"Base directory: {BASE_DIR}")
        echo_log(f"OS: {platform.system()} ({platform.machine()})")
        success_log("Setup complete")

    except Exception as e:
        echo_log(f"Setup failed: {e}", "ERROR", err=True)
        sys.exit(1)


@app.command("doctor")
def doctor():
    console.print("\n[bold cyan]Running diagnostics...[/]\n")

    issues = []

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
            console.print(f"[cyan]xecli version:[/] {current_version}")

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
                else:
                    echo_log(
                        f"xecli update available: {current_clean} → {latest_clean}", "WARNING")
                    console.print(f"  [dim]Run 'xe upgrade-self' to update[/]")
                    issues.append("xecli outdated")
            except requests.RequestException as e:
                echo_log(f"Could not check for xecli updates: {e}", "WARNING")
        else:
            echo_log("xecli installation not found via pip/pipx", "WARNING")
            issues.append("xecli not found")
    except Exception as e:
        echo_log(f"Error checking xecli version: {e}", "WARNING")

    console.print()

    if BASE_DIR.exists():
        success_log(f"Base directory exists: {BASE_DIR}")
    else:
        echo_log(f"Base directory missing: {BASE_DIR}", "WARNING")
        issues.append("Base directory missing")

    if TOOLS_JSON.exists():
        try:
            with open(TOOLS_JSON, "r") as f:
                json.load(f)
            success_log("tools.json is valid JSON")
        except json.JSONDecodeError:
            echo_log("tools.json is invalid JSON", "ERROR")
            issues.append("Invalid tools.json")
    else:
        echo_log("tools.json not found", "WARNING")
        issues.append("tools.json missing")

    try:
        test_file = BASE_DIR / ".test_write"
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        test_file.touch()
        test_file.unlink()
        success_log(f"Write permissions OK for {BASE_DIR}")
    except Exception as e:
        echo_log(f"Write permission error: {e}", "ERROR")
        issues.append("Permission error")

    try:
        requests.get("https://www.google.com", timeout=5)
        success_log("Internet connectivity OK")
    except requests.RequestException:
        echo_log("No internet connection", "ERROR")
        issues.append("No internet")

    try:
        r = requests.get(
            f"https://api.github.com/orgs/{GITHUB}", timeout=10)
        r.raise_for_status()

        config = load_config()
        if config.get("github_token"):
            success_log(f"GitHub API reachable ({GITHUB}) [using token]")
        else:
            success_log(f"GitHub API reachable ({GITHUB}) [no token]")
    except requests.RequestException as e:
        echo_log(f"Cannot reach GitHub API: {e}", "ERROR")
        issues.append("GitHub unreachable")

    console.print(f"\n[bold]Platform Information:[/]")
    console.print(f"  OS: {platform.system()}")
    console.print(f"  Architecture: {platform.machine()}")
    console.print(f"  Python: {platform.python_version()}")

    console.print()
    if issues:
        echo_log(
            f"Found {len(issues)} issue(s): {', '.join(issues)}", "WARNING")
    else:
        success_log("All checks passed!")


@app.command("upgrade-self")
def upgrade_self():
    console.print("[bold cyan]Checking for xecli updates...[/]\n")

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
                    # Extract version from pipx list output
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
            echo_log("xecli not found via pip or pipx", "WARNING")
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
                return
            else:
                console.print(
                    f"[yellow]Update available: {current_clean} → {latest_clean}[/]\n")
        except requests.RequestException as e:
            echo_log(f"Failed to check PyPI: {e}", "WARNING")
            console.print("[cyan]Proceeding with upgrade anyway...[/]\n")

        if package_manager == "pip":
            result = subprocess.run(
                ["pip", "install", "--upgrade", "xecli"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                success_log("xecli updated successfully!")
            else:
                echo_log(f"pip upgrade failed: {result.stderr}", "ERROR")

        elif package_manager == "pipx":
            result = subprocess.run(
                ["pipx", "upgrade", "xecli"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                success_log("xecli updated successfully via pipx!")
            else:
                echo_log(f"pipx upgrade failed: {result.stderr}", "ERROR")

    except FileNotFoundError:
        echo_log("pip/pipx not found. Install manually:", "ERROR")
        echo_log("pip install --upgrade xecli", "INFO")
        echo_log(
            "or: pipx install xecli --pip-args 'typer[all] requests rich'", "INFO")


@tools_app.command("list")
def list_tools():
    url = f"https://api.github.com/orgs/{GITHUB}/repos"

    try:
        log(f"Fetching repos from {url}", "DEBUG")
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        repos = r.json()

        filtered_repos = [
            repo for repo in repos if repo['name'] not in EXCLUDED_REPOS]

        if not filtered_repos:
            echo_log("No tools available")
            return

        console.print(f"\n[bold cyan]Available tools from {GITHUB}:[/]\n")

        table = Table(show_header=True,
                      header_style="bold magenta", box=box.ROUNDED)
        table.add_column("Tool", style="cyan")
        table.add_column("Description", style="white")

        for repo in filtered_repos:
            table.add_row(
                repo['name'],
                repo.get('description', 'No description')
            )

        console.print(table)
        log(f"Listed {len(filtered_repos)} tools", "INFO")

    except requests.RequestException as e:
        echo_log(f"Failed to fetch tools: {e}", "ERROR", err=True)
        sys.exit(1)
    except Exception as e:
        echo_log(f"Unexpected error: {e}", "ERROR", err=True)
        sys.exit(1)


@tools_app.command("install")
def install(name: str, branch: str = typer.Option(None, "--branch", help="Install from specific branch")):
    if name in EXCLUDED_REPOS:
        echo_log(
            f"Cannot install {name}: excluded repository", "ERROR", err=True)
        sys.exit(1)

    try:
        log(f"Installing {name}" +
            (f" from branch {branch}" if branch else ""), "INFO")
        download_update(name, branch=branch)
        success_log(f"{name} installed successfully")
    except Exception as e:
        echo_log(f"Install failed for {name}: {e}", "ERROR", err=True)
        sys.exit(1)


@tools_app.command("info")
def info(name: str):
    tools = load_tools()
    local_data = tools.get(name)

    repo = f"{GITHUB}/{name}"
    url = f"https://api.github.com/repos/{repo}/releases/latest"

    console.print(f"\n[bold cyan]Tool Information: {name}[/]\n")

    if local_data:
        console.print("[bold]Local Installation:[/]")
        console.print(
            f"  Version: [green]{local_data.get('version', 'unknown')}[/]")
        console.print(f"  Path: {local_data.get('file', 'unknown')}")
        console.print(
            f"  Installed: {local_data.get('installed_at', 'unknown')}")
        console.print(f"  OS: {local_data.get('os', 'unknown')}")
    else:
        echo_log("Not installed locally", "WARNING")

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        release = r.json()

        console.print(f"\n[bold]Remote Information:[/]")
        console.print(
            f"  Latest Version: [cyan]{release.get('tag_name', 'unknown')}[/]")
        console.print(f"  Published: {release.get('published_at', 'unknown')}")

        repo_url = f"https://api.github.com/repos/{repo}"
        repo_r = requests.get(repo_url, timeout=10)
        if repo_r.status_code == 200:
            repo_data = repo_r.json()
            console.print(
                f"  Description: {repo_data.get('description', 'No description')}")

        body = release.get('body', '')
        if body:
            console.print(f"\n[bold]Release Notes:[/]")
            console.print(Panel(body, box=box.ROUNDED))

    except requests.RequestException as e:
        echo_log(f"Failed to fetch remote info: {e}", "ERROR")


@tools_app.command("check")
def check(name: str):
    tools = load_tools()
    local_version = tools.get(name, {}).get("version")

    repo = f"{GITHUB}/{name}"
    url = f"https://api.github.com/repos/{repo}/releases/latest"

    try:
        log(f"Checking latest release for {name}", "DEBUG")
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        release = r.json()
        latest_tag = release.get("tag_name", "latest")

        if not local_version:
            echo_log(f"{name} is not installed locally")
            echo_log(f"Latest release: {latest_tag}")
            log(f"{name} not installed, latest is {latest_tag}", "INFO")
            return

        if local_version == latest_tag:
            success_log(f"{name} is up-to-date (version {latest_tag})")
            log(f"{name} is up-to-date at {latest_tag}", "INFO")
        else:
            echo_log(f"Update available for {name}", "WARNING")
            console.print(f"  Local: [yellow]{local_version}[/]")
            console.print(f"  Latest: [green]{latest_tag}[/]")
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

    console.print("\n[bold cyan]Checking for updates...[/]\n")

    table = Table(show_header=True,
                  header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Tool", style="cyan")
    table.add_column("Local", style="yellow")
    table.add_column("Remote", style="green")
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
                status = "[green]up-to-date[/]"
            else:
                status = "[yellow]update available[/]"
                outdated_count += 1

            table.add_row(tool_name, local_version, remote_version, status)

        except Exception as e:
            table.add_row(tool_name, local_version,
                          "[red]error[/]", f"[red]{str(e)[:30]}[/]")

    console.print(table)

    if outdated_count > 0:
        console.print(
            f"\n[yellow]{outdated_count} tool(s) have updates available[/]")
        console.print(
            "[cyan]Run 'xe tools update --all' to update all tools[/]")
    else:
        success_log("All tools are up-to-date!")


@tools_app.command("update")
def update(name: str = typer.Argument(None), all: bool = typer.Option(False, "--all", help="Update all installed tools")):
    tools = load_tools()

    if all:
        if not tools:
            echo_log("No tools installed to update")
            return

        log(f"Updating all {len(tools)} tools", "INFO")
        failed = []

        for tool_name in tools.keys():
            try:
                update_single(tool_name)
            except Exception as e:
                echo_log(
                    f"Failed to update {tool_name}: {e}", "ERROR", err=True)
                failed.append(tool_name)

        if failed:
            echo_log(f"Failed to update: {', '.join(failed)}", "WARNING")
        else:
            success_log("All tools updated successfully")
    else:
        if not name:
            echo_log("Provide a tool name or use --all", "ERROR", err=True)
            sys.exit(1)
        try:
            update_single(name)
        except Exception as e:
            echo_log(f"Update failed: {e}", "ERROR", err=True)
            sys.exit(1)


@tools_app.command("remove")
def remove(name: str):
    tools = load_tools()

    if name not in tools:
        echo_log(f"{name} is not installed", "WARNING")
        return

    file_path = Path(tools[name]["file"])

    try:
        if file_path.exists():
            file_path.unlink()
            success_log(f"Deleted {file_path}")
            log(f"Deleted file {file_path}", "INFO")
        else:
            echo_log(
                f"File {file_path} not found, skipping deletion", "WARNING")

        tools.pop(name)
        save_tools(tools)
        success_log(f"Removed {name}")
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
            f"\n[cyan]Allowed keys:[/] {', '.join(ALLOWED_CONFIG_KEYS)}")
        sys.exit(1)

    config = load_config()
    config[key] = value
    save_config(config)
    success_log(f"Set {key} = {value}")


@config_app.command("get")
def config_get(key: str):
    config = load_config()
    value = config.get(key)
    if value is not None:
        console.print(f"[cyan]{key}[/] = [green]{value}[/]")
    else:
        echo_log(f"Key '{key}' not found", "WARNING")


@config_app.command("list")
def config_list():
    config = load_config()
    if not config:
        echo_log("No configuration set")
        return

    console.print("\n[bold cyan]Configuration:[/]\n")
    table = Table(show_header=True,
                  header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    for key, value in config.items():
        table.add_row(key, str(value))

    console.print(table)


@config_app.command("delete")
def config_delete(key: str):
    config = load_config()

    if key not in config:
        echo_log(f"Key '{key}' not found in configuration", "WARNING")
        return

    deleted_value = config.pop(key)
    save_config(config)
    success_log(f"Deleted {key} (was: {deleted_value})")


def update_single(name: str):
    tools = load_tools()
    local_version = tools.get(name, {}).get("version")

    repo = f"{GITHUB}/{name}"
    url = f"https://api.github.com/repos/{repo}/releases/latest"

    try:
        log(f"Checking updates for {name}", "DEBUG")
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
            log(f"Fetching release info for {name}", "DEBUG")
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

    log(f"Downloading from {dl_url} to {dest_path}", "DEBUG")

    try:

        headers = {}

        with requests.get(dl_url, stream=True, headers=headers, timeout=30) as req:
            req.raise_for_status()
            total_size = int(req.headers.get('content-length', 0))

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                console=console
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Downloading {file_name}...", total=total_size)

                with open(dest_path, "wb") as f:
                    for chunk in req.iter_content(8192):
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))

        success_log(f"Downloaded {file_name}")
        log(f"Downloaded {file_name} to {dest_path}", "INFO")

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
        log(f"Updated json for: {name}", "DEBUG")

    except requests.RequestException as e:
        log(f"download failed for: {name}: {e}", "ERROR")
        raise
    except Exception as e:
        log(f"Error while downloading: {name}: {e}", "ERROR")
        raise


if __name__ == "__main__":
    app()
