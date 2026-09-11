FROM node:20-slim AS frontend
WORKDIR /frontend
COPY part1_email_agent/frontend/package.json part1_email_agent/frontend/package-lock.json ./
RUN npm ci
COPY part1_email_agent/frontend/ ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/hf-cache

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

RUN python -m playwright install-deps firefox \
 && python -m camoufox fetch

ARG EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')"

ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

COPY . .
COPY --from=frontend /static/dist ./part1_email_agent/static/dist

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "part1_email_agent.web:app", "--host", "0.0.0.0", "--port", "8000"]
