#!/usr/bin/env python3
"""Generate DOCX for Chapters 1,3,4 + References + combined all-chapters, same style as Ch2."""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
import pathlib

BLUE = "2F5597"
LIGHT_BLUE = "D9E1F2"
OUTDIR = pathlib.Path(__file__).parent

def base_doc():
    doc = Document()
    s = doc.styles['Normal']
    s.font.name = 'Times New Roman'
    s.font.size = Pt(12)
    s.paragraph_format.space_after = Pt(6)
    s.paragraph_format.line_spacing = 1.5
    for sec in doc.sections:
        sec.top_margin = Inches(1); sec.bottom_margin = Inches(1)
        sec.left_margin = Inches(1); sec.right_margin = Inches(1)
        sec.header_distance = Inches(0.5); sec.footer_distance = Inches(0.5)
    # page number
    for sec in doc.sections:
        f = sec.footer; f.is_linked_to_previous=False
        p = f.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = p.add_run()
        a=OxmlElement('w:fldChar'); a.set(qn('w:fldCharType'),'begin')
        b=OxmlElement('w:instrText'); b.set(qn('xml:space'),'preserve'); b.text='PAGE'
        c=OxmlElement('w:fldChar'); c.set(qn('w:fldCharType'),'end')
        r2=r._r; r2.append(a); r2.append(b); r2.append(c)
        for run in p.runs: run.font.name='Times New Roman'; run.font.size=Pt(10)
    return doc

def chap(doc, num, title):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(f"CHAPTER {num}"); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(14)
    p.paragraph_format.space_before=Pt(24); p.paragraph_format.space_after=Pt(2)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(title); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(14)
    p.paragraph_format.space_after=Pt(12)

def sec(doc, txt):
    p=doc.add_paragraph(); r=p.add_run(txt); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(12)
    p.paragraph_format.space_before=Pt(12); p.paragraph_format.space_after=Pt(6)

def para(doc, txt, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=12, sup=False):
    p=doc.add_paragraph(); p.alignment=align; p.paragraph_format.space_after=Pt(6); p.paragraph_format.line_spacing=1.5
    r=p.add_run(txt); r.font.name='Times New Roman'; r.font.size=Pt(size); r.bold=bold; r.italic=italic
    if sup: r.font.superscript=True
    return p

def shade(cell, hex):
    sh=OxmlElement('w:shd'); sh.set(qn('w:fill'), hex); sh.set(qn('w:val'),'clear'); cell._tc.get_or_add_tcPr().append(sh)

def tbl(doc, headers, rows, widths=None, caption=None, source=None):
    if caption:
        p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        r=p.add_run(caption); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(10)
        p.paragraph_format.space_before=Pt(12); p.paragraph_format.space_after=Pt(6)
    t=doc.add_table(rows=1+len(rows), cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.autofit=False
    if widths:
        for i,w in enumerate(widths):
            for row in t.rows: row.cells[i].width=Inches(w)
    hdr=t.rows[0]
    for i,h in enumerate(headers):
        c=hdr.cells[i]; c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER; shade(c, BLUE)
        p=c.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        r=p.add_run(h); r.bold=True; r.font.name='Times New Roman'; r.font.size=Pt(9); r.font.color.rgb=RGBColor.from_string("FFFFFF")
        p.paragraph_format.space_before=Pt(2); p.paragraph_format.space_after=Pt(2)
    for ri,row in enumerate(rows):
        tr=t.rows[ri+1]; bg=LIGHT_BLUE if ri%2==0 else "FFFFFF"
        for ci,val in enumerate(row):
            c=tr.cells[ci]; shade(c,bg); c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p=c.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.LEFT if ci!=0 else WD_ALIGN_PARAGRAPH.CENTER
            r=p.add_run(str(val)); r.font.name='Times New Roman'; r.font.size=Pt(9)
            p.paragraph_format.space_before=Pt(2); p.paragraph_format.space_after=Pt(2)
    # borders
    tblBorders=OxmlElement('w:tblBorders')
    for edge in ['top','left','bottom','right','insideH','insideV']:
        e=OxmlElement(f'w:{edge}'); e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'4'); e.set(qn('w:space'),'0'); e.set(qn('w:color'),'A6A6A6'); tblBorders.append(e)
    t._tbl.tblPr.append(tblBorders)
    if source:
        p=doc.add_paragraph(); r=p.add_run(f"Source: {source}"); r.italic=True; r.font.name='Times New Roman'; r.font.size=Pt(8)
        p.paragraph_format.space_after=Pt(6)
    return t

