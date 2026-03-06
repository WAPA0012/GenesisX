# Genesis X Environment Variables

This document describes all environment variables used by Genesis X.

## Required Environment Variables

### LLM API Configuration

Genesis X requires an LLM API to function properly. Configure one of the following:

#### Universal Format (Recommended)

```bash
# API Base URL
LLM_API_BASE=https://your-api-endpoint.com/v1

# API Key
LLM_API_KEY=your-api-key-here

# Model Name
LLM_MODEL=model-name

# Optional: Temperature (default: 0.7)
LLM_TEMPERATURE=0.7

# Optional: Max Tokens (default: 2000)
LLM_MAX_TOKENS=2000
```

#### Dashscope (Aliyun) - Legacy Format

```bash
# API Key (will auto-configure base URL and model)
DASHSCOPE_API_KEY=sk-your-dashscope-key-here
```

#### Example Configurations

**Qwen (Dashscope):**
```bash
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=sk-your-key-here
LLM_MODEL=qwen-plus
```

**OpenAI-compatible:**
```bash
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4
```

---

## Optional Environment Variables

### Logging

```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log file path
LOG_DIR=logs
```

### Data Directories

```bash
# Artifacts directory (for episodes, tool calls, etc.)
ARTIFACTS_DIR=artifacts

# Configuration directory
CONFIG_DIR=config
```

### Performance Tuning

```bash
# Maximum workers for parallel processing
MAX_WORKERS=4

# Memory limit for certain operations (in MB)
MEMORY_LIMIT=1024
```

---

## Setting Environment Variables

### Windows (Command Prompt)
```cmd
set LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
set LLM_API_KEY=sk-your-key-here
set LLM_MODEL=qwen-plus
```

### Windows (PowerShell)
```powershell
$env:LLM_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:LLM_API_KEY="sk-your-key-here"
$env:LLM_MODEL="qwen-plus"
```

### Linux/macOS
```bash
export LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
export LLM_API_KEY=sk-your-key-here
export LLM_MODEL=qwen-plus
```

---

## .env File

You can also create a `.env` file in the project root:

```bash
# LLM Configuration
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=sk-your-key-here
LLM_MODEL=qwen-plus
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs

# Data
ARTIFACTS_DIR=artifacts
CONFIG_DIR=config
```

**Security Note:** Never commit `.env` file to version control. Add it to `.gitignore`!

---

## Validation

Environment variables are automatically validated during startup:

- **Temperature**: Must be between 0.0 and 2.0 (auto-clipped if invalid)
- **Max Tokens**: Must be between 1 and 32000 (auto-clipped if invalid)

---

## Troubleshooting

### Issue: "LLM API not configured"

**Solution:** Set the required environment variables before running:

```bash
# Check if variables are set
echo %LLM_API_BASE%  # Windows CMD
echo $LLM_API_BASE  # Linux/macOS

# If empty, set them
export LLM_API_BASE=...
```

### Issue: "Invalid temperature"

**Solution:** The system will auto-correct to default 0.7 if out of range.

### Issue: "Module not found" errors

**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Testing Configuration

For testing without real LLM API (simulation mode):

```bash
# Don't set LLM_API_BASE or LLM_API_KEY
# System will run in simulation mode with mock responses
```
