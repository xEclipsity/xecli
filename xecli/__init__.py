import typer
import requests
import os
import json
from pathlib import Path
import platform
from datetime import datetime
import sys

app = typer.Typer()
tools_app = typer.Typer()
app.add_typer(tools_app, name="tools")

GITHUB = "xEclipsity"
EXCLUDED_REPOS = [".github"]


def get_base_dir():
    if platform.system() == "Windows":
        return Path(os.environ["LOCALAPPDATA"]) / "xecli"
    else:
        return Path.home() / ".local/share/xecli"


BASE_DIR = get_base_dir()
TOOLS_JSON = BASE_DIR / "tools.json"
LOG_FILE = BASE_DIR / "xecli.log"


def log(message: str, level: str = "INFO"):
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] [{level}] {message}\n")


def echo_log(message: str, level: str = "INFO", err: bool = False):
    typer.echo(message, err=err)
    log(message, level)


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


@app.command("help")
def show_help():
    help_text = f"""
╭─────────────────────────────────────────────────────────────╮
│                   xecli - Tool Manager                      │
│                    GitHub: {GITHUB}                       │
╰─────────────────────────────────────────────────────────────╯

USAGE:
  xe [COMMAND] [OPTIONS]

COMMANDS:
  setup              Initialize xecli
  help               Show this help message

TOOLS COMMANDS:
  tools list         List all available tools from {GITHUB}
  tools install NAME Install a specific tool
  tools check NAME   Check if a tool has updates available
  tools update NAME  Update a specific tool to the latest version
  tools update --all Update all installed tools
  tools remove NAME  Remove an installed tool

EXAMPLES:
  xe setup                    # First time setup
  xe tools list               # See all available tools
  xe tools install example    # Install 'example'
  xe tools check example      # Check for updates
  xe tools update example     # Update 'example'
  xe tools update --all       # Update all tools
  xe tools remove example     # Remove 'example'

CONFIGURATION:
  Base Directory: {BASE_DIR}
  Tools Config:   {TOOLS_JSON}
  Log File:       {LOG_FILE}

For more information, visit: https://github.com/{GITHUB}
"""
    typer.echo(help_text)
    log("Displayed help information", "INFO")


@app.command("setup")
def setup():
    try:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        log(f"Created base directory at {BASE_DIR}", "DEBUG")

        if not TOOLS_JSON.exists():
            with open(TOOLS_JSON, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)
            echo_log(f"Created tools.json at {TOOLS_JSON}")
        else:
            echo_log(f"tools.json already exists at {TOOLS_JSON}")

        if not LOG_FILE.exists():
            LOG_FILE.touch()
            echo_log(f"Created log file at {LOG_FILE}")

        echo_log(f"Base directory: {BASE_DIR}")
        echo_log(f"OS: {platform.system()} ({platform.machine()})")
        echo_log("Setup complete")

    except Exception as e:
        echo_log(f"Setup failed: {e}", "ERROR", err=True)
        sys.exit(1)


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

        echo_log(f"All {GITHUB} tools available:")
        for repo in filtered_repos:
            echo_log(
                f"- {repo['name']}  —  {repo.get('description', 'No description')}")

        log(f"Listed {len(filtered_repos)} tools", "INFO")

    except requests.RequestException as e:
        echo_log(f"Failed to fetch tools: {e}", "ERROR", err=True)
        sys.exit(1)
    except Exception as e:
        echo_log(f"Unexpected error: {e}", "ERROR", err=True)
        sys.exit(1)


@tools_app.command("install")
def install(name: str):
    if name in EXCLUDED_REPOS:
        echo_log(
            f"Cannot install {name}: excluded repository", "ERROR", err=True)
        sys.exit(1)

    try:
        log(f"Installing {name}", "INFO")
        download_update(name)
        echo_log(f"Successfully installed {name} ✅")
    except Exception as e:
        echo_log(f"Install failed for {name}: {e}", "ERROR", err=True)
        sys.exit(1)


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
            echo_log(f"{name} is up-to-date (version {latest_tag})")
            log(f"{name} is up-to-date at {latest_tag}", "INFO")
        else:
            echo_log(f"Update available for {name} ⚠️")
            echo_log(f"Local: {local_version}")
            echo_log(f"Latest: {latest_tag}")
            log(f"{name} outdated: {local_version} -> {latest_tag}", "INFO")

    except requests.RequestException as e:
        echo_log(f"Failed to check updates: {e}", "ERROR", err=True)
        sys.exit(1)
    except Exception as e:
        echo_log(f"Unexpected error: {e}", "ERROR", err=True)
        sys.exit(1)


@tools_app.command("update")
def update(name: str = None, all: bool = typer.Option(False, "--all", help="Update all installed tools")):
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
            echo_log("All tools updated successfully")
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
            echo_log(f"Deleted {file_path}")
            log(f"Deleted file {file_path}", "INFO")
        else:
            echo_log(
                f"File {file_path} not found, skipping deletion", "WARNING")

        tools.pop(name)
        save_tools(tools)
        echo_log(f"Removed {name}")
        log(f"Removed {name} from tools.json", "INFO")

    except Exception as e:
        echo_log(f"Failed to remove {name}: {e}", "ERROR", err=True)
        sys.exit(1)


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
            echo_log(f"{name} is already up-to-date ({latest_tag})")
            return

        echo_log(f"Updating {name}: {local_version or 'new'} → {latest_tag}")
        log(f"Updating {name} from {local_version} to {latest_tag}", "INFO")
        download_update(name)

    except Exception as e:
        log(f"Update failed for {name}: {e}", "ERROR")
        raise


def download_update(name: str):
    repo = f"{GITHUB}/{name}"
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

        dest_path = Path.cwd() / file_name
        echo_log(f"Downloading {file_name}...")
        log(f"Downloading from {dl_url} to {dest_path}", "DEBUG")

        with requests.get(dl_url, stream=True, timeout=30) as req:
            req.raise_for_status()
            total_size = int(req.headers.get('content-length', 0))

            with open(dest_path, "wb") as f:
                downloaded = 0
                for chunk in req.iter_content(8192):
                    f.write(chunk)
                    downloaded += len(chunk)

        echo_log(f"Downloaded {file_name}")
        log(f"Downloaded {file_name} ({downloaded} bytes)", "INFO")

        tools = load_tools()
        tools[name] = {
            "version": tag_name,
            "file": str(dest_path),
            "os": system,
            "installed_at": datetime.now().isoformat()
        }
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
