FROM node:20-slim AS frontend
WORKDIR /app/pixora/frontend
COPY pixora/frontend/package*.json ./
RUN npm ci --production=false
COPY pixora/frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /app/pixora/frontend/dist /app/pixora/frontend/dist

ENV PIXORA_DEPLOYMENT_MODE=serverless
ENV PIXORA_DEFAULT_TIER=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health').raise_for_status()" || exit 1

CMD uvicorn pixora.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
