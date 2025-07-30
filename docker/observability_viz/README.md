# Claude Code Observability Dashboard

Real-time monitoring and visualization for your Claude Code sessions.

## 🚀 Quick Start

1. **Create the observability directory**:
   ```bash
   mkdir -p ~/.claude/observability_docker
   cd ~/.claude/observability_docker
   ```

2. **Download the configuration files**:
   ```bash
   # Download docker-compose.yml and .env
   curl -o docker-compose.yml https://github.com/JaimeCernuda/iowarp-hooks/releases/latest/download/docker-compose.yml
   curl -o .env https://github.com/JaimeCernuda/iowarp-hooks/releases/latest/download/.env
   ```

3. **Start the dashboard**:
   ```bash
   docker-compose up -d
   ```

4. **Access your dashboard**:
   - **Grafana**: http://localhost:3000 (admin/admin)
   - **InfluxDB**: http://localhost:8086 (admin/admin123456)

## 📊 Dashboard Features

- **Events Timeline**: Real-time visualization of Claude Code events
- **Event Type Distribution**: Pie chart showing event type breakdown  
- **Recent Events Log**: Table with the last 50 events and payloads
- **Tool Usage Metrics**: Analysis of tool usage patterns

## ⚙️ Storage Options

### Ephemeral (Default - Recommended)
Perfect cleanup when you're done:
```bash
docker-compose up -d           # Start dashboard
docker-compose down            # Stop and clean everything
```

### Persistent (Keep Data Between Sessions)
For longer-term analysis:
```bash
docker-compose --profile persistent up -d    # Start with data persistence
docker-compose down -v                       # Clean removal when done
```

## 🔧 Configuration

Edit `.env` file to customize:
```bash
# InfluxDB token (change for security)
INFLUXDB_TOKEN=your-secure-token

# Grafana admin password
GRAFANA_ADMIN_PASSWORD=your-secure-password
```

## 📋 Requirements

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Ports**: 3000 (Grafana) and 8086 (InfluxDB) available

## 🔍 Troubleshooting

### Dashboard shows no data?
1. Ensure your Claude Code hooks are sending data to InfluxDB
2. Check the hook script token matches your `.env` file
3. Verify InfluxDB is accessible: `curl http://localhost:8086/health`

### Containers won't start?
1. Check port availability: `netstat -tulpn | grep -E ':(3000|8086)'`
2. Ensure Docker has sufficient resources (2GB+ RAM recommended)
3. View logs: `docker-compose logs`

### Permission issues?
1. Ensure your user is in the docker group: `sudo usermod -aG docker $USER`
2. Restart your shell or logout/login

## 🧹 Cleanup

### Stop services (keep data in persistent mode):
```bash
docker-compose stop
```

### Complete cleanup (remove all data):
```bash
docker-compose down -v
```

### Remove downloaded images (free disk space):
```bash
docker-compose down --rmi all -v
```

## 🔗 Integration with Claude Code

This dashboard automatically works with Claude Code hooks. The hooks send events to InfluxDB, which Grafana then visualizes in real-time.

For hook setup, see: [Claude Code Hooks Documentation](https://docs.anthropic.com/en/docs/claude-code/hooks)

Built with iowarp-hooks for easy installation and management.

## 📈 What's Monitored

- **User Prompts**: When you send commands to Claude Code
- **Tool Usage**: Every tool Claude Code uses (Read, Write, Bash, etc.)
- **Assistant Messages**: Claude Code's responses
- **Session Lifecycle**: Start/stop events
- **Sub-agent Activity**: When Claude Code spawns additional agents

---

*Questions? Issues? Check the [main repository](https://github.com/jcernuda/graphana_test) or open an issue.*