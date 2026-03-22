# md-to-pdf — Branded Markdown-to-PDF Service

A self-hosted Docker container that accepts plain Markdown and returns a
branded, print-ready PDF.  Replaces per-project PowerShell / Python build
scripts with a single reusable service.

## Rendering pipeline

```
Markdown  →  Pandoc 3.x (--to typst)  →  Typst body fragment
                                               ↓
                           Brand config (brand.typ template + meta.json)
                                               ↓
                            build_typst() — template + meta block + body
                                               ↓
                             typst compile  →  PDF section(s)
                                               ↓
                    reportlab (optional)  →  watermark PDF
                                               ↓
                     pypdf  →  stamp + assemble  →  final PDF
```

**Why Typst?**  A four-way bake-off (Pandoc/odfpy, Pandoc/Typst,
LibreOffice HTML import, LibreOffice headless) confirmed that Typst
delivers full brand fidelity — logo header, accent rules, styled
headings, blockquotes with fill, and dark-header tables — in a single
compile pass.  `typst compile` is a self-contained binary with no
runtime dependencies, making it significantly simpler to containerize
than the Chrome headless approach.

---

## Quick start

```bash
cd services/md-to-pdf
docker compose up -d

# Basic render test
curl -s -X POST http://localhost:8100/render \
  -H "Content-Type: application/json" \
  -d '{
        "brand": "greencrest-villa",
        "markdown": "# Hello World\n\nThis is a test document.",
        "meta": {
          "prepared_by": "Board of Directors",
          "date": "2026-03-22",
          "subject": "Test Document",
          "status": "DRAFT"
        },
        "watermark": "DRAFT"
      }' \
  -o output.pdf
```

---

## API Reference

### `GET /health`

Returns service health status and dependency versions.

**Response** `200 OK`

```json
{
  "status": "ok",
  "pandoc": "pandoc 3.6.4",
  "typst": "typst 0.13.1"
}
```

---

### `GET /brands`

Returns a sorted list of all available brand identifiers.

**Response** `200 OK`

```json
["greencrest-villa", "mike-and-key", "traintracking", "wiseman-of-the-internet"]
```

---

### `POST /render`

Render one or more Markdown sections to a single branded PDF.

**Request body** (`application/json`)

| Field       | Type               | Required | Description |
|-------------|--------------------|----------|-------------|
| `brand`     | `string`           | ✅        | Brand identifier (must exist in the brands volume). |
| `markdown`  | `string \| string[]` | ✅      | Markdown content. Provide a list for multi-section documents. |
| `meta`      | `object`           | —        | Optional document metadata. |
| `watermark` | `string`           | —        | Diagonal watermark text (e.g. `"DRAFT"`). |

**`meta` object**

| Field         | Type     | Description |
|---------------|----------|-------------|
| `prepared_by` | `string` | Author / originating body. |
| `date`        | `string` | Document date (ISO 8601 recommended). |
| `subject`     | `string` | Document subject / title. |
| `status`      | `string` | Status label (e.g. `DRAFT`, `FINAL`). |

**Example — single section**

```json
{
  "brand": "greencrest-villa",
  "markdown": "# Building Envelope Study\n\n## Executive Summary\n\n...",
  "meta": {
    "prepared_by": "Board of Directors",
    "date": "2026-03-22",
    "subject": "Building Envelope Study",
    "status": "DRAFT"
  },
  "watermark": "DRAFT"
}
```

**Example — multi-section document**

```json
{
  "brand": "mike-and-key",
  "markdown": [
    "# March Meeting Minutes\n\n## Call to Order\n\n...",
    "## Appendix A — Treasurer's Report\n\n..."
  ],
  "meta": {
    "prepared_by": "Club Secretary",
    "date": "2026-03-15",
    "subject": "March 2026 Meeting Minutes"
  }
}
```

**Response** `200 OK`

- `Content-Type: application/pdf`
- `Content-Disposition: attachment; filename="<subject>.pdf"`
- Body: raw PDF bytes

**Error responses**

| Status | Cause |
|--------|-------|
| `400`  | Unknown brand identifier or malformed request. |
| `500`  | Pandoc or Typst compilation failure. |

---

## Brand configuration

Each brand is a sub-directory under the brands volume.  The default
volume mount is `./brands` (relative to `services/md-to-pdf/`).

### Directory layout

```
brands/
└── <brand-id>/
    ├── meta.json   ← required
    ├── brand.typ   ← required  (Typst template)
    └── logo.png    ← optional  (placed alongside .typ at compile time)
```

