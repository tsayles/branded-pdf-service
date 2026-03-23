# SPDX-License-Identifier: GPL-3.0-or-later
# ──────────────────────────────────────────────────────────────────────────────
# branded-pdf-service — multi-stage, multi-arch Dockerfile
#
# Build args
#   PANDOC_VERSION   Pandoc release to install (default: 3.6.4)
#   TYPST_VERSION    Typst release to install  (default: 0.14.2)
#
# The brands/ directory is NOT baked into the image.
# Mount your brand configs at /brands at runtime:
#   -v ./my-brands:/brands:ro
# ──────────────────────────────────────────────────────────────────────────────

# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ARG PANDOC_VERSION=3.6.4
ARG TYPST_VERSION=0.14.2
ARG TARGETARCH

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Pandoc — amd64 only deb package; arm64 uses the generic binary tarball
RUN if [ "$TARGETARCH" = "arm64" ]; then \
      curl -fsSL \
        "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-linux-arm64.tar.gz" \
        -o /tmp/pandoc.tar.gz \
      && tar -xzf /tmp/pandoc.tar.gz -C /tmp \
      && install -m 755 /tmp/pandoc-${PANDOC_VERSION}/bin/pandoc /usr/local/bin/pandoc \
      && rm -rf /tmp/pandoc*; \
    else \
      curl -fsSL \
        "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-1-amd64.deb" \
        -o /tmp/pandoc.deb \
      && dpkg -i /tmp/pandoc.deb \
      && cp /usr/bin/pandoc /usr/local/bin/pandoc \
      && rm /tmp/pandoc.deb; \
    fi

# Typst — static binary, arch-specific
RUN if [ "$TARGETARCH" = "arm64" ]; then \
      TYPST_ARCH="aarch64-unknown-linux-musl"; \
    else \
      TYPST_ARCH="x86_64-unknown-linux-musl"; \
    fi \
    && curl -fsSL \
      "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-${TYPST_ARCH}.tar.xz" \
      -o /tmp/typst.tar.xz \
    && tar -xJf /tmp/typst.tar.xz -C /tmp \
    && install -m 755 /tmp/typst-${TYPST_ARCH}/typst /usr/local/bin/typst \
    && rm -rf /tmp/typst*

# Python deps into a prefix we can COPY into the final stage
WORKDIR /install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim

ARG PANDOC_VERSION=3.6.4
ARG TYPST_VERSION=0.14.2

LABEL org.opencontainers.image.title="branded-pdf-service" \
      org.opencontainers.image.description="Agentic Markdown-to-PDF rendering service with brand templates" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.source="https://github.com/tsayles/branded-pdf-service" \
      org.opencontainers.image.licenses="GPL-3.0-or-later" \
      org.opencontainers.image.authors="Tom Sayles"

RUN apt-get update && apt-get install -y --no-install-recommends \
    fontconfig \
    fonts-liberation \
    fonts-open-sans \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f

# Binaries from builder
COPY --from=builder /usr/local/bin/pandoc /usr/local/bin/pandoc
COPY --from=builder /usr/local/bin/typst  /usr/local/bin/typst

# Python packages from builder
COPY --from=builder /install/deps /usr/local

# Non-root user
RUN groupadd --gid 1001 pdfservice \
    && useradd --uid 1001 --gid pdfservice --shell /bin/bash --create-home pdfservice

WORKDIR /app
COPY app/ ./app/

RUN chown -R pdfservice:pdfservice /app
USER pdfservice

ENV BRANDS_DIR=/brands \
    PANDOC_PATH=/usr/local/bin/pandoc \
    TYPST_PATH=/usr/local/bin/typst \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
