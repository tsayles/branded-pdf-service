// Greencrest Villa Owners Association — Document Template
// ─────────────────────────────────────────────────────────────────────────────
// This template is prepended to Pandoc-generated Typst source by the
// md-to-pdf renderer.
//
// Logo
// ----
// Place logo.png in this brand directory to enable the header logo.  The
// renderer copies it alongside the .typ source at compile time.  To use it
// uncomment the #image() line in the header block below.
//
// Fonts
// -----
// "Liberation Serif"  — headings  (ships with fonts-liberation on Linux)
// "Liberation Sans"   — body text (ships with fonts-liberation on Linux)
// Google Fonts variants (Georgia / Open Sans) work fine on a machine that
// has them installed; the renderer falls back to Liberation equivalents.

// ── Colours ───────────────────────────────────────────────────────────────────
#let gcv-green-dark = rgb("#1e4326")
#let gcv-green-mid  = rgb("#2a5c34")
#let gcv-green-lt   = rgb("#e8f2ea")
#let gcv-gold       = rgb("#b8922a")
#let gcv-gold-lt    = rgb("#f5e9d0")

// ── Page layout ───────────────────────────────────────────────────────────────
#set page(
  paper: "us-letter",
  margin: (top: 1.3in, bottom: 1.0in, left: 1.0in, right: 1.0in),
  header: [
    #block(
      fill: gcv-green-dark,
      inset: (x: 0.4em, y: 0.35em),
      width: 100%,
    )[
      // Uncomment and adjust the grid below once logo.png is added:
      // #grid(columns: (0.65in, 1fr), gutter: 8pt,
      //   align(center + horizon)[#image("logo.png", width: 0.55in)],
      //   align(left + horizon)[
      //     #text(font: "Liberation Serif", size: 12pt, weight: "bold",
      //           fill: white)[Greencrest Villa Owners Association]
      //   ],
      // )
      #text(
        font: "Liberation Serif",
        size: 12pt,
        weight: "bold",
        fill: white,
      )[Greencrest Villa Owners Association]
    ]
    #v(-0.3em)
    #line(length: 100%, stroke: 2.5pt + gcv-gold)
  ],
  footer: [
    #line(length: 100%, stroke: 0.5pt + gcv-green-lt)
    #v(2pt)
    #set text(size: 8pt, fill: gcv-green-dark)
    #align(center)[
      Greencrest Villa Owners Association #sym.bar.v
      Confidential Board Document #sym.bar.v
      Page #context counter(page).display()
    ]
  ],
)

// ── Body text ─────────────────────────────────────────────────────────────────
#set text(font: "Liberation Sans", size: 10.5pt, fill: rgb("#222222"))
#set par(leading: 0.75em, spacing: 0.65em)

// ── Headings ──────────────────────────────────────────────────────────────────
#show heading.where(level: 1): it => {
  v(14pt)
  text(
    font: "Liberation Serif",
    size: 18pt,
    weight: "bold",
    fill: gcv-green-mid,
  )[#it.body]
  v(2pt)
  line(length: 100%, stroke: 1.5pt + gcv-gold)
  v(4pt)
}

#show heading.where(level: 2): it => {
  v(10pt)
  text(
    font: "Liberation Serif",
    size: 13pt,
    weight: "bold",
    fill: gcv-green-mid,
  )[#it.body]
  v(2pt)
  line(length: 100%, stroke: 0.5pt + gcv-green-lt)
  v(3pt)
}

#show heading.where(level: 3): it => {
  v(8pt)
  text(
    font: "Liberation Serif",
    size: 11pt,
    weight: "bold",
    fill: gcv-green-mid,
  )[#it.body]
  v(2pt)
}

// ── Blockquotes ───────────────────────────────────────────────────────────────
#show quote: it => {
  pad(left: 1em)[
    #block(
      fill: gcv-gold-lt,
      stroke: (left: 3pt + gcv-gold),
      inset: (left: 10pt, top: 6pt, bottom: 6pt, right: 6pt),
      radius: (right: 2pt),
    )[
      #text(fill: rgb("#554422"), style: "italic")[#it.body]
    ]
  ]
}

// ── Tables ────────────────────────────────────────────────────────────────────
#set table(
  stroke: (col, row) =>
    if row == 0 { none } else { 0.5pt + gcv-green-lt },
  inset: 6pt,
  fill: (col, row) =>
    if row == 0 { gcv-green-mid }
    else if calc.odd(row) { gcv-green-lt }
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
  line(length: 100%, stroke: 0.8pt + gcv-gold)
  v(4pt)
}
