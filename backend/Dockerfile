# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gcc \
        netcat-openbsd \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create a user for security
RUN useradd -m django
WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . /app
# Copy Linux Stockfish binary and set executable permissions
COPY stockfish-linux/stockfish/stockfish-ubuntu-x86-64-avx2 /app/stockfish-linux/stockfish/stockfish-ubuntu-x86-64-avx2
RUN chmod +x /app/stockfish-linux/stockfish/stockfish-ubuntu-x86-64-avx2

# Set permissions
RUN chown -R django:django /app
USER django

EXPOSE 8000

# Only one CMD is used; the last one takes effect.
# If you want to run tests, override the CMD at runtime (e.g., docker run ... pytest)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "backend.asgi:application"]