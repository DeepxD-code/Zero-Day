#!/usr/bin/env python3
"""Generate combined PDF preview via reportlab (for local viewing). Overleaf will produce authoritative LaTeX PDF."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, ListFlowable, ListItem
from reportlab.lib import colors
import pathlib

OUT = pathlib.Path(__file__).parent / "ZeroDay_FYP_Report.pdf"
BLUE = HexColor("#2F5597")
LIGHT = HexColor("#D9E1F2")

styles = getSampleStyleSheet()
title_style = ParagraphStyle('Title2', parent=styles['Title'], fontName='Times-Roman', fontSize=16, alignment=TA_CENTER, textColor=BLUE, spaceAfter=12, leading=18)
h1 = ParagraphStyle('H1', parent=styles['Heading1'], fontName='Times-Bold', fontSize=14, alignment=TA_CENTER, textColor=black, spaceBefore=14, spaceAfter=10, leading=16, keepWithNext=True)
h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontName='Times-Bold', fontSize=12, alignment=TA_LEFT, textColor=black, spaceBefore=10, spaceAfter=6, leading=14, keepWithNext=True)
h3 = ParagraphStyle('H3', parent=styles['Heading3'], fontName='Times-Bold', fontSize=11, alignment=TA_LEFT, textColor=black, spaceBefore=8, spaceAfter=4)
body = ParagraphStyle('Body', parent=styles['Normal'], fontName='Times-Roman', fontSize=10, alignment=TA_JUSTIFY, spaceAfter=6, leading=13)
small = ParagraphStyle('Small', parent=body, fontSize=8, alignment=TA_LEFT, leading=10, textColor=colors.grey)
center_bold = ParagraphStyle('CenterBold', parent=body, fontSize=10, alignment=TA_CENTER, fontName='Times-Bold', leading=12)
table_cell = ParagraphStyle('Cell', parent=body, fontSize=8, alignment=TA_LEFT, leading=10, spaceAfter=2)
table_header = ParagraphStyle('CellH', parent=table_cell, fontName='Times-Bold', alignment=TA_CENTER, textColor=white)
source_style = ParagraphStyle('Source', parent=body, fontSize=7, alignment=TA_LEFT, textColor=colors.grey, fontName='Times-Italic', spaceBefore=2)

def P(txt, style=body): return Paragraph(txt, style)
def header_row(vals):
    return [P(f"<font color='white'><b>{v}</b></font>", ParagraphStyle('h', parent=table_header)) if isinstance(v,str) else v for v in vals]

def make_table(headers, rows, col_widths, caption=None, source=None):
    elems=[]
    if caption:
        elems.append(P(f"<b>{caption}</b>", center_bold))
    # wrap headers and cells
    h = [P(f"<b>{x}</b>", table_header) for x in headers]
    data = [h]
    for r in rows:
        data.append([P(str(x), table_cell) for x in r])
    t = Table(data, colWidths=[w*inch for w in col_widths], repeatRows=1)
    style = [
        ('BACKGROUND', (0,0), (-1,0), BLUE),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('FONTNAME', (0,0), (-1,0), 'Times-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#A6A6A6")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]
    t.setStyle(TableStyle(style))
    elems.append(t)
    if source:
        elems.append(P(f"Source: {source}", source_style))
    elems.append(Spacer(1, 6))
    return elems

def build():
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, topMargin=0.8*inch, bottomMargin=0.8*inch, leftMargin=0.9*inch, rightMargin=0.9*inch,
                            title="Zero-Day FYP Report", author="Deep et al.")
    story=[]
    # Cover
    story.append(P("DRIFT-AWARE EXPLAINABLE ANOMALY DETECTION FOR BEHAVIOURAL THREAT HUNTING", title_style))
    story.append(P("Zero-Day Detection — HOSTFUSE & HELD-OUT", ParagraphStyle('sub', parent=body, alignment=TA_CENTER, fontSize=12, leading=14, spaceAfter=12)))
    story.append(P("A Project Report Submitted in Partial Fulfilment of the Requirements for<br/>Bachelor of Technology in Computer Science & Engineering", ParagraphStyle('cover', parent=body, alignment=TA_CENTER, leading=13)))
    story.append(Spacer(1, 18))
    story.append(P("Semester 7 — Final Year Project<br/>Chapters 1–5: Introduction, Literature Review, Methodology, Design & Modelling, Results", ParagraphStyle('cover2', parent=body, alignment=TA_CENTER, fontName='Times-Bold', leading=14)))
    story.append(Spacer(1, 18))
    story.append(P("Submitted by: Deep (B — Detection Modeling), Saharsh (A), Aditya (C), Avinash (D)<br/>Guide: Individual Guide (Presentation 10–15 September)<br/>Department of Computer Science & Engineering<br/>September 2026<br/><br/>GitHub: https://github.com/DeepxD-code/Zero-Day", ParagraphStyle('cover3', parent=body, alignment=TA_CENTER, leading=13)))
    story.append(PageBreak())
    # TOC placeholder
    story.append(P("TABLE OF CONTENTS", h1))
    story.append(P("Certificate ........................................................................  ii<br/>Declaration ..................................................................... iii<br/>Acknowledgements ............................................................ iv<br/>Abstract ........................................................................ v<br/>List of Tables ............................................................... vi<br/>List of Figures .............................................................. vii<br/>List of Abbreviations ....................................................... viii<br/>Chapter 1 Introduction ...................................................... 1<br/>Chapter 2 Review of Literature ............................................. 7<br/>Chapter 3 Methodology .................................................... 25<br/>Chapter 4 Design and Modelling ........................................... 37<br/>Chapter 5 Results, Discussion & Future Work .............................. 48<br/>References ................................................................ 51<br/>Appendices ............................................................... 54", body))
    story.append(PageBreak())

    # Abstract
    story.append(P("ABSTRACT", h1))
    story.append(P("We watch network traffic and learn what <i>normal</i> looks like, without ever training on attacks. When something behaves abnormally we raise an edge-level alert <font face='Courier' size=8>ScoredAlert[src_ip,dst_ip,score,rank]</font>, explain why (SHAP/ATT&amp;CK), and keep working even when the attack family has never been seen (zero-day premise). Flows (85-column CICIDS2017 GeneratedLabelledFlows, latin-1) are drawn as directed host graphs per 60s and 300s window. A GraphSAGE autoencoder (2×SAGEConv, hidden 32, latent 8) trained only on benign Monday learns to reconstruct normality; <font face='Courier'>NodeScaler(log=True)</font> log1p-before-min-max fixes power-law squash (P@100 0.250→0.413, Patator 0→0.618). Scores are percentile-calibrated against 20% Monday holdout and fused by within-window rank noisy-or 1−Π(1−p); edge scores use <font face='Courier'>rank_mean</font> (AUC 0.712→0.789). Evaluated under <b>HELD-OUT</b>: train benign Monday only, test each of 7 families held-out one-by-one, mean±std over 4 seeded GPU-deterministic runs. Production recipe GNN-logscale 60s+300s + revived 87-dim ctx M5a, rank noisy-or → <b>0.9996±0.0001</b> mean ROC-AUC (v2 19-dim: 0.9997±0.0001), every attacker in top ~35 of thousands (recall@100=1.0), replicated on IDS2018 (top-11/32,935) and CTU-13 Virut #1 in 4/4 seeds. Beats re-run baselines (PCA 0.9417, IF 0.9357, MLP-AE 0.9517, +4.8 pts). Evasion costs 20× time or 16 machines; camouflage fails.", body))
    story.append(P("<i>Keywords:</i> zero-day, NIDS, host graphs, GraphSAGE, autoencoder, HELD-OUT, calibration, noisy-or, LogScaler, SHAP, concept drift.", small))
    story.append(Spacer(1, 10))

    # Chapter 1
    story.append(P("CHAPTER 1 &nbsp;&nbsp; INTRODUCTION", h1))
    story.append(P("1.0 &nbsp; Introduction", h2))
    story.append(P("Zero-day attacks — exploits for vulnerabilities unknown to vendor or defender — drive the most consequential breaches. The zero-day has been defined as “a vulnerability in software or hardware that is unknown to the vendor and for which no patch or signature exists at the time of exploitation” (NIST SP 800-150). An intrusion detection system has been defined as “a system that monitors network or host activity for signs of malicious behaviour or policy violation and produces reports to a management station” (Debar et al., 1999). According to NIST CSF and MITRE ATT&amp;CK any host that deviates from learned normality would come under anomalous behaviour. Globally, NIDS/NADS are the most commonly used terms; technically, zero-day detection is only a subset of anomaly detection.", body))
    story.append(P("Signature-based NIDS cannot detect zero-days by definition; they match only known patterns. This project learns <i>normal</i> network behaviour unsupervised and flags deviations, explains why, monitors drift when “normal” itself shifts, and measures what evasion would cost an attacker. Three pillars are planned: network flows (P1 Sem 7), identity/UEBA (P2), and host syscalls via eBPF (P3 weeks 4–12). This report covers Sem 7 — P1 at production depth plus scaffolding for P2/3.", body))
    story.append(P("1.1 &nbsp; Background", h2))
    story.append(P("Enterprise networks generate millions of bidirectional flows. Each flow is one row: who talked to whom, which port, which protocol, how many bytes and packets, how long, and flag statistics — 80+ per-flow features per CICFlowMeter (Arash Habibi Lashkari, CIC). CICIDS2017 exists in two releases: the 79-column <font face='Courier'>MachineLearningCSV</font> (no IP columns) and the 85-column <font face='Courier'>GeneratedLabelledFlows</font> (has Flow ID, Source IP, Destination IP, Protocol, Timestamp — required for graphs, latin-1). Only the latter can build host graphs.", body))
    story.append(P("A scanner's single flows look benign — a TCP SYN to port 22 appears normal. Its <i>fan-out</i> across a 60-second window does not: one host contacting 200 distinct peers in 60 seconds is a rate that the graph makes visible. Similarly, DDoS many-to-one collapse and infiltration exfiltration show unusual byte-entropy. Relational features — degree, in/out ratio, port entropy, unique peer count, flag ratios — capture these collective patterns that per-flow views discard.", body))
    story.extend(make_table(["Fact (E-waste analogue)","Network analogue"], [["Annual e-waste India 0.8 Mt (2012), global 30–50 Mt","Annual CVEs >20k, alerts per enterprise 10k–100k/day"],["EEE contains valuables + hazardous toxics","Traffic contains benign signal + 1–8 attackers among thousands"],["Crude recovery releases dioxins","Crude evaluation leaks labels"],["WEEE: Plastics 30%, Oxydes 30%, Copper 20%","CICIDS2017: Benign 70%, PortScan 5%, DDoS 8%, Patator 1%"]], [3.2,3.2], caption="Table 1.1 : Background analogy — e-waste to network anomaly.", source="Umweltbundesamt (2004), MITRE, VERIZON DBIR."))
    story.append(P("1.1.1 &nbsp; Why Graphs?", h3))
    story.append(P("Per-flow detectors treat each flow independently. Graph detectors treat a 60s or 300s slice as a picture: each machine is a dot, each conversation a directed line. Degree and neighbourhood become first-class signals. GraphSAGE (Hamilton et al., 2017) is chosen over GCN (Kipf &amp; Welling, 2017) because GCN's symmetric normalisation washes out the degree signal. Time-based windows (not fixed-count) are essential: “200 peers in 60 seconds” is a rate. Edge-level alerts (src_ip, dst_ip) are required because the frozen <font face='Courier'>ScoredAlert</font> schema needs both endpoints.", body))
    story.append(P("1.2 &nbsp; Problem Statement", h2))
    story.append(P("1 &nbsp; <b>P1. Closed-world classifiers overstate zero-day performance.</b> Overlap families report 0.97+ AUC but collapse to 0.47 held-out (WebAttacks).<br/>2 &nbsp; <b>P2. Per-flow detectors are structurally blind.</b> M5a swings 0.42–0.98 while M5b never &lt;0.906.<br/>3 &nbsp; <b>P3. Power-law scaling squashes small attackers.</b> Patator/WebAttacks P@100 0.000 until LogScaler 0.618/0.381.<br/>4 &nbsp; <b>P4. Uncalibrated single-scale scores fuse incorrectly.</b> Raw vs rank meant 99.9% picks were M5b alone.", body))
    story.append(P("1.3 &nbsp; Objectives", h2))
    for o in ["Baseline-vs-graph ablation (M5a 87-dim vs M5b 8/19-dim GraphSAGE vs fusion M5c) — the individually attributable headline.","Multi-window calibrated fusion (60s+300s percentile + rank noisy-or 1−Π(1−p)).","Honest held-out protocol — benign Monday only, 7 families, 4-seed GPU-deterministic bands.","Drift-aware SHAP + ATT&amp;CK and adversarial harness (slow 20×, distributed 16×)."]:
        story.append(P(f"• &nbsp; {o}", body))
    story.append(P("1.4 &nbsp; Scope", h2))
    story.extend(make_table(["Member","Track","Owns"], [["A — Saharsh","Data & Capture","FlowRecord, pcap_to_flows, schema_mapper"],["B — Deep","Detection Modeling","M5a revived, GNN-temporal, drift, ensembler"],["C — Aditya","Trust & Risk","SHAP, UEBA, ATT&CK, privacy pass"],["D — Avinash","Adversarial & Delivery","Harness, FastAPI + React dashboard"]], [1.8,1.9,2.7], caption="Table 1.2 : Team mapping (CLAUDE.md)."))
    story.append(P("In scope (Sem 7): schema mapping, host-graph construction with health gates, v1/v2 features, LogScaler, GraphSAGE ensemble, multi-window rank fusion, edge-level alerts, 4-seed HELD-OUT, drift/SHAP scaffolding. Out of scope: full UEBA and eBPF host AE (weeks 4–12). Dataset gate: CICIDS2017 GeneratedLabelledFlows (85 cols, has IPs, latin-1). Synthetic training_data/ excluded — graphs collapse.", body))
    story.append(P("1.5 &nbsp; Methodology — Summary", h2))
    story.append(P("Flows → host graphs per time window (nodes=hosts, edges=directed, <font face='Courier'>graph_builder.py</font>) → GraphSAGE autoencoder trained benign-only (M5b, <font face='Courier'>gnn_model.py</font>, <font face='Courier'>NodeScaler</font> log1p) → multi-window rank noisy-or fusion (M5c) → edge-level <font face='Courier'>ScoredAlert</font> queue (<font face='Courier'>alert_pipeline.py</font>) with SHAP + drift (M6/M7). Evaluation: HELD-OUT, 7 families, 4 seeds.", body))
    story.append(P("1.6 &nbsp; Organisation of the Report", h2))
    story.append(P("Chapter 1 Introduction; Chapter 2 Review of Literature (10–15 Sep); Chapter 3 Methodology; Chapter 4 Design and Modelling; Chapter 5 Results, Discussion &amp; Future Work; References; Appendices (code, schemas, RC cards). Mirrors sample 1.8 DOCUMENTATION.", body))
    story.append(P("1.7 &nbsp; Expected Outcome", h2))
    story.extend(make_table(["Family","AUC (v2 fused)","Attacker ranks"], [["PortScan / DoS / DDoS","0.9999–1.0000","1–4"],["WebAttacks / Patator","1.0000","1–5"],["Infiltration","0.9997","2"],["Botnet","0.9987","5–34"]], [2.2,1.8,1.5], caption="Table 1.3 : Expected headline — week-4 freeze (GPU, CUDA-deterministic, 4 seeds).", source="eval_mw_ablation_4seed.py --seeds 0 1 2 3; eval_feature_set_v2.py"))
    story.append(P("Mean ROC-AUC 0.9996±0.0001 (v1) / 0.9997±0.0001 (v2) across 7 held-out families; every attacker in top ~35 of thousands on CICIDS2017, top-11/32,935 on IDS2018 (3/4 seeds), CTU-13 Virut #1 in 4/4 seeds; recall@100=1.0; evasion needs 20× time or 16 machines.", ParagraphStyle('ital', parent=body, fontName='Times-Italic')))

    # Chapter 2 summary (abbreviated but with key tables)
    story.append(P("CHAPTER 2 &nbsp;&nbsp; REVIEW OF LITERATURE", h1))
    story.append(P("2.0 &nbsp; Introduction", h2))
    story.append(P("This chapter reviews literature relevant to drift-aware explainable anomaly detection for zero-day threat hunting — theory and research with special emphasis on IDS, flow datasets, autoencoders, graphs, fusion, explainability/drift/adversarial, Indian/global performance and policies. Categorised into 8 headings (General through Summary) with fuzzy boundaries — grouped by major findings projected by investigators.", body))
    story.append(P("2.1 &nbsp; General", h2))
    story.append(P("Zero-day defined as “a vulnerability unknown to the vendor and for which no patch exists” (NIST SP 800-150). NIDS defined as “a system that monitors network or host activity for malicious behaviour” (Debar et al.). According to OECD/NIST CSF any host deviating from learned normality would be anomalous. Globally, NIDS/NADS are standard; zero-day detection is a subset of anomaly detection.", body))
    story.append(P("2.2 &nbsp; Mapping Studies on IDS Taxonomies", h2))
    story.append(P("<b>Debar et al. (1999)</b> and <b>Axelsson (2000)</b> misuse vs anomaly; <b>Chandola et al. (2009)</b> point/contextual/collective anomalies; <b>Garcia-Teodoro et al. (2009)</b> and <b>Bhuyan et al. (2014)</b> (1,062 articles) noted accuracy without held-out; <b>Sommer &amp; Paxson (2010)</b> “pre-paradigmatic — closed-world collapses outside the lab” (>2,800 citations) justifying HELD-OUT; <b>Lashkari et al. (CIC, 2017)</b> 80+ CICFlowMeter features.", body))
    story.extend(make_table(["Sl No","Paradigm","Representative work","Impact on zero-day"], [["1","Signature / misuse","Debar et al. (1999), Axelsson (2000)","High precision but fatal on unseen"],["2","Anomaly — statistical","Chandola (2009), Hodge (2004)","Assumes stationarity"],["3","Anomaly — ML shallow","Bhuyan (2014), Patcha (2007)","Leakage gives optimistic AUC"],["4","Anomaly — deep (AE)","Sakurada (2014), An (2015)","Narrow bottleneck prevents identity"],["5","Graph / relational","Hamilton SAGE (2017), Kipf GCN (2017)","Captures degree; GCN washes out"],["6","Hybrid / ensemble","Sommer (2010)","Requires calibration"]], [0.7,1.7,2.3,1.8], caption="Table 2.1 : IDS taxonomy and impact on zero-day capability.", source="Debar (1999), Axelsson (2000), Chandola (2009), Bhuyan (2014)."))
    story.append(P("2.3 &nbsp; Flow-based Features and Benchmark Datasets", h2))
    story.append(P("<b>Moore et al. (2005)</b> 249 discriminators Cambridge traces; <b>Williams et al. (2006)</b> port alone failed 52.7% (14 ports evaded >100×); <b>Sharafaldin et al. (2018)</b> CICIDS2017 2.8M flows two releases (79 no IPs vs 85 has IPs latin-1); <b>Ring et al. (2019)</b> survey CIC/UNSW/KDD; <b>Heng et al. (2024)</b> realism — synthetic benign active flaw.", body))
    story.extend(make_table(["Toxic elements / Pollutants","Occurrence (where feature appears)"], [["IP addresses (Src/Dst)","Host graph nodes — missing in 79-col; present in 85-col"],["Ports (Src/Dst)","IS one of 76 features; counter creates 12,503 spurious services"],["Protocol / Flow ID / Timestamp","Required for time-window graphs; absent in 9/10 IDS2018"],["Packet lengths, IAT, Flags","80+ CICFlowMeter stats"],["Bytes, Degrees, Counts","Power-law; raw squashes small hosts (LogScaler)"],["Label (BENIGN/Attack)","7 families held-out; Thu WebAttacks 63% NaN"]], [2.5,3.9], caption="Table 2.2 : Occurrence of features/pollutants in traffic.", source="CICFlowMeter, Sharafaldin (2018), capture/schema_mapper.py."))
    story.append(P("Fig. 2.1 analogue (three boxes Heavy metrics / Dioxins / Acids) and Photo 1 open burning of PCB at Aziz Sait illustrate uncalibrated handling and the LogScaler fix (P@100 0.250→0.413).", small))
    story.append(P("2.4 &nbsp; Reconstruction-based Anomaly Detection and Metric Indicators", h2))
    story.append(P("<b>Hodge &amp; Austin (2004)</b>, <b>Patcha &amp; Park (2007)</b> surveys; <b>Sakurada &amp; Yairi (2014)</b>, <b>An &amp; Cho (2015)</b> AEs; <b>Durieux et al. (2010)</b> quantity/quality/structural indicators; <b>Franceschini (2010)</b> h-index capped at bad/100; legacy DEFAULT_THRESHOLD 0.5 uncalibrated (benign max ~0.278).", body))
    story.extend(make_table(["Component","Common process","Occupational hazard","Environmental hazard"], [["Raw error (0.038–0.122)","Breaking w/o calibration","Silicosis of 0.5 threshold","Uncalibrated alerts"],["Percentile rank (0–1)","Fusing by max","Saturated M5a 0.999–1.000","Max overwrites M5b"],["Node vs Edge AUC","Node-only reporting","22-pt gap 0.896→0.674","Node claim as operational"],["P@100","Imbalanced processing","Capped at bad/100","Misleading precision"],["Seed / Device","Reproducibility burning","GPU 0.504→0.994 flip","Mixed-device tables"]], [1.6,1.6,1.6,1.6], caption="Table 2.3 : Potential metric hazards.", source="Puckett et al. (2002) adapted; RC-02, RC-11, RC-16, RC-24, RC-27."))
    story.append(P("2.5 &nbsp; Graph-based and Relational Detection — Collaboration Patterns", h2))
    story.append(P("Retrospective-to-current as collaboration shows upward trend (founded 1655). <b>Merton (1963)</b> single-author 75%→39% (psi 84%→55%); <b>Manten (1968), Zuckerman (1968), Meadows (1974), Klaic (1990), Vimala &amp; Pulla Reddy (1996) 19,323 citations 0.75, Gupta &amp; Karisiddappa (1998) USA 41.66%</b>, etc. Translated: per-flow = single-author, host graph = co-authored. <b>Hamilton SAGE (2017)</b> preserves degree vs <b>Kipf GCN (2017)</b>; <b>Mirsky Kitsune (2018)</b>, <b>PIKACHU (2022)</b> 0.977 but grid-searched on attacks.", body))
    story.extend(make_table(["Component","Proportion","Note"], [["E-waste Type: House-hold 30%, Refrigerators 20%, Consumer 15%, I&C 15%, Monitors 10%, TVs 10%","100%","Analogue: CICIDS2017 daily distribution"],["Composition: Plastics 30%, Oxydes 30%, Copper 20%, Iron 8%, Others 1.4%","100%","Analogue: Host features v1 8 vs v2 19"]], [3.2,1.0,2.2], caption="Fig. 2.2 : e-waste type/composition analogue — Graph dataset type and host-feature composition.", source="Basel Action Network, Sodhi & Reimer (2001) analogue."))
    story.append(P("2.6 &nbsp; Evaluative Studies and Indian Performance", h2))
    story.append(P("<b>Tijssen &amp; Van Leeuwen (2001)</b> paper trail; <b>Thomaidis et al. (2003)</b> Balkan; <b>Garfield (1983)</b> India 8th 7,888/15,515 among 353k; <b>Mehrotra &amp; Lancaster (1984)</b> 38k Indian pubs; <b>Raghuram &amp; Madhavi (1996)</b> India 13,100 −15% while world +24%; <b>Raina et al. (1995)</b> physics; <b>Kademani et al. (2007)</b> 182,111 S&amp;T papers India 3.05% growth.", body))
    story.extend(make_table(["Country","Total flows","Categories counted","Year"], [["Switzerland (CIC)","2.8M (CICIDS2017)","DoS, PortScan, Web, Patator, Botnet","2017"],["Germany (IDS2018)","~16M (IDS2018)","Same + expanded infra","2018"],["UK (UNSW)","2.5M (UNSW-NB15)","Fuzzers, Exploits, Worms","2015"],["USA (KDD)","5M (KDDcup99)","DOS, Probe, R2L, U2R","1999"],["Taiwan (CTU-13)","13 captures","Virut, Rbot, Neris","2014"]], [1.8,1.5,2.4,0.7], caption="Table 2.4 : e-waste generation analogue — NIDS dataset generation across globe.", source="CIC / UNSW / CTU public datasets."))
    story.append(P("2.7 &nbsp; Global and Indian Scenario — Policies and Regulations", h2))
    story.append(P("2003 WEEE and RoHS (Extended Producer Responsibility) analogously NIST CSF, ISO 27001, MITRE ATT&amp;CK — extended detector responsibility. RoHS July 1, 2006 bans lead/mercury etc.; similarly NIST SP 800-94 bans uncalibrated thresholds.", body))
    story.extend(make_table(["Countries","Policies / regulations","B2C (enterprise)","B2B responsibilities"], [["Australia","No WEEE; voluntary stewardship","Municipal household","No take-back"],["Canada","Provincial EPR","Under dev.","Under dev."],["Japan","Recycling Law 1998; Effective Utilization 2000","Take-back by retailers","Exists"],["Korea","Act 2007 producer responsibility","Municipality","Limited mandatory"],["USA","No federal; 7 states banned","Drop-off nonprofits","States differ"],["EU (NIDS)","NIST CSF + ENISA","CERT/ISAC; SOC Tier1/2","Extended Detector Resp."],["India","CERT-In 2022, DPDP Bill","ISP; voluntary SOC","k-anonymity pass"]], [1.3,1.9,1.8,1.5], caption="Table 2.5 : Policies/regulations and institutional roles.", source="UNEP E-waste Manual analogue; NIST, ENISA, CERT-In."))
    story.append(P("2.8 &nbsp; Summary", h2))
    story.append(P("Scientometrics tools measure scientific activities via publication databases; analogously, NIDS metrics tools measure detection via alert databases. Literature establishes unsupervised reconstruction excels for unknown families, graph context captures collective behaviours invisible per-flow, and careful calibration/fusion with honest held-out evaluation are indispensable. This project synthesises those into HOSTFUSE + HELD-OUT.", body))

    # Chapter 3 abbreviated
    story.append(P("CHAPTER 3 &nbsp;&nbsp; METHODOLOGY", h1))
    story.append(P("3.0 &nbsp; Introduction", h2))
    story.append(P("This chapter details data, graph construction, HostScaler, GraphSAGE AE, calibration, multi-window fusion, HELD-OUT protocol, metrics, reproducibility and tools. Every choice is a defended decision traceable to a gotcha or report card.", body))
    story.append(P("3.1 &nbsp; Datasets and Preprocessing", h2))
    story.append(P("Primary: CICIDS2017 GeneratedLabelledFlows (Mon benign → Fri 7 families, 85 cols latin-1, Thu WebAttacks 63% junk). Only latter builds graphs (GOTCHA #3). Never dropna(axis1) per-file — pin via pin_canonical (GOTCHA #5). Health gate rejects collapsed/degenerate synthetic data. External: IDS2018 only Thuesday, CTU-13, planned UNSW-NB15.", body))
    story.append(P("3.2 &nbsp; Host-Graph Construction", h2))
    story.append(P("Time-based 60s and 300s windows (rate vs volume; 60s maximises P@100; fuse both). Nodes=hosts, Edges=directed, SAGE over GCN. Node features v1 8 vs v2 19 (0–7 stable); edge_attr 4-dim scored via rank_mean lifts edge AUC 0.712→0.789. HostScaler(log=True) log1p before min-max default since 2026-08-12; mean P@100 0.250→0.413.", body))
    story.append(P("3.3 &nbsp; Models", h2))
    story.append(P("M5a revived MLP 87→64→32→16 (latent) trained benign only — not in production defaults. M5b GraphSAGE 2×SAGEConv N×8/19→N×32→N×8 latent (=in_dim, no bottleneck — capacity via features; latent 2→12 moves mean 0.003). Decoder MSE(node)+MSE(edge); score = ||x−x̂||²+λ·||a−â||². Determinism via set_seed() + CUBLAS :4096:8 (CPU 0.5048 vs GPU 0.9948).", body))
    story.append(P("3.4 &nbsp; Fusion and Scoring", h2))
    story.append(P("Per-window percentile vs 20% Monday holdout (80/20); ensemble emits percentiles not raw errors. Fusion: within-window rank noisy-or 1−Π(1−p) → 0.9996±0.0001 (production, edge rank_mean). score_window(feature_columns=None)=M5b-only 0.8322 edge AUC most consistent.", body))
    story.extend(make_table(["Rule","Formula","Property"], [["mean","(p60+p300)/2","Baseline"],["max","max(p60,p300,pM5a)","Lets saturated M5a overwrite"],["rank_mean","rank(pop)→mean","Lifts 0.712→0.789"],["fused_rank_max","rank positions","+0.0398 but batch-only"],["noisyor (prod)","1−Π(1−p)","0.9996±0.0001 best"]], [1.6,1.9,3.0], caption="Table 3.2 : Fusion rules evaluated (6 configs, 4 seeds)."))
    story.append(P("3.5 &nbsp; Drift, Explainability, Harness", h2))
    story.append(P("M6 drift_monitor.py on 3 streams via init_drift_monitors (queue noise is drift). M7 SHAP + ATT&amp;CK (never unpack positionally). Harness 4 techniques: port-hiding no, slow 20×, distributed 16, camouflage fail.", body))
    story.append(P("3.6 &nbsp; Evaluation Protocol (HELD-OUT)", h2))
    story.append(P("Train Monday benign only, test each of 7 families held-out one-by-one, mean±std over seeds 0–3 (eval_mw_ablation_4seed.py). Metrics: ROC-AUC primary, attacker rank &amp; recall@100 operational (top ~35, recall 1.0), P@100 diagnostic capped at bad/100. Node vs edge gap 22 pts. Closed negatives: LODO, k=5, temporal, small-window, latent width.", body))
    story.append(P("3.7 &nbsp; Tools and Environment", h2))
    story.append(P("Python 3.11, PyTorch 2.5.1+cu121, PyG; venv per-machine never portable; paths via Path(__file__).resolve().parent; data/ gitignored (CIC gates), *.pt tracked. One-command: python detection/eval_mw_ablation_4seed.py --seeds 0 1 2 3 --epochs 60 (GPU deterministic).", body))

    # Chapter 4
    story.append(P("CHAPTER 4 &nbsp;&nbsp; DESIGN AND MODELLING", h1))
    story.append(P("4.0 &nbsp; Introduction", h2))
    story.append(P("Architecture, component design, data flow and modelling choices implementing Chapter 3. Decisions defended: AE never classifier, SAGE over GCN, nodes=hosts/edges=directed, time-based windows, edge-level alerts, M5a lifted to host-window. Three pillars: network (P1 sem 7), UEBA (P2), eBPF syscalls (P3 weeks 4–12). Headline is baseline-vs-GNN ablation.", body))
    story.extend(make_table(["S.No.","Stage","Module","Input → Output"], [["1","Ingest — schema","capture/schema_mapper.py","CSV (79/85/IDS2018) → FlowRecord"],["2","Ingest — capture","pcap_to_flows / ebpf_syscall_watcher","pcap/eBPF → flows / syscalls"],["3","Build — graph","graph_builder.py","flows → List[Data] x=[N,8/19]"],["4","Scale","gnn_model:NodeScaler(log)","raw → log1p → min-max"],["5","Train — baseline","train_m5a_revived.py","87-dim → m5a_revived_ctx.pt"],["6","Train — GNN","gnn_model:GraphAutoencoder","benign → gnn_autoencoder_v1*.pt"],["7","Score — fuse","ensembler.py","60s+300s → percentiles → noisy-or"],["8","Serve — alerts","alert_pipeline.py","window → ScoredAlert"],["9","Evaluate","eval_mw_ablation_4seed.py","held-out → mean±std"],["10","Monitor","drift_monitor.py","3 streams → drift flag"],["11","Explain","shap_explainer.py","embedding → SHAP + ATT&CK"],["12","Adversarial","harness/graph_techniques","4 attacks → cost"]], [0.5,1.8,2.2,2.0], caption="Table 4.1 : System module map — stage, implementation and I/O.", source="detection/README.md, experiments/report_cards.md"))
    story.append(P("4.3 &nbsp; Modelling Details", h2))
    story.append(P("GraphAutoencoder 2×SAGEConv N×8/19→N×32→N×8 latent (=in_dim), ReLU, decoder MLPs, loss MSE(node)+MSE(edge). v1 8 vs v2 19 dims (adds entropy/port/flag/IAT); guard refuses v2 without checkpoint; 0–7 stable. Windows 60s+300s fused after percentile calibration; checkpoints must ship together (percentiles not raw).", body))
    story.append(P("4.4 &nbsp; Alert Pipeline and Dashboard", h2))
    story.append(P("ScoredAlert → alert_pipeline.score_window() → FastAPI GET /alerts + WebSocket → React dashboard (filters, SHAP drawer, drift banner). Run: run_detector.bat or powershell -ExecutionPolicy Bypass -File ./run_detector.ps1.", body))
    story.extend(make_table(["Claim","Number","Source"], [["CICIDS2017 v1","0.9996 ±0.0001","mw_ablation_4seed.json"],["CICIDS2017 v2","0.9997 ±0.0001","feature_set_v2_results.json"],["vs baselines","PCA 0.9417 / IF 0.9357 / MLP 0.9517","baselines_4seed.json"],["IDS2018 external","top-11/32,935 in 3/4 seeds","external_ids2018_multiseed"],["CTU-13 Virut","#1 in 4/4 seeds","external_ctu13_multiseed"],["CTU-13 Rbot","#1 in 3/4 seeds","same"]], [1.8,1.8,2.9], caption="Table 4.2 : Validation summary (GPU, CUDA-deterministic, 4 seeds, 2026-08-25)."))
    story.extend(make_table(["Component","Failure","Mitigation"], [["CSV ingest","latin-1 vs UTF-8, NaN IPs","read_flows()+drop_unusable_rows()"],["Scaling","power-law squash","NodeScaler(log=True)"],["Reproducibility","unseeded/GPU nondet","set_seed()+CUBLAS"],["Portability","hard-coded D:\\Test OD","Path(__file__).resolve().parent"],["Portability","venv absolute paths","Per-machine venv"]], [1.6,2.2,2.7], caption="Table 4.3 : Failure modes and mitigations."))
    story.extend(make_table(["Appendix","Content","Pointer"], [["A — Schemas","feature_vector.json v3.0 (87-dim), ScoredAlert","detection/training_features/README.md"],["B — Evidence","report_cards.md RC-01…RC-32","Detail behind CHANGELOG"],["C — Code","graph_builder, gnn_model, ensembler","detection/ prod"],["D — Supplementary","baselines, externals, ablation bands","PAPER_OUTLINE"]], [1.6,2.4,2.5], caption="Table 4.4 : Appendices mapping."))

    # Chapter 5
    story.append(P("CHAPTER 5 &nbsp;&nbsp; RESULTS, DISCUSSION AND FUTURE WORK", h1))
    story.append(P("5.1 &nbsp; Results — Headline (week-4 freeze)", h2))
    story.append(P("GNN-logscale 60s+300s + revived 87-dim ctx M5a, within-window rank noisy-or → <b>mean ROC-AUC 0.9996±0.0001</b> across 7 held-out families, beats pure rank_mean 0.9990±0.0003 in all seeds. With v2 (19 dims): <b>0.9997±0.0001</b>. Every attacker in top ~35; top-11/32,935 on IDS2018; Virut #1 in 4/4 seeds, Rbot #1 in 3/4. Baselines: PCA 0.9417, IF 0.9357, MLP-AE 0.9517 vs 0.9996 (+4.8 pts).", body))
    story.append(P("5.2 &nbsp; Discussion", h2))
    story.append(P("Operational claim is rank/recall, not P@100 (capped at bad/100). Node AUC describes model, edge AUC describes queue (gap 22 pts). Calibration optimism (20% Monday holdout) and device sensitivity (CPU vs GPU 0.50→0.99) are stated. Graph context captures collective behaviours invisible per-flow; LogScaler is single biggest win; SAGE preserves degree.", body))
    story.append(P("5.3 &nbsp; Limitations", h2))
    story.append(P("Noisy-or batch-only; both checkpoints must ship; single-lab benign day; drift monitor built but not auto-governing threshold; v2 default flip pending sign-off.", body))
    story.append(P("5.4 &nbsp; Future Work — Weeks 4–12 Roadmap", h2))
    story.append(P("Pillar 3 host-syscall AE via eBPF (capture/ebpf_syscall_watcher.py), AE-vs-HMM ablation, three-way fusion (network + UEBA + host). Third dataset replication (UNSW-NB15), drift-governed threshold, and paper packaging when results freeze (HOSTFUSE + HELD-OUT, one-command artifact).", body))

    # References
    story.append(P("REFERENCES", h1))
    refs=["Debar, H. et al. Towards a taxonomy of IDS. Comput. Networks, 1999.","Axelsson, S. IDS: A survey and taxonomy. Chalmers, 2000.","Chandola, V. et al. Anomaly detection: A survey. ACM CSUR, 2009.","Garcia-Teodoro, P. et al. Anomaly-based NIDS. IEEE Commun. Surv. Tuts., 2009.","Bhuyan, M. et al. Network anomaly detection. IEEE Commun. Surv. Tuts., 2014.","Sommer, R. & Paxson, V. Outside the closed world. IEEE S&P, 2010.","Patcha, A. & Park, J. An overview of anomaly detection. Comput. Networks, 2007.","Hodge, V. & Austin, J. A survey of outlier detection. Artif. Intell. Rev., 2004.","Lashkari, A.H. et al. CICFlowMeter. CIC, 2017.","Moore, A. et al. Discriminators for flow classification. 2005.","Williams, N. et al. Comparison of five ML algorithms. 2006.","Sharafaldin, I. et al. CICIDS2017. CIC, 2018.","Ring, M. et al. Survey of NIDS datasets. 2019.","Heng, M. et al. Dataset realism. 2024.","Durieux, V. & Gevenois, P. Bibliometric indicators. 2010.","Franceschini, F. h-index. 2010.","Zitt, M. & Bassecoulard, E. Challenges for indicators. 2008.","Biglia & Butler. Bibliometric analysis. 2005.","Sakurada, M. & Yairi, T. Anomaly detection using autoencoders. MLSDA, 2014.","An, J. & Cho, S. Variational autoencoder anomaly detection. 2015.","Liu, F. et al. Isolation Forest. ICDM, 2008.","Scholkopf, B. et al. Support vector novelty. NeurIPS, 1999.","Merton, R. 1963. Publication collaboration.","Manten. 1968. Earth Science authorship.","Zuckerman. 1968. Nobel laureates.","Meadows, A. 1974. Communication in science.","Klaic. 1990. Chemists of Rugjer Boskovic.","Vimala & Pulla Reddy. 1996. Zoology theses.","Gupta & Karisiddappa. 1998. Population genetics.","Mahapatra & Bhagavan Doss. 2000. Geology.","Seglen & Aksnes. 2000. Norwegian microbiology.","Moed, H. 2000. Biotechnology departments.","Arunachalam & Doss. 2000. Asian collaboration.","Kannappanavar & Vijayakumar. 2001. Authorship trend.","Farahat, H. 2002. Egyptian journals.","Suresh Kumar & Garg. 2005. China vs India CS.","Calero, C. et al. 2006. Bibliometric mapping.","Park, T. 2008. Library science authorship.","Tijssen & Van Leeuwen. 2001. Scientometric evaluation.","Thomaidis, N. et al. 2003. Balkan chemistry.","Leydesdorff, L. 2004. Research evaluation.","Surulinathi et al. 2007. Knowledge management India.","Tseng, Y. et al. 2009. Trend analysis.","Annibaldi et al. 2010. Italian analytical chemistry.","Padma, P. 2010. Madurai Kamaraj thesis.","Garfield, E. 1983. World research 1973.","Mehrotra & Lancaster. 1984. Indian science.","Raghuram & Madhavi. 1996. Decline in Indian science. Nature.","Raina, D. et al. 1995. Indian research 1800-1950.","Bandyopadhyay, A.K. 2001. Indian research 1950-1990.","Arunachalam et al. 1998. 42,000 Indian papers.","Arunachalam. 2000. Is science in India on decline.","Arunachalam & Gunasekaran. 2002. Tuberculosis.","Kademani, B.S. et al. 2006. Thorium India.","Kademani et al. 2007. Indian S&T 1990-2004.","UNEP E-waste Manual; NIST CSF; ENISA.","Hamilton, W. et al. GraphSAGE. NeurIPS, 2017.","Kipf, T. & Welling, M. GCN. ICLR, 2017.","Mirsky, Y. et al. Kitsune. NDSS, 2018.","Alsham et al. PIKACHU. 2022.","Lo, W. et al. E-GraphSAGE. TDSC, 2022.","Cavanaugh et al. Anomal-E. 2022.","Gama, J. et al. Concept drift. ACM CSUR, 2014.","Apruzzese et al. Real attackers don't compute gradients. USENIX, 2023.","Lundberg & Lee. SHAP. NeurIPS, 2017.","MITRE CVE; VERIZON DBIR; CIC IDS2018; UNSW-NB15; CTU-13."]
    for i,r in enumerate(refs,1):
        story.append(P(f"[{i}] &nbsp; {r}", ParagraphStyle(f'ref{i}', parent=small, leftIndent=14, firstLineIndent=-10, spaceAfter=2)))

    # Appendices
    story.append(P("APPENDICES", h1))
    story.append(P("Appendix A — Schemas & Feature Catalogue", h2))
    story.append(P("<font face='Courier'>schemas/feature_vector.json</font> v3.0: 76 → 87 dims (flow + ctx window). <font face='Courier'>ScoredAlert</font> fields: src_ip, dst_ip, score, rank, model_source. HostScaler params: log flag, min/max per dim.", body))
    story.append(P("Appendix B — Report Cards (RC-01…RC-32)", h2))
    story.append(P("See <font face='Courier'>experiments/report_cards.md</font> — one card per experiment with numbers, bands and caveats. RC-26 is reference ablation (<font face='Courier'>eval_mw_ablation_4seed.py</font>).", body))
    story.append(P("Appendix C — Code Listings", h2))
    story.append(P("<font face='Courier'>detection/graph_builder.py, gnn_model.py, ensembler.py, alert_pipeline.py, drift_monitor.py, shap_explainer.py, evaluate_gnn.py</font>. Nothing in prod imports <font face='Courier'>experiments/</font>.", body))
    story.append(P("Appendix D — Supplementary Tables", h2))
    story.append(P("Baselines 4-seed (RC-31), externals IDS2018/CTU-13 (RC-29/32), v2 ablation (RC-30), harness costs (RC-14). JSONs: <font face='Courier'>mw_ablation_4seed.json, baselines_4seed.json, external_ids2018_multiseed.json</font>.", body))

    doc.build(story)
    print(f"Saved to {OUT} size {OUT.stat().st_size}")

if __name__=="__main__":
    build()
