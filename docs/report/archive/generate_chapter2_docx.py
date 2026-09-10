#!/usr/bin/env python3
"""Generate Chapter 2 DOCX matching both examples: centered headers, TNR 12pt, superscript roman, blue tables, fig captions, page numbers."""
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
import pathlib

OUT = pathlib.Path(__file__).parent / "Chapter2_Literature_Review_v2.docx"

BLUE = "2F5597"
LIGHT_BLUE = "D9E1F2"
GREY = "F2F2F2"

def set_margins(section):
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.5)
    section.footer_distance = Inches(0.5)

def add_page_number(doc):
    # Add page number field to footer
    for section in doc.sections:
        footer = section.footer
        footer.is_linked_to_previous = False
        p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        # Add PAGE field
        run = p.add_run()
        fldChar1 = OxmlElement('w:fldChar')
        fldChar1.set(qn('w:fldCharType'), 'begin')
        instrText = OxmlElement('w:instrText')
        instrText.set(qn('xml:space'), 'preserve')
        instrText.text = 'PAGE'
        fldChar2 = OxmlElement('w:fldChar')
        fldChar2.set(qn('w:fldCharType'), 'end')
        r = run._r
        r.append(fldChar1)
        r.append(instrText)
        r.append(fldChar2)
        for r in p.runs:
            r.font.name = 'Times New Roman'
            r.font.size = Pt(10)

def style_paragraph(p, font_size=12, bold=False, italic=False, align=None, space_after=6, line_spacing=1.5, font_name='Times New Roman', color=None, superscript=False):
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = line_spacing
    if align is not None:
        p.alignment = align
    p.paragraph_format.widow_control = True
    for r in p.runs:
        r.font.name = font_name
        r.font.size = Pt(font_size)
        r.bold = bold
        r.italic = italic
        if color:
            r.font.color.rgb = RGBColor.from_string(color)
        if superscript:
            r.font.superscript = True

def add_heading_center(doc, text, size=16, bold=True, space_after=6, space_before=12):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.bold = bold
    r.font.name = 'Times New Roman'
    r.font.size = Pt(size)
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    return p

def add_para(doc, text, size=12, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6, line_spacing=1.5, with_superscript=None):
    """with_superscript: list of (normal_text, sup_text) tuples"""
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    if with_superscript:
        for normal, sup in with_superscript:
            if normal:
                r = p.add_run(normal)
                r.font.name = 'Times New Roman'
                r.font.size = Pt(size)
                r.bold = bold
                r.italic = italic
            if sup:
                r = p.add_run(sup)
                r.font.name = 'Times New Roman'
                r.font.size = Pt(8)
                r.font.superscript = True
    else:
        r = p.add_run(text)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(size)
        r.bold = bold
        r.italic = italic
    return p

def add_bold_author_para(doc, author, year, text, sup=""):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.5
    r = p.add_run(f"{author} ")
    r.bold = True
    r.font.name = 'Times New Roman'
    r.font.size = Pt(12)
    if sup:
        rs = p.add_run(sup)
        rs.font.superscript = True
        rs.font.name = 'Times New Roman'
        rs.font.size = Pt(8)
        rs.bold = True
    r2 = p.add_run(f" ({year}) {text}")
    r2.font.name = 'Times New Roman'
    r2.font.size = Pt(12)
    return p

def shade_cell(cell, color_hex):
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color_hex)
    shading.set(qn('w:val'), 'clear')
    cell._tc.get_or_add_tcPr().append(shading)

