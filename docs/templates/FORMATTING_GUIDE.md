# Formatting Guide — Derived from Example PDF (pp. 21–33)

This guide distills the layout used in the e-waste reference document you provided (Table 2.5 p.21, Table 2.6 p.27, Table 2.7–2.8 p.28–29, Tables 2.9–2.10 p.30–31, Fig. 2.4 p.33). Apply it when exporting `docs/report/*.md` to PDF/DOCX.

## 1. Page Setup (matches example)

- **Paper:** A4, margins 1 inch (2.54 cm) all sides
- **Font:** Times New Roman throughout
  - Body: 12pt, justified, line spacing 1.5, paragraph spacing 6pt after, no first-line indent (blank line between paras as in example — or 0.5" indent if university requires; be consistent)
  - Footnotes / Source lines: 9–10pt italic
- **Page numbers:** bottom-right footer, plain Arabic, starting at Chapter I = 1 (example runs 21–33 continuous across chapters — use continuous numbering for whole report)
- **Headers:** none (example has no running header; chapter title only on first page of chapter)

## 2. Chapter & Section Headings

Example pattern:
```
            CHAPTER II              (centered, uppercase, bold, 14–16pt, 18pt before)
        REVIEW OF LITERATURE        (centered, uppercase, bold, 14pt)

2.0 Introduction                    (left, bold, 12pt, numbered)
2.8 Indian Scenario—Policies ...    (left, bold, 12pt)
2.11 e-waste Scenario in Bangalore  (left, bold, 12pt)
2.2.1 Feature Engineering           (left, bold-italic, 12pt)
```

Markdown mapping already uses this:
- `# CHAPTER I` → centered uppercase → add CSS `text-align:center; text-transform:uppercase`
- `## INTRODUCTION` → centered uppercase
- `### 2.0 Introduction` → left bold numbered
- `**2.2.1 Feature Engineering**` → bold sub-section

Keep numbering continuous: 1.0, 1.1 … 2.0, 2.1, 2.1.1, 3.0 … Never skip.

## 3. Body Text

- Justified (Word: Ctrl+J / LaTeX: default). Example has fully justified columns, ragged right not used.
- One blank line between paragraphs (or 6pt after). No extra indent if you use blank line — pick one style.
- Foreign terms, dataset names italicized sparingly (e.g., *CICIDS2017*); code identifiers in monospace `` `graph_builder.py` `` as now.

## 4. Tables — Exact Replication of Example

Panels p.21, 27–31 show one style:

**Caption — ABOVE table, centered, bold, 11–12pt:**
```
Table 2.5. Policies/regulations and institutional roles for e-waste management in developed countries.¹
Table 2.7. Top ten states generating e-waste in India.
Table 2.8. Top 10 cities in India generating e-waste.
Table 2.9. Availability of take-back services in India.
```
Format: `Table <chapter>.<serial>. <Title sentence case, period at end.>`

In markdown/HTML export use:
```html
<p style="text-align:center;"><strong>Table 2.1. Baseline comparison under identical features.</strong></p>
```

**Grid:** all cells with 0.5pt black border, header row shaded light grey (optional) and bold centered. First column = serial S.No. centered. Use `|:--:|` for centered S.No. Example table 2.7/2.8 has 3 cols (S.No. | State/City | WEEE ton); Table 2.5 has 4 cols; Table 2.9 has 2 cols; Table 2.10 has 3 cols header + grouped sub-header.

**Source line — BELOW table, left-aligned, italic, 9–10pt, 3pt spacing:**
```
Source: E-waste management in India—Consumers Voice (April 2009).
Source: E-waste Management Manual, UNEP.
Source: An assessment of e-waste take-back in India, www.designouttoxics.org.
```
With footnotes:
```
ᵃInformation regarding take-back in India is only available on global website.
ᵇTake-back service is only available for mobile phone.
ᶜTake-back service is only available for corporate customers.
```
In markdown:
```html
<p style="font-size:10pt;"><em>Source: eval_baselines_4seed.py (RC-31), GPU, 4 seeds.</em></p>
<p style="font-size:9pt;"><em>ᵃ...</em></p>
```

**Notes inside table:** superscript letters/numbers (example uses ᵃ ᵇ ᶜ and ¹ ³ ⁴). Keep footnotes immediately below Source line.

Reformatted in this repo:
- Ch2 Table 2.1 (baselines), Table 2.2 (harness), Table 2.3 (gaps)
- Ch4 Table 4.1 (module map)
All now carry S.No. column + centered caption + italic Source.

## 5. Figures

Example p.33:
```
[map image, centered, bordered]
         Fig. 2.4. Zones of Bangalore.      (centered, bold, 11pt, below image)
         Source: Maps of India.            (centered, italic, 9pt)
```
- Caption BELOW image, centered, bold: `Fig. <chapter>.<serial>. <Title.>`
- Source line below caption, italic.
- Refer in text as (Fig. 2.4) — parenthetical, italic Fig.

Ch2 ships Figs 2.1–2.2 as rendered PNGs in `docs/report/figures/` (generator: `figures/make_figures.py`); use the same block for architecture / ROC plots.

## 6. Citations & References

Example mixes two styles across the document:
- p.26–31 footnotes as superscript ³ ⁴ ¹² showing source of statement
- References list at end (this report uses IEEE numeric [1], [2] per `References.md`)

For FYP submission: follow university guide. Current `References.md` is already IEEE numeric — keep it. If guide mandates superscript footnotes, convert `[12]` → `¹²` and move full citation to footer; otherwise keep bracketed numeric and list at end. Either way, DOI where available, as in example p.21 footnote style would appear as:

> Source: E-waste Management Manual, UNEP.

## 7. Lists & Bullets

Example p.31:
```
The following categories … account for almost 90%:
• Large household appliances, 42%.
• Information and communications technology equipment, 33.9%.
• Consumer electronics, 13.7%.
```
- Bullet = • (or hyphen), 0.25" indent, 6pt between items, justified text.

## 8. Conversion to PDF/DOCX

**Option A — Pandoc (recommended, keeps markdown source):**
```powershell
pandoc docs/report/Chapter1_Introduction.md docs/report/Chapter2_Literature_Review.md docs/report/Chapter3_Methodology.md docs/report/Chapter4_Design_and_Modelling.md docs/report/References.md `
  -o docs/report/ZeroDay_Report.pdf `
  --pdf-engine=xelatex `
  -V mainfont="Times New Roman" -V fontsize=12pt -V geometry:margin=1in `
  -V linestretch=1.5 --citeproc
```
Add YAML header for page numbers: `header-includes: \usepackage{fancyhdr}\pagestyle{plain}`

**Option B — Word template:** create `template.docx` with Styles mapped above (Heading 1 = centered uppercase, Heading 2 = left bold 12pt, Table Caption = centered bold, Source = italic 9pt), then `pandoc -o report.docx --reference-doc=template.docx`.

**Option C — LaTeX:** use `report` class with `\usepackage{times, setspace}\doublespacing` and `\usepackage[margin=1in]{geometry}` — table captions via `\caption{}` above `tabular`.

## 9. Checklist Before Submission

- [ ] All tables have Table X.Y caption above + Source italic below (no orphan tables)
- [ ] All figures have Fig. X.Y caption below + Source italic below
- [ ] Page numbers bottom-right continuous
- [ ] Body justified, 12pt Times, 1.5 spacing
- [ ] Headings numbered consistently, no markdown `#` left unstyled in PDF
- [ ] References IEEE style, DOI included,hanging indent
- [ ] No absolute paths, no `venv/` committed (per CLAUDE.md gotchas)

---
*Guide created 2026-09-03 from example PDF pp.21–33; templates applied to Ch2 Tables 2.1–2.3 and Ch4 Table 4.1.*
