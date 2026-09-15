# Evidence Pack — Claims + Defense + Experiments (single folder)

This folder aggregates the 3 sources that together are the defensible claim. Originals stay in their canonical places — this folder is an index + convenience copies (no fork).

| What | Canonical path | Why it matters |
|------|----------------|----------------|
| **Experimental proofs** | `experiments/report_cards.md` | RC-01…RC-32 — every number's method, seed, device, config. **Source of truth for any claim.** |
| **Lab notebook** | `CHANGELOG.md` | Append-only dated entries, newest on top. Detail behind each RC. |
| **Full reference** | `docs/guides/COMPLETE_REFERENCE.md` §23 | Viva/TGPT source of truth — bumps on every major finding. |
| **Headline numbers** | `docs/report/Chapter4_Design_and_Modelling.md:40-41` | Week-4 freeze: 0.9996±0.0001 (v2 0.9997), IDS2018 top-11, CTU-13 #1 |
| **Methodology** | `docs/report/Chapter3_Methodology.md` | Held-out protocol, fusion, determinism flags |
| **Comparison vs papers** | `docs/paper/papers_faceoff.md` + `papers_profiles.md` | Where we beat PIKACHU/Kitsune and why |
| **Defense deck** | `docs/presentations/week3-presentation.html` | Slides for review / viva |
| **Handover / defense checklist** | `HANDOVER.md` + `CLAUDE.md` (gotchas 1–25) | Failure modes examiners will ask |

**How to use in viva:**
1. Quote headline → point to `experiments/report_cards.md:RC-26` + `CHANGELOG.md:2026-08-25`
2. Show protocol → `docs/report/Chapter3_Methodology.md:34-36` (HELD-OUT, 4 seeds, GPU deterministic)
3. Show defense → `docs/presentations/week3-presentation.html` + `CLAUDE.md:Design decisions`

**No duplication rule:** edit the canonical file, not the copy. If you need a one-folder handout, run:
```powershell
Copy-Item experiments/report_cards.md docs/evidence/
Copy-Item CHANGELOG.md docs/evidence/
Copy-Item docs/guides/COMPLETE_REFERENCE.md docs/evidence/
```
