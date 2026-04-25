from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import pytesseract
from PIL import Image
import pdfplumber
import io
import os

app = FastAPI(title="OCR Service")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename or ""
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    try:
        if ext == "pdf" or file.content_type == "application/pdf":
            text = extract_pdf(content)
        else:
            text = extract_image(content)
        if not text.strip():
            raise HTTPException(status_code=422, detail="No text could be extracted")
        return JSONResponse({"text": text.strip(), "chars": len(text.strip())})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def extract_pdf(content: bytes) -> str:
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        pages_text = []
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages_text.append(page_text)
            else:
                img = page.to_image(resolution=200).original
                ocr_text = pytesseract.image_to_string(img, lang="spa+eng")
                pages_text.append(ocr_text)
        return "\n\n".join(pages_text)

def extract_image(content: bytes) -> str:
    image = Image.open(io.BytesIO(content))
    return pytesseract.image_to_string(image, lang="spa+eng")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
