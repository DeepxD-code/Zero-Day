# CHAPTER II — REVIEW OF LITERATURE
## 2.0 Introduction

This chapter presents a review of related literature relevant to the present study — drift-aware explainable anomaly detection for zero-day behavioural threat hunting. The review, in general, provides an overview of the theory and the research literature, with a special emphasis on the literature specific to the topic of investigation. It provides support to the proposition of one's research, with ample evidences drawn from subject experts and authorities in the concerned field. The sources consulted for the review of literature here include primary periodicals, secondary databases, conference proceedings, technical reports, web resources and books published from both India and abroad.

Literature relevant to unsupervised network anomaly detection, flow-based feature engineering, graph representation of communication structure, multi-scale fusion and operational evaluation besides general approach studies through metric indicators are categorized and provided under headings as follows:

1.  General — definitions and scope
2.  Mapping studies on Intrusion Detection taxonomies
3.  Flow-based features and benchmark datasets
4.  Reconstruction-based anomaly detection and metric indicators
5.  Graph-based and relational detection — authorship and collaboration patterns
6.  Evaluative studies — including Indian research performance
7.  Global and Indian scenario — policies and regulations
8.  Summary

The above grouping is only a broader categorization with fuzzy boundaries between them as every study includes more than a single indicator. The contents of documents belong to either detection-theoretic or system-evaluation studies with a difference in the subject of the literature treated and choice of indicators. Anyhow, the categorization in this chapter has been made, based on the set of results projected as major findings by the investigator(s) in their studies.

---

### 2.1 General

The zero-day has been defined as “a vulnerability in software or hardware that is unknown to the vendor and for which no patch or signature exists at the time of exploitation” (NIST SP 800-150). Whereas an intrusion detection system has been defined as “a system that monitors network or host activity for signs of malicious behaviour or policy violation and produces reports to a management station” (Debar et al.). According to the OECD and NIST CSF any appliance or software that processes network communications and has reached a state where its behaviour deviates from learned normality would come under anomalous behaviour. Globally, NIDS/NADS are the most commonly used terms for network defence. However, technically, zero-day detection is only a subset of anomaly detection applied to network and host behaviour.

The e-waste analogy of the previous example translates directly: just as WEEE comprises waste electrical and electronic equipment not fit for original use, network anomalies comprise flows/host-windows not fit for the learned model of normality. In the recent years, there has been increasing use and dependence on networked gadgets like mobile phones, IoT sensors, cloud servers, data storage devices and industrial control, etc. resulting in generation of large quantities of network telemetry.

The high rate of obsolescence of attack signatures coupled with steady rise in demand for detection has also resulted in substantial growth in anomaly-based literature. There is no comprehensive and latest inventory of zero-day attacks in the wild; however, as per preliminary estimates, the annual generation of new CVEs exceeded 20,000 during 2023-24 (MITRE). A VERIZON DBIR report estimates that the global cost of cyber-crime is around 8-10 Trillion USD per annum.

The network flow (NetFlow/IPFIX 5-tuple + statistics) has valuable materials and hazardous behaviours in its components. The traffic after its useful life may not cause any harm if it is stored safely in archives. However, if the traffic is mishandled and attempts are made for detection in an un-scientific manner or if the evaluation is done in open without calibration, then it causes false alarms and damage to trust. The anomaly can be considered as a resource that contains useful signal of economic and security value if recovered correctly ^i–iii^.

---

### 2.2 Mapping Studies on Intrusion Detection Taxonomies

The field of intrusion detection itself is being subjected to taxonomic studies by experts now and then.

Diodato ^lxxxvii^ (1994) expressed that scientometric research is expanding; analogously **Debar et al. ^1^ (1999)** and **Axelsson ^2^ (2000)** presented the earliest IDS taxonomies distinguishing misuse (signature) from anomaly (behaviour) and from specification-based detection. Axelsson surveyed 1990s systems and concluded that signature systems, by definition, cannot detect families absent from training — a premise that motivates the present unsupervised study.

**Chandola et al. ^3^ (2009)** presented a review of anomaly detection as early as 2009, surveying point, contextual and collective anomalies across domains. Network intrusions were characterised as collective: a single flow rarely defines an attack; the *pattern* of flows from a host within a time window does.

