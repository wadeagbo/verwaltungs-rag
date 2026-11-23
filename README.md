# Complete Thesis — LaTeX Source (Revised Descriptive Version)

**Title:** Pattern of White Blood Cell Functional Indices Among Seropositive
Hepatitis B and C Students in Some Selected Tertiary Institutions in Oyo State

**By:** Wale-Adeagbo Bolatito Victoria (AU22/01/MLS 093)

---

## Contents

| File | Description |
|------|-------------|
| `Complete_Thesis.tex` | Full LaTeX source — single, self-contained file (references inlined) |
| `Complete_Thesis.pdf` | Pre-compiled PDF (59 pages) |
| `figures/` | The 6 data figures used in Chapter Four |

---

## How to compile

Keep the `figures/` folder in the **same directory** as `Complete_Thesis.tex`.

### Option 1 — Overleaf (easiest)
1. Create a new blank project at overleaf.com.
2. Upload `Complete_Thesis.tex` **and** the whole `figures/` folder.
3. Set the compiler to **pdfLaTeX** and click *Recompile*.

### Option 2 — Command line
```bash
pdflatex Complete_Thesis.tex
pdflatex Complete_Thesis.tex   # run 2–3 times for TOC + references
pdflatex Complete_Thesis.tex
```

### Option 3 — Local editor (TeXstudio / TeXworks)
Open `Complete_Thesis.tex`, set the compiler to **pdfLaTeX**, and build.

---

## What this version reflects

This is the **revised, descriptive** thesis incorporating the supervisor's
feedback:

- Standardised title; descriptive cross-sectional design (no control group,
  no HBV-vs-HCV comparison).
- Objectives with no citations; demographics included as an objective; the
  fourth objective relates demographics to the WBC parameters.
- Hypotheses framed around the demographic–WBC relationship (no controls).
- Greatly expanded Literature Review (~20 pp): virus biology, structure &
  genome, pathophysiology of HBV and HCV separately, epidemiology, aetiology,
  diagnosis (serological / haematological / biochemical / histological),
  and management.
- **Table 2.1** — comparative characteristics of the five hepatitis viruses.
- Methodology: names the University of Ibadan, the 4 mL blood volume, sample
  size (n = 27), and the Sysmex KX-21N analyser.
- One presentation per variable (demographics in a table; WBC data in charts).
- Figures use colour **plus hatching** so they remain readable in black-and-white
  printing.
- Expanded questionnaire (age, sex, BMI, height, BP, temperature, admission,
  length of stay) in the appendix.
- 37 references, all within ~10 years (2016–2025), alphabetised.

---

## Notes

- Font: Palatino (`mathpazo`). Standard packages only (graphicx, booktabs,
  longtable, hyperref, etc.) — available in any full TeX distribution.
- The references are already embedded in `Complete_Thesis.tex`; there is no
  separate bibliography file to manage.
