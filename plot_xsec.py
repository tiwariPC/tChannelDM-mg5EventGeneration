#!/usr/bin/env python3
"""
plot_xsec.py
------------
Cross section vs mediator mass for S3M_br and S3D_br.

Curves: M_chi = 10, 100, 1000 GeV  (linestyle)
        lambda = 1.0, 2.2, 3.0      (colour)

One PDF per scenario (S3M, S3D) + one combined.

Usage:
  python3 plot_xsec.py
  python3 plot_xsec.py --linear
  python3 plot_xsec.py --fmt png
"""

import argparse
import os

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import mplhep as hep
import numpy as np
import pandas as pd

hep.style.use(hep.style.CMS)

# ── config ────────────────────────────────────────────────────────────────────
XSEC_DIR    = "xsection"
LAMBDA_SEL  = [1.0, 2.2, 3.0]
MCHI_SEL    = [10, 100, 500]
MCHI_LS     = {10: "-", 100: "--", 500: ":"}
MCHI_LABELS = {m: rf"$M_{{\chi}}={m}$ GeV" for m in MCHI_SEL}

CMS_COLORS  = ["#5790fc", "#f89c20", "#e42536", "#964a8b", "#9c9ca1", "#7a21dd"]

SCENARIO_INFO = {
    "S3M_br": dict(marker="o", label="S3M", subtitle="Scalar mediator, Majorana $\\chi$ (PDG 52)"),
    "S3D_br": dict(marker="s", label="S3D", subtitle="Scalar mediator, Dirac $\\chi$ (PDG 57)"),
}

# ── helpers ───────────────────────────────────────────────────────────────────
def load_data(path):
    df = pd.read_csv(path)
    for col in ["m_med", "m_dm", "lambda"]:
        df[col] = df[col].round(4)
    return df


def make_plot(df, scenario, output, logy=True):
    sdf = df[(df["scenario"] == scenario) &
             (df["m_dm"].isin(MCHI_SEL)) &
             (df["lambda"].isin(LAMBDA_SEL))].copy()
    if sdf.empty:
        print(f"  [skip] no data for {scenario}")
        return

    info      = SCENARIO_INFO.get(scenario, dict(marker="o", title=scenario))
    lam_color = {l: CMS_COLORS[i] for i, l in enumerate(LAMBDA_SEL)}

    fig, ax = plt.subplots(figsize=(10, 8))

    for lam in LAMBDA_SEL:
        for mchi in MCHI_SEL:
            sub = sdf[(np.isclose(sdf["lambda"], lam)) &
                      (sdf["m_dm"] == mchi)].sort_values("m_med")
            if sub.empty:
                continue
            ax.plot(sub["m_med"], sub["xsec_pb"],
                    color=lam_color[lam],
                    linestyle=MCHI_LS[mchi],
                    linewidth=1.8,
                    marker=info["marker"],
                    markersize=5)

    lam_handles = [mlines.Line2D([], [], color=lam_color[l], linewidth=2,
                                 label=rf"$\lambda={l}$")
                   for l in LAMBDA_SEL]
    mchi_handles = [mlines.Line2D([], [], color="black",
                                  linestyle=MCHI_LS[m], linewidth=2,
                                  label=MCHI_LABELS[m])
                    for m in MCHI_SEL]

    leg1 = ax.legend(handles=lam_handles, title=r"Coupling $\lambda$",
                     loc="upper right", framealpha=0.9)
    ax.add_artist(leg1)
    ax.legend(handles=mchi_handles, title=r"DM mass $M_{\chi}$",
              loc="lower left", framealpha=0.9)

    ax.set_xlabel(r"Mediator mass $M_{\phi}$ [GeV]")
    ax.set_ylabel(r"Cross section $\sigma$ [pb]")
    if logy:
        ax.set_yscale("log")
    ax.set_xlim(left=0)
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
    if not logy:
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())

    hep.cms.label(text="Work in Progress", ax=ax, loc=0, fontsize=20, com=13.6)
    info = SCENARIO_INFO[scenario]
    ax.text(0.5, 0.97, info["label"],
            transform=ax.transAxes, ha="center", va="top",
            fontsize=16, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8))
    ax.text(0.5, 0.90, info["subtitle"],
            transform=ax.transAxes, ha="center", va="top",
            fontsize=14)

    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    print(f"wrote {output}")
    plt.close(fig)