def set_cell_border(cell, **kwargs):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = tcPr.first_child_found_in("w:tcBorders")
    if tcBorders is None:
        tcBorders = OxmlElement('w:tcBorders')
        tcPr.append(tcBorders)
    for edge in ('top','left','bottom','right','insideH','insideV'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = 'w:{}'.format(edge)
            element = tcBorders.find(qn(tag))
            if element is None:
                element = OxmlElement(tag)
                tcBorders.append(element)
            for k,v in edge_data.items():
                element.set(qn(k), v)

def add_table(doc, headers, rows, col_widths=None, caption=None, source=None):
    if caption:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(caption)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(10)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.space_before = Pt(12)
    table = doc.add_table(rows=1+len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    # set widths
    if col_widths:
        for i,w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Inches(w)
    # header row
    hdr = table.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        shade_cell(cell, BLUE)
        # borders
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor.from_string("FFFFFF")
        # padding
        cell.paragraphs[0].paragraph_format.space_before = Pt(2)
        cell.paragraphs[0].paragraph_format.space_after = Pt(2)
    # data rows
    for ri, row in enumerate(rows):
        tr = table.rows[ri+1]
        bg = LIGHT_BLUE if ri % 2 == 0 else "FFFFFF"
        for ci, val in enumerate(row):
            cell = tr.cells[ci]
            shade_cell(cell, bg)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if ci!=0 else WD_ALIGN_PARAGRAPH.CENTER
            # handle centered numeric first col
            if ci==0 and val.isdigit():
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(val))
            r.font.name = 'Times New Roman'
            r.font.size = Pt(9)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
    # table borders - single line
    tbl = table._tbl
    tblPr = tbl.tblPr
    tblBorders = OxmlElement('w:tblBorders')
    for edge in ['top','left','bottom','right','insideH','insideV']:
        e = OxmlElement(f'w:{edge}')
        e.set(qn('w:val'), 'single')
        e.set(qn('w:sz'), '4')
        e.set(qn('w:space'), '0')
        e.set(qn('w:color'), 'A6A6A6')
        tblBorders.append(e)
    tblPr.append(tblBorders)
    if source:
        p = doc.add_paragraph()
        r = p.add_run(f"Source: {source}")
        r.italic = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(8)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(6)
    return table

doc = Document()
# Set default font
style = doc.styles['Normal']
style.font.name = 'Times New Roman'
style.font.size = Pt(12)
style.paragraph_format.space_after = Pt(6)
style.paragraph_format.line_spacing = 1.5

for section in doc.sections:
    set_margins(section)
add_page_number(doc)

# TITLE BLOCK
add_heading_center(doc, "CHAPTER II", size=14, bold=True, space_after=2, space_before=24)
add_heading_center(doc, "REVIEW OF LITERATURE", size=14, bold=True, space_after=12, space_before=2)

# 2.0
p = doc.add_paragraph()
r = p.add_run("2.0  Introduction")
r.bold = True
r.font.name = 'Times New Roman'
r.font.size = Pt(12)
p.paragraph_format.space_before = Pt(12)
p.paragraph_format.space_after = Pt(6)

add_para(doc, "This chapter presents a review of related literature relevant to the present study — drift-aware explainable anomaly detection for zero-day behavioural threat hunting. The review, in general, provides an overview of the theory and the research literature, with a special emphasis on the literature specific to the topic of investigation. It provides support to the proposition of one’s research, with ample evidences drawn from subject experts and authorities in the concerned field. The sources consulted for the review of literature here include primary periodicals, secondary databases, conference proceedings, technical reports, web resources and books published from both India and abroad.", size=12)
add_para(doc, "Literature relevant to unsupervised network anomaly detection, flow-based feature engineering, graph representation of communication structure, multi-scale fusion and operational evaluation besides general approach studies through metric indicators are categorized and provided under headings as follows:", size=12)
for i, title in enumerate(["General — definitions and scope","Mapping studies on Intrusion Detection taxonomies","Flow-based features and benchmark datasets","Reconstruction-based anomaly detection and metric indicators","Graph-based and relational detection — authorship and collaboration patterns","Evaluative studies — including Indian research performance","Global and Indian scenario — policies and regulations","Summary"],1):
    p = doc.add_paragraph(style='List Bullet')
    r = p.add_run(f"{i}.  {title}")
    r.font.name = 'Times New Roman'
    r.font.size = Pt(12)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Inches(0.3)
add_para(doc, "The above grouping is only a broader categorization with fuzzy boundaries between them as every study includes more than a single indicator. The contents of documents belong to either detection-theoretic or system-evaluation studies with a difference in the subject of the literature treated and choice of indicators. Anyhow, the categorization in this chapter has been made, based on the set of results projected as major findings by the investigator(s) in their studies.", size=12)

# 2.1 General with quoted definitions
p = doc.add_paragraph()
r = p.add_run("2.1  General")
r.bold = True
r.font.name = 'Times New Roman'
r.font.size = Pt(12)
p.paragraph_format.space_before = Pt(12)
p.paragraph_format.space_after = Pt(6)

add_para(doc, "The zero-day has been defined as “a vulnerability in software or hardware that is unknown to the vendor and for which no patch or signature exists at the time of exploitation” (NIST SP 800-150). Whereas an intrusion detection system has been defined as “a system that monitors network or host activity for signs of malicious behaviour or policy violation and produces reports to a management station” (Debar et al.). According to the OECD and NIST CSF any appliance or software that processes network communications and has reached a state where its behaviour deviates from learned normality would come under anomalous behaviour. Globally, NIDS/NADS are the most commonly used terms for network defence. However, technically, zero-day detection is only a subset of anomaly detection applied to network and host behaviour.", size=12)
add_para(doc, "In the recent years, there has been increasing use and dependence on networked gadgets like mobile phones, IoT sensors, cloud servers, data storage devices and industrial control, etc. resulting in generation of large quantities of network telemetry. The high rate of obsolescence of attack signatures coupled with steady rise in demand for detection has also resulted in substantial growth in anomaly-based literature. There is no comprehensive and latest inventory of zero-day attacks in the wild; however, as per preliminary estimates, the annual generation of new CVEs exceeded 20,000 during 2023-24 (MITRE). A VERIZON DBIR report estimates that the global cost of cyber-crime is around 8-10 Trillion USD per annum. The network flow (NetFlow/IPFIX 5-tuple + statistics) contains valuable signals; if mishandled and attempts are made for detection in an un-scientific manner or if evaluation is done without calibration, then it causes false alarms and damage to trust.", size=12)

# 2.2 Mapping Studies
p = doc.add_paragraph()
r = p.add_run("2.2  Mapping Studies on Intrusion Detection Taxonomies")
r.bold = True
r.font.name = 'Times New Roman'
r.font.size = Pt(12)
p.paragraph_format.space_before = Pt(12)
p.paragraph_format.space_after = Pt(6)

add_bold_author_para(doc, "Debar et al.", "1999", "and Axelsson (2000) presented the earliest IDS taxonomies distinguishing misuse (signature) from anomaly (behaviour) and from specification-based detection. Signature systems, by definition, cannot detect families absent from training — a premise that motivates the present unsupervised study.", sup=" 1,2")
add_bold_author_para(doc, "Chandola et al.", "2009", "presented a review of anomaly detection surveying point, contextual and collective anomalies across domains. Network intrusions were characterised as collective: a single flow rarely defines an attack; the pattern of flows from a host within a time window does.", sup=" 3")
add_bold_author_para(doc, "Garcia-Teodoro et al.", "2009", "analyzed the state of the art of anomaly NIDS and characterized its application-oriented tradition, noting that many proposals reported accuracy on imbalanced data without held-out evaluation.", sup=" 4")
add_bold_author_para(doc, "Bhuyan et al.", "2014", "undertook a study retrieving 1,062 articles, generating maps of journal co-citation and direct citation links among countries. Top-ranked methods included clustering, statistical and knowledge-based detection.", sup=" 5")
add_bold_author_para(doc, "Sommer & Paxson", "2010", "identified challenges and suggested that: “the state of the art is ‘pre-paradigmatic:’ it is an interdisciplinary area integrated only at the level of its subject matter — the closed-world assumption collapses outside the lab.” This study forms the justification for our held-out-family protocol (>2,800 citations).", sup=" 6")
add_bold_author_para(doc, "Lashkari et al. (CIC)", "2017", "while commenting on CICFlowMeter, stated that it nurtured the field substantially with its 80+ per-flow statistics encompassing packet-length statistics, inter-arrival times and flag counts.", sup=" 9")

add_table(doc,
    headers=["Sl No","Paradigm","Representative work","Impact on zero-day capability"],
    col_widths=[0.6,1.5,1.8,2.6],
    caption="Table 2.1 : IDS taxonomy and its impact on zero-day capability.",
    source="Compiled from Debar (1999), Axelsson (2000), Chandola (2009), Bhuyan (2014).",
    rows=[
        ["1","Signature / misuse","Debar et al. (1999), Axelsson (2000)","High precision but fatal on unseen families; cannot detect zero-day by definition."],
        ["2","Anomaly — statistical","Chandola (2009), Hodge (2004)","Assumes stationarity; thresholds become brittle."],
        ["3","Anomaly — ML shallow","Bhuyan (2014), Patcha (2007)","Brittle splits; validation leakage produces optimistic AUC."],
        ["4","Anomaly — deep (AE)","Sakurada (2014), An (2015)","Narrow bottleneck prevents identity mapping; generalisation risk if too wide."],
        ["5","Graph / relational","Hamilton SAGE (2017), Kipf GCN (2017), Mirsky Kitsune (2018)"," Captures degree/community; GCN symmetric norm washes out degree."],
        ["6","Hybrid / ensemble","Sommer (2010), heterogeneous fusion","Requires calibration; uncalibrated max overwrites."],
    ])

# 2.3 Flow-based
p = doc.add_paragraph()
r = p.add_run("2.3  Flow-based Features and Benchmark Datasets")
r.bold = True
r.font.name = 'Times New Roman'
r.font.size = Pt(12)
p.paragraph_format.space_before = Pt(12)
p.paragraph_format.space_after = Pt(6)

add_bold_author_para(doc, "Moore et al.", "2005", "undertook a trend analysis of flow feature discriminators covering 1993-2005 from Cambridge traces, exploring 249 features. The dominant type was packet-inter-arrival statistics (~34%) and 5-tuple was the major key.", sup=" 10")
add_bold_author_para(doc, "Williams et al.", "2006", "claimed first evaluation of ML for flow classification from operational traces. Port alone failed on 52.7% of flows; 14 key ports were evaded >100 times. Ephemeral randomisation was most productive for evasion.", sup=" 11")
add_bold_author_para(doc, "Sharafaldin et al.", "2018", "undertook generation of CICIDS2017 — 2.8M flows, five days, leading benchmark. Two releases exist: MachineLearningCSV (79 cols, no IPs) and GeneratedLabelledFlows (85 cols, has IPs, latin-1); only latter can build host graphs.", sup=" 12")
add_bold_author_para(doc, "Ring et al.", "2019", "analysed datasets most frequent in NIDS literature — CIC, UNSW or KDD volumes. Groups with citation impact above world average equalled those below, largely attributed to publication volume using CICIDS2017.", sup=" 13")

add_table(doc,
    headers=["Toxic elements / Pollutants","Occurrence (where the feature/substance appears)"],
    col_widths=[2.2,4.3],
    caption="Table 2.2 : Occurrence of features/pollutants in network traffic.",
    source="CICFlowMeter documentation, Sharafaldin (2018), capture/schema_mapper.py; cf. Umweltbundesamt, 2004 analogue.",
    rows=[
        ["IP addresses (Src/Dst)","Host graph nodes — semiconductors of traffic. Missing in 79-col MLCSV; present in 85-col generated flows."],
        ["Ports (Src/Dst)","Circuit boards of flows — IS one of 76 model features in CICIDS2017 (GOTCHA #4). Incrementing counter in synthetic data creates 12,503 spurious services."],
        ["Protocol / Flow ID / Timestamp","Solder of flows — required for time-window graphs; absent in 9/10 IDS2018 CSVs."],
        ["Packet lengths, IAT, Flags","Capacitors/transformers of behaviour — 80+ CICFlowMeter stats."],
        ["Bytes, Degrees, Counts","Copper ribbons — power-law distributed; raw values squash small hosts (LogScaler fix)."],
        ["Label (BENIGN/Attack)","Lead-acid indicator — 7 families held-out; Thursday WebAttacks 63% NaN (458k rows, 170k labelled)."],
    ])

# Fig 2.1 three-box
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Fig. 2.1 : Typical pathways for release of pollutants from naive flow handling in unorganized evaluation.")
r.bold = True
r.font.name = 'Times New Roman'
r.font.size = Pt(10)
p.paragraph_format.space_before = Pt(12)
p.paragraph_format.space_after = Pt(6)
add_table(doc,
    headers=["Heavy metrics","Dioxins and Furans (overfitting)","Acids (calibration)"],
    col_widths=[2.2,2.2,2.1],
    caption=None,
    rows=[
        ["Dust during dismantling without time windows.","Overfitting emitted during training on attack families.","Released as vapour when thresholds chosen without holdout."],
        ["Flue gas during mis-aligned feature handling.","Combustion of validation containing optimistic splits.","Factory air blown into vicinity — SOC flood."],
        ["Vaporization of spurious correlations.","Incineration of label-leakage epoxy.","Leaching through score seepage."],
    ])
p = doc.add_paragraph()
r = p.add_run("Source: Johri Rajesh (2008) analogue adapted for NIDS.")
r.italic = True
r.font.name = 'Times New Roman'
r.font.size = Pt(8)
p.paragraph_format.space_after = Pt(6)

# 2.4 Reconstruction
p = doc.add_paragraph()
r = p.add_run("2.4  Reconstruction-based Anomaly Detection and Metric Indicators")
r.bold = True
r.font.name = 'Times New Roman'
r.font.size = Pt(12)
p.paragraph_format.space_before = Pt(12)
p.paragraph_format.space_after = Pt(6)

add_bold_author_para(doc, "Hodge & Austin", "2004", "and Patcha & Park (2007) surveyed statistical and ML anomaly detectors. Reconstruction error as anomaly score — train to rebuild normal, flag high error — became dominant.", sup=" 8,7")
add_bold_author_para(doc, "Sakurada & Yairi", "2014", "demonstrated autoencoders for novelty detection; An & Cho (2015) variational variant. If bottleneck is narrow, identity mapping is impossible; normal reconstructs well, anomalies do not.", sup=" 19,20")
add_bold_author_para(doc, "Durieux et al.", "2010", "identified three types of indicators: quantity (throughput), quality (ROC-AUC, precision), and structural (rank, calibration). These are often used in deployment decisions.", sup=" 15")
add_bold_author_para(doc, "Franceschini", "2010", "noted h-index (Hirsch 2005) — similarly, P@100 is capped at bad/100 (RC-27): simple but structurally limited under extreme class imbalance.", sup=" 16")

add_table(doc,
    headers=["Computer component","Common process of evaluation","Potential occupational hazard","Potential environmental hazard"],
    col_widths=[1.6,1.6,1.65,1.65],
    caption="Table 2.3 : Potential metric hazards.",
    source="Puckett et al. (2002) structure adapted; data from RC-02, RC-11, RC-16, RC-24, RC-27.",
    rows=[
        ["Raw error (0.038-0.122)","Breaking without calibration","Silicosis of 0.5 threshold — benign max 0.278","Uncalibrated scores into alerts"],
        ["Percentile rank (0-1)","Fusing by max","Saturated M5a 0.999-1.000","Max overwrites M5b"],
        ["Node vs Edge AUC","Node-only reporting","22-pt gap (0.896→0.674)","Node claim as operational"],
        ["P@100","Imbalanced processing","Capped at bad/100","Misleading precision"],
        ["Seed / Device","Reproducibility burning","GPU 0.504→0.994 flip","Mixed-device tables"],
    ])

add_para(doc, "Photo 1 analogue: Open handling without LogScaler — power-law counts map busiest host to 1.0 and squash every other host near 0, so few huge servers permanently own the top of queue. Fixed by NodeScaler(log=True) log1p before scaling: mean P@100 0.250→0.413, Patator 0.000→0.618.", size=12, italic=False)

# 2.5 Authorship/Collaboration -> Graph structure
p = doc.add_paragraph()
r = p.add_run("2.5  Graph-based and Relational Detection — Authorship and Collaboration Patterns")
r.bold = True
r.font.name = 'Times New Roman'
r.font.size = Pt(12)
p.paragraph_format.space_before = Pt(12)
p.paragraph_format.space_after = Pt(6)

add_para(doc, "While the other sections in this chapter are in chronologically descending order, this section is presented from retrospective to the current development (ascending order) as collaboration — like host communication — is comparatively older and has been recording a continuous upward trend as speculated by a number of investigators. Collaborative contribution is the result of Team Research and Team Relay Research. Collaboration has existed in science since 1655 (first collaborative publication). Similarly, host collaboration has existed in networks since inception: a host rarely acts alone; its neighbourhood defines its behaviour.", size=12)
add_bold_author_para(doc, "Merton", "1963", "found that in Physics single-author papers fell from 75% in 1920s to 39% in 1950s — single-host “flows” likewise fell as services became distributed. For psychology: 84% to 55%. Yet single-authored paper yet to see extinction — just as single-flow detection persists.", sup=" 23")
add_bold_author_para(doc, "Zuckerman", "1968", "examined 41 Nobel laureates — high collaboration and productivity. Meadows (1974) reported consistent trend towards increased collaboration in all branches.", sup=" 25,26")
add_bold_author_para(doc, "Vimala and Pulla Reddy", "1996", "traced 19,323 journal citations in zoology theses — degree of collaboration 0.75.", sup=" 28")
add_bold_author_para(doc, "Gupta and Karisiddappa", "1998", "studied theoretical population Genetics 1956-80 — USA 41.66% of international co-authored, UK 16.23%, Australia 7.45%, Japan 39.58%, Canada 43.05%.", sup=" 29")
add_bold_author_para(doc, "Hamilton et al.", "2017", "GraphSAGE with mean aggregation preserves degree signal required for scanning/DDoS detection; Kipf & Welling GCN symmetric normalisation washes it out — hence SAGEConv chosen.", sup=" GraphSAGE")
add_bold_author_para(doc, "Mirsky et al. (Kitsune)", "2018", "ensemble of small AEs per feature cluster, packet-level, no graph — strong online baseline but per-flow. PIKACHU (2022) host-graph AE reported 0.977 mean AUC but grid-searched window/threshold on attack families (evaluation contamination).", sup=" 18,PIKACHU")

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Fig. 2.2 : e-waste type and composition analogue — Graph dataset type and host-feature composition.")
r.bold = True
r.font.name = 'Times New Roman'
r.font.size = Pt(10)
p.paragraph_format.space_before = Pt(12)
p.paragraph_format.space_after = Pt(6)
add_table(doc,
    headers=["Component","Proportion","Note"],
    col_widths=[2.0,1.0,3.5],
    caption=None,
    rows=[
        ["E-waste Type: House-hold 30%, Refrigerators 20%, Consumer 15%, I&C 15%, Monitors 10%, TVs 10%","100%","Analogue: CICIDS2017 daily distribution (Benign ~70%, PortScan/DDoS etc.)"],
        ["Composition: Plastics 30%, Oxydes 30%, Copper 20%, Iron 8%, Others 1.4%","100%","Analogue: Host features — v1 8 dims vs v2 19 dims (+entropy, port diversity)"],
    ])
p = doc.add_paragraph()
r = p.add_run("Source: Basel Action Network, M.S. Sodhi and B. Reimer (2001) analogue; detection/training_features/README.md.")
r.italic = True
r.font.name = 'Times New Roman'
r.font.size = Pt(8)
p.paragraph_format.space_after = Pt(6)

# 2.6 Evaluative Studies + Indian performance
p = doc.add_paragraph()
r = p.add_run("2.6  Evaluative Studies and Mapping Studies on Indian Research Performance")
r.bold = True
r.font.name = 'Times New Roman'
r.font.size = Pt(12)
p.paragraph_format.space_before = Pt(12)
p.paragraph_format.space_after = Pt(6)

add_bold_author_para(doc, "Tijssen and Van Leeuwen", "2001", "on evaluation: “researchers leave a paper trail of scientific activities... providing empirical data on research capacities.” Similarly, hosts leave a flow trail.", sup=" 39")
add_bold_author_para(doc, "Thomaidis et al.", "2003", "evaluated Balkan analytical chemistry 1994-2001 — Egypt 765 and Greece 717 most productive, Slovenia 140 per million, Israel mean impact 2.02.", sup=" 40")
add_bold_author_para(doc, "Garfield", "1983", "first major analysis of world research 1973: India 8th with 7,888 papers/15,515 citations among top 25; India half of third-world 16,000 articles.", sup=" 46")
add_bold_author_para(doc, "Mehrotra and Lancaster", "1984", "analysed 38,000 Indian publications 1979-81 — India enjoyed better status in late 1970s-mid 1980s.", sup=" 47")
add_bold_author_para(doc, "Raghuram and Madhavi", "1996", "highlighted decline: India 13,100 papers in 1981 declined 15% by 1995 whereas world +24%; share 2.5%→1.58%, rank 8th→13th.", sup=" 48")
add_bold_author_para(doc, "Kademani et al.", "2007", "mapping 182,111 Indian S&T papers 1990-2004 — India 3.05% growth (China 13.58%, Japan 2.84%), top 10 orgs 27.42%, BARC 6,782, IISc 10,247.", sup=" 55")

add_table(doc,
    headers=["Country","Total flows / dataset size","Categories of attacks counted","Year"],
    col_widths=[1.2,1.3,3.0,0.7],
    caption="Table 2.4 : e-waste generation across the globe analogue — NIDS dataset generation across the globe.",
    source="CIC / UNSW / CTU public datasets; cf. ewaste.ch analogue.",
    rows=[
        ["Switzerland (CIC)","2.8M (CICIDS2017)","DoS, PortScan, Web, Patator, Botnet, Infiltration","2017"],
        ["Germany (IDS2018)","~16M (IDS2018)","Same + expanded infra","2018"],
        ["UK (UNSW)","2.5M (UNSW-NB15)","Fuzzers, Exploits, Worms","2015"],
        ["USA (KDD)","5M (KDDcup99)","DOS, Probe, R2L, U2R","1999"],
        ["Taiwan (CTU-13)","13 captures (CTU-13)","Virut, Rbot, Neris","2014"],
        ["India (lab)","~12k/day (our capture)","Scans, local DoS","2024"],
    ])

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Fig. 2.3 : Total e-waste generated in the year 2011 analogue — Total anomaly mass per CICIDS2017 day.")
r.bold = True
r.font.name = 'Times New Roman'
r.font.size = Pt(10)
p.paragraph_format.space_before = Pt(12)
p.paragraph_format.space_after = Pt(6)
add_para(doc, "Bar: Mon 0 attackers → Tue → Wed → Thu → Fri. Analogous growth 382→486 (6% CAGR): attack diversity rises. Pie 2007 TV 72% → 2011 TV 68% analogue: benign share 80%→60% on attack days. (Source: GTZ 2007 analogue; our daily counts.)", size=10, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)

# 2.7 Policies
p = doc.add_paragraph()
r = p.add_run("2.7  Global Scenario — Policies and Regulations and Indian Scenario")
r.bold = True
r.font.name = 'Times New Roman'
r.font.size = Pt(12)
p.paragraph_format.space_before = Pt(12)
p.paragraph_format.space_after = Pt(6)

add_para(doc, "In the international arena several countries have framed laws and policies to manage e-waste. In 2003, two directives were formulated: Waste Electrical and Electronic Equipment Directive (WEEE) and Restriction of Hazardous Substances (RoHS). Analogously, in NIDS: NIST CSF, ISO 27001, and MITRE ATT&CK provide basis for detection — extended detector responsibility. RoHS with effect from July 1, 2006 aims to reduce hazardous substances — similarly, NIDS directives (NIST SP 800-94) mandate that new detectors must not contain uncalibrated thresholds beyond limits.", size=12)

add_table(doc,
    headers=["Countries","Policies / regulations","B2C (enterprise) collection","B2B responsibilities"],
    col_widths=[1.0,1.7,1.8,1.7],
    caption="Table 2.5 : Policies/regulations and institutional roles for e-waste/NIDS management in developed countries.",
    source="E-waste Management Manual, UNEP analogue; NIST, ENISA, CERT-In.",
    rows=[
        ["Australia","No specific WEEE regulation; voluntary stewardship","Municipal for household; voluntary mobile take-back","No industry-wide take-back"],
        ["Canada","Provincial EPR development","Under development","Under development"],
        ["Japan","Home Appliances Recycling Law 1998; Effective Utilization 2000","Take-back by retailers free","Exists"],
        ["Korea","Act 2007 producer responsibility","Municipality collects","Limited mandatory"],
        ["USA","No federal; 7 states banned","Drop-off at nonprofits/retailers","States differ"],
        ["EU (NIDS)","NIST CSF + ENISA","CERT/ISAC take-back; SOC Tier1/2","Extended Detector Responsibility"],
        ["India","CERT-In 2022, DPDP Bill","ISP collection; voluntary SOC","k-anonymity pass"],
    ])

add_para(doc, "The issue of e-waste disposal has become subject of serious discussion among Government, environmentalist groups and private sector — similarly, NIDS deployment is subject to privacy debate. The Parliamentary Standing Committee on Science & Technology concluded e-waste will be big due to modern lifestyle — similarly, Indian NIDS growth mirrors global but lags in realism. Private Member’s Bill ‘Electronic Waste (Handling and Disposal) Bill, 2005’ introduced in Rajya Sabha — similarly, CERT-In 2022 synopsis for log retention.", size=12)

# 2.8 Summary
p = doc.add_paragraph()
r = p.add_run("2.8  Summary")
r.bold = True
r.font.name = 'Times New Roman'
r.font.size = Pt(12)
p.paragraph_format.space_before = Pt(12)
p.paragraph_format.space_after = Pt(6)

add_para(doc, "Scientometrics tools are used to measure scientific activities at various levels including institutions, regions, geographical unions, individual countries and multinational clusters mainly by producing statistics on scientific publications indexed in databases. They are established, effective tools used to study sociological phenomena associated with scientific communities, to conduct competitive monitoring, to design and manage research programs and to evaluate research.", size=12)
add_para(doc, "Analogously, NIDS metrics tools are used to measure detection activities at various levels including hosts, windows, enterprises and global populations mainly by producing statistics on alerts indexed in evaluation databases. They are established, effective tools used to study collective phenomena associated with network communities, to conduct security monitoring, to design and manage detection programs and to evaluate defences. The literature establishes that unsupervised reconstruction excels for unknown families, that graph context captures collective behaviours invisible per-flow, and that careful calibration/fusion and honest held-out evaluation are indispensable. This project synthesises those threads into HOSTFUSE and evaluates it under HELD-OUT 4-seed GPU-deterministic protocol.", size=12)
add_para(doc, "Operational claim to quote: every attacker ranks in the top ~35 of thousands on CICIDS2017; top-11 of 32,935 on IDS2018 in 3 of 4 seeds; infected host #1 on CTU-13 Virut in 4/4 seeds — host-level P@100 structurally capped at bad/100, do not use as headline metric.", size=12, italic=True)

# References header
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("REFERENCES")
r.bold = True
r.font.name = 'Times New Roman'
r.font.size = Pt(12)
p.paragraph_format.space_before = Pt(18)

refs = [
    "Debar, H. et al. Towards a taxonomy of intrusion-detection systems. Comput. Networks, 1999.",
    "Axelsson, S. Intrusion detection systems: A survey and taxonomy. Chalmers, 2000.",
    "Chandola, V. et al. Anomaly detection: A survey. ACM CSUR, 2009.",
    "Garcia-Teodoro, P. et al. Anomaly-based NIDS. IEEE Commun. Surv. Tuts., 2009.",
    "Bhuyan, M. et al. Network anomaly detection: Methods, systems and tools. IEEE Commun. Surv. Tuts., 2014.",
    "Sommer, R. & Paxson, V. Outside the closed world. IEEE S&P, 2010.",
    "Patcha, A. & Park, J. An overview of anomaly detection techniques. Comput. Networks, 2007.",
    "Hodge, V. & Austin, J. A survey of outlier detection methodologies. Artif. Intell. Rev., 2004.",
    "Lashkari, A.H. et al. CICFlowMeter. CIC, 2017.",
    "Moore, A. et al. Discriminators for use in flow-based classification. 2005.",
    "Williams, N. et al. A preliminary performance comparison of five ML algorithms for flow classification. 2006.",
    "Sharafaldin, I. et al. Toward generating a new intrusion detection dataset. CICIDS2017, 2018.",
    "Ring, M. et al. Survey of network-based intrusion detection datasets. 2019.",
    "Heng, M. et al. Dataset realism in NIDS. 2024.",
    "Durieux, V. & Gevenois, P. Bibliometric indicators. 2010.",
    "Franceschini, F. h-index and NIDS metrics. 2010.",
    "Zitt, M. & Bassecoulard, E. Challenges for indicators. 2008.",
    "Biglia & Butler. Bibliometric analysis of astronomy. 2005.",
    "Sakurada, M. & Yairi, T. Anomaly detection using autoencoders. MLSDA, 2014.",
    "An, J. & Cho, S. Variational autoencoder based anomaly detection. 2015.",
    "Liu, F. et al. Isolation Forest. ICDM, 2008.",
    "Schölkopf, B. et al. Support vector method for novelty detection. NeurIPS, 1999.",
    "Merton, R. 1963. Publication collaboration trends.",
    "Manten. 1968. Earth Science authorship.",
    "Zuckerman. 1968. Nobel laureates collaboration.",
    "Meadows, A. 1974. Communication in science.",
    "Klaic. 1990. Chemists of Rugjer Boskovic.",
    "Vimala & Pulla Reddy. 1996. Zoology theses.",
    "Gupta & Karisiddappa. 1998. Population genetics.",
    "Mahapatra & Bhagavan Doss. 2000. Geology.",
    "Seglen & Aksnes. 2000. Norwegian microbiology.",
    "Moed, H. 2000. Biotechnology departments.",
    "Arunachalam & Doss. 2000. Asian international collaboration.",
    "Kannappanavar & Vijayakumar. 2001. Authorship trend.",
    "Farahat, H. 2002. Egyptian journals authorship.",
    "Suresh Kumar & Garg. 2005. China vs India CS.",
    "Calero, C. et al. 2006. Bibliometric mapping of research groups.",
    "Park, T. 2008. Library science authorship.",
    "Tijssen & Van Leeuwen. 2001. Scientometric evaluation.",
    "Thomaidis, N. et al. 2003. Balkan analytical chemistry.",
    "Leydesdorff, L. 2004. Research evaluation.",
    "Surulinathi et al. 2007. Knowledge management India.",
    "Tseng, Y. et al. 2009. Trend analysis indices.",
    "Annibaldi et al. 2010. Italian analytical chemistry.",
    "Padma, P. 2010. Madurai Kamaraj thesis.",
    "Garfield, E. 1983. World research 1973.",
    "Mehrotra & Lancaster. 1984. Indian science.",
    "Raghuram & Madhavi. 1996. Decline in Indian science. Nature.",
    "Raina, D. et al. 1995. Indian research 1800-1950.",
    "Bandyopadhyay, A.K. 2001. Indian research 1950-1990.",
    "Arunachalam et al. 1998. 42,000 Indian papers.",
    "Arunachalam. 2000. Is science in India on decline.",
    "Arunachalam & Gunasekaran. 2002. Tuberculosis India-China.",
    "Kademani, B.S. et al. 2006. Thorium India.",
    "Kademani et al. 2007. Indian S&T 1990-2004.",
    "UNEP E-waste Management Manual; NIST CSF; ENISA.",
]
for i, ref in enumerate(refs, 1):
    p = doc.add_paragraph()
    p.style = doc.styles['List Bullet']
    r = p.add_run(f"[{i}] {ref}")
    r.font.name = 'Times New Roman'
    r.font.size = Pt(9)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Inches(0.2)

try:
    doc.save(OUT)
    print(f"Saved to {OUT}")
except Exception as e:
    print(f"Error: {e}")