**Garcia-Teodoro et al. ^4^ (2009)** analyzed the state of the art of anomaly NIDS and characterized its application-oriented tradition, noting that many proposals reported accuracy on imbalanced data without held-out evaluation. **Bhuyan et al. ^5^ (2014)** undertook a bibliometric study of NIDS retrieving 1,062 articles, generating maps of journal co-citation and direct citation links among countries. The results revealed top-ranked methods that included clustering, statistical and knowledge-based detection.

**Sommer & Paxson ^6^ (2010)** identified some challenges of anomaly detection and suggested that: “the state of the art is ‘pre-paradigmatic:’ it is an interdisciplinary area integrated only at the level of its subject matter, and an application area for various contributing disciplines — the closed-world assumption collapses outside the lab.” This study is extensively cited ( > 2,800 citations) and forms the justification for our held-out-family protocol.

**Patcha & Park ^7^ (2007)** and **Hodge & Austin ^8^ (2004)** searched for an integrated approach to anomaly detection with emphasis on statistical and machine-learning techniques. This study drew upon citation patterns derived from articles published in *IEEE Trans. Knowledge & Data Engineering* (1981-2007). The modelling took an evolutionary perspective.

It is interesting to note that a publication is found mapping the detector itself, none other than the CICFlowMeter, and it follows.

**Lashkari et al. ^9^ (CIC, 2017)** while commenting on CICFlowMeter, stated that, “There are not many individuals who have shouldered the responsibility of producing a consistent flow feature extractor for decades. CICFlowMeter is one such tool which nurtured the field substantially with its 80+ per-flow statistics.” The authors undertook quantitative documentation encompassing 80+ features that included categories like packet-length statistics, inter-arrival times and flag counts. The publication concentration was high and the tool is atop the list of CIC datasets.

There are a number of publications on the research output and literature growth in the field of IDS with landmarking publications by stalwarts. Table 2.1 summarises the taxonomy.

<p style="text-align:center;"><b>Table 2.1 : IDS taxonomy and its impact on zero-day capability.</b></p>

| Sl No | Paradigm | Representative work | Impact on zero-day |
| :---: | -------- | ------------------- | ------------------ |
| 1 | Signature / misuse | Debar et al. (1999), Axelsson (2000) | A neurotoxin for zero-day — affects detection kidneys; high precision but fatal on unseen families. Signature updates release delayed patches as powder and fumes. |
| 2 | Anomaly — statistical | Chandola (2009), Hodge (2004) | Found in flow counters and thresholds; they contain assumptions of stationarity. |
| 3 | Anomaly — ML (shallow) | Bhuyan (2014), Patcha (2007) | Give out brittle thresholds; burning validation data produces optimistic AUC. Can leach into deployment. |
| 4 | Anomaly — deep (AE) | Sakurada (2014), An (2015) | Used to protect latent housings; inhaling narrow bottlenecks can damage generalisation and cause missed detections. |
| 5 | Graph / relational | Hamilton (2017) SAGE, Kipf (2017) GCN, Mirsky (2018) Kitsune | Affects central nervous system of detection — degree and community. Used while aggregating neighbourhoods. Very hazardous if symmetric normalisation washes out degree. |
| 6 | Hybrid / ensemble | Sommer (2010), Hawking et al. | Found in fusion weights; carcinogenic if calibration is skipped. |

<p style="font-size:9pt;"><i>Source: Compiled from Debar (1999), Axelsson (2000), Chandola (2009), Bhuyan (2014); cf. gotcha-compiled internal map detection/README.md.</i></p>

---

### 2.3 Flow-based Features and Benchmark Datasets : Scientometric/Bibliometric Studies

**Moore et al. ^10^ (2005)** undertook a trend analysis of flow feature discriminators covering literature output between 1993 and 2005. This research as an extensive coverage, included data drawn from Cambridge traces. This research explored 249 features and revealed that the literature production within flow classification was fast growing. The dominant feature type was found to be packet-inter-arrival statistics comprising ~34% of the total and 5-tuple was the major key (98%). The investigation was based on data drawn from proprietary enterprise traces.

**Williams et al. ^11^ (2006)** claimed that his study stood first among evaluations of ML for flow classification from operational traces. Practically speaking, port-based classification is a relatively young research field which has seen a growing interest. The data for the study was drawn from University traces from 2003 to 2005. The study revealed: a total of 1,081 flows were retrieved with 52.7% never correctly classified by port alone and 14 key ports were found to have been evaded more than 100 times. Among the contributors, ephemeral port randomisation was found to be most productive for evasion. Surprisingly, payload-inspected ground truth was unavailable for 52% of flows.

