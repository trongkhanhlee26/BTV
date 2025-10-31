# Python 3.12 slim
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl bash \
    && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Requirements
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Default: keep container alive until we mount code & run command from compose
CMD ["bash", "-lc", "sleep infinity"]
