FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if needed (e.g., for psycopg, curl for healthcheck)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend codebase into /app/backend to match python package root
COPY . ./backend/

ENV PYTHONPATH=/app \
    PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
