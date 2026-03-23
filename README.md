# branded-pdf-service

**A self-hosted, agent-friendly Markdown-to-PDF rendering service with pluggable brand templates.**

[![CI](https://github.com/tsayles/branded-pdf-service/actions/workflows/ci.yml/badge.svg)](https://github.com/tsayles/branded-pdf-service/actions/workflows/ci.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Docker Pulls](https://img.shields.io/docker/pulls/tsayles/branded-pdf-service)](https://hub.docker.com/r/tsayles/branded-pdf-service)

---

## Who this is for

**Primary users: AI agents and automation pipelines.**

This service is designed to be called by agentic workers -- Claude, GPT-based
agents, LangChain pipelines, CI/CD workflows -- that need to produce
branded, print-ready PDFs from Markdown without human involvement. Every
design decision optimizes for machine-friendly operation:

- Simple JSON request body -- no multipart forms, no file uploads for rendering
- Predictable error responses with HTTP status codes agents can branch on
- Bearer token auth -- one env var, one header, done
- MCP tool interface (roadmap) -- native tool discovery for MCP-compatible agents
- No browser, no GUI, no polling -- `POST /render` returns the PDF bytes directly

Human operators configure and maintain the service; agents are the primary
callers at runtime.

---

## Quick start

```bash
docker run -d \
  --name branded-pdf \
  -p 8100:8000 \
  -v ./brands/acme-corp:/brands/acme-corp:ro \
  ghcr.io/tsayles/branded-pdf-service:latest
```

Render a document:

```bash
curl -s -X POST http://localhost:8100/render \
  -H "Content-Type: application/json" \
  -d '{"brand":"acme-corp","markdown":"# Hello World\n\nThis is a test."}' \
  -o output.pdf
```

---

## API reference

### `GET /healthz`
Liveness probe. Returns Pandoc and Typst versions. No auth required.

**Response 200:**
```json
{
  "status": "ok",
  "pandoc": "pandoc 3.6.4",
  "typst": "typst 0.14.2"
}
```

---

### `GET /brands`
List all registered brand identifiers. No auth required.

**Response 200:** `["acme-corp", "my-brand"]`

---

### `POST /render`
Render Markdown to a branded PDF.

**Request body:**
```json
{
  "brand": "acme-corp",
  "markdown": "# Title\n\nBody text.",
  "meta": {
    "prepared_by": "Automated Agent",
    "date": "2026-01-15",
    "subject": "Quarterly Report",
    "status": "DRAFT"
  },
  "watermark": "DRAFT"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `brand` | string | yes | Brand identifier -- must match a sub-directory under `/brands` |
| `markdown` | string or array | yes | Markdown content. Array = multi-section document |
| `meta` | object | no | Document metadata rendered as a styled header block |
| `watermark` | string | no | Diagonal watermark stamped on every page (e.g. `"DRAFT"`) |

**Response 200:** `application/pdf` binary
**Response 400:** Unknown brand or invalid input
**Response 500:** Pandoc or Typst rendering failure

---

## Brand config format

Each brand is a directory under the `/brands` volume mount:

```
/brands/
  acme-corp/
    meta.json     <- organisation metadata
    brand.typ     <- Typst brand template
    logo.png      <- organisation logo (optional)
```

### `meta.json`

```json
{
  "org_name": "Acme Corporation",
  "footer_text": "Acme Corporation - A Company Making Everything",
  "default_font": "Liberation Sans",
  "heading_font": "Liberation Serif"
}
```

### `brand.typ`

The Typst template that defines page layout, colours, heading styles, and more.
See `brands/acme-corp/brand.typ` for the fully-commented reference implementation.

The template is prepended to the Pandoc-generated Typst body at render time.
It must define `#set page(...)` and all heading/paragraph show rules. It must
also define `#let horizontalrule = ...` (Pandoc compatibility shim).

### Fonts

The container ships with Liberation fonts:
- **Liberation Serif** approx Times New Roman (headings)
- **Liberation Sans** approx Arial (body text)
- **Liberation Mono** approx Courier New (code blocks)
- **Open Sans** (available as an alternative body font)

Custom fonts can be added by extending the Dockerfile or by mounting a fonts
directory and running `fc-cache`.

---

## Volume mount

Mount your brand configs at `/brands`:

```yaml
volumes:
  - ./my-brands:/brands:ro
```

Each sub-directory of `/brands` becomes an available brand identifier.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BRANDS_DIR` | `/brands` | Path to the brands volume inside the container |
| `PANDOC_PATH` | `/usr/local/bin/pandoc` | Pandoc binary path |
| `TYPST_PATH` | `/usr/local/bin/typst` | Typst binary path |
| `PYTHONUNBUFFERED` | `1` | Disable Python output buffering |

Authentication variables (`PDF_API_KEYS`) are added in v0.2.0 (Phase 5b).

---

## Docker Compose example

```yaml
services:
  branded-pdf:
    image: ghcr.io/tsayles/branded-pdf-service:latest
    container_name: branded-pdf
    restart: unless-stopped
    ports:
      - "8100:8000"
    volumes:
      - ./my-brands:/brands:ro
    environment:
      BRANDS_DIR: /brands
    security_opt:
      - no-new-privileges:true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
```

---

## Rendering pipeline

```
Markdown input
    |
    v
Pandoc 3.x  (--from markdown+smart --to typst)
    |  Typst body fragment
    v
Template injection  (brand.typ + meta block prepended)
    |  Complete .typ document
    v
typst compile  (static binary, single pass)
    |  PDF
    v
Optional: reportlab watermark -> pypdf stamp
    |
    v
PDF bytes returned in HTTP response
```

---

## Roadmap

| Version | Feature |
|---------|---------|
| v0.1.0 | Core rendering service (current) |
| v0.2.0 | Brand Management API -- runtime CRUD for brand configs |
| v0.2.0 | KISS Authentication -- Bearer token, agent-friendly |
| v0.2.0 | MCP Server -- native tool interface for MCP-compatible agents |

---

## License

[GPL-3.0-or-later](LICENSE) (C) 2026 Tom Sayles
