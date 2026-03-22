# ──────────────────────────────────────────────────────────────────────────────
# md-to-pdf — Branded Markdown-to-PDF rendering service
#
# Build:   docker build -t md-to-pdf .
# Run:     docker compose up -d
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Pandoc 3.x is required for --to typst output support.
# Typst is a self-contained binary — no runtime dependencies.
ARG PANDOC_VERSION=3.6.4
ARG TYPST_VERSION=0.13.1

# ── System dependencies ───────────────────────────────────────────────────────
# curl / xz-utils  — download and unpack Pandoc .deb and Typst archive
# fontconfig       — font discovery for Typst
# fonts-liberation — Liberation Serif / Sans / Mono (Times/Arial/Courier equiv)
# fonts-open-sans  — Open Sans body font
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    xz-utils \
    fontconfig \
    fonts-liberation \
    fonts-open-sans \
    && rm -rf /var/lib/apt/lists/*

# ── Pandoc 3.x ────────────────────────────────────────────────────────────────
RUN curl -fsSL \
    "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-1-amd64.deb" \
    -o /tmp/pandoc.deb \
    && dpkg -i /tmp/pandoc.deb \
    && rm /tmp/pandoc.deb

# ── Typst ─────────────────────────────────────────────────────────────────────
RUN curl -fsSL \
    "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-x86_64-unknown-linux-musl.tar.xz" \
    -o /tmp/typst.tar.xz \
    && tar -xJf /tmp/typst.tar.xz -C /tmp \
    && install -m 755 \
       /tmp/typst-x86_64-unknown-linux-musl/typst \
       /usr/local/bin/typst \
    && rm -rf /tmp/typst*

# Refresh the system font cache so Typst can discover installed fonts.
RUN fc-cache -f

# ── Python dependencies ───────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY app/ ./app/

# ── Runtime configuration ─────────────────────────────────────────────────────
# Brands volume is expected to be mounted at /brands at runtime.
# Override PANDOC_PATH / TYPST_PATH if the binary locations differ.
ENV BRANDS_DIR=/brands \
    PANDOC_PATH=/usr/local/bin/pandoc \
    TYPST_PATH=/usr/local/bin/typst \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# ── Entry point ───────────────────────────────────────────────────────────────
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
