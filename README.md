# iowarp-hooks

A Claude Code hook manager for easy installation and management of hook sets.

## Installation

```bash
pip install iowarp-hooks
# or
uvx install iowarp-hooks
```

## Usage

### List available hook sets
```bash
uvx iowarp-hooks list
```

### Install a hook set
```bash
# Install with all parameters
uvx iowarp-hooks install observability my-project-name

# Install with interactive prompts for missing parameters
uvx iowarp-hooks install observability

# Install to global Claude config
uvx iowarp-hooks install observability my-project --install-type global
```

### Uninstall a hook set
```bash
uvx iowarp-hooks uninstall observability
```

## Available Hook Sets

### Observability
Multi-agent observability hooks with telemetry and notifications.

**Inputs:**
- `project_name`: Your project name for telemetry identification
- `database_url`: Optional database connection string

**Features:**
- Pre/post tool use logging
- Event telemetry to observability server
- Notification handling
- Session and subagent lifecycle tracking

## Creating Custom Hook Sets

1. Create a directory in `hooks/` with your hook set name
2. Add a `config.yaml` file with hook configuration
3. Add hook Python files in a `hooks/` subdirectory
4. Use template variables like `{{project_name}}` in your files

### Example config.yaml

```yaml
name: my-hooks
description: "Custom hook set"
version: "1.0.0"

targets:
  - claude

inputs:
  project_name:
    prompt: "Enter your project name"
    required: true

hooks:
  PreToolUse:
    matcher: ""
    hooks:
      - type: command
        command: "uv run .claude/hooks/my_hook.py --project {{project_name}}"
```

## Development

```bash
# Clone the repo
git clone https://github.com/yourusername/iowarp-hooks
cd iowarp-hooks

# Install in development mode
uv sync
uv run iowarp-hooks --help
```