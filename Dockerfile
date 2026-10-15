# syntax=docker/dockerfile:1.4
# =============================================================================
# Algorise DevEx Platform: Multi-Stage Production Dockerfile
# =============================================================================

# --- Stage 1: Build & Dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./

# Install core devex + server dependencies into user directory
RUN pip install --no-cache-dir --user .[server]

# --- Stage 2: Final Minimal Runtime ---
FROM python:3.11-slim AS runtime

LABEL maintainer="Algorise AI <support@algorise.ai>"
LABEL org.opencontainers.image.title="Algorise DevEx & Autonomous SRE Platform"
LABEL org.opencontainers.image.description="Enterprise autonomous developer experience sentry & SRE engine"
LABEL org.opencontainers.image.version="1.0.0"

WORKDIR /app

# Create non-root system user for security
RUN groupadd -g 10001 algorise && \
    useradd -u 10001 -g algorise -s /bin/bash -m algorise

# Copy installed python packages from builder
COPY --from=builder /root/.local /home/algorise/.local
COPY . /app

RUN chown -R algorise:algorise /app /home/algorise

USER algorise
ENV PATH="/home/algorise/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000 9090

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

ENTRYPOINT ["devex"]
CMD ["status"]