# Tests

## Directory layout

```
tests/
├── sample-data/          Markdown source files used for manual & smoke tests
├── sample-results/       Generated PDFs (gitignored; see .gitignore in that dir)
├── smoke_test.py         Integration smoke tests (requires a running container)
└── test_brand_loader.py  Unit tests for brand loading logic
```

## Running unit tests

No container required.

```bash
pip install -r requirements.txt
pip install pytest requests
pytest tests/test_brand_loader.py -v
```

## Running integration smoke tests

Requires the service to be running (default port 8000 inside Docker, mapped
as you prefer outside).

```bash
docker compose up -d --build
pytest tests/smoke_test.py -v
docker compose down
```

---

## Preferred smoke-test method

The canonical manual smoke test is to render the ACME anvil order confirmation
and verify the result is substantially similar to the committed reference PDF.

**Input:**
```
tests/sample-data/acme-anvil-order-WEC-2026-0042.md
```

**Reference output:**
```
tests/sample-results/acme-anvil-order-WEC-2026-0042.pdf
```
_(Reference PDF is gitignored and not committed; regenerate it as described
below and compare visually or by file size in the same ballpark as the
original ~130–150 KB result.)_

### How to regenerate the reference PDF

With the service running at `http://localhost:8100` (adjust port as needed):

```bash
curl -s http://localhost:8100/brands
# should include "acme-corp"

curl -X POST http://localhost:8100/render \
  -H "Content-Type: application/json" \
  -d "{\"brand\":\"acme-corp\",
       \"title\":\"Order Confirmation WEC-2026-0042\",
       \"markdown\":$(jq -Rs . \
           < tests/sample-data/acme-anvil-order-WEC-2026-0042.md)}" \
  -o tests/sample-results/acme-anvil-order-WEC-2026-0042.pdf

echo "Exit: $?  Size: $(wc -c \
    < tests/sample-results/acme-anvil-order-WEC-2026-0042.pdf) bytes"
```

### What "substantially similar" means

| Check | Expected |
|-------|----------|
| HTTP status | `200 OK` |
| `Content-Type` | `application/pdf` |
| First 4 bytes | `%PDF` |
| File size | 100 KB – 200 KB |
| Visual inspection | ACME logo, red headings, order table, spec table, footer |

A ±20 % size variation from the reference is acceptable (font hinting and
Typst version can affect PDF size). A blank page, missing tables, or a Typst
compile error are failure conditions.

### Why this test is valuable

The anvil order exercises every feature of the pipeline:
- Multi-section tables (order summary + spec table)
- Bullet lists (accessories, certifications)
- Blockquotes (safety warnings)
- Unicode characters (`×`, `·`, `™`, `±`, `°F`, `–`)
- Long-form prose paragraphs
- Bold and italic inline markup
- Document footer with ACME Corp branding

A passing render on this document provides high confidence the full
Pandoc → Typst → PDF pipeline is healthy.
