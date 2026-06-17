#!/usr/bin/env python3
"""Cross section as a function of (m_med, m_DM, lambda) for S3D and S3M.

Outputs (one PDF per plot):
  xsec_scatter_S3D.pdf / xsec_scatter_S3M.pdf   — 3D scatter
  xsec_heatmap_S3D.pdf / xsec_heatmap_S3M.pdf   — (m_phi, m_DM) facet heatmaps
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

hep.style.use(hep.style.CMS)

XSEC_DIR = "xsection"
os.makedirs(XSEC_DIR, exist_ok=True)

s3d = pd.read_csv(os.path.join(XSEC_DIR, "xsec_S3D_br.csv"))
s3m = pd.read_csv(os.path.join(XSEC_DIR, "xsec_S3M_br.csv"))
data = {"S3D_Dirac": ("S3D (Dirac)", s3d), "S3M_Majorana": ("S3M (Majorana)", s3m)}

vmin = min(np.log10(df.xsec_pb).min() for _, df in data.values())
vmax = max(np.log10(df.xsec_pb).max() for _, df in data.values())

CMAP = "viridis"

# ── 3D scatter, one PDF per scenario ─────────────────────────────────────────
med_ticks = [10, 50, 100, 200, 500, 1500, 2500]
dm_ticks  = [1, 10, 50, 100, 200, 500, 1000, 2000]

for key, (name, df) in data.items():
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(projection="3d")
    sc = ax.scatter(np.log10(df.m_med), np.log10(df.m_dm), df["lambda"],
                    c=np.log10(df.xsec_pb), cmap=CMAP,
                    vmin=vmin, vmax=vmax, s=40, depthshade=False)
    ax.set_xticks(np.log10(med_ticks))
    ax.set_xticklabels([str(v) for v in med_ticks], fontsize=12)
    ax.set_yticks(np.log10(dm_ticks))
    ax.set_yticklabels([str(v) for v in dm_ticks], fontsize=12)
    ax.tick_params(axis="z", labelsize=12)
    ax.set_xlabel(r"$M_{\phi}$ [GeV]", labelpad=18, fontsize=12)
    ax.set_ylabel(r"$M_{\chi}$ [GeV]", labelpad=18, fontsize=12)
    ax.set_zlabel(r"$\lambda$", labelpad=10, fontsize=12)
    ax.set_title(name, fontsize=14, pad=14)
    cbar = fig.colorbar(sc, ax=ax, shrink=0.55, pad=0.12)
    cbar.set_label(r"$\log_{10}(\sigma\,[\mathrm{pb}])$", fontsize=16)
    ax2d = fig.add_axes([0.1, 0.88, 0.8, 0.08], frameon=False)
    ax2d.axis("off")
    hep.cms.label(text="Internal", ax=ax2d, loc=0, fontsize=14, com=13.6)
    out = os.path.join(XSEC_DIR, f"xsec_scatter_{key}.pdf")
    with PdfPages(out) as pdf:
        pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")

# ── facet heatmaps, one PDF per scenario ─────────────────────────────────────
lam_values = sorted(s3d["lambda"].unique())
ncol = 5
nrow = int(np.ceil(len(lam_values) / ncol))

for key, (name, df) in data.items():
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.5 * ncol, 3.2 * nrow),
                             sharex=True, sharey=True)
    axes = np.atleast_2d(axes)
    im = None
    for k, lam in enumerate(lam_values):
        ax = axes[k // ncol, k % ncol]
        sel = df[np.isclose(df["lambda"], lam)]
        grid = sel.pivot_table(index="m_dm", columns="m_med", values="xsec_pb")
        im = ax.pcolormesh(grid.columns, grid.index, np.log10(grid.values),
                           cmap=CMAP, vmin=vmin, vmax=vmax, shading="nearest")
        ax.set_title(rf"$\lambda={lam:g}$", fontsize=11)
        ax.tick_params(labelsize=10)
    for k in range(len(lam_values), nrow * ncol):
        axes[k // ncol, k % ncol].axis("off")
    for ax in axes[-1, :]:
        ax.set_xlabel(r"$M_{\phi}$ [GeV]", fontsize=12)
    for ax in axes[:, 0]:
        ax.set_ylabel(r"$M_{\chi}$ [GeV]", fontsize=12)
    cbar = fig.colorbar(im, ax=axes, shrink=0.85)
    cbar.set_label(r"$\log_{10}(\sigma\,[\mathrm{pb}])$", fontsize=16)
    fig.suptitle(rf"{name}: $\sigma(M_{{\phi}}, M_{{\chi}})$ per $\lambda$",
                 fontsize=14, y=1.06)
    fig.text(0.02, 1.02, "CMS  Internal",
             fontsize=13, fontweight="bold", transform=fig.transFigure)
    fig.text(0.98, 1.02, r"$\sqrt{s}=13.6$ TeV",
             fontsize=12, ha="right", transform=fig.transFigure)
    out = os.path.join(XSEC_DIR, f"xsec_heatmap_{key}.pdf")
    with PdfPages(out) as pdf:
        pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")