def bullet(doc, txt):
    p=doc.add_paragraph(style='List Bullet')
    r=p.add_run(txt); r.font.name='Times New Roman'; r.font.size=Pt(12)
    p.paragraph_format.space_after=Pt(2); p.paragraph_format.left_indent=Inches(0.3)
    return p

# --- CHAPTER 1 DOCX ---
doc = base_doc()
chap(doc, "I", "INTRODUCTION")
sec(doc, "1.0  Introduction")
para(doc, "Zero-day attacks — exploits for vulnerabilities unknown to vendor or defender — drive the most consequential breaches. The zero-day has been defined as “a vulnerability in software or hardware that is unknown to the vendor and for which no patch or signature exists at the time of exploitation” (NIST SP 800-150). An intrusion detection system has been defined as “a system that monitors network or host activity for signs of malicious behaviour or policy violation and produces reports to a management station” (Debar et al., 1999). According to NIST CSF and MITRE ATT&CK any host that processes network communications and deviates from learned normality would come under anomalous behaviour. Globally, NIDS/NADS are the most commonly used terms for network defence. However, technically, zero-day detection is only a subset of anomaly detection applied to network and host behaviour.")
para(doc, "Signature-based NIDS cannot detect zero-days by definition; they match only known patterns. This project learns normal network behaviour unsupervised and flags deviations, explains why, monitors drift when “normal” itself shifts, and measures what evasion would cost an attacker. Three pillars are planned: network flows (Pillar 1, Semester 7), identity/UEBA (Pillar 2), and host syscalls via eBPF (Pillar 3, weeks 4–12). This report covers Semester 7 — Pillar 1 at production depth plus scaffolding for Pillars 2/3.")
sec(doc, "1.1  Background")
para(doc, "Enterprise networks generate millions of bidirectional flows. Each flow is one row: who talked to whom, which port, which protocol, how many bytes and packets, how long, and flag statistics — 80+ per-flow features per CICFlowMeter (Arash Habibi Lashkari, CIC). CICIDS2017 exists in two releases: the 79-column MachineLearningCSV (no IP columns) and the 85-column GeneratedLabelledFlows (has Flow ID, Source IP, Destination IP, Protocol, Timestamp — required for graphs, latin-1 encoded). Only the latter can build host graphs.")
para(doc, "A scanner’s single flows look benign — a TCP SYN to port 22 appears normal. Its fan-out across a 60-second window does not: one host contacting 200 distinct peers in 60 seconds is a rate that the graph makes visible. Similarly, a DDoS victim shows many-to-one collapse, and infiltration shows a single internal host quietly exfiltrating to an external peer with unusual byte-entropy. Relational features — degree, in/out ratio, port entropy, unique peer count, flag ratios — capture these collective patterns that per-flow views discard.")
para(doc, "The field has expanded rapidly. As per MITRE, annual new CVEs exceeded 20,000 during 2023-24. VERIZON DBIR estimates global cyber-crime cost at 8-10 Trillion USD per annum.")
tbl(doc, ["Fact (E-waste analogue)","Network analogue"], [["Annual e-waste India 0.8 Mt (2012), global 30-50 Mt","Annual CVEs >20k, alerts per enterprise 10k-100k/day"],["EEE contains valuables + hazardous toxics","Traffic contains benign signal + 1-8 attackers among thousands"],["Crude recovery (open burning) releases dioxins","Crude evaluation (training on attacks) leaks labels"],["WEEE: Plastics 30%, Oxydes 30%, Copper 20%","CICIDS2017: Benign 70%, PortScan 5%, DDoS 8%, Patator 1%"]], widths=[2.6,3.9], caption="Table 1.1 : Background analogy — e-waste to network anomaly.", source="Umweltbundesamt (2004), MITRE, VERIZON DBIR.")
sec(doc, "1.2  Problem Statement")
bullet(doc, "P1. Closed-world classifiers overstate zero-day performance — overlap families report 0.97+ AUC but collapse to 0.47 held-out (WebAttacks).")
bullet(doc, "P2. Per-flow detectors are structurally blind — M5a swings 0.42–0.98 while M5b never <0.906 (consistency gap).")
bullet(doc, "P3. Power-law scaling squashes small attackers — Patator/WebAttacks P@100 0.000 until LogScaler fixed to 0.618/0.381.")
bullet(doc, "P4. Uncalibrated single-scale scores fuse incorrectly — raw vs rank meant 99.9% picks were M5b alone.")
sec(doc, "1.3  Objectives")
for o in ["Baseline-vs-graph ablation (M5a 87-dim vs M5b 8/19-dim GraphSAGE vs fusion M5c) — the individually attributable headline.","Multi-window calibrated fusion (60s+300s percentile + rank noisy-or 1-Π(1-p)).","Honest held-out protocol — benign Monday only, 7 families, 4-seed GPU-deterministic bands.","Drift-aware SHAP + ATT&CK and adversarial harness (slow 20×, distributed 16×)."]:
    p=doc.add_paragraph(style='List Number'); r=p.add_run(o); r.font.name='Times New Roman'; r.font.size=Pt(12)
