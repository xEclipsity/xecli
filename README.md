# xecli
A Python CLI to manage xEclipsity tools and releases

## Installation
```bash
pip install xecli
```

---

##  Usage
```bash
xe [COMMAND] [OPTIONS]
```

```bash
xe help
```
---
## Commands
```
COMMANDS
  setup                   Initialize xecli
  help                    Show this help message
  doctor                  Run diagnostic checks
  upgrade-self            Update xecli to latest version

TOOLS COMMANDS
  tools list                             List all available tools
  tools install NAME                     Install a specific tool
  tools install NAME --branch BRANCH     Install from specific branch
  tools info NAME                        Show detailed info about a tool
  tools check NAME                       Check if a tool has updates
  tools update NAME                      Update a specific tool
  tools update --all                     Update all installed tools
  tools outdated                         Show all tools with updates
  tools remove NAME                      Remove an installed tool

CONFIG COMMANDS
  config set KEY VALUE                   Set a configuration value
  config get KEY                         Get a configuration value
  config list                            List all configuration values
  config delete KEY                      Delete a configuration key

CONFIGURATION KEYS

   Key              Description                        Required
 ────────────────────────────────────────────────────────────────
   download_dir     Directory for downloaded tools     No


EXAMPLES
  xe setup                                         First time setup
  xe doctor                                        Run diagnostics
  xe tools list                                    See all available tools
  xe tools install example                         Install 'example'
  xe tools install test --branch main              Install from main branch
  xe tools info example                            Show tool details
  xe tools outdated                                Check for updates
  xe tools update --all                            Update all tools
  xe config set download_dir ~/tools               Set download directory
  xe upgrade-self                                  Update xecli itself
```

---
## Use of this
**You can use this to check, download, update, our tools with ease.**
