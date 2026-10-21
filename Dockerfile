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

# pip, setuptools, wheel and build are upgraded before the install. The
# versions bundled in the base image carry known path-traversal and
# privilege-escalation advisories, and this build tooling is what installs
# every other package into the image. The upgrade has to happen before the
# project install, because the project install itself runs through pip.
RUN python -m pip install --no-cache-dir --upgrade \
        pip \
        setuptools \
        wheel \
        build

# Install core devex + server dependencies into user directory.
RUN python -m pip install --no-cache-dir --user .[server]

# Remove the build tooling from the builder output. It is not needed at
# runtime, and the advisories above apply to the copies that would
# otherwise be carried into the final image.
RUN python -m pip uninstall -y --no-input \
        pip \
        setuptools \
        wheel \
        build \
    || true

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

# The base image ships pip, setuptools and wheel with known path-traversal
# and privilege-escalation advisories. The runtime never installs or builds
# anything, so the build tooling is removed from the final image.
RUN python -m pip uninstall -y --no-input \
        pip \
        setuptools \
        wheel \
    || true

# Copy installed python packages from builder
COPY --from=builder /root/.local /home/algorise/.local
COPY . /app

# data/ holds runtime-created local state (agent memory, checkpoints,
# quarantine DLQ, distribution store). The application creates it on
# demand, so the image ships the directory empty and writable.
RUN mkdir -p /app/data && \
    chown -R algorise:algorise /app /home/algorise && \
    chmod 770 /app/data

USER algorise
ENV PATH="/home/algorise/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

EXPOSE 8000 9090

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/readyz').read()" || exit 1

# The image runs the API service. The DevEx CLI stays available as a
# separate entrypoint for operator tooling.
ENTRYPOINT ["uvicorn"]
CMD ["engine.main:app", "--host", "0.0.0.0", "--port", "8000"]