sec(doc, "1.4  Scope")
tbl(doc, ["Member","Track","Owns"], [["A — Saharsh","Data & Capture","FlowRecord, pcap_to_flows, schema_mapper"],["B — Deep","Detection Modeling","M5a revived, GNN-temporal, drift, ensembler"],["C — Aditya","Trust & Risk","SHAP, UEBA, ATT&CK, privacy pass"],["D — Avinash","Adversarial & Delivery","Harness, FastAPI + React dashboard"]], widths=[1.4,1.8,3.3], caption="Table 1.2 : Team mapping (CLAUDE.md).")
para(doc, "In scope (Sem 7): schema mapping, host-graph construction with health gates, v1/v2 features, LogScaler, GraphSAGE ensemble, multi-window rank fusion, edge-level alerts, 4-seed HELD-OUT evaluation, drift/SHAP scaffolding. Out of scope: full UEBA and eBPF host AE (weeks 4–12, Knowledge/). Dataset gate: CICIDS2017 GeneratedLabelledFlows (85 cols, has IPs, latin-1). Synthetic training_data/ excluded — graphs collapse (GOTCHA #6).")
sec(doc, "1.5  Methodology — Summary")
para(doc, "Flows → host graphs per time window (nodes=hosts, edges=directed, graph_builder.py) → GraphSAGE autoencoder trained benign-only (M5b, gnn_model.py, NodeScaler log1p) → multi-window rank noisy-or fusion (M5c, eval_mw_ablation_4seed.py) → edge-level ScoredAlert queue (alert_pipeline.py) with SHAP + drift (M6/M7). Evaluation: HELD-OUT, 7 families, 4 seeds. Detail in Chapter III; design in Chapter IV.")
sec(doc, "1.6  Organisation of the Report")
para(doc, "Chapter I Introduction; Chapter II Review of Literature (presentation 10–15 September); Chapter III Methodology; Chapter IV Design and Modelling; References; Appendices (code, schemas, RC cards). Mirrors sample 1.8 DOCUMENTATION structure (pp. 43-73 and 9-22).")
sec(doc, "1.7  Expected Outcome")
tbl(doc, ["Family","AUC (v2 fused)","Attacker ranks"], [["PortScan / DoS / DDoS","0.9999–1.0000","1–4"],["WebAttacks / Patator","1.0000","1–5"],["Infiltration","0.9997","2"],["Botnet","0.9987","5–34"]], widths=[2.0,1.5,1.5], caption="Table 1.3 : Expected headline — week-4 freeze (GPU, CUDA-deterministic, 4 seeds).", source="eval_mw_ablation_4seed.py --seeds 0 1 2 3; eval_feature_set_v2.py")
para(doc, "Mean ROC-AUC 0.9996±0.0001 (v1) / 0.9997±0.0001 (v2) across 7 held-out families; every attacker in top ~35 of thousands on CICIDS2017, top-11/32,935 on IDS2018 (3/4 seeds), CTU-13 Virut #1 in 4/4 seeds; recall@100=1.0; evasion needs 20× time or 16 machines.", italic=True, size=11)
doc.save(OUTDIR/"Chapter1_Introduction_v2.docx")
print("Saved Chapter1")

