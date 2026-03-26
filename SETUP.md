# 🐾 Wildlife AI Platform — Environment Setup Guide

> **Target System**: Windows 10/11 · NVIDIA RTX 3080 (10 GB) · 32 GB RAM  
> **Python**: 3.10 · **CUDA**: 11.8 · **PyTorch**: 2.1+

---

## Prerequisites

| Software | Version | Download |
|----------|---------|----------|
| [Miniconda](https://docs.conda.io/en/latest/miniconda.html) | Latest | Required for environment management |
| [Git](https://git-scm.com/downloads) | Latest | Required for cloning AWC135 repo |
| [NVIDIA Driver](https://www.nvidia.com/Download/index.aspx) | ≥ 522.06 | Required for CUDA 11.8 support |
| [Node.js](https://nodejs.org/) | 18+ LTS | Required for frontend (install later) |

> [!NOTE]
> You do **NOT** need to install CUDA Toolkit or cuDNN separately — conda handles it.

---

## Step 1: Create Conda Environment

Open **Anaconda Prompt** (or any terminal with conda) and run:

```bash
# Create environment with Python 3.10
conda create -n wildlife python=3.10 -y

# Activate it
conda activate wildlife
```

> [!IMPORTANT]
> Always run `conda activate wildlife` before any work.

---

## Step 2: Install PyTorch with CUDA 11.8

```bash
# Install PyTorch 2.1 with CUDA 11.8 (includes cuDNN)
pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
```

### Verify GPU:
```bash
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0)); print('VRAM:', round(torch.cuda.get_device_properties(0).total_mem / 1e9, 1), 'GB')"
```

**Expected output:**
```
CUDA available: True
GPU: NVIDIA GeForce RTX 3080
VRAM: 10.0 GB
```

> [!CAUTION]
> If CUDA is `False`, update your NVIDIA driver first, then reinstall PyTorch.

---

## Step 3: Install MegaDetector

```bash
pip install megadetector
```

### Download MegaDetector v5a weights:

```bash
# Create model directory
mkdir -p ml_models/megadetector

# Download MDv5a weights (~180 MB)
curl -L -o ml_models/megadetector/md_v5a.0.0.pt https://github.com/agentmorris/MegaDetector/releases/download/v5.0/md_v5a.0.0.pt
```

> If `curl` doesn't work on Windows, download manually from:  
> https://github.com/agentmorris/MegaDetector/releases/download/v5.0/md_v5a.0.0.pt  
> and place in `ml_models/megadetector/`

### Verify MegaDetector:
```bash
python -c "from megadetector.detection.run_detector import load_detector; m = load_detector('ml_models/megadetector/md_v5a.0.0.pt'); print('MegaDetector loaded OK')"
```

---

## Step 4: Install AWC135 Classifier

```bash
# Clone AWC Wildlife Classifier repository
git clone https://github.com/Australian-Wildlife-Conservancy-AWC/awc-wildlife-classifier.git ml_models/awc135_repo

# Install awc_helpers package
pip install -e ml_models/awc135_repo
```

### Download AWC135 model weights:

Follow the instructions in the AWC repo README to download:
1. **AWC135 classifier weights** (`.pth` file) → save to `ml_models/awc135/awc135_weights.pth`
2. **Labels file** → save to `ml_models/awc135/labels.txt`

```bash
mkdir -p ml_models/awc135
# Move downloaded files to ml_models/awc135/
```

---

## Step 5: Install Backend Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- **FastAPI** + **Uvicorn** (web server)
- **SQLAlchemy** + **Alembic** (database ORM + migrations)
- **aiosqlite** (async SQLite for development)
- **Pillow** + **opencv-python-headless** (image processing)
- **pandas** (CSV loading)
- **tqdm** (progress bars)

---

## Step 6: Initialize Database

```bash
# Run initial database setup
python -m backend.app.db.init_db
```

---

## Step 7: Verify Full Installation

Run the verification script:

```bash
python -c "
import torch
print('✅ PyTorch:', torch.__version__)
print('✅ CUDA:', torch.cuda.is_available())
print('✅ GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')

import fastapi
print('✅ FastAPI:', fastapi.__version__)

import sqlalchemy
print('✅ SQLAlchemy:', sqlalchemy.__version__)

from PIL import Image
print('✅ Pillow: OK')

import cv2
print('✅ OpenCV:', cv2.__version__)

import pandas
print('✅ Pandas:', pandas.__version__)

print()
print('🎉 All dependencies installed successfully!')
"
```

---

## Step 8: Frontend Setup (Later)

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:5173`

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `conda activate wildlife` | Activate environment |
| `uvicorn backend.app.main:app --reload` | Start backend API |
| `python scripts/bulk_import.py` | Import dataset into DB |
| `python scripts/run_pipeline.py` | Run ML detection pipeline |
| `cd frontend && npm run dev` | Start frontend |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `CUDA not available` | Update NVIDIA driver to ≥ 522.06, reinstall PyTorch |
| `Out of memory` | Reduce `BATCH_SIZE` in `backend/app/config.py` (default 8 → try 4) |
| `ImportError: megadetector` | Run `pip install megadetector` in the wildlife conda env |
| `ModuleNotFoundError: awc_helpers` | Re-run `pip install -e ml_models/awc135_repo` |
| `Database locked` error | Only one process should write to SQLite at a time |
