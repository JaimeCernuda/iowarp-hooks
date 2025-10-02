# AgentLog Single-Node Deployment Guide

This guide provides comprehensive instructions for deploying AgentLog using ChronoLog in single-nodenconfiguration.

## What is AgentLog?

AgentLog records agent outputs and reasoning during tool executions, capturing conversation context, tool results (via hooks), and streaming them through ChronoLog for persistent storage and retrieval.


## Set up ChronoLog

#### 1.1 Dependency: Spack

```bash
cd ${HOME}
git clone --branch v0.21.2 https://github.com/spack/spack.git
cd spack
source /share/spack/setup-env.sh
```

#### 1.2 Checkout ChronoLog

```bash
cd ${HOME}
git clone https://github.com/grc-iit/ChronoLog.git

cd ChronoLog
git switch develop
spack env activate .

# To check if the environment is activated the following can be executed:
spack env status

# If the environment is properly activated, it can be installed
spack install -v
```

**Note:** Installation will take 30 to 40 minutes.

### 2. ChronoLog Build, Install and Deploy Commands

#### 2.1 Build ChronoLog

```bash
cd $HOME/ChronoLog/tools/deploy/ChronoLog
./local_single_user_deploy.sh -b -t Debug -l $HOME/chronolog-install/
```

#### 2.2 Initialize Installation

```bash
./local_single_user_deploy.sh -i -w $HOME/chronolog-install/Debug
```

#### 2.3 Deploy

```bash
cd $HOME/ChronoLog/tools/deploy/ChronoLog
./local_single_user_deploy.sh -d -w $HOME/chronolog-install/Debug
```

### 3. Clean

#### 3.1 Clean Services

```bash
cd $HOME/ChronoLog/tools/deploy/ChronoLog
./local_single_user_deploy.sh -c -w $HOME/chronolog-install/Debug
```

#### 3.2 Stop Services

```bash
./local_single_user_deploy.sh -s -w $HOME/chronolog-install/Debug
```

---

## Set up the Hooks

Configure the AgentLog hooks to capture Claude Code events and stream them to ChronoLog.

### Installation Steps

1. **Create the hooks directory** (if it doesn't exist):

```bash
mkdir -p ~/.claude/hooks
```
2. **Install UV** (if not already installed):

```bash
# Install UV using the official installer
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv

# Verify installation
uv --version
```

3. **Sync dependencies with UV**:

```bash
# Navigate to the project directory containing pyproject.toml
cd /path/to/observability_agentlog

# Sync dependencies
uv sync
```
4. **Copy the hook script**:

```bash
cp send_event_chronolog_unified.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/send_event_chronolog_unified.py
```

5. **Copy the settings configuration**:

```bash
cp settings.json ~/.claude/
```

6. **Configure environment variables**:

```bash
# Copy the environment template
cp .env.single.example ~/.claude/.env

# Edit the .env file with your specific configuration
vim ~/.claude/.env  # or use your preferred editor
```

7. **Update the `.env` file** with your ChronoLog configuration:
   - Set `CHRONOLOG_HOST` to your ChronoVisor host address
   - Set `CHRONOLOG_PORT` (default: 5555)
   - Set `CHRONOLOG_LIB_PATH` to your ChronoLog library path
   - Configure `SPACK_LIB_PATHS` if using Spack dependencies

### Verification

```bash
# Verify files are in place
ls -la ~/.claude/hooks/send_event_chronolog_unified.py
ls -la ~/.claude/settings.json
ls -la ~/.claude/.env
```

---

## MCP Setup

Setup chronolog-mcp from here:
https://github.com/iowarp/iowarp-mcps/tree/main/mcps/Chronolog

---

## Test AgentLog

### Pre-Test Verification

Before testing, verify that all components are working:

```bash
# Check ChronoLog services are running
ps aux | grep chrono | grep -v grep

# Check hook debug log
tail -20 ~/.claude/logs/chronolog_hook_debug.log

# Verify ChronoLog data directory
ls -la $HOME/chronolog-install/Debug/output/
```

### Reading ChronoLog Data

You can read logged data from ChronoLog using UV. Make sure you have the `chronolog_reader_unified.py` script available in your working directory or provide the full path.

**NOTE**:  make sure updating ChronoVisor and ChronoPlayer host

```bash
# Navigate to your scripts directory (if needed)
# cd /path/to/your/scripts

# Using UV with ChronoLog to read logged data
CHRONOLOG_LIB_PATH="$HOME/chronolog-install/Debug/lib" \
LD_LIBRARY_PATH="$HOME/chronolog-install/Debug/lib:$LD_LIBRARY_PATH" \
PYTHONPATH="$HOME/chronolog-install/Debug/lib:$PYTHONPATH" \
uv run --python 3.11 chronolog_reader_unified.py

# Alternative: Use absolute path to the script
# CHRONOLOG_LIB_PATH="$HOME/chronolog-install/Debug/lib" \
# LD_LIBRARY_PATH="$HOME/chronolog-install/Debug/lib:$LD_LIBRARY_PATH" \
# PYTHONPATH="$HOME/chronolog-install/Debug/lib:$PYTHONPATH" \
# uv run --python 3.11 /path/to/chronolog_reader_unified.py
```


### Agent Testing Procedure

1. **Open Claude Code** in terminal or in VS Code 

2. **Start a New Conversation** and perform various tasks:

   **Example Session 1: System Information**
   - "Show my CPU information"
   - "Show my network information"
   - "List the contents of my home directory"

   **Example Session 2: File Operations**
   - "Create a Python script that prints 'Hello World'"
   - "Read the content of the script you just created"
   - "Modify the script to include a function"

   **Example Session 3: Code Analysis**
   - "Analyze the Python files in my current directory"
   - "Check for any syntax errors in my Python scripts"
   - "Suggest improvements to my code"

3. **Wait for ChronoLog Processing**
   - Data is typically logged instantly
   - Allow 2-4 minutes for ChronoLog to index and make data retrievable
   - You can monitor the logs during this time

4. **Test Memory Retrieval** using the Chronolog MCP:

   **Example Queries:**
   - "What was my CPU information from our previous conversation?"
   - "Can you show me the Python script we created earlier?"
   - "What files did we analyze in our last session?"
   - "Retrieve the system information we discussed a few minutes ago"

### Verification Steps

```bash
# Check that events are being logged
tail -50 ~/.claude/logs/chronolog_hook_debug.log | grep -E "(Event.*sent|chronicle|story)"

# Verify ChronoLog data files are being created
ls -lth $HOME/chronolog-install/Debug/output/*.h5 | head -5

# Check the size of data files (should be growing)
du -sh $HOME/chronolog-install/Debug/output/
```

### Expected Results

**Success Indicators:**
- Hook debug log shows events being sent successfully
- ChronoLog `.h5` files are created in the output directory
- Claude can retrieve and reference previous conversations
- MCP queries return relevant historical data

**Troubleshooting:**
- If events aren't logging: Check `~/.claude/logs/chronolog_hook_debug.log` for errors
- If data files aren't created: Verify ChronoLog services are running
- If retrieval fails: Wait longer (3-4 minutes) or check MCP configuration

---