# --- CHAPTER 3 DOCX ---
doc = base_doc()
chap(doc, "III", "METHODOLOGY")
sec(doc, "3.0  Introduction")
para(doc, "This chapter details data, graph construction, HostScaler, GraphSAGE autoencoder, calibration, multi-window fusion, HELD-OUT protocol, metrics, reproducibility and tools. Every choice is traceable to a gotcha or report card (RC). Time-based windows, directed edges, SAGE over GCN, log1p before scaling, and edge-level alerts are defended decisions.")
sec(doc, "3.1  Datasets and Preprocessing")
para(doc, "Primary: CICIDS2017 GeneratedLabelledFlows (Mon benign → Fri attacks, 85 cols, latin-1, Thursday 63% junk NaN IPs handled by drop_unusable_rows). Two releases only latter builds graphs (GOTCHA #3). Naming drift handled by schema_mapper. Never dropna(axis=1) per-file (GOTCHA #5) — pin via pin_canonical. Health gate rejects collapsed/degenerate synthetic data (GOTCHA #6). External: IDS2018 only Thuesday-20-02-2018 graphable (GOTCHA #13), CTU-13 and planned UNSW-NB15.")
tbl(doc, ["Release","Cols","Has IPs?","Use"], [["MachineLearningCSV","79","No","Per-flow M5a only"],["GeneratedLabelledFlows","85 (latin-1)","Yes","Host graphs (production gate)"],["IDS2018 (10 CSVs)","varies","1/10 only","Thuesday only graphable, bytes_sent zero"]], widths=[2.2,0.7,0.9,2.7], caption="Table 3.1 : Dataset releases and graph capability.")
sec(doc, "3.2  Host-Graph Construction")
para(doc, "Time windows: 60s and 300s time-based (not fixed-count). 60s→1800s AUC 0.917→0.983 but P@100 0.244→0.093 (RC-02) — 60s maximises P@100; we fuse both. Nodes=hosts, Edges=directed (scan vs DDoS distinct), no self-loops, SAGEConv chosen because GCN symmetric norm washes out degree.")
para(doc, "Node features: v1 8 dims (degree, bytes, counts), v2 19 dims (+entropy, port diversity, flags). Indices 0–7 stable; never unpack positionally (GOTCHA #23). Edge_attr (4-dim) scored via rank_mean lifts edge AUC 0.712→0.789 — only change improving both (GOTCHA #19).")
para(doc, "HostScaler(log=True) log1p before min-max is default since 2026-08-12: x_log=log(1+x), x_scaled=(x_log-min)/range fit on benign only. Fixes power-law squash: P@100 0.250→0.413, Patator 0.000→0.618 (GOTCHA #14).")
sec(doc, "3.3  Models")
para(doc, "M5a revived: MLP 87→64→32→16→32→64→87, MSE, benign only — not in production defaults (pending). M5b GraphSAGE: 2×SAGEConv N×8/19→N×32→N×8 latent (=in_dim, no bottleneck — capacity via features not width, latent 2→12 moves mean 0.003, hidden 32→64 0.0002). Decoder reconstructs x and edge_attr; loss MSE(node)+MSE(edge); score = ||x-x̂||² + λ·||a-â||².")
para(doc, "Determinism: set_seed() sets torch.manual_seed, cuda.manual_seed_all, cudnn.deterministic=True, benchmark=False, CUBLAS_WORKSPACE_CONFIG=:4096:8. Same seed CPU 0.5048 vs GPU 0.9948 on WebAttacks (GOTCHA #24). Always --seed; single-seed differences <6 pts are noise (GOTCHA #11).")
sec(doc, "3.4  Fusion and Scoring")
para(doc, "Calibration: per-window percentile against 20% Monday holdout (80/20). Ensemble checkpoint emits percentiles, not raw errors (GOTCHA #18). Uncalibrated fuse until 2026-08-12 was M5b alone 99.9% (GOTCHA #21). Fusion rules (6 configs, 4 seeds): mean, max (saturated M5a overwrites), rank_mean, fused_rank_max (+0.0398 AUC but batch-only), noisyor (production 0.9996±0.0001). Production default is rank noisy-or over 60s+300s, edge rank_mean. score_window(feature_columns=None)=M5b-only 0.8322 edge AUC best consistent (GOTCHA #22).")
tbl(doc, ["Rule","Formula","Property"], [["mean","(p60+p300)/2","Baseline"],["max","max(p60,p300,pM5a)","Lets saturated M5a overwrite"],["rank_mean","rank(pop)→mean","Window-local, lifts 0.712→0.789"],["fused_rank_max","rank positions","+0.0398 AUC but batch-only"],["noisyor (prod)","1-Π(1-p)","0.9996±0.0001 best"]], widths=[1.6,1.8,3.1], caption="Table 3.2 : Fusion rules evaluated (eval_mw_ablation_4seed.py).")
sec(doc, "3.5  Drift, Explainability, Harness")
para(doc, "M6 DetectorDriftMonitors on 3 streams via init_drift_monitors (queue noise is drift RC-28). M7 SHAP + ATT&CK (never unpack positionally). Harness: 4 techniques — port-hiding no effect, slow scan 20× time, distributed 16-way succeeds but costs 16 machines, camouflage fails (RC-14). Privacy k-anonymity out of scope sem 7.")
sec(doc, "3.6  Evaluation Protocol (HELD-OUT) and Metrics")
para(doc, "HELD-OUT: train Monday benign only (80/20 cal), test each of 7 families held-out one-by-one, mean±std over seeds 0–3 (reference eval_mw_ablation_4seed.py --seeds 0 1 2 3 --epochs 60). Metrics: ROC-AUC (primary), attacker rank & recall@100 (operational, attackers in top ~35, recall 1.0), P@100 diagnostic only capped at bad/100 (RC-27, 60s→1800s 0.244→0.093). Node AUC for modelling, edge AUC for operational (gap 22pts). Closed negatives: LODO, k=5, temporal, small-window, latent width — do not revisit.")
sec(doc, "3.7  Tools and Environment")
para(doc, "Python 3.11, PyTorch 2.5.1+cu121, PyG; venv per-machine never portable (GOTCHA #1); paths via Path(__file__).resolve().parent (GOTCHA #2); data/ gitignored (CIC gates), *.pt tracked. One-command: python detection/eval_mw_ablation_4seed.py --seeds 0 1 2 3 --epochs 60 (GPU deterministic).")
doc.save(OUTDIR/"Chapter3_Methodology_v2.docx")
print("Saved Chapter3")

