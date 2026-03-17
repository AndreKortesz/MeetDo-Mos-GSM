# Stage 1: Build React
FROM node:20-alpine AS frontend
WORKDIR /app
COPY package.json ./
RUN npm install
COPY index.html vite.config.js ./
COPY src/ ./src/
RUN mkdir -p public
RUN npm run build

# Stage 2: Python server
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY --from=frontend /app/dist ./dist

EXPOSE 8080
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}