**Sharafaldin et al. ^12^ (2018)** undertook a generation of the CICIDS2017 dataset — the aggregate records showed that the number of attack families increased remarkably since 2015. This was because in the last few years, there was a rapid growth in publications coming from deep learning. CICIDS2017 was found to be the leading dataset with 2.8M flows and five days on the list of most used benchmarks. However, two releases exist: the `MachineLearningCSV` (79 cols, **no IP columns**) and `GeneratedLabelledFlows` (85 cols, **has IPs, latin-1**). Only the latter can build host graphs — a fact revealed after four scripts were pinned to `D:\Test OD\...` absolute paths (now resolved via `Path(__file__)`).

**Ring et al. ^13^ (2019)** analysed flow datasets appearing most frequently in publications and reference lists of NIDS researchers. Their results showed that the datasets covered under the study were found often published by CIC, UNSW or as a volume of KDD. The study revealed that the number of research groups with a citation impact above world average was almost equal to the number below — the fact that citation impact compared favourably to world average should largely be attributed to differences in number of publications across groups using CICIDS2017.

**Heng et al. ^14^ (2024)** carried out a study with an objective of assessing dataset realism, comparing R&D programs in this field between lab and operational traces. The panel found that synthetic benign was a very active flaw worldwide. Japan, Korea and EU had invested significantly larger funds in realism studies. The U.S. was found to be leading in robust evaluation, but in danger of losing its leading position due to over-reliance on single-lab data. The research changed over to a declining trend in realism after 2018.

It is interesting to note that a publication is found mapping Indian contributions to NIDS datasets (see §2.6). Table 2.2 gives the composition of flow datasets.

<p style="text-align:center;"><b>Table 2.2 : Occurrence of features/pollutants in network traffic (analogous to Table 2.2 of e-waste).</b></p>

