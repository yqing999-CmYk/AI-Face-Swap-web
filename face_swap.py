import os
import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
INSWAPPER_PATH = os.path.join(MODEL_DIR, "inswapper_128.onnx")

# Globals — loaded once at startup
_face_app: FaceAnalysis = None
_swapper = None


def load_models():
    """Load InsightFace analysis app and inswapper model. Called once at startup."""
    global _face_app, _swapper

    if not os.path.exists(INSWAPPER_PATH):
        raise FileNotFoundError(
            f"inswapper_128.onnx not found at {INSWAPPER_PATH}\n"
            "Download it from: https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128.onnx\n"
            f"Then place it in: {MODEL_DIR}"
        )

    # ctx_id=-1 means CPU; 0 means first GPU
    _face_app = FaceAnalysis(
        name="buffalo_l",
        root=MODEL_DIR,
        providers=["CPUExecutionProvider"],
    )
    _face_app.prepare(ctx_id=-1, det_size=(640, 640))

    _swapper = insightface.model_zoo.get_model(
        INSWAPPER_PATH,
        providers=["CPUExecutionProvider"],
    )

    print("Models loaded successfully (CPU mode).")


def read_image(image_bytes: bytes) -> np.ndarray:
    """Decode image bytes to OpenCV BGR array."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image. Ensure it is a valid JPEG or PNG.")
    return img


def swap_faces(source_bytes: bytes, target_face_bytes: bytes) -> bytes:
    """
    Swap the face from target_face_bytes onto the person in source_bytes.

    Args:
        source_bytes:      The full person image (body to keep).
        target_face_bytes: The face donor image (face to use).

    Returns:
        PNG-encoded bytes of the result image.
    """
    if _face_app is None or _swapper is None:
        raise RuntimeError("Models not loaded. Call load_models() first.")

    source_img = read_image(source_bytes)
    target_img = read_image(target_face_bytes)

    # Detect faces in both images
    source_faces = _face_app.get(source_img)
    target_faces = _face_app.get(target_img)

    if len(source_faces) == 0:
        raise ValueError("No face detected in the source (person) image.")
    if len(target_faces) == 0:
        raise ValueError("No face detected in the target (face donor) image.")

    # Use the largest/most prominent face in each image (bbox = [x1,y1,x2,y2])
    source_face = max(source_faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    target_face = max(target_faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

    # Perform swap: replace source_face in source_img with target_face identity
    result_img = source_img.copy()
    result_img = _swapper.get(result_img, source_face, target_face, paste_back=True)

    # Encode result to PNG bytes
    success, encoded = cv2.imencode(".png", result_img)
    if not success:
        raise RuntimeError("Failed to encode result image.")

    return encoded.tobytes()
