from fastapi import FastAPI, File, UploadFile, HTTPException
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import io
import os
import tempfile
import subprocess

app = FastAPI()

SUPPORTED_IMAGES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}

def markitdown_extract(file_bytes: bytes, suffix: str) -> str:
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(file_bytes)
            tmp_path = f.name
        result = subprocess.run(
            ["markitdown", tmp_path],
            capture_output=True, text=True, timeout=30
        )
        os.unlink(tmp_path)
        if result.returncode == 0 and len(result.stdout.strip()) > 50:
            return result.stdout.strip()
    except Exception:
        pass
    return ""

def tesseract_extract(image: Image.Image) -> str:
    return pytesseract.image_to_string(image, lang="spa+eng").strip()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    content = await file.read()
    mime = file.content_type or ""
    filename = file.filename or ""

    try:
        if mime in SUPPORTED_IMAGES:
            suffix = ".jpg" if "jpeg" in mime else ".png"
            text = markitdown_extract(content, suffix)
            source = "markitdown"
            if not text:
                img = Image.open(io.BytesIO(content))
                text = tesseract_extract(img)
                source = "tesseract"
            return {"text": text, "source": source}

        if mime == "application/pdf" or filename.endswith(".pdf"):
            text = markitdown_extract(content, ".pdf")
            if text:
                return {"text": text, "source": "markitdown"}

            doc = fitz.open(stream=content, filetype="pdf")
            native_text = "".join(page.get_text() for page in doc)
            if len(native_text.strip()) > 100:
                return {"text": native_text.strip(), "source": "native"}

            ocr_text = ""
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text += tesseract_extract(img) + "\n"
            return {"text": ocr_text.strip(), "source": "tesseract"}

        raise HTTPException(status_code=400, detail=f"Tipo no soportado: {mime}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
