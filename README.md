# AI Face Swap

A web application that swaps faces between two images using open-source AI models. Upload a person image and a face donor image, click button to swap, and the result is downloadable.

---

## Introduction

This app runs entirely on your local machine — no cloud API required, no usage fees. It uses InsightFace's `inswapper_128` model for face detection and swapping, served through a FastAPI backend and a plain HTML/CSS/JS frontend. CPU-only operation is supported (no NVIDIA GPU needed), with each swap taking roughly 15–30 seconds.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | [FastAPI](https://fastapi.tiangolo.com/) (Python) |
| ASGI server | [Uvicorn](https://www.uvicorn.org/) |
| Face detection | [InsightFace](https://github.com/deepinsight/insightface) — `buffalo_l` model |
| Face swapping | InsightFace `inswapper_128.onnx` |
| ML inference | [ONNX Runtime](https://onnxruntime.ai/) (CPU) |
| Image processing | OpenCV, Pillow |
| Frontend | Vanilla HTML + CSS + JavaScript (no build step) |
| Python version | 3.11 |

---

## Project Structure

```
AI-Face-Swap/
├── backend/
│   ├── main.py               # FastAPI app — routes, startup, static serving
│   ├── face_swap.py          # InsightFace model loading + swap logic
│   ├── requirements.txt      # Python dependencies
│   └── models/
│       ├── inswapper_128.onnx        # Face swap model (~529 MB, download once)
│       └── models/buffalo_l/         # Face detection models (auto-downloaded)
├── frontend/
│   ├── index.html            # Two-panel upload UI
│   ├── style.css             # Dark theme styles
│   └── app.js                # Drag-drop upload, fetch /swap, show result
├── static/
│   └── results/              # Swapped output images saved here
├── Plan/
│   ├── plan.txt              # Tech stack research and options
│   └── setup_steps.txt       # Detailed setup reference
├── start.bat                 # One-click launcher (Windows)
└── README.md                 # This file
```

---

## How It Works

```
User uploads two images in the browser
        │
        ▼
Browser POSTs multipart form-data to POST /swap
        │
        ▼
FastAPI reads both image files into memory
        │
        ▼
face_swap.py — InsightFace buffalo_l detects faces in both images
        │
        ▼
inswapper_128.onnx — replaces the face in the source image
        with the identity from the target face image
        │
        ▼
Result PNG saved to static/results/<uuid>.png
        │
        ▼
Backend returns { "result_url": "/static/results/<uuid>.png" }
        │
        ▼
Browser displays result image + Download button
```

**Key design decisions:**
- Model loading happens once at server startup (~20s), not per request
- The swap runs in a thread pool executor so it does not block the async event loop
- The frontend mounts at `/` after all API routes, so API endpoints take priority

---

## Environment Setup (one-time)

### Prerequisites
- Python 3.11 installed
- ~1.5 GB free disk space (models)
- Internet connection for initial model download

### Step 1 — Create virtual environment

Open a terminal in the project root:

```bash
cd C:\Users\***\AI-Face-Swap
python -m venv venv
```

> **Note:** If you see a `PYTHONHOME`/`PYTHONPATH` error, remove those variables from
> Windows System Environment Variables (Win+R → `sysdm.cpl` → Advanced → Environment Variables).

### Step 2 — Install dependencies

```bash
venv\Scripts\activate
cd backend
pip install -r requirements.txt
```

This installs: fastapi, uvicorn, insightface, onnxruntime, opencv-python, pillow, and dependencies.

### Step 3 — Download the face swap model (~529 MB, one-time)

The `buffalo_l` face detection model auto-downloads on first run. The swap model must be downloaded manually:

**Option A — Python (recommended):**
```python
# Run from project root with venv activated
python -c "
import urllib.request, sys
url = 'https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx'
dest = r'backend/models/inswapper_128.onnx'
def progress(c, b, t):
    sys.stdout.write(f'\r{min(c*b/t*100,100):.1f}%'); sys.stdout.flush()
urllib.request.urlretrieve(url, dest, reporthook=progress)
print(' Done.')
"
```

**Option B — Browser:**
1. Visit: `https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx`
2. Save the file to: `backend\models\inswapper_128.onnx`

**Option C — curl.exe (Windows 11):**
```cmd
curl.exe -L -o "backend\models\inswapper_128.onnx" "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx"
```

---

## How to Test

With the server running (see next section), you can test the API directly:

**Health check:**
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

**Face swap via curl:**
```bash
curl -X POST http://localhost:8000/swap \
  -F "source_image=@path/to/person.jpg;type=image/jpeg" \
  -F "target_image=@path/to/face.jpg;type=image/jpeg"
# Expected: {"result_url":"/static/results/<uuid>.png"}
```

**Interactive API docs:**
Open `http://localhost:8000/docs` in your browser to test endpoints via Swagger UI.

**Check saved results:**
```
AI-Face-Swap\static\results\
```

---

## How to Run

### Daily use — double-click `start.bat`

The launcher automatically:
1. Activates the virtual environment
2. Frees port 8000 if occupied
3. Starts the FastAPI server with hot-reload

Then open `http://localhost:8000` in your browser.

### Manual start

```bash
cd C:\Users\***\AI-Face-Swap
venv\Scripts\activate
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### First startup note

On first run, InsightFace downloads `buffalo_l` face detection models (~350 MB) automatically. This takes 1–2 minutes. Subsequent starts are fast (~20s for model loading).

### Usage

1. Open `http://localhost:8000`
2. Left panel — upload the **person image** (the body you want to keep)
3. Right panel — upload the **face donor image** (the face you want to use)
4. Click **Go** and wait ~15–30 seconds
5. The result appears below — click **Download** to save it

---

## Deployment

### Option A — Local network (simplest)

The server already binds to `0.0.0.0`, so other devices on your network can access it:

```
http://<your-PC-ip>:8000
```

Find your IP: `ipconfig` → look for IPv4 address under your active adapter.

### Option B — Docker container

Create `Dockerfile` in the project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY static/ ./static/

WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t ai-face-swap .
docker run -p 8000:8000 -v ./backend/models:/app/backend/models ai-face-swap
```

> Mount `backend/models/` as a volume so the large model files are not baked into the image.

---

## Notes

- Result images accumulate in `static/results/` — safe to delete periodically
- Best results with clear, front-facing portraits
- The `inswapper_128` model was trained for research use; review its license before commercial deployment
- API documentation auto-generated at `http://localhost:8000/docs`