# --- CHAPTER 4 DOCX ---
doc = base_doc()
chap(doc, "IV", "DESIGN AND MODELLING")
sec(doc, "4.0  Introduction")
para(doc, "System architecture, component design, data flow and modelling choices implementing Chapter III. Design decisions defended: autoencoder never classifier, SAGE over GCN, nodes=hosts / edges=directed, time-based windows, edge-level alerts, M5a lifted to host-window (not M5b down). Three pillars: network (P1 sem 7), UEBA (P2), eBPF syscalls (P3 weeks 4–12). Headline is baseline-vs-GNN ablation (B — Deep).")
sec(doc, "4.1  System Architecture — Three Pillars and Four Persons")
para(doc, "Pillar 1 Network: capture/schema_mapper → pcap_to_flows → graph_builder → gnn_model (LogScaler) → ensembler (60s+300s rank noisy-or) → alert_pipeline → dashboard (FastAPI+React). Pillar 2 UEBA: identity logs → risk model. Pillar 3 Host: ebpf_syscall_watcher → host AE (weeks 4–12). Cross-cutting: M6 drift_monitor, M7 shap_explainer, harness D. Four-person mapping as in Table 1.2. Named method HOSTFUSE + HELD-OUT protocol (one-command artifact).")
sec(doc, "4.2  Data Flow and Module Map")
tbl(doc, ["S.No.","Stage","Module","Input → Output"], [["1","Ingest — schema","capture/schema_mapper.py","CSV (79/85/IDS2018) → canonical FlowRecord"],["2","Ingest — capture","pcap_to_flows / ebpf_syscall_watcher","pcap/eBPF → flows / syscalls"],["3","Build — graph","graph_builder.py","flows → List[Data] x=[N,8/19]"],["4","Scale","gnn_model:NodeScaler(log)","raw → log1p → min-max (fit benign)"],["5","Train — baseline","train_m5a_revived.py","87-dim → m5a_revived_ctx.pt"],["6","Train — GNN","gnn_model:GraphAutoencoder","benign graphs → gnn_autoencoder_v1*.pt"],["7","Score — fuse","ensembler.py","60s+300s errors → percentiles → noisy-or"],["8","Serve — alerts","alert_pipeline.py","window → ScoredAlert[src,dst,score,rank]"],["9","Evaluate — lab","eval_mw_ablation_4seed.py","held-out loop → mean±std"],["10","Monitor","drift_monitor.py","3 streams → drift flag"],["11","Explain","shap_explainer.py","embedding → SHAP + ATT&CK"],["12","Adversarial","harness/graph_techniques","4 attacks → cost"]], widths=[0.5,1.3,1.9,2.8], caption="Table 4.1 : System module map — stage, implementation and I/O.", source="detection/README.md, experiments/report_cards.md")
sec(doc, "4.3  Modelling Details")
para(doc, "GraphAutoencoder: 2× SAGEConv N×8/19→N×32→N×8 latent (=in_dim), ReLU, decoder MLPs, loss MSE(node)+MSE(edge), score = ||x-x̂||²+λ·||a-â||² via edge_score rank_mean. Latent width tuning null (0.003), add features not width. v1 8 dims vs v2 19 dims (adds port/peer entropy, flag ratios, IAT); guard refuses v2 without 19-dim checkpoint; indices 0–7 stable. Windows 60s+300s fused after percentile calibration; checkpoints must ship together (percentiles not raw).")
sec(doc, "4.4  Alert Pipeline and Dashboard")
para(doc, "ScoredAlert → alert_pipeline.score_window() → FastAPI GET /alerts + WebSocket tail → React dashboard (filters, pagination, severity, SHAP drawer, drift banner). Run: run_detector.bat or powershell -ExecutionPolicy Bypass -File .\\run_detector.ps1 or VS Code stub_detector.py (deprecated shim, real code in legacy/).")
sec(doc, "4.5  Validation and Results Summary — Week-4 Freeze")
tbl(doc, ["Claim","Number","Source"], [["CICIDS2017 v1","0.9996 ±0.0001","mw_ablation_4seed.json"],["CICIDS2017 v2","0.9997 ±0.0001","feature_set_v2_results.json"],["vs baselines","PCA 0.9417 / IF 0.9357 / MLP 0.9517 → +4.8pts","baselines_4seed.json"],["IDS2018 external","top-11/32,935 in 3/4 seeds","external_ids2018_multiseed"],["CTU-13 Virut","#1 in 4/4 seeds","external_ctu13_multiseed"],["CTU-13 Rbot","#1 in 3/4 seeds","same"]], widths=[1.6,1.8,2.2], caption="Table 4.2 : Validation summary (GPU, CUDA-deterministic, 4 seeds, 2026-08-25).")
sec(doc, "4.6  Deployment Considerations")
para(doc, "Known weaknesses first: noisyor batch-only, calibration optimism (20% holdout), device sensitivity (GPU vs CPU 0.504→0.994), both checkpoints required, near-ceiling dataset. Failure mitigations: latin-1/junk NaN handling, LogScaler, set_seed+CUBLAS, Path resolution, per-machine venv.")
tbl(doc, ["Component","Failure","Mitigation"], [["CSV ingest","latin-1 vs UTF-8, NaN IPs","read_flows()+drop_unusable_rows()"],["Scaling","power-law squash","NodeScaler(log=True)"],["Reproducibility","unseeded/GPU nondeterminism","set_seed()+CUBLAS :4096:8"],["Portability","hard-coded D:\\Test OD","Path(__file__).resolve().parent"],["Portability","venv absolute paths","Per-machine venv, never copy"]], widths=[1.5,2.1,2.9], caption="Table 4.3 : Failure modes and mitigations.")
sec(doc, "4.7  Appendices Mapping")
tbl(doc, ["Appendix","Content","Pointer"], [["A — Schemas","feature_vector.json v3.0 (87-dim), ScoredAlert","detection/training_features/README.md"],["B — Evidence","report_cards.md RC-01…RC-32","Detail behind CHANGELOG"],["C — Code","graph_builder, gnn_model, ensembler, alert_pipeline","detection/ prod"],["D — Supplementary","baselines, externals, ablation bands","PAPER_OUTLINE"]], widths=[1.4,2.5,2.6], caption="Table 4.4 : Appendices mapping (code & supplementary in appendices per guideline).")
doc.save(OUTDIR/"Chapter4_Design_and_Modelling_v2.docx")
print("Saved Chapter4")

