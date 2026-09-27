"""Step 4: read text from a screenshot using Tesseract OCR.

Tesseract itself must be installed separately:
  Windows: https://github.com/UB-Mannheim/tesseract/wiki
  Then set TESSERACT_CMD in .env if it is not on your PATH.
"""

import os

import pytesseract
from dotenv import load_dotenv
from PIL import Image, ImageOps

load_dotenv()
if os.getenv("TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD")


def preprocess(image: Image.Image) -> Image.Image:
    """Grayscale + upscale small images, which improves OCR accuracy."""
    image = ImageOps.grayscale(image)
    if image.width < 1000:
        scale = 1000 / image.width
        image = image.resize((int(image.width * scale), int(image.height * scale)))
    return image


def extract_text(image_file) -> dict:
    """Take a file path or file-like object (e.g. Streamlit upload).

    Returns {'text', 'error'}.
    """
    try:
        image = Image.open(image_file)
        text = pytesseract.image_to_string(preprocess(image))
    except pytesseract.TesseractNotFoundError:
        return {"text": "", "error": "Tesseract is not installed or TESSERACT_CMD is wrong."}
    except Exception as e:
        return {"text": "", "error": f"Could not read image: {e}"}

    text = " ".join(text.split())  # collapse broken lines/whitespace
    if not text:
        return {"text": "", "error": "No text found in the image."}
    return {"text": text, "error": None}
