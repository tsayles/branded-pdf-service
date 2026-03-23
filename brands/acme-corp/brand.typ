// brands/acme-corp/brand.typ
// ─────────────────────────────────────────────────────────────────────────────
// Acme Corporation — Reference Brand Template
// ─────────────────────────────────────────────────────────────────────────────
//
// This is the reference / demo brand template for branded-pdf-service.
// It demonstrates all supported template features:
//   • Page layout with header (logo + org name) and footer (text + page number)
//   • Colour palette using named colour variables
//   • Body text and paragraph settings
//   • Heading styles for H1, H2, H3
//   • Blockquote styling
//   • Table header + alternating row colours
//   • Horizontal rule shim (required by Pandoc's Typst output)
//
// Customising this template
// ─────────────────────────
// 1. Copy this directory to brands/<your-org>/
// 2. Edit meta.json with your organisation details
// 3. Replace logo.png with your organisation logo (400×120 px recommended)
// 4. Update the colour variables in the "Colours" section below
// 5. Adjust header text and footer text to match your branding
//
// Fonts
// ─────
// "Liberation Serif"  — headings  (bundled in the Docker image via fonts-liberation)
// "Liberation Sans"   — body text (bundled in the Docker image via fonts-liberation)
// Both fonts are metric-compatible substitutes for Times New Roman and Arial.
//
// Logo
// ────
// logo.png is read from the same directory as this .typ file at compile time.
// The renderer copies it into the Typst compile directory alongside the source.
// Remove or comment out the #image() call if you do not have a logo.

// ── Colours ───────────────────────────────────────────────────────────────────
#let acme-red      = rgb("#CC0000")
#let acme-red-dark = rgb("#990000")
#let acme-red-lt   = rgb("#FDECEA")
#let acme-black    = rgb("#111111")
#let acme-gray     = rgb("#F5F5F5")
#let acme-gray-mid = rgb("#CCCCCC")

// ── Page layout ───────────────────────────────────────────────────────────────
#set page(
  paper: "us-letter",
  margin: (top: 1.3in, bottom: 1.0in, left: 1.0in, right: 1.0in),
  header: [
    #block(
      fill: acme-black,
      inset: (x: 0.4em, y: 0.35em),
      width: 100%,
    )[
      #grid(
        columns: (0.65in, 1fr),
        gutter: 8pt,
        align(center + horizon)[#image("logo.png", width: 0.55in)],
        align(left + horizon)[
          #text(
            font: "Liberation Serif",
            size: 11pt,
            weight: "bold",
            fill: white,
          )[Acme Corporation]
        ],
      )
    ]
    #v(-0.3em)
    #line(length: 100%, stroke: 2.5pt + acme-red)
  ],
  footer: [
    #line(length: 100%, stroke: 0.5pt + acme-gray-mid)
    #v(2pt)
    #set text(size: 8pt, fill: acme-black)
    #align(center)[
      Acme Corporation #sym.bar.v
      A Company Making Everything #sym.bar.v
      Page #context counter(page).display()
    ]
  ],
)

// ── Body text ─────────────────────────────────────────────────────────────────
#set text(font: "Liberation Sans", size: 10.5pt, fill: acme-black)
#set par(leading: 0.75em, spacing: 0.65em)

// ── Headings ──────────────────────────────────────────────────────────────────
#show heading.where(level: 1): it => {
  v(14pt)
  text(
    font: "Liberation Serif",
    size: 18pt,
    weight: "bold",
    fill: acme-red,
  )[#it.body]
  v(2pt)
  line(length: 100%, stroke: 1.5pt + acme-red)
  v(4pt)
}

#show heading.where(level: 2): it => {
  v(10pt)
  text(
    font: "Liberation Serif",
    size: 13pt,
    weight: "bold",
    fill: acme-black,
  )[#it.body]
  v(2pt)
  line(length: 100%, stroke: 0.5pt + acme-gray-mid)
  v(3pt)
}

#show heading.where(level: 3): it => {
  v(8pt)
  text(
    font: "Liberation Serif",
    size: 11pt,
    weight: "bold",
    fill: acme-red-dark,
  )[#it.body]
  v(2pt)
}

// ── Blockquotes ───────────────────────────────────────────────────────────────
#show quote: it => {
  pad(left: 1em)[
    #block(
      fill: acme-red-lt,
      stroke: (left: 3pt + acme-red),
      inset: (left: 10pt, top: 6pt, bottom: 6pt, right: 6pt),
      radius: (right: 2pt),
    )[
      #text(fill: acme-black, style: "italic")[#it.body]
    ]
  ]
}

// ── Tables ────────────────────────────────────────────────────────────────────
#set table(
  stroke: (col, row) =>
    if row == 0 { none } else { 0.5pt + acme-gray-mid },
  inset: 6pt,
  fill: (col, row) =>
    if row == 0 { acme-black }
    else if calc.odd(row) { acme-gray }
    else { white },
)
#show table.cell.where(y: 0): set text(
  fill: white,
  weight: "bold",
  font: "Liberation Serif",
  size: 9pt,
)

// ── Horizontal rule (Pandoc compatibility shim) ───────────────────────────────
#let horizontalrule = {
  v(4pt)
  line(length: 100%, stroke: 0.8pt + acme-red)
  v(4pt)
}
