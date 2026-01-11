# xecli
A Python CLI to manage xEclipsity tools and releases

## Installation
--
```bash
pip install xecli
```

##  Usage
```bash
xe [COMMAND] [OPTIONS]
```

```bash
xe help
```

## Commands
```
COMMANDS:
  setup              Initialize xecli
  help               Show this help message

TOOLS COMMANDS:
  tools list         List all available tools from xEclipsity
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
```

## Use of this
**You can use this to check, download, update, our tools with ease.**
