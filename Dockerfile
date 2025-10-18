# Start from official Python 3.13 image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# -------------------------------
# 1. Install curl and certificates (required for UV installer)
# -------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# -------------------------------
# 2. Install UV (official installer)
# -------------------------------
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure uv is in PATH
ENV PATH="/root/.local/bin/:$PATH"

# -------------------------------
# 3. Copy project files
# -------------------------------
COPY . /app

# -------------------------------
# 4. Install dependencies via UV
# -------------------------------
ENV UV_HTTP_TIMEOUT=300
RUN uv sync --frozen --no-cache

# Activate the environment
ENV PATH="/app/.venv/bin:$PATH"

# -------------------------------
# 5. Expose and Run FastAPI app
# -------------------------------
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