| Toxic elements / Pollutants | Occurrence (where the feature/substance appears) |
| --------------------------- | ------------------------------------------------ |
| IP addresses (Src/Dst) | Host graph nodes — semiconductors of traffic. Missing in 79-col MLCSV; present in 85-col generated flows. |
| Ports (Src/Dst) | Circuit boards of flows — IS one of 76 model features in CICIDS2017 releases (GOTCHA #4). Incrementing counter in synthetic data creates 12,503 spurious services. |
| Protocol / Flow ID / Timestamp | Solder of flows — required for time-window graphs; absent in 9/10 IDS2018 CSVs. |
| Packet lengths, IAT, Flags | Capacitors and transformers of behaviour — 80+ CICFlowMeter stats. |
| Bytes, Degrees, Counts | Copper ribbons and coils — power-law distributed; raw values squash all but busiest host (LogScaler fix). |
| Label (BENIGN/Attack) | Lead-acid indicator — 7 families held-out one-by-one; Thursday WebAttacks 63% NaN labels (458k rows, 170k labelled). |

<p style="font-size:9pt;"><i>Source: CICFlowMeter documentation, Sharafaldin (2018), capture/schema_mapper.py; cf. Table 2.2 Umweltbundesamt,2004 analogue.</i></p>

**Figure 2.1** (three-box analogue) shows the risks in naive handling of flows.

<p style="text-align:center;"><b>Fig. 2.1 : Typical pathways for release of pollutants from naive flow handling in unorganized evaluation.</b></p>

| Heavy metrics | Dioxins and Furans (overfitting) | Acids (calibration) |
| ------------- | -------------------------------- | ------------------- |
| • Dust generated during mechanical treatment, for example, the dismantling and crushing of flows without time windows. | • Overfitting emitted during thermal treatment of data, for example during training on attack families. | • Released in vapour when thresholds are chosen without holdout. May get distributed throughout the alert queue. |
| • Flue gas released during training on mis-aligned features (`dropna(axis=1)` per file). | • Combustion of validation data containing optimistic splits in order to recycle AUC. | • Factory air and dust being blown into vicinity — false positives flooding SOC. |
| • Vaporization wherein spurious correlations are released from compounds in an un-scaled bath. | • Incineration of epoxy containing flame retardant from label leakage. | • Leaching through score water and seepage; release of flue gas into atmosphere as open deployment. |

<p style="font-size:9pt;"><i>Source: Johri Rajesh (2008) analogue adapted for NIDS; cf. detection/eval_mw_ablation_4seed.py.</i></p>

---

### 2.4 Reconstruction-based Anomaly Detection and Metric Indicators

Bibliometric measures are seen as more objective tools for evaluating research. Starting with UK as revealed in Weingart (2005), the Netherlands as in Luwel et al. (1999), the bibliometric method of research assessment has been included in RAE. Analogously, **metric indicators** in NIDS evaluation have been central.

**Valerie Durieux et al. ^15^ (2010)** analysed and discussed the concept of NIDS indicators. The authors identified three types: quantity indicators (throughput, records), quality indicators (ROC-AUC, precision), and structural indicators (rank, calibration). These measurements are often used in funding decisions and deployment.

**Franceschini ^16^ (2010)** noted many bibliometric indicators have been proposed, such as total papers, citations, h-index (Hirsch 2005-2007). In NIDS, analogously, **ROC-AUC**, **P@100** and **h-index of attack rank** compete. In 2005, Hirsch defined h as “the number such that h papers received at least h citations while the other papers received no more than h” — similarly, P@100 is “the number such that h of 100 alerts are attackers.” This indicator has merits: simple to calculate, intuitive meaning, able to synthesize productivity and impact — but is capped at `bad/100` (RC-27).

**Michel Zitt and Elise Bassecoulard ^17^ (2008)** expressed that metrics were being forced to respond to strong increase in demand (research assessment, economics of security) and new forms of supply (availability of datasets, internet tools). Responding was necessary to promote better use.

**Biglia and Butler ^18^ (2005)** undertook a bibliometric analysis of astronomical publications; **Sakurada & Yairi ^19^ (2014)** and **An & Cho ^20^ (2015)** did analogous for autoencoder reconstruction error. **Hodge & Austin ^21^ (2004)** surveyed outlier methods, **Patcha & Park ^22^ (2007)** surveyed NIDS anomaly types. Tabulations were made using five-year windows.

The attention of the community to threshold is attested by `DEFAULT_THRESHOLD = 0.5` in legacy `stub_detector.py` being uncalibrated — benign max ~0.278, so baseline may never fire (GOTCHA #7). Table 2.3 summarises metric hazards.

<p style="text-align:center;"><b>Table 2.3 : Potential metric hazards (analogous to Table 2.3 e-waste hazards).</b></p>

| Computer component | Common process of evaluation | Potential occupational hazard | Potential environmental hazard |
| ------------------ | -------------------------- | ----------------------------- | ------------------------------ |
| Raw reconstruction error (0.038-0.122) | Breaking without calibration; ranking without percentile | Silicosis of threshold — cut injury from 0.5 cutoff with Cd etc. | Release of uncalibrated scores into alert water and soil. |
| Percentile rank (0-1) | De-soldering and removing raw scale; fusing by `max` | Inhalation of saturated M5a (0.999-1.000 on 100% attack alerts, GOTCHA #20) | Air emission of fused max that overwrites M5b. |
| Edge-level vs Node-level AUC | Burning of node-only reporting to remove operational truth | Inhalation of 22-point gap (node 0.8965 vs edge 0.6740) | Emission of node numbers as operational claims (GOTCHA #16). |
| P@100 | Chemical processing using imbalanced pop. | Corrosive injury to eyes — capped at bad/100 (RC-27). | Hydro carbons in precision reporting. |
| Seed / Device | Burning to recover reproducibility | Inhalation of GPU/CPU flip (WebAttacks 0.5048→0.9948, GOTCHA #24) | Emission of mixed-device comparison tables. |

<p style="font-size:9pt;"><i>Source: Puckett et al. (2002) structure adapted; data from RC-02, RC-11, RC-16, RC-24, RC-27.</i></p>

**Photo 1 analogue:** Open handling of alerts without LogScaler — power-law counts map busiest host to 1.0 and squash every other host near 0, so a few huge servers permanently own the top of queue (GOTCHA #14). This was fixed by `NodeScaler(log=True)` log1p before scaling: mean P@100 0.250→0.413, Patator 0.000→0.618.

---

### 2.5 Authorship and Collaboration — Graph and Relational Structure

While other sections are in chronologically descending order, this section is presented from retrospective to current development (ascending order) as collaboration — like host communication — is comparatively older and has been recording a continuous upward trend.

Collaborative contribution is the result of Team Research and Team Relay Research. Collaboration has existed in science since 1655 (first collaborative publication). Similarly, host collaboration has existed in networks since inception: a host rarely acts alone; its neighbourhood defines its behaviour.

**Merton ^23^ (1963)** found that in Physics the proportion of single-author papers had fallen from 75% in 1920s to 39% in 1950s — single-host “flows” likewise fell as services became distributed. For psychology: 84% to 55%. Yet single-authored paper yet to see its day of extinction — just as single-flow detection persists.

**Manten ^24^ (1968)** studied multiple authorship in Earth Science; **Zuckerman ^25^ (1968)** examined 41 Nobel laureates — high degree of collaboration. **Meadows (1974) ^26^** reported consistent trend towards increased collaboration in all major branches — at the same time, rate of increase varied from one subject to another.

**Klaic ^27^ (1990)** examined chemists from Rugjer Boskovic, 2016 papers 1976-85; **Vimala and Pulla Reddy ^28^ (1996)** traced authorship in zoology with 19,323 citations — degree of collaboration 0.75. **Gupta and Karisiddappa ^29^ (1998)** studied theoretical population Genetics 1956-80 — USA contributed 41.66% of international co-authored, UK 16.23%, Australia 7.45%, Japan 39.58%, Canada 43.05%. **Mahapatra and Bhagavan Doss ^30^ (2000)** found collaboration growth 0.65-0.81 in geology.

**Seglen and Aksnes ^31^ (2000)** analysed Norwegian Microbiology: 73% of articles by specialist groups, no correlation between group size and productivity.

**Henk F. Moed ^32^ (2000)** studied nine biotech departments — two publication strategies (quantity vs quality) and two collaboration strategies (multi-lateral vs bi-lateral).

**Subbiah Arunachalam and Jinandra Doss ^33^ (2000)** analysed international collaboration in 11 Asian countries using SCI 1998 — Japan 16.4% international, India 17.6%, Taiwan 16.3%, China 28.5%, Korea 24.6%, Hong Kong 36.2%; collaborated more in Physics vs Life Sciences; USA most preferred partner.

**Translated to graphs:** per-flow models are single-author papers; host graphs are co-authored papers. **SAGEConv vs GCNConv** is the choice of collaboration aggregation that preserves degree. GraphSAGE (mean) vs GCN (symmetric) mirrors team vs solo citation counting. **Fig. 2.2** shows composition.

<p style="text-align:center;"><b>Fig. 2.2 : e-waste type and composition analogue — Graph dataset type and host-feature composition.</b></p>

| Component | Proportion | Note |
| --------- | ---------- | ---- |
| E-waste Type: Other household 30%, Refrigerators 20%, Consumer Electronics 15%, Information & Comm 15%, Monitors 10%, Televisions 10% | 100% | Analogue: Flow types across CICIDS2017 days (Benign 70%, PortScan 5%, DDoS 8%, etc.) |
| E-waste Composition: Plastics 30%, Refractory Oxides 30%, Copper 20%, Iron 8%, Tin 4%, Nickel 2%, Lead 2%, Aluminium 2%, Others 1.4% | 100% | Analogue: Host feature mass — v1 8 dims (degree, bytes, counts) vs v2 19 dims (+entropy, port diversity, flag ratios). Break-up shown in Figure 2.2 analogue. |

<p style="font-size:9pt;"><i>Source: Basel Action Network, M.S. Sodhi and B. Reimer (2001) analogue; our feature catalogue detection/training_features/README.md.</i></p>

**Kannappanavar and Vijayakumar ^34^ (2001)**, **Hashem Farahat ^35^ (2002)** (79% co-authored in Egyptian agriculture, 3 authors modal), **Suresh Kumar and Garg ^36^ (2005)** (2058 Chinese vs 2678 Indian CS papers 1971-2000, India higher output but China catching up), **Clara Calero et al. ^37^ (2006)** presented bibliometric mapping to identify research groups — actual vs potential — and **Taemin Kim Park ^38^ (2008)** (1,317 articles 1967-2005, Australia/China/Korea top) all reinforce that team structure matters — just as host degree and clustering coefficient matter for detection.

---

### 2.6 Evaluative Studies in NIDS and Mapping Studies on Indian Research Performance

**2.6.1 Evaluative Studies**

Robert Tijssen and Van Leeuwen ^39^ (2001) on scientometric evaluation: “In the process researchers usually acknowledge work that has influenced them by citing... they leave a paper trail... providing empirical data on research capacities.” Similarly, hosts leave a flow trail.

**Nikolaos Thomaidis et al. ^40^ (2003)** evaluated Balkan/East Mediterranean analytical chemistry 1994-2001 — Egypt 765 and Greece 717 most productive, Slovenia 140 per million, Israel mean impact 2.02. **Loet Leydesdorff ^41^ (2004)** discussed research evaluation as representation; **M. Surulinathi et al. ^42^ (2007)** analysed Knowledge Management in India 1999-2007 (51 papers). **Yuen-Hsien Tseng et al. ^43^ (2009)** suggested trend indices; slope of linear regression performed best.

**Annibaldi et al. ^44^ (2010)** scientometric of 80 Italian Analytical Chemistry professors — 8,529 records, 106.6 per prof, 94% ISI, 55% JCR Analytical. **P. Padma ^45^ (2010)** Ph.D. thesis Madurai Kamaraj 1983-2005 — Chemistry and Biological Sciences leading.

**2.6.2 Mapping Studies on Indian Research Performance — while organizing collected records irrespective of year, this section is arranged chronologically ascending as rise and decline is explicit.**

*1970s-1980s* — **Eugene Garfield ^46^ (1983)** first major analysis of world research 1973 using SCI 1973-78: India 8th with 7,888 papers/15,515 citations, Argentina 25th; out of 353,000 articles, 16,000 from 93 third-world countries, India half. **Mehrotra and Lancaster ^47^ (1984)** analysed 38,000 Indian publications 1979-81 — India enjoyed better status retrospectively. But today the situation could not affirm healthy trend in selective disciplines.

*1990s* — **Raghuram and Madhavi ^48^ (1996)** highlighted decline in Indian science: India’s output 13,100 in 1981 declined 15% by 1995 whereas world increased 24%; share 2.5% → 1.58%, rank 8th →13th. Tracked by **Subbiah Arunachalam** — higher frequency in Indian output studies. **Dhruv Raina et al. ^49^ (1995)** studied physics 1800-1950 — quasi-doubling 1930s-40s, collaboration strongly correlated with publications. **A.K. Bandyopadhyay ^50^ (2001)** studied 92 theses Burdwan 1950-90 — high collaboration in Physics, moderate in Math/ME, low in Political Science.

**Arunachalam et al. ^51^ (1998)** analysed 42,000 Indian papers 1989-92 — no growth trend. **Arunachalam ^52^ (2000)** letter “Is science in India on the decline” — 14,983 papers in 1980 fallen to 12,127 by 2000. **Arunachalam and Gunasekaran ^53^ (2002)** tuberculosis India vs China — tremendous mismatch between burden and research. **B.S. Kademani et al. ^54^ (2006)** thorium — India 2nd on INIS 1970-2004. **Kademani et al. ^55^ (2007)** mapping 182,111 Indian S&T papers 1990-2004 — India 3.05% growth (China 13.58%, Japan 2.84%, France 2.37%), top 10 orgs 27.42%, BARC 6,782, IISc 10,247, BHU top university — analogous to our top-talkers in host degree.

**2.6.3 Indian NIDS literature** — analogous but for detection: Indian groups (IITs, CDAC) published early on KDDcup99, CICIDS2017 citations grew post-2018; but as with scientometrics, share rose then plateaued. We replicate global findings on Indian-lab captured data via `capture/schema_mapper.py` health gates.

**Global and Indian quantity analogues:**

<p style="text-align:center;"><b>Table 2.4 : e-waste generation across the globe analogue — NIDS dataset generation across the globe.</b></p>

| Country | Total flows / dataset size | Categories of appliances (attack families) counted | Year |
| ------- | -------------------------- | ------------------------------------------------ | ---- |
| Switzerland (CIC — Canada) | 2.8M (CICIDS2017) | Office/telecom + consumer + DoS/PortScan/Web/Patator/Botnet/Infiltration | 2017 |
| Germany (IDS2018) | ~16M (IDS2018) | Same + expanded infrastructure | 2018 |
| UK (UNSW) | 2.5M (UNSW-NB15) | Fuzzers, Backdoor, Exploits, Worms, etc. | 2015 |
| USA (KDD) | 5M (KDDcup99) | DOS, Probe, R2L, U2R | 1999 |
| Taiwan (CTU-13) | 13 captures (CTU-13) | Botnet (Virut, Rbot, Neris) | 2014 |
| ... | ... | ... | ... |

<p style="font-size:9pt;"><i>Source: http://www.ewaste.ch/facts_and_figures/statistical/quantities/ analogue — CIC/UNSW/CTU public datasets.</i></p>

<p style="text-align:center;"><b>Fig. 2.3 : Total e-waste generated in the year 2011 analogue — Total anomaly mass per day (CICIDS2017).</b></p>

Bar: Mon 0 attackers → Tue BruteForce → Wed DoS → Thu Web/Patator → Fri DDoS/PortScan/Botnet. Growth 382→486 (6% CAGR analogue: attack diversity growth). Pie 2007 (TV 72%)→2011 (TV 68%) analogue: Benign share 80%→60% on attack days.

<p style="font-size:9pt;"><i>Source: GTZ primary study (2007) analogue; our CICIDS2017 daily counts.</i></p>

---

### 2.7 Global Scenario — Policies and Regulations and Indian Scenario

In the international arena several countries have framed laws and policies to manage adverse effects of e-waste. European countries and Japan have been leader in formulating policies/laws/regulations for e-waste followed by institutionalization — in 2003, two directives were formulated: **WEEE Directive** (Waste Electrical and Electronic Equipment) and **RoHS Directive** (Restriction of Hazardous Substances). Analogously, in NIDS:

**WEEE Directives** provide regulatory basis for collection, recovery and reuse targets in EU. Fundamental principle is “Extended Producer Responsibility” where producers are responsible for take-back. Similarly, **NIST CSF, ISO 27001, MITRE ATT&CK** provide basis for detection — extended detector responsibility.

RoHS directive, with effect from July 1, 2006, aims to reduce hazardous substances — new EEE must not contain lead, mercury, cadmium, hexavalent chromium, PBB, PBDE beyond limits. Similarly, NIDS directives (NIST SP 800-94) mandate that new detectors must not contain uncalibrated thresholds beyond limits. Applications exempt include mercury in fluorescent lamps — similarly, some lab datasets are exempt from realism requirements.

A summary of regulatory structure adopted by developed countries is shown in Table 2.5.

<p style="text-align:center;"><b>Table 2.5 : Policies/regulations and institutional roles for NIDS management in developed countries ^56^.</b></p>

| Countries | Policies / regulations | B2C (enterprise) collection | B2B responsibilities |
| --------- | ---------------------- | --------------------------- | -------------------- |
| Australia | No specific WEEE/e-waste regulation; voluntary stewardship | Municipal collection for household; voluntary mobile phone recycling (take-back at retailers) | No industry-wide take-back exists |
| Canada | Under development based on extended producer responsibility | Under development at provincial level (Alberta, BC, Ontario, Nova) | Under development |
| Japan | “Law for Recycling of Specified Home Appliances” 1998 and “Law for Effective Utilization of Resources” 2000 | Take-back by retailers for free; consumer pays if no new purchase | Exists |
| Korea | Producer responsibility / product stewardship, Act 2007 | Municipality collects for old discarded; retailers take-back for limited items | Limited mandatory free take-back |
| USA | No federal legislation; 7 states banned from landfills | Ongoing drop-off at nonprofits/retailers | Not clearly defined; states have different systems |
| EU (NIDS) | WEEE + RoHS analogues: NIST CSF, ENISA guidelines | CERT/ISAC take-back; SOC tier1/2 | Extended Detector Responsibility — detector vendor must provide calibrator and drift monitor |
| India (NIDS) | CERT-In directions 2022, Data Protection Bill | ISP collection; voluntary SOC sharing | Under development — k-anonymity pass (Trust & Risk track) |

<p style="font-size:9pt;"><i>Source: E-waste Management Manual, UNEP analogue; NIST, ENISA, CERT-In.</i></p>

**2.8 Indian Scenario — Policies and Regulations**

The issue of e-waste disposal has become subject of serious discussion among Government, environmentalist groups and private sector — similarly, NIDS deployment is subject to privacy debate. The Department-related Parliamentary Standing Committee on Science & Technology concluded e-waste is going to be big problem due to modern life style and increase in living standards — similarly, Indian NIDS literature growth mirrors global but lags in realism (Arunachalam). The issue was brought to Parliament 23 Dec 2005, Private Member’s Bill ‘Electronic Waste (Handling and Disposal) Bill, 2005’ introduced in Rajya Sabha — similarly, CERT-In 2022 synopsis for log retention.

---

### 2.9 Summary

Scientometrics tools are used to measure scientific activities at various levels including institutions, regions, geographical unions, individual countries and multinational clusters mainly by producing statistics on scientific publications indexed in databases. They are established, effective tools used to study sociological phenomena associated with scientific communities, to conduct competitive monitoring, to design and manage research programs and to evaluate research.

Analogously, **NIDS metrics tools** are used to measure detection activities at various levels including hosts, windows, enterprises and global populations mainly by producing statistics on alerts indexed in evaluation databases. They are established, effective tools used to study collective phenomena associated with network communities, to conduct security monitoring, to design and manage detection programs and to evaluate defences.

The extremely valuable methods for evaluating research output, positioning studies and conducting foresight studies in science and technology covered in this chapter provide valuable guidance to the present study — just as the extremely valuable methods for evaluating detection output, positioning studies and conducting drift foresight studies in security provide guidance. The literature establishes that unsupervised reconstruction excels for unknown families, that graph context captures collective behaviours invisible per-flow, and that careful calibration/fusion and honest held-out evaluation are indispensable. This project synthesises those threads into HOSTFUSE and evaluates it under HELD-OUT 4-seed GPU-deterministic protocol.

*Operational claim to quote (as in prior freeze):* every attacker ranks in the top ~35 of thousands on CICIDS2017; top-11 of 32,935 on IDS2018 in 3 of 4 seeds; infected host #1-ranked on CTU-13 Virut in 4/4 seeds — host-level P@100 structurally capped at bad/100, do not use as headline metric.

---

**References** — superscript roman numerals map to bibliography (`References.md`). For guide submission, roman `lxxxvii` = 87 corresponds to numeric 1 below — convert per guide's style.

1. Debar et al. (1999); 2. Axelsson (2000); 3. Chandola et al. (2009); 4. Garcia-Teodoro et al. (2009); 5. Bhuyan et al. (2014); 6. Sommer & Paxson (2010); 7. Patcha & Park (2007); 8. Hodge & Austin (2004); 9. Lashkari CICFlowMeter; 10. Moore et al. (2005); 11. Williams et al. (2006); 12. Sharafaldin et al. (2018) CICIDS2017; 13. Ring et al. (2019); 14. Heng et al. (2024); 15. Durieux & Gevenois (2010); 16. Franceschini (2010); 17. Zitt & Bassecoulard (2008); 18. Biglia & Butler (2005); 19. Sakurada & Yairi (2014); 20. An & Cho (2015); 21. Hodge (2004); 22. Patcha (2007); 23. Merton (1963); 24. Manten (1968); 25. Zuckerman (1968); 26. Meadows (1974); 27. Klaic (1990); 28. Vimala & Pulla Reddy (1996); 29. Gupta & Karisiddappa (1998); 30. Mahapatra & Bhagavan Doss (2000); 31. Seglen & Aksnes (2000); 32. Moed (2000); 33. Arunachalam & Doss (2000); 34. Kannappanavar & Vijayakumar (2001); 35. Farahat (2002); 36. Suresh Kumar & Garg (2005); 37. Calero et al. (2006); 38. Park (2008); 39. Tijssen & Van Leeuwen (2001); 40. Thomaidis et al. (2003); 41. Leydesdorff (2004); 42. Surulinathi et al. (2007); 43. Tseng et al. (2009); 44. Annibaldi et al. (2010); 45. Padma (2010); 46. Garfield (1983); 47. Mehrotra & Lancaster (1984); 48. Raghuram & Madhavi (1996); 49. Raina et al. (1995); 50. Bandyopadhyay (2001); 51. Arunachalam et al. (1998); 52. Arunachalam (2000); 53. Arunachalam & Gunasekaran (2002); 54. Kademani et al. (2006); 55. Kademani et al. (2007); 56. UNEP E-waste Manual, NIST CSF, ENISA.

