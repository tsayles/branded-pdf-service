// WiseManOfTheInternet — Document Template
// ─────────────────────────────────────────────────────────────────────────────
// Prepended to Pandoc-generated Typst source by the md-to-pdf renderer.
// Place logo.png in this brand directory and uncomment the logo grid to
// enable the header logo.

// ── Colours ───────────────────────────────────────────────────────────────────
#let wmoti-indigo    = rgb("#2c3e7a")
#let wmoti-indigo-md = rgb("#3d52a0")
#let wmoti-indigo-lt = rgb("#eaedf7")
#let wmoti-amber     = rgb("#d97706")
#let wmoti-amber-lt  = rgb("#fef3c7")

// ── Page layout ───────────────────────────────────────────────────────────────
#set page(
  paper: "us-letter",
  margin: (top: 1.3in, bottom: 1.0in, left: 1.0in, right: 1.0in),
  header: [
    #block(
      fill: wmoti-indigo,
      inset: (x: 0.4em, y: 0.35em),
      width: 100%,
    )[
      // Uncomment once logo.png is added:
      // #grid(columns: (0.65in, 1fr), gutter: 8pt,
      //   align(center + horizon)[#image("logo.png", width: 0.55in)],
      //   align(left + horizon)[
      //     #text(font: "Liberation Serif", size: 12pt, weight: "bold",
      //           fill: white)[WiseManOfTheInternet]
      //   ],
      // )
      #text(
        font: "Liberation Serif",
        size: 12pt,
        weight: "bold",
        fill: white,
      )[WiseManOfTheInternet]
    ]
    #v(-0.3em)
    #line(length: 100%, stroke: 2.5pt + wmoti-amber)
  ],
  footer: [
    #line(length: 100%, stroke: 0.5pt + wmoti-indigo-lt)
    #v(2pt)
    #set text(size: 8pt, fill: wmoti-indigo)
    #align(center)[
      WiseManOfTheInternet #sym.bar.v
      Thoughtful writing for curious minds #sym.bar.v
      Page #context counter(page).display()
    ]
  ],
)

// ── Body text ─────────────────────────────────────────────────────────────────
#set text(font: "Liberation Sans", size: 10.5pt, fill: rgb("#1f2937"))
#set par(leading: 0.8em, spacing: 0.7em)

// ── Headings ──────────────────────────────────────────────────────────────────
#show heading.where(level: 1): it => {
  v(14pt)
  text(
    font: "Liberation Serif",
    size: 18pt,
    weight: "bold",
    fill: wmoti-indigo,
  )[#it.body]
  v(2pt)
  line(length: 100%, stroke: 1.5pt + wmoti-amber)
  v(4pt)
}

#show heading.where(level: 2): it => {
  v(10pt)
  text(
    font: "Liberation Serif",
    size: 13pt,
    weight: "bold",
    fill: wmoti-indigo,
  )[#it.body]
  v(2pt)
  line(length: 100%, stroke: 0.5pt + wmoti-indigo-lt)
  v(3pt)
}

#show heading.where(level: 3): it => {
  v(8pt)
  text(
    font: "Liberation Serif",
    size: 11pt,
    weight: "bold",
    fill: wmoti-indigo,
  )[#it.body]
  v(2pt)
}

// ── Blockquotes ───────────────────────────────────────────────────────────────
#show quote: it => {
  pad(left: 1em)[
    #block(
      fill: wmoti-amber-lt,
      stroke: (left: 3pt + wmoti-amber),
      inset: (left: 10pt, top: 6pt, bottom: 6pt, right: 6pt),
      radius: (right: 2pt),
    )[
      #text(fill: rgb("#78400a"), style: "italic")[#it.body]
    ]
  ]
}

// ── Tables ────────────────────────────────────────────────────────────────────
#set table(
  stroke: (col, row) =>
    if row == 0 { none } else { 0.5pt + wmoti-indigo-lt },
  inset: 6pt,
  fill: (col, row) =>
    if row == 0 { wmoti-indigo-md }
    else if calc.odd(row) { wmoti-indigo-lt }
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
  line(length: 100%, stroke: 0.8pt + wmoti-amber)
  v(4pt)
}
