# OpenCode Plugins

This directory contains OpenCode plugins that can be installed and managed using the iowarp-hooks tool.

## Available Plugins

### observability_influxdb

An InfluxDB observability plugin for OpenCode that captures and sends telemetry data to InfluxDB for comprehensive monitoring and analytics.

**Features:**
- Captures all OpenCode events including MCP tools
- Sends data to InfluxDB for analysis and visualization
- Comprehensive event logging and debugging
- Support for chat messages, tool executions, and storage operations

**Installation:**
```bash
# Local installation (installs to ./.opencode/plugin/)
iowarp-hooks install-opencode-plugin observability_influxdb

# Global installation (installs to ~/.config/opencode/plugin/)
iowarp-hooks install-opencode-plugin observability_influxdb --global-install
```

## Installation Paths

OpenCode plugins are installed directly into the plugin directory (no subdirectories):

- **Global**: `~/.config/opencode/plugin/` - Available system-wide
- **Local**: `./.opencode/plugin/` - Available in current project only

All plugin files are copied directly to the plugin directory, not into subdirectories.

## Plugin Structure

Each plugin directory contains:
- `config.yaml` - Plugin configuration and metadata
- `package.json` - Node.js dependencies and scripts
- `*.js` - Plugin implementation files
- `.env.template` - Environment variable template

## Environment Setup

After installing a plugin, you'll need to set up environment variables. Each plugin includes a `.env.template` file that shows the required configuration.

For the InfluxDB plugin:
```bash
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-influxdb-token-here
INFLUXDB_ORG=my-org
INFLUXDB_BUCKET=application-events
DEBUG_LOGGING=true
```

Create a `.env` file in the plugin directory with your actual values.

## OpenCode Integration

Installed plugins are automatically detected by OpenCode when placed in the correct plugin directory. The plugin system follows the OpenCode plugin architecture:

1. **Global plugins**: `~/.config/opencode/plugin/`
2. **Local plugins**: `./.opencode/plugin/`

OpenCode will automatically load and initialize plugins found in these directories.

## Plugin Management Commands

```bash
# List all available plugins and hooks
iowarp-hooks list

# Get detailed information about a plugin
iowarp-hooks info observability_influxdb

# Install plugin locally
iowarp-hooks install-opencode-plugin observability_influxdb

# Install plugin globally
iowarp-hooks install-opencode-plugin observability_influxdb --global-install

# Force installation (skip confirmation)
iowarp-hooks install-opencode-plugin observability_influxdb --force
```

## Development

To create a new plugin:

1. Create a new directory under `opencode_plugins/`
2. Add a `config.yaml` file with plugin metadata
3. Implement your plugin following the OpenCode plugin API
4. Add a `package.json` for Node.js dependencies
5. Test your plugin with OpenCode

## Plugin Development Structure

```yaml
# config.yaml
name: my_plugin
description: Description of the plugin
version: "1.0.0"
category: observability

environment:
  ENV_VAR: "default_value"

files:
  - src: plugin-file.js
    dest: plugin-file.js
    executable: true

install_instructions: |
  Setup instructions here
```

## References

- [OpenCode Plugin Documentation](https://opencode.ai/docs/plugins/)
- [OpenCode Plugin API](https://opencode.ai/docs/plugins/api/)
