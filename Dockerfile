# ==============================================================================
# SyncOps Assistant - Production Container Image
# Multi-purpose container supporting FastAPI API, Streamlit Dashboard, and Worker
# ==============================================================================
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace

WORKDIR /workspace

# Install system dependencies (curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code, runbooks, and scripts
COPY app/ ./app/
COPY dashboard/ ./dashboard/
COPY runbooks/ ./runbooks/
COPY scripts/ ./scripts/
COPY pytest.ini .

# Create volume mount point for SQLite database persistence
RUN mkdir -p /workspace/data

EXPOSE 8000 8501

# Default command: Launch FastAPI REST API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
