FROM node:20-slim AS frontend
WORKDIR /build/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake g++ make libopenblas-dev liblapack-dev && \
    rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server/ .
COPY --from=frontend /build/server/static/web ./static/web
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port $PORT"]
