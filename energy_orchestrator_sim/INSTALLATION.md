# Installation Guide

Complete step-by-step instructions for setting up AI Energy Orchestrator.

## System Requirements

- **Python:** 3.11 or higher
- **OS:** Linux, macOS, or Windows 10+
- **RAM:** 4 GB minimum (8 GB recommended for 50+ homes)
- **Disk Space:** 500 MB for installation + dependencies

## Method 1: Standard Installation (Recommended)

### Step 1: Clone or Navigate to Repository

```bash
cd ~/Documents/SFS2/energy_orchestrator_sim
```

### Step 2: Create Virtual Environment

**Linux/macOS:**
```bash
python3.11 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

### Step 3: Upgrade pip and Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -e .
```

**For development (optional):**
```bash
pip install -e ".[dev]"  # Includes black, ruff, mypy, pytest
```

### Step 4: Verify Installation

```bash
python -c "from energy_orchestrator_sim import *; print('✓ Installation successful!')"
```

## Method 2: Docker Installation

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 1.29+ (optional)

### Build & Run

```bash
cd ~/Documents/SFS2/energy_orchestrator_sim

# Build image
docker build -t energy-orchestrator:latest .

# Run simulation
docker run --rm energy-orchestrator:latest
```

**Custom parameters:**
```bash
docker run --rm energy-orchestrator:latest \
  python main.py --homes 50 --days 30 --seed 42
```

**Mount output directory (to save CSV results locally):**
```bash
docker run --rm -v $(pwd)/results:/app \
  energy-orchestrator:latest \
  python main.py --homes 10 --days 7
```

## Method 3: Windows-Specific Setup

### Using Anaconda

```bash
# Create conda environment
conda create -n energy-orchestrator python=3.11

# Activate
conda activate energy-orchestrator

# Install from repository
cd C:\Users\<YourUsername>\Documents\SFS2\energy_orchestrator_sim
pip install -e .
```

### Troubleshooting on Windows

**Issue:** `No module named 'energy_orchestrator_sim'`

**Solution:**
```powershell
# Ensure pip is updated
python -m pip install --upgrade pip

# Reinstall in development mode
pip install -e . --no-cache-dir
```

**Issue:** Path not found for venv

**Solution:**
```powershell
# Use full path
set PYTHONPATH=C:\Users\<YourUsername>\Documents\SFS2\energy_orchestrator_sim;%PYTHONPATH%
```

## Method 4: Development Setup (For Contributors)

### Full Development Environment

```bash
# Clone repository (if not already done)
git clone https://github.com/your-org/energy-orchestrator.git
cd energy-orchestrator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Verify
pytest tests/ -v
```

### Pre-commit Hooks
Auto-format code before commit:
```bash
pre-commit run --all-files
```

## Dependency Verification

### Check Installed Packages

```bash
pip list | grep -E "ortools|pandas|numpy|streamlit|pytest"
```

### Expected Versions
```
ortools              >= 9.7.2996
pandas               >= 2.0.0
numpy                >= 1.24.0
streamlit            >= 1.30.0
pytest               >= 7.4.0
black                >= 23.0.0
ruff                 >= 0.1.0
mypy                 >= 1.0.0
```

## Python Import Verification

Test each core module:

```python
# Core physics
from energy_orchestrator_sim.core import HouseholdModel, HouseholdConfig

# Data generation
from energy_orchestrator_sim.data import generate_simulation_data

# Simulation engines
from energy_orchestrator_sim.simulation import EstateSimulator

# Metrics
from energy_orchestrator_sim.metrics import MetricsCalculator

print("✓ All imports successful!")
```

## Running First Test

### Quick sanity check (2 min)

```bash
python main.py --homes 3 --days 1 --seed 42
```

**Expected output:**
```
================================================================================
SIMULATION SUMMARY
================================================================================
Homes: 3, Days: 1
Transformer capacity: 100 kW

COST IMPACT
  Reduction: £5-10 (2-5%)
  Per home: £1-3

PEAK LOAD REDUCTION
  Reduction: 2-5 kW (5-10%)
  ...

✓ Simulation PASSED
```

### Full test suite (30 sec)

```bash
pytest tests/ -v --tb=short
```

**Expected:** All tests PASSED with >85% coverage

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'ortools'`

**Cause:** OR-Tools not installed

**Fix:**
```bash
pip install ortools >= 9.7.2996
```

### Issue: `ImportError: cannot import name 'HouseholdModel' from 'core.household'`

**Cause:** Package not in development mode

**Fix:**
```bash
pip install -e . --force-reinstall
```

### Issue: Solver timeout (optimization takes >60 sec)

**Cause:** Too many homes + too many days, or solver struggling

**Fix:**
```bash
# Use smaller scenario
python main.py --homes 10 --days 7

# Or check .gitignore and increase time limit in code
# optimization_engine.py: solver_time_limit_seconds=120
```

### Issue: Out of memory

**Cause:** Too large scenario (>100 homes × 90 days)

**Fix:**
```bash
# Use smaller scenario
python main.py --homes 50 --days 30

# Or increase swap space on Linux
```

### Issue: Tests fail with `RuntimeError: solver not available`

**Cause:** OR-Tools CBC solver not properly installed

**Fix:**
```bash
pip uninstall ortools
pip install ortools --no-cache-dir
```

## Uninstalling

### Remove from Virtual Environment

```bash
# Deactivate
deactivate

# Delete environment
rm -rf venv  # Linux/Mac
rmdir venv /s /q  # Windows
```

### Uninstall Package

```bash
pip uninstall energy-orchestrator-sim
```

## Next Steps

1. **Run simulation:**
   ```bash
   python main.py
   ```

2. **Explore results:**
   ```bash
   ls -la simulation_results_*.csv
   python -c "import pandas as pd; print(pd.read_csv('simulation_results_baseline.csv').head())"
   ```

3. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

4. **Read documentation:**
   - [README.md](README.md) - Overview & quick start
   - [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Detailed design (coming)
   - [API.md](docs/API.md) - Class & function reference (coming)

## Support

- **Questions about installation?** Open an issue
- **Need help with setup?** Check existing issues
- **Found a bug?** Report with Python version + OS info

---

Last updated: 2024-01
Status: Production-ready