def make_combined_plot(df, output, logy=True):
    df = df[df["m_dm"].isin(MCHI_SEL) & df["lambda"].isin(LAMBDA_SEL)].copy()
    scenarios = [s for s in ["S3M_br", "S3D_br"] if s in df["scenario"].values]
    if not scenarios:
        print("  [skip] no data for combined plot")
        return

    lam_color   = {l: CMS_COLORS[i] for i, l in enumerate(LAMBDA_SEL)}
    scen_marker = {s: SCENARIO_INFO[s]["marker"] for s in scenarios}

    fig, ax = plt.subplots(figsize=(9, 6))

    for scenario in scenarios:
        sdf = df[df["scenario"] == scenario]
        for lam in LAMBDA_SEL:
            for mchi in MCHI_SEL:
                sub = sdf[(np.isclose(sdf["lambda"], lam)) &
                          (sdf["m_dm"] == mchi)].sort_values("m_med")
                if sub.empty:
                    continue
                ax.plot(sub["m_med"], sub["xsec_pb"],
                        color=lam_color[lam],
                        linestyle=MCHI_LS[mchi],
                        linewidth=1.8,
                        marker=scen_marker[scenario],
                        markersize=5)

    lam_handles = [mlines.Line2D([], [], color=lam_color[l], linewidth=2,
                                 label=rf"$\lambda={l}$")
                   for l in LAMBDA_SEL]
    mchi_handles = [mlines.Line2D([], [], color="black",
                                  linestyle=MCHI_LS[m], linewidth=2,
                                  label=MCHI_LABELS[m])
                    for m in MCHI_SEL]
    scen_handles = [mlines.Line2D([], [], color="black",
                                  marker=scen_marker[s], linewidth=0,
                                  markersize=7, label=s.replace("_", r"\_"))
                    for s in scenarios]

    leg1 = ax.legend(handles=lam_handles, title=r"$\lambda$",
                     loc="upper right", framealpha=0.9)
    leg2 = ax.legend(handles=mchi_handles, title=r"$M_{\chi}$",
                     loc="lower left", framealpha=0.9)
    ax.add_artist(leg1)
    ax.add_artist(leg2)
    ax.legend(handles=scen_handles, title="Scenario",
              loc="center right", framealpha=0.9)

    ax.set_xlabel(r"Mediator mass $M_{\phi}$ [GeV]")
    ax.set_ylabel(r"Cross section $\sigma$ [pb]")
    if logy:
        ax.set_yscale("log")
    ax.set_xlim(left=0)
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
    if not logy:
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())

    hep.cms.label(text="Work in Progress", ax=ax, loc=0, fontsize=20, com=13.6)

    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    print(f"wrote {output}")
    plt.close(fig)


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--linear", action="store_true")
    parser.add_argument("--fmt", default="pdf")
    args = parser.parse_args()

    logy = not args.linear
    fmt  = args.fmt

    s3m = load_data(os.path.join(XSEC_DIR, "xsec_S3M_br.csv"))
    s3d = load_data(os.path.join(XSEC_DIR, "xsec_S3D_br.csv"))
    df  = pd.concat([s3m, s3d], ignore_index=True)

    os.makedirs(XSEC_DIR, exist_ok=True)

    make_plot(df, "S3M_br",
              os.path.join(XSEC_DIR, f"xsec_vs_mmed_S3M_br.{fmt}"), logy)
    make_plot(df, "S3D_br",
              os.path.join(XSEC_DIR, f"xsec_vs_mmed_S3D_br.{fmt}"), logy)
    make_combined_plot(df,
              os.path.join(XSEC_DIR, f"xsec_vs_mmed_combined.{fmt}"), logy)


if __name__ == "__main__":
    main()
