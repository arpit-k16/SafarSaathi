# Single-service image: builds the web console, then serves it and the API from one origin.
# Build context: SafarSaathi_Project/
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
# Empty API URL => the console calls the API on its own origin.
ENV VITE_SAFARSAATHI_API_URL=""
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    SAFARSAATHI_DATA_MODE=auto \
    PORT=8000
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY models ./models
COPY deploy_snapshot ./deploy_snapshot
COPY outputs/indicators ./outputs/indicators
COPY outputs/reports/ml_data_readiness.json ./outputs/reports/ml_data_readiness.json
COPY outputs/metrics ./outputs/metrics
COPY data/processed ./data/processed
COPY research/research_status.json ./research/research_status.json
COPY --from=web /web/dist ./web/dist
RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/health',timeout=4)"
CMD ["sh", "-c", "uvicorn safarsaathi_ml.asgi:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
