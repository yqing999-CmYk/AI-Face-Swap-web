import os
import uuid
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from face_swap import load_models, swap_faces

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
STATIC_DIR = os.path.join(ROOT_DIR, "static")
RESULTS_DIR = os.path.join(STATIC_DIR, "results")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

os.makedirs(RESULTS_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load ML models at startup (blocking is fine here — happens once)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, load_models)
    yield


app = FastAPI(title="AI Face Swap", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve saved result images
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.post("/swap")
async def swap(
    source_image: UploadFile = File(..., description="Person image (body to keep)"),
    target_image: UploadFile = File(..., description="Face donor image"),
):
    """
    Perform face swap.
    Returns JSON: { "result_url": "/static/results/<filename>.png" }
    """
    # Validate content types
    allowed = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    if source_image.content_type not in allowed:
        raise HTTPException(400, f"source_image: unsupported type '{source_image.content_type}'")
    if target_image.content_type not in allowed:
        raise HTTPException(400, f"target_image: unsupported type '{target_image.content_type}'")

    source_bytes = await source_image.read()
    target_bytes = await target_image.read()

    # Run CPU-bound swap in thread pool to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    try:
        result_bytes = await loop.run_in_executor(
            None, swap_faces, source_bytes, target_bytes
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))

    # Save result
    filename = f"{uuid.uuid4().hex}.png"
    result_path = os.path.join(RESULTS_DIR, filename)
    with open(result_path, "wb") as f:
        f.write(result_bytes)

    return JSONResponse({"result_url": f"/static/results/{filename}"})


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve frontend — mounted last so API routes above take priority
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
