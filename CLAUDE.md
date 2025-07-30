# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Package Management
```bash
# Install dependencies and setup development environment
uv sync

# Run the CLI tool in development
uv run iowarp-hooks --help
uv run iowarp-hooks list
uv run iowarp-hooks install observability my-project
```

### Testing Hook Scripts
```bash
# Test individual hook scripts (they expect JSON on stdin)
echo '{"session_id": "test", "transcript_path": "/path/to/transcript.jsonl"}' | uv run hooks/observability/hooks/send_event.py --source-app test-app --event-type PreToolUse
```

## Architecture Overview

### Core Components

**CLI Layer** (`src/iowarp_hooks/`):
- `hook_manager.py`: Main CLI entry point with commands for list/install/uninstall
- `installer.py`: Handles copying hook files and updating Claude settings.json
- `templates.py`: Jinja2-based template processing for variable substitution

**Hook Sets** (`hooks/`):
- Each hook set is a directory with `config.yaml` defining hook configurations
- Hook sets contain executable Python scripts in `hooks/` subdirectory
- Templates use `{{variable}}` or `{variable}` syntax for substitution

**Observability Hook Set** (`hooks/observability/`):
- Provides comprehensive Claude Code event tracking
- Uses uv script headers for dependency management
- Sends telemetry to external observability server (default: localhost:4000)

### Installation Flow

1. User runs `uv run iowarp-hooks install <hook_set> [params]`
2. CLI collects required inputs via command args or interactive prompts
3. `HookInstaller` copies hook files to `.claude/hooks/` (local) or `~/.claude/hooks/` (global)
4. Template processor substitutes variables like `{{project_name}}` in files
5. Updates `.claude/settings.json` with hook configurations that reference installed scripts

### Hook Execution Model

Claude Code executes hooks defined in settings.json at specific lifecycle events:
- `PreToolUse`/`PostToolUse`: Before/after each tool invocation
- `Notification`: When notifications are displayed
- `Stop`/`SubagentStop`: When sessions end
- `UserPromptSubmit`: When user submits prompts

Each hook receives JSON context via stdin and can perform logging, telemetry, or notifications.

### Key Design Patterns

- **Template-driven deployment**: Hook files are templates processed during installation
- **uv script execution**: Hook scripts use `#!/usr/bin/env -S uv run --script` with inline dependencies
- **Fail-safe hooks**: All hooks exit with code 0 to avoid blocking Claude Code operations
- **Modular hook sets**: Each hook set is self-contained with its own config and dependencies