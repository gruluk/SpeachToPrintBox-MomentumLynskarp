FROM node:20-slim AS booth
WORKDIR /build/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM node:20-slim AS admin
WORKDIR /build/web-admin
COPY web-admin/package*.json ./
RUN npm ci
COPY web-admin/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server/ .
COPY assets/ /assets/
COPY --from=booth /build/server/static/web ./static/web
COPY --from=admin /build/server/static/admin-app ./static/admin-app
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
