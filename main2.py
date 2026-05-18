"""
Acne Diagnosis Web App — FastAPI Backend
========================================
This backend uses:
- FastAPI -> to create the web server/API
- TensorFlow/Keras -> to load the trained CNN model
- Pillow (PIL) -> to process uploaded images
- NumPy -> for image array manipulation

The system predicts acne type from an uploaded image.
"""

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────────────────

import json                     # Used to read class_names.json
import numpy as np              # Used for numerical/image array operations
from pathlib import Path        # Easier file path handling
from PIL import Image           # Image processing library
import io                       # Handles image bytes in memory

# FastAPI modules
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# TensorFlow / Keras for Machine Learning model
import tensorflow as tf
from tensorflow import keras


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Image size expected by the CNN model
IMG_SIZE = (224, 224)

# Paths to saved ML model and class labels
MODEL_PATH = Path("acne_model_best.h5")
CLASS_NAMES_PATH = Path("class_names.json")


# Maps acne class -> severity level
SEVERITY_MAPPING = {
    'Clear'    : 'None',
    'Blackhead': 'Mild',
    'Whitehead': 'Mild',
    'Papule'   : 'Moderate',
    'Pustule'  : 'Moderate',
    'Nodule'   : 'Severe',
    'Cyst'     : 'Severe',
    'Scar'     : 'Post-Acne',
}


# Recommendations shown after prediction
RECOMMENDATIONS = {
    'None'     : "Your skin looks clear! Keep up your current skincare routine.",
    'Mild'     : "Mild acne detected. Try a gentle cleanser with salicylic acid.",
    'Moderate' : "Moderate acne detected. Consider seeing a dermatologist.",
    'Severe'   : "Severe acne detected. Please consult a dermatologist.",
    'Post-Acne': "Post-acne scarring detected. Retinol and niacinamide may help.",
}


# Description of every acne class
ACNE_DESCRIPTIONS = {
    'Clear'    : "No active acne detected.",
    'Blackhead': "Open clogged pore exposed to air.",
    'Whitehead': "Closed clogged pore under the skin.",
    'Papule'   : "Small inflamed red bump.",
    'Pustule'  : "Pimple containing pus.",
    'Nodule'   : "Large deep painful acne lump.",
    'Cyst'     : "Deep pus-filled acne lesion.",
    'Scar'     : "Post-acne skin damage or marks.",
}


# ─────────────────────────────────────────────────────────────────────────────
# CREATE FASTAPI APPLICATION
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="DermaScan: A Skin Analysis Tool",

    # Description shown in Swagger docs
    description="Upload a skin photo for AI-assisted acne prediction.",

    version="1.0.0",
)

# Loads HTML templates from "templates" folder
templates = Jinja2Templates(directory="templates")


# Global variables
# These will store the loaded model and class names
model = None
class_names = None


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP EVENT
# Runs ONCE when the server starts
# ─────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
def load_model():

    # Use global variables so they can be accessed everywhere
    global model, class_names

    # Check if model file exists
    if not MODEL_PATH.exists():
        raise RuntimeError(
            f"Model file not found: {MODEL_PATH}"
        )

    # Check if class names file exists
    if not CLASS_NAMES_PATH.exists():
        raise RuntimeError(
            f"Class names file not found: {CLASS_NAMES_PATH}"
        )

    print("Loading CNN model...")

    # Load trained CNN model
    model = keras.models.load_model(str(MODEL_PATH))

    # Load class labels from JSON
    with open(CLASS_NAMES_PATH) as f:
        class_names = json.load(f)

    print(f"Model loaded successfully!")
    print(f"Classes: {class_names}")


# ─────────────────────────────────────────────────────────────────────────────
# STATIC FILES
# Used for CSS, JS, images
# ─────────────────────────────────────────────────────────────────────────────

static_dir = Path("static")

# If static folder exists, mount it
if static_dir.is_dir():
    app.mount(
        "/static",
        StaticFiles(directory=str(static_dir)),
        name="static"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PREDICTION FUNCTION
# Main ML processing logic
# ─────────────────────────────────────────────────────────────────────────────

def run_prediction(image_bytes: bytes) -> dict:

    # Open uploaded image from bytes
    img = Image.open(io.BytesIO(image_bytes))

    # Convert image to RGB format
    img = img.convert("RGB")

    # Resize image to 224x224
    img = img.resize(IMG_SIZE)

    # Convert image into NumPy array
    arr = np.array(img).astype("float32")

    # Normalize pixel values (0-255 -> 0-1)
    arr = arr / 255.0

    # Add batch dimension for CNN
    # Shape becomes: (1, 224, 224, 3)
    arr = np.expand_dims(arr, axis=0)

    # CNN model prediction
    preds = model.predict(arr)[0]

    # Get index of highest probability
    idx = int(np.argmax(preds))

    # Convert index to class name
    pred_class = class_names[idx]

    # Convert confidence to percentage
    confidence = float(preds[idx]) * 100

    # Get severity level
    severity = SEVERITY_MAPPING.get(pred_class, "Unknown")


    # Store all prediction probabilities
    all_confidences = {
        class_names[i]: round(float(preds[i]) * 100, 2)
        for i in range(len(class_names))
    }


    # Return prediction results
    return {
        "predicted_class": pred_class,
        "confidence": round(confidence, 1),
        "severity": severity,
        "description": ACNE_DESCRIPTIONS.get(pred_class, ""),
        "recommendation": RECOMMENDATIONS.get(severity, ""),
        "all_confidences": all_confidences,
    }


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE VALIDATION FUNCTION
# Checks if uploaded file is a real image
# ─────────────────────────────────────────────────────────────────────────────

def _is_image_bytes(data: bytes) -> bool:

    # Empty file check
    if not data:
        return False

    try:
        # Try opening image
        with Image.open(io.BytesIO(data)) as im:

            # Verify image integrity
            im.verify()

        return True

    except Exception:
        # If invalid image
        return False


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES / API ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

# HOME PAGE
@app.get("/", response_class=HTMLResponse)
def index(request: Request):

    """
    Serves the frontend HTML page.
    """

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "title": "DermaScan - A Skin Analysis Tool"
        },
    )


# HEALTH CHECK ROUTE
@app.get("/health")
def health():

    """
    Used by hosting platforms to check server status.
    """

    return {
        "status": "ok",
        "model_loaded": model is not None
    }


# PREDICTION ROUTE
@app.post("/predict")
async def predict(file: UploadFile = File(...)):

    """
    Receives uploaded image
    Runs CNN prediction
    Returns JSON result
    """

    # Read uploaded image
    image_bytes = await file.read()

    # Check if file is empty
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    # Validate image format
    if not _is_image_bytes(image_bytes):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be a valid image."
        )

    try:
        # Run ML prediction
        result = run_prediction(image_bytes)

    except Exception as e:

        # Handle prediction errors
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )

    # Return prediction result as JSON
    return result