#!/usr/bin/env python3
"""
Kinematic comparison: S3D vs S3M DM pair system.
DM system reconstructed from final-state DM particles (status==1):
  S3M: PID ±52 (Majorana xm)
  S3D: PID ±57 (Dirac xd)

Output: kinematics_S3D_S3M.pdf  (4 panels × 2 scenarios)

Panel layout per scenario:
  P1 — M_phi scan  : fix M_DM=1,    lam=2.5, vary M_phi (10→1000 GeV)
  P2 — M_DM scan   : fix M_phi=500, lam=2.5, vary M_DM  (all valid)
  P3 — lambda scan : fix M_phi=1000, M_DM=1, vary lam   (1.0→5.0)
  P4 — ratio scan  : fix lam=2.5, ratio M_DM/M_phi~0.1, vary M_phi

Observable shown: MET = p_T of the DM pair.
"""

import argparse
import glob
import os
import re

import awkward as ak
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np
import uproot
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D

hep.style.use(hep.style.CMS)

# ----------------------------------------------------------------
S3M_DIR = "tChannel_S3M_br_bbMET_bMET_LO/Events"
S3D_DIR = "tChannel_S3D_br_bbMET_bMET_LO/Events"
DM_PID  = {"S3M": 52, "S3D": 57}

MET_BINS = np.linspace(0, 1500, 75)

# CMS color palette (6 colors); cycle linestyle for >6 curves
CMS_COLORS = ["#5790fc", "#f89c20", "#e42536", "#964a8b", "#9c9ca1", "#7a21dd"]
LINE_STYLES = ["-", "--", ":", "-."]