### `meta.json`

```json
{
  "org_name":     "Full Organisation Name",
  "footer_text":  "Footer line printed at the bottom of every page",
  "default_font": "Liberation Sans",
  "heading_font": "Liberation Serif"
}
```

| Key            | Required | Description |
|----------------|----------|-------------|
| `org_name`     | ✅        | Displayed in the header band. |
| `footer_text`  | ✅        | Printed in the footer bar. |
| `default_font` | —        | Informational only. |
| `heading_font` | —        | Informational only. |

### `brand.typ`

A Typst source file that is **prepended** to the Pandoc-generated body.
It defines page layout, heading styles, table styles, blockquote styles,
and the `#horizontalrule` compatibility shim required by Pandoc.

The renderer assembles the final document as:

```
[brand.typ contents]

[meta block — injected from request meta fields]

[pandoc --to typst body]
```

#### Minimum viable template

```typst
#set page(paper: "us-letter", margin: 1in)
#set text(font: "Liberation Sans", size: 11pt)

// Required Pandoc compatibility shim
#let horizontalrule = line(length: 100%)
```

#### Adding a logo

1. Place `logo.png` in the brand directory alongside `brand.typ`.
2. The renderer copies it to the compile temp-dir automatically.
3. Uncomment (or add) an `#image("logo.png", ...)` call in the
   `header:` block of your `#set page(...)`.

Example header with logo:

```typst
#set page(
  header: [
    #grid(columns: (0.65in, 1fr), gutter: 8pt,
      align(center + horizon)[
        #image("logo.png", width: 0.55in)
      ],
      align(left + horizon)[
        #text(font: "Liberation Serif", size: 12pt,
              weight: "bold")[My Organisation]
      ],
    )
    #line(length: 100%, stroke: 1.5pt + rgb("#b8922a"))
  ],
)
```

#### Font notes

The container installs **Liberation Serif** and **Liberation Sans**
(`fonts-liberation`) and **Open Sans** (`fonts-open-sans`).  Use any
of these by name in your Typst template.  Typst searches the system
font directories — no additional configuration is required.

| Typst font name       | Equivalent to      | Package         |
|-----------------------|--------------------|-----------------|
| `"Liberation Serif"`  | Times New Roman    | fonts-liberation |
| `"Liberation Sans"`   | Arial              | fonts-liberation |
| `"Liberation Mono"`   | Courier New        | fonts-liberation |
| `"Open Sans"`         | Open Sans          | fonts-open-sans  |

---

## Included brands

| Brand ID                   | Organisation |
|----------------------------|--------------|
| `greencrest-villa`         | Greencrest Villa Owners Association |
| `mike-and-key`             | Mike & Key Amateur Radio Club |
| `wiseman-of-the-internet`  | WiseManOfTheInternet |
| `traintracking`            | TrainTracking.us |

### Adding a new brand

1. Create `brands/<brand-id>/` directory.
2. Add `meta.json` and `brand.typ`; optionally add `logo.png`.
3. The new brand is immediately available via `POST /render` — no
   restart required (brands are loaded on every request).

---

## Volume mount

The brands directory is mounted read-only at `/brands` inside the
container.  Override `BRANDS_DIR` if you prefer a different mount
point:

```yaml
volumes:
  - /path/to/your/brands:/data/brands:ro
environment:
  BRANDS_DIR: /data/brands
```

---

## Environment variables

| Variable      | Default                   | Description |
|---------------|---------------------------|-------------|
| `BRANDS_DIR`  | `/brands`                 | Path to the brands volume inside the container. |
| `PANDOC_PATH` | `/usr/local/bin/pandoc`   | Path to the Pandoc 3.x binary. |
| `TYPST_PATH`  | `/usr/local/bin/typst`    | Path to the Typst binary. |

---

## Development

```bash
# Install Python dependencies locally
pip install -r requirements.txt

# Run the service locally (requires Pandoc 3.x and Typst on PATH)
BRANDS_DIR=./brands uvicorn app.main:app --reload

# Interactive API docs
open http://localhost:8000/docs
```

### Installing Typst locally

```bash
# macOS
brew install typst

# Linux (manual)
curl -fsSL https://github.com/typst/typst/releases/latest/download/\
typst-x86_64-unknown-linux-musl.tar.xz | tar -xJ
sudo install typst-x86_64-unknown-linux-musl/typst /usr/local/bin/

# Windows
winget install Typst.Typst
```

### Installing Pandoc 3.x locally

Download the appropriate package from
<https://github.com/jgm/pandoc/releases>.
