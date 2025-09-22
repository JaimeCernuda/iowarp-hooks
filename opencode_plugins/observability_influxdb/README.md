# OpenCode InfluxDB Observability Plugin

A comprehensive observability plugin for OpenCode that captures all events and sends them to InfluxDB for monitoring and analytics.

## Features

- **Complete Event Capture**: Captures all OpenCode events including MCP tools, chat messages, tool executions, and storage operations
- **InfluxDB Integration**: Sends structured data to InfluxDB for time-series analysis
- **Debug Logging**: Comprehensive logging when `DEBUG_LOGGING` is enabled
- **Event Classification**: Automatically classifies and tags events for better organization
- **Session Tracking**: Tracks events by session ID for correlation

## Installation

Using iowarp-hooks:
```bash
# Local installation (installs to ./.opencode/plugin/)
iowarp-hooks install-opencode-plugin observability_influxdb

# Global installation (installs to ~/.config/opencode/plugin/)
iowarp-hooks install-opencode-plugin observability_influxdb --global-install
```

Manual installation:
```bash
# Copy to OpenCode plugin directory (global)
cp -r observability_influxdb ~/.config/opencode/plugin/
cd ~/.config/opencode/plugin/
npm install

# Or copy to local OpenCode plugin directory
cp -r observability_influxdb ./.opencode/plugin/
cd ./.opencode/plugin/
npm install
```

## Installation Paths

OpenCode plugins are installed directly into the plugin directory:

- **Global**: `~/.config/opencode/plugin/` - Available system-wide
- **Local**: `./.opencode/plugin/` - Available in current project only

**Important**: All plugin files are copied directly to the plugin directory, not into subdirectories. The plugin structure is flattened during installation.

## Configuration

1. Copy the environment template to the plugin directory:
```bash
# For global installation
cp ~/.config/opencode/plugin/.env.template ~/.config/opencode/plugin/.env

# For local installation  
cp ./.opencode/plugin/.env.template ./.opencode/plugin/.env
```

2. Edit the `.env` file with your InfluxDB settings:
```bash
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-influxdb-token-here
INFLUXDB_ORG=my-org
INFLUXDB_BUCKET=application-events
DEBUG_LOGGING=true
```

3. Ensure InfluxDB is running and accessible

## Event Types Captured

- **chat.message**: Chat messages and responses
- **chat.params**: Chat configuration (model, temperature, etc.)
- **tool.execute.before/after**: Tool execution events
- **storage.write**: Storage operations (where MCP tools are detected)
- **permission.ask**: Permission requests
- **mcp_tool_execution**: Specific MCP tool executions
- **config**: Configuration changes
- **auth**: Authentication events

## Data Schema

Events are stored in InfluxDB with the following structure:

**Measurement**: `opencode_events`

**Tags**:
- `event_type`: Type of event
- `session_id`: Session identifier
- `tool_name`: Tool name (if applicable)
- `call_id`: Call identifier (for tool events)

**Fields**:
- `payload`: JSON payload of the event
- `event_count`: Count of events (always 1)
- Various event-specific fields based on event type

## Debug Logging

When `DEBUG_LOGGING=true`, the plugin creates detailed logs in `plugin-debug.log`. This includes:
- All event processing
- InfluxDB connection status
- Event classification details
- Error information

## Plugin API

The plugin exports `InfluxDBObservabilityPlugin` which implements the OpenCode plugin interface:

```javascript
export const InfluxDBObservabilityPlugin = async ({ app, client, $ }) => {
  // Plugin initialization
  return {
    name: 'opencode-influxdb-observability',
    version: '3.0.0',
    
    // Event handlers
    event: async ({ event }) => { /* Handle all events */ },
    "chat.message": async ({ message, parts, sessionId }) => { /* Handle chat */ },
    // ... other handlers
  };
};
```

## Requirements

- Node.js >= 16.0.0
- InfluxDB instance
- OpenCode application

## Troubleshooting

1. **Plugin not loading**: Check OpenCode logs and ensure the plugin files are in the correct directory:
   - Global: `~/.config/opencode/plugin/`
   - Local: `./.opencode/plugin/`
2. **InfluxDB connection issues**: Verify URL, token, org, and bucket settings in your `.env` file
3. **Missing events**: Enable debug logging (`DEBUG_LOGGING=true`) to see event processing details
4. **npm install failures**: Ensure Node.js and npm are properly installed
5. **Permission issues**: Make sure the plugin files have correct permissions and the `influxdb-observability.js` file is executable

## Development

To modify the plugin:

1. Edit `influxdb-observability.js` for functionality changes
2. Update `config.yaml` for metadata changes
3. Modify `package.json` for dependency changes
4. Test with OpenCode and verify data in InfluxDB
5. Reinstall using `iowarp-hooks install-opencode-plugin observability_influxdb --force`

## Verification

After installation, you can verify the plugin is correctly installed:

```bash
# Check global installation
ls -la ~/.config/opencode/plugin/
node -c ~/.config/opencode/plugin/influxdb-observability.js

# Check local installation
ls -la ./.opencode/plugin/
node -c ./.opencode/plugin/influxdb-observability.js
```

## License

MIT License
