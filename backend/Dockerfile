FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Set to "true" to also install the heavy local embedding stack
# (sentence-transformers + torch) for the 100% local path. Default slim image
# targets API providers (OpenAI / Anthropic / Ollama LLM).
ARG INSTALL_LOCAL_EMBEDDINGS=false
# Set to "true" to install the OCR stack (Tesseract + PyMuPDF) for scanned PDFs.
ARG INSTALL_OCR=false

# build-essential is needed for optional extras' wheels; tesseract for OCR.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && if [ "$INSTALL_OCR" = "true" ]; then \
         apt-get install -y --no-install-recommends \
           tesseract-ocr tesseract-ocr-por; \
       fi \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-local.txt requirements-ocr.txt ./
RUN pip install --upgrade pip && \
    if [ "$INSTALL_LOCAL_EMBEDDINGS" = "true" ]; then \
        pip install -r requirements-local.txt; \
    else \
        pip install -r requirements.txt; \
    fi && \
    if [ "$INSTALL_OCR" = "true" ]; then pip install -r requirements-ocr.txt; fi

COPY app ./app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
