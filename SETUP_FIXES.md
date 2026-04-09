# Agent-NN Setup Fixes and Troubleshooting Guide

This document explains the fixes applied to resolve the setup script errors and Docker build issues.

## Issues Fixed

### 1. Missing Functions in log_utils.sh

**Problem**: The setup script was calling undefined functions:
- `verify_installation`
- `run_project_tests` 
- `print_next_steps`

**Solution**: Added these functions to `scripts/lib/log_utils.sh`

### 2. Missing Utility Functions in setup.sh

**Problem**: The setup script was calling undefined functions:
- `return_to_main_menu`
- `clean_environment`
- `show_current_config`

**Solution**: Added these functions directly to the setup.sh script.

### 3. Docker Build Failure with torch

**Problem**: torch-2.7.1 download was failing due to network issues (incomplete download: 244.1/821.2 MB)

**Solutions Applied**:
- Pinned torch to stable version 2.5.1 in `requirements.txt`
- Added retry mechanisms and increased timeout in `Dockerfile`
- Created fallback `requirements-light.txt` without torch
- Created `Dockerfile.fallback` with CPU-only torch version
- Enhanced `docker_utils.sh` with fallback build logic

## New Files Created

1. **requirements-light.txt**: Lightweight dependencies without torch
2. **Dockerfile.fallback**: Alternative Dockerfile with CPU-only torch
3. **scripts/build_docker.sh**: Standalone Docker build script with fallback
4. **Enhanced docker_utils.sh**: Added `docker_compose_up` function with fallback logic

## Usage Instructions

### Running Setup After Fixes

```bash
# Navigate to project directory
cd ~/Agent-NN

# Run full setup
./scripts/setup.sh --full

# Or run with specific options
./scripts/setup.sh --minimal  # Python only
./scripts/setup.sh --preset dev  # canonical services/* setup
```

### Testing Docker Build Separately

```bash
# Test Docker build before full setup
./scripts/build_docker.sh

# This will try main Dockerfile first, then fallback if needed
```

### Manual Docker Build with Fallback

```bash
# Try main build
docker build -t agent-nn:latest .

# If it fails, try fallback
docker build -f Dockerfile.fallback -t agent-nn:fallback .
```

## Environment Variables

The setup script now properly handles these configuration options:

- `POETRY_METHOD`: Method for installing Poetry (system|venv|pipx)
- `AUTO_MODE`: Skip interactive prompts
- `BUILD_FRONTEND`: Whether to build frontend
- `START_DOCKER`: Whether to start Docker services
- `START_MCP`: Whether to start MCP services

## Troubleshooting Common Issues

### Poetry Installation Issues

If Poetry installation fails:

```bash
# Try manual installation
curl -sSL https://install.python-poetry.org | python3 -

# Or use the venv method within the project
python3 -m venv ./Agent-NN/.venv
source ./Agent-NN/.venv/bin/activate
pip install poetry
```

### Docker Issues

If Docker services fail to start:

```bash
# Check Docker status
docker ps
docker-compose ps

# View logs
docker-compose logs

# Clean up and restart
docker-compose down --volumes
docker-compose up -d
```

### Network Issues with Package Downloads

If pip/npm downloads fail:

```bash
# Use mirrors or proxy
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Or try the light requirements
pip install -r requirements-light.txt
```

### Permission Issues

If you encounter permission errors:

```bash
# Run setup with sudo flag
./scripts/setup.sh --with-sudo

# Or fix ownership
sudo chown -R $USER:$USER ~/Agent-NN
```

## Configuration Files

The setup script uses these configuration files:

1. `.agentnn_config`: Project-specific settings
2. `.agentnn/status.json`: Setup status tracking
3. `logs/setup.log`: Detailed setup logs

## Recovery Mode

If setup fails, you can try recovery:

```bash
./scripts/setup.sh --recover
```

Or clean and restart:

```bash
./scripts/setup.sh --clean
./scripts/setup.sh --full
```

## Verification

After successful setup, verify everything works:

```bash
# Check status
./scripts/status.sh

# Test API
curl http://localhost:8000/health

# Check services
docker-compose ps
```

## Support

If you continue to experience issues:

1. Check the logs: `cat logs/setup.log`
2. Run with verbose output: `./scripts/setup.sh --verbose`
3. Try minimal setup first: `./scripts/setup.sh --minimal`
4. Use recovery mode: `./scripts/setup.sh --recover`
