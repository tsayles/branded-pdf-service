// TrainTracking.us — Document Template
// ─────────────────────────────────────────────────────────────────────────────
// Prepended to Pandoc-generated Typst source by the md-to-pdf renderer.
// Place logo.png in this brand directory and uncomment the logo grid to
// enable the header logo.

// ── Colours ───────────────────────────────────────────────────────────────────
#let tt-rail     = rgb("#2d2d2d")
#let tt-rail-mid = rgb("#4a4a4a")
#let tt-rail-lt  = rgb("#f0f0f0")
#let tt-signal   = rgb("#c0392b")
#let tt-sig-lt   = rgb("#fdecea")

// ── Page layout ───────────────────────────────────────────────────────────────
#set page(
  paper: "us-letter",
  margin: (top: 1.3in, bottom: 1.0in, left: 1.0in, right: 1.0in),
  header: [
    #block(
      fill: tt-rail,
      inset: (x: 0.4em, y: 0.35em),
      width: 100%,
    )[
      // Uncomment once logo.png is added:
      // #grid(columns: (0.65in, 1fr), gutter: 8pt,
      //   align(center + horizon)[#image("logo.png", width: 0.55in)],
      //   align(left + horizon)[
      //     #text(font: "Liberation Serif", size: 12pt, weight: "bold",
      //           fill: white)[TrainTracking.us]
      //   ],
      // )
      #text(
        font: "Liberation Serif",
        size: 12pt,
        weight: "bold",
        fill: white,
      )[TrainTracking.us]
    ]
    #v(-0.3em)
    #line(length: 100%, stroke: 2.5pt + tt-signal)
  ],
  footer: [
    #line(length: 100%, stroke: 0.5pt + tt-rail-lt)
    #v(2pt)
    #set text(size: 8pt, fill: tt-rail-mid)
    #align(center)[
      TrainTracking.us #sym.bar.v
      Real-time railroad tracking and documentation #sym.bar.v
      Page #context counter(page).display()
    ]
  ],
)

// ── Body text ─────────────────────────────────────────────────────────────────
#set text(font: "Liberation Sans", size: 10.5pt, fill: rgb("#1a1a1a"))
#set par(leading: 0.75em, spacing: 0.65em)

// ── Headings ──────────────────────────────────────────────────────────────────
#show heading.where(level: 1): it => {
  v(14pt)
  text(
    font: "Liberation Serif",
    size: 18pt,
    weight: "bold",
    fill: tt-rail,
  )[#it.body]
  v(2pt)
  line(length: 100%, stroke: 1.5pt + tt-signal)
  v(4pt)
}

#show heading.where(level: 2): it => {
  v(10pt)
  text(
    font: "Liberation Serif",
    size: 13pt,
    weight: "bold",
    fill: tt-rail,
  )[#it.body]
  v(2pt)
  line(length: 100%, stroke: 0.5pt + tt-rail-lt)
  v(3pt)
}

#show heading.where(level: 3): it => {
  v(8pt)
  text(
    font: "Liberation Serif",
    size: 11pt,
    weight: "bold",
    fill: tt-rail,
  )[#it.body]
  v(2pt)
}

// ── Blockquotes ───────────────────────────────────────────────────────────────
#show quote: it => {
  pad(left: 1em)[
    #block(
      fill: tt-sig-lt,
      stroke: (left: 3pt + tt-signal),
      inset: (left: 10pt, top: 6pt, bottom: 6pt, right: 6pt),
      radius: (right: 2pt),
    )[
      #text(fill: rgb("#5c1a14"), style: "italic")[#it.body]
    ]
  ]
}

// ── Tables ────────────────────────────────────────────────────────────────────
#set table(
  stroke: (col, row) =>
    if row == 0 { none } else { 0.5pt + tt-rail-lt },
  inset: 6pt,
  fill: (col, row) =>
    if row == 0 { tt-rail-mid }
    else if calc.odd(row) { tt-rail-lt }
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
  line(length: 100%, stroke: 0.8pt + tt-signal)
  v(4pt)
}