def cms_color_ls(i):
    """Return (color, linestyle) for curve index i using CMS palette."""
    return CMS_COLORS[i % len(CMS_COLORS)], LINE_STYLES[i // len(CMS_COLORS) % len(LINE_STYLES)]


# Panel definitions
PANELS = [
    dict(
        title=r"$M_{\chi}=1$ GeV, $\lambda=2.5$ — vary $M_{\phi}$",
        filt=lambda mm, md, l: md == 1 and abs(l - 2.5) < 0.01,
        label=lambda mm, md, l: rf"$M_{{\phi}}={mm}$ GeV",
        ref_label=lambda mm, md, l: mm == 10,
        ref_str=r"M_{\phi}=10\,\mathrm{GeV}",
    ),
    dict(
        title=r"$M_{\phi}=1000$ GeV, $\lambda=2.5$ — vary $M_{\chi}$",
        filt=lambda mm, md, l: mm == 1000 and abs(l - 2.5) < 0.01 and md <= 750,
        label=lambda mm, md, l: rf"$M_{{\chi}}={md}$ GeV",
        ref_label=lambda mm, md, l: md == 1,
        ref_str=r"M_{\chi}=1\,\mathrm{GeV}",
    ),
    dict(
        title=r"$M_{\phi}=1000$ GeV, $M_{\chi}=1$ GeV — vary $\lambda$",
        filt=lambda mm, md, l: mm == 1000 and md == 1,
        label=lambda mm, md, l: rf"$\lambda={l}$",
        ref_label=lambda mm, md, l: abs(l - 1.0) < 0.01,
        ref_str=r"\lambda=1.0",
    ),
    dict(
        title=r"$M_{\chi}/M_{\phi}\approx 0.1$, $\lambda=2.5$ — vary $M_{\phi}$",
        filt=lambda mm, md, l: abs(l - 2.5) < 0.01 and abs(md / mm - 0.1) < 0.02,
        label=lambda mm, md, l: rf"$M_{{\phi}}={mm}$, $M_{{\chi}}={md}$ GeV",
        ref_label=lambda mm, md, l: mm == 100,
        ref_str=r"M_{\phi}=100\,\mathrm{GeV}",
    ),
]
# ----------------------------------------------------------------


def build_run_index(events_dir):
    idx = {}
    for banner in sorted(glob.glob(f"{events_dir}/mMed*/*_tag_1_banner.txt")):
        tm = re.match(r"(mMed\d+_mDM\d+_lam[^_]+)_tag_\d+_banner", os.path.basename(banner))
        if not tm:
            continue
        m = re.match(r"mMed(\d+)_mDM(\d+)_lam(.+)", tm.group(1))
        if not m:
            continue
        key = int(m.group(1)), int(m.group(2)), float(m.group(3).replace("p", "."))
        root = os.path.join(os.path.dirname(banner), "unweighted_events.root")
        if os.path.exists(root):
            idx[key] = root
    return idx


def load_met(root_path, dm_pid):
    with uproot.open(root_path) as f:
        t = f["LHEF"]
        d = t.arrays(
            ["Particle/Particle.PID", "Particle/Particle.Status",
             "Particle/Particle.Px",  "Particle/Particle.Py"],
            library="ak",
        )
    mask = (abs(d["Particle/Particle.PID"]) == dm_pid) & \
           (d["Particle/Particle.Status"] == 1)
    px = np.array(ak.sum(d["Particle/Particle.Px"][mask], axis=1))
    py = np.array(ak.sum(d["Particle/Particle.Py"][mask], axis=1))
    return np.sqrt(px**2 + py**2)


def make_hist(vals, bins, normalize):
    counts, edges = np.histogram(vals, bins=bins)
    if normalize:
        area = counts.sum() * (edges[1] - edges[0])
        counts = counts / area if area > 0 else counts.astype(float)
    return counts, edges


def make_panel_page(pdf, panel_def, idx_s3m, idx_s3d, normalize):
    """One page: left=S3M, right=S3D."""
    filt   = panel_def["filt"]
    lbl    = panel_def["label"]
    is_ref = panel_def["ref_label"]

    keys = sorted(k for k in idx_s3m if filt(*k))
    if not keys:
        print(f"  [skip] no points for: {panel_def['title']}")
        return

    color_ls = {k: cms_color_ls(i) for i, k in enumerate(keys)}

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    for ax_main, (scen_name, idx, pid) in zip(axes, [
            ("S3M (Majorana)", idx_s3m, DM_PID["S3M"]),
            ("S3D (Dirac)",    idx_s3d, DM_PID["S3D"])]):

        histograms = {}
        for k in keys:
            if k not in idx:
                continue
            h, edges = make_hist(load_met(idx[k], pid), MET_BINS, normalize)
            histograms[k] = h

        centres = 0.5 * (edges[:-1] + edges[1:])
        legend_handles = []
        for k in keys:
            if k not in histograms:
                continue
            h = histograms[k]
            c, ls = color_ls[k]
            lw = 2.2 if is_ref(*k) else 1.6
            ax_main.step(centres, h, where="mid", color=c, ls=ls, lw=lw)
            legend_handles.append(
                Line2D([0], [0], color=c, ls=ls, lw=1.8, label=lbl(*k)))

        ax_main.set_yscale("log")
        ax_main.set_ylim(bottom=1e-6 if normalize else 0.5)
        ax_main.set_xlim(0, MET_BINS[-1])
        ax_main.set_ylabel("Normalised events / GeV" if normalize else "Events / GeV")
        ax_main.set_xlabel(r"$p_T^{\rm miss}$ [GeV]")
        ax_main.grid(alpha=0.2, which="both")
        ax_main.legend(handles=legend_handles, loc="upper right",
                       framealpha=0.8, fontsize=14)
        ax_main.set_title(scen_name, fontsize=15, pad=38)

        hep.cms.label(
            text="Work in progress",
            ax=ax_main,
            loc=0,
            fontsize=16,
            com=13.6,
        )

    fig.suptitle(panel_def["title"], fontsize=15, y=1.01)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {panel_def['title'][:60]}")


def main():
    parser = argparse.ArgumentParser(description="Plot MET kinematics for S3M/S3D.")
    parser.add_argument("--normalize", action="store_true", default=True,
                        help="Normalise histograms to unit area (default: on)")
    parser.add_argument("--no-norm", dest="normalize", action="store_false",
                        help="Plot raw event counts")
    args = parser.parse_args()

    print("Building run index...")
    idx_s3m = build_run_index(S3M_DIR)
    idx_s3d = build_run_index(S3D_DIR)
    print(f"  S3M: {len(idx_s3m)},  S3D: {len(idx_s3d)} runs")

    out_dir = "kinematics"
    os.makedirs(out_dir, exist_ok=True)
    suffix = "norm" if args.normalize else "raw"

    panel_names = ["mphi_scan", "mchi_scan", "lambda_scan", "ratio_scan"]
    for panel, name in zip(PANELS, panel_names):
        out_path = os.path.join(out_dir, f"kinematics_{name}_{suffix}.pdf")
        pdf = PdfPages(out_path)
        make_panel_page(pdf, panel, idx_s3m, idx_s3d, args.normalize)
        pdf.close()
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
