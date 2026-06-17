# t-Channel Dark Matter — MadGraph5 Event Generation

LO cross-section scans and kinematic studies for t-channel scalar mediator dark matter at the LHC (√s = 13.6 TeV).

Two signal models from **DMSimpt v2.0**:

| Model | Mediator | DM particle | PDG |
|-------|----------|-------------|-----|
| **S3M** | Scalar S3 (PDG 2000005) | Majorana χ (xm) | 52 |
| **S3D** | Scalar S3 (PDG 2000005) | Dirac χ (xd) | 57 |

Processes: `pp → b χ b̄ χ`, `pp → b χ χ`, `pp → b̄ χ χ`, `pp → b b χ χ`, `pp → b̄ b̄ χ χ` (bbMET + bMET signatures, LO).

---

## Parameter grid

| Parameter | Values |
|-----------|--------|
| M_φ (mediator) [GeV] | 10, 50, 100, 200, 500, 750, 1000, 1500, 2000, 2500 |
| M_χ (DM) [GeV] | 1, 10, 50, 100, 200, 500, 750, 1000, 1500, 2000 |
| λ (coupling DMS3D 3 3) | 1.0, 1.5, 2.0, 2.2, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0 |

Only kinematically valid points (M_φ > M_χ) are run. ~700 points per model.

---

## Scripts

| Script | Purpose |
|--------|---------|
| `mg5_Generate_Run_tChannel.py` | Orchestrate MG5 runs — generate process cards, set param/run cards, execute MG5 |
| `collect_xsec.py` | Parse MG5 banner files → extract cross sections → write CSV |
| `plot_xsec.py` | σ vs M_φ curves (CMS style), one PDF per scenario + combined |
| `plot_xsec_3d_full.py` | 3D scatter + (M_φ, M_χ) facet heatmaps of σ |
| `plot_kinematics.py` | MET distributions from LHE files — M_φ / M_χ / λ / ratio scans |

---

## Requirements

```
python >= 3.9
MadGraph5_aMC@NLO >= 3.x  (DMSimpt_v2_0 UFO model installed)
pandas
numpy
matplotlib
mplhep
uproot
awkward
```

---

## Usage

### 1. Generate events

```bash
# Single point (S3M): M_phi=1000, M_DM=100, lambda=1.0
python mg5_Generate_Run_tChannel.py --proc s3m --mode single --mMED 1000 --mDM 100 --dms3d 1.0

# Full grid (both models, parallel threads)
python mg5_Generate_Run_tChannel.py --proc both --mode grid

# Background (detached)
nohup python mg5_Generate_Run_tChannel.py --proc both --mode grid > orchestrator.log 2>&1 &

# tmux persistent session
tmux new-session -d -s mg5scan 'python mg5_Generate_Run_tChannel.py --proc both --mode grid 2>&1 | tee orchestrator.log'
```

> **Note:** Set `MG5_EXE` in `mg5_Generate_Run_tChannel.py` to your local MadGraph5 binary path.

### 2. Collect cross sections

```bash
python collect_xsec.py
# outputs: xsection/xsec_S3M_br.csv, xsection/xsec_S3D_br.csv, xsection/xsec_all.csv
```

### 3. Plot cross sections

```bash
python plot_xsec.py           # log scale (default)
python plot_xsec.py --linear  # linear scale
python plot_xsec.py --fmt png # PNG instead of PDF

python plot_xsec_3d_full.py   # 3D scatter + heatmaps
```

### 4. Plot kinematics

```bash
python plot_kinematics.py
# reads LHE files from MG5 output dirs
# outputs: kinematics/*.pdf
```

---

## Outputs

```
xsection/
  xsec_S3M_br.csv            # cross sections, S3M model
  xsec_S3D_br.csv            # cross sections, S3D model
  xsec_all.csv               # combined
  xsec_vs_mmed_S3M_br.pdf
  xsec_vs_mmed_S3D_br.pdf
  xsec_vs_mmed_combined.pdf
  xsec_scatter_S3D_Dirac.pdf
  xsec_scatter_S3M_Majorana.pdf
  xsec_heatmap_S3D_Dirac.pdf
  xsec_heatmap_S3M_Majorana.pdf

kinematics/
  kinematics_mphi_scan_{raw,norm}.pdf
  kinematics_mchi_scan_{raw,norm}.pdf
  kinematics_lambda_scan_{raw,norm}.pdf
  kinematics_ratio_scan_{raw,norm}.pdf
```

MG5 run directories (`tChannel_S3*_br_bbMET_bMET_LO/`) are excluded from the repo — they contain multi-GB event files.

---

## Model details

- UFO model: `DMSimpt_v2_0` with restricted cards `restrict_S3M_br` / `restrict_S3D_br`
- Inactive DM species and all non-S3 mediators decoupled to 10⁹ GeV
- Non-S3 couplings (DMF1E, DMF1L, DMF3D, DMF3Q, DMF3U, DMS1E, DMS1L, DMS3Q, DMS3U) set to zero
- Beam: 6800 GeV per beam (13.6 TeV), 10000 events per point
- Mediator width: `Auto`