# --- REFERENCES DOCX ---
doc = base_doc()
chap(doc, "", "REFERENCES")
para(doc, "Formatted IEEE-style per guide; code/supplementary in Appendices, not References. Use before Appendices.", align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, size=10)
refs=["Debar, H. et al. Towards a taxonomy of IDS. Comput. Networks, 1999.","Axelsson, S. IDS: A survey and taxonomy. Chalmers, 2000.","Chandola, V. et al. Anomaly detection: A survey. ACM CSUR, 2009.","Garcia-Teodoro, P. et al. Anomaly-based NIDS. IEEE Commun. Surv. Tuts., 2009.","Bhuyan, M. et al. Network anomaly detection. IEEE Commun. Surv. Tuts., 2014.","Sommer, R. & Paxson, V. Outside the closed world. IEEE S&P, 2010.","Patcha, A. & Park, J. An overview of anomaly detection. Comput. Networks, 2007.","Hodge, V. & Austin, J. A survey of outlier detection. Artif. Intell. Rev., 2004.","Lashkari, A.H. et al. CICFlowMeter. CIC, 2017.","Moore, A. et al. Discriminators for flow classification. 2005.","Williams, N. et al. Comparison of five ML algorithms for flow classification. 2006.","Sharafaldin, I. et al. CICIDS2017. CIC, 2018.","Ring, M. et al. Survey of NIDS datasets. 2019.","Heng, M. et al. Dataset realism. 2024.","Durieux, V. & Gevenois, P. Bibliometric indicators. 2010.","Franceschini, F. h-index. 2010.","Zitt, M. & Bassecoulard, E. Challenges for indicators. 2008.","Biglia & Butler. Bibliometric analysis. 2005.","Sakurada, M. & Yairi, T. Anomaly detection using autoencoders. MLSDA, 2014.","An, J. & Cho, S. Variational autoencoder anomaly detection. 2015.","Liu, F. et al. Isolation Forest. ICDM, 2008.","Scholkopf, B. et al. Support vector novelty. NeurIPS, 1999.","Merton, R. 1963. Publication collaboration.","Manten. 1968. Earth Science authorship.","Zuckerman. 1968. Nobel laureates.","Meadows, A. 1974. Communication in science.","Klaic. 1990. Chemists of Rugjer Boskovic.","Vimala & Pulla Reddy. 1996. Zoology theses.","Gupta & Karisiddappa. 1998. Population genetics.","Mahapatra & Bhagavan Doss. 2000. Geology.","Seglen & Aksnes. 2000. Norwegian microbiology.","Moed, H. 2000. Biotechnology departments.","Arunachalam & Doss. 2000. Asian collaboration.","Kannappanavar & Vijayakumar. 2001. Authorship trend.","Farahat, H. 2002. Egyptian journals.","Suresh Kumar & Garg. 2005. China vs India CS.","Calero, C. et al. 2006. Bibliometric mapping.","Park, T. 2008. Library science authorship.","Tijssen & Van Leeuwen. 2001. Scientometric evaluation.","Thomaidis, N. et al. 2003. Balkan chemistry.","Leydesdorff, L. 2004. Research evaluation.","Surulinathi et al. 2007. Knowledge management India.","Tseng, Y. et al. 2009. Trend analysis.","Annibaldi et al. 2010. Italian analytical chemistry.","Padma, P. 2010. Madurai Kamaraj thesis.","Garfield, E. 1983. World research 1973.","Mehrotra & Lancaster. 1984. Indian science.","Raghuram & Madhavi. 1996. Decline in Indian science. Nature.","Raina, D. et al. 1995. Indian research 1800-1950.","Bandyopadhyay, A.K. 2001. Indian research 1950-1990.","Arunachalam et al. 1998. 42,000 Indian papers.","Arunachalam. 2000. Is science in India on decline.","Arunachalam & Gunasekaran. 2002. Tuberculosis.","Kademani, B.S. et al. 2006. Thorium India.","Kademani et al. 2007. Indian S&T 1990-2004.","UNEP E-waste Manual; NIST CSF; ENISA.","MTRE CVE, VERIZON DBIR, CIC IDS2018, UNSW-NB15, CTU-13."]
for i, ref in enumerate(refs,1):
    p=doc.add_paragraph(style='List Bullet')
    r=p.add_run(f"[{i}] {ref}"); r.font.name='Times New Roman'; r.font.size=Pt(9)
    p.paragraph_format.space_after=Pt(2); p.paragraph_format.left_indent=Inches(0.2)
doc.save(OUTDIR/"References_v2.docx")
print("Saved References")

# Combined
print("All DOCX generated")
