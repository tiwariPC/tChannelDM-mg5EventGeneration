#!/usr/bin/env python
"""
collect_xsec.py
---------------
Collects cross sections from MadGraph5 banner files for t-channel
S3M_br (Majorana) and S3D_br (Dirac) signal grids.

Reads:
  tChannel_S3M_br_bbMET_bMET_LO/Events/mMed*/mMed*_tag_1_banner.txt
  tChannel_S3D_br_bbMET_bMET_LO/Events/mMed*/mMed*_tag_1_banner.txt

Outputs:
  xsec_S3M_br.csv
  xsec_S3D_br.csv
  xsec_combined.csv  (both scenarios merged)

Usage:
  python collect_xsec.py
  python collect_xsec.py --dirs tChannel_S3M_br_bbMET_bMET_LO tChannel_S3D_br_bbMET_bMET_LO
  python collect_xsec.py --output my_xsec.csv
"""

import os
import re
import glob
import csv
import argparse


#------------------------------------------------------------
# Parse one banner file — returns dict of extracted values
#------------------------------------------------------------
def parse_banner(filepath):
    result = {
        'banner'  : filepath,
        'scenario': None,
        'run_tag' : None,
        'm_med'   : None,
        'm_dm'    : None,
        'lambda'  : None,
        'width'   : None,
        'xsec_pb' : None,
        'nevents' : None,
    }

    try:
        with open(filepath) as f:
            content = f.read()
    except Exception as e:
        print(f'WARNING: could not read {filepath}: {e}')
        return None

    # ── cross section ──────────────────────────────────────
    m = re.search(r'Integrated weight \(pb\)\s*:\s*([\d.eE+\-]+)', content)
    if m:
        result['xsec_pb'] = float(m.group(1))

    # ── number of events ───────────────────────────────────
    m = re.search(r'Number of Events\s*:\s*(\d+)', content)
    if m:
        result['nevents'] = int(m.group(1))

    # ── mediator mass (PDG 2000005) ────────────────────────
    m = re.search(r'^\s*2000005\s+([\d.eE+\-]+)\s*#\s*mys3d3',
                  content, re.MULTILINE | re.IGNORECASE)
    if m:
        result['m_med'] = float(m.group(1))

    # ── scenario from filepath (authoritative) ────────────
    # Both PDG 52 and 57 appear in every banner (one active,
    # one at model default ~13 GeV), so directory name is the
    # only reliable discriminator.
    if 'S3M' in filepath and 'S3D' not in filepath:
        active_scenario = 'S3M_br'
    elif 'S3D' in filepath and 'S3M' not in filepath:
        active_scenario = 'S3D_br'
    else:
        active_scenario = None  # truly combined or unknown dir

    # ── DM mass: pick PDG matching active scenario ─────────
    m52 = re.search(r'^\s*52\s+([\d.eE+\-]+)\s*#\s*mxm',
                    content, re.MULTILINE | re.IGNORECASE)
    m57 = re.search(r'^\s*57\s+([\d.eE+\-]+)\s*#\s*mxd',
                    content, re.MULTILINE | re.IGNORECASE)

    if active_scenario == 'S3M_br' and m52:
        result['m_dm']     = float(m52.group(1))
        result['scenario'] = 'S3M_br'
    elif active_scenario == 'S3D_br' and m57:
        result['m_dm']     = float(m57.group(1))
        result['scenario'] = 'S3D_br'
    else:
        # fallback: both active → Combined
        if m52 and float(m52.group(1)) < 1e8:
            result['m_dm']     = float(m52.group(1))
            result['scenario'] = 'S3M_br'
        if m57 and float(m57.group(1)) < 1e8:
            result['m_dm']     = float(m57.group(1))
            result['scenario'] = 'S3D_br'
        if (m52 and float(m52.group(1)) < 1e8 and
                m57 and float(m57.group(1)) < 1e8):
            result['scenario'] = 'Combined'

    # ── lambda (DMS3D 3 3) ─────────────────────────────────
    # find block DMS3D then entry 3 3
    m = re.search(
        r'(?i)BLOCK\s+DMS3D.*?\n(?:.*?\n)*?\s*3\s+3\s+([\d.eE+\-]+)',
        content, re.DOTALL)
    if m:
        result['lambda'] = float(m.group(1))

    # ── mediator width (PDG 2000005) ───────────────────────
    m = re.search(r'DECAY\s+2000005\s+([\d.eE+\-]+)',
                  content, re.IGNORECASE)
    if m:
        result['width'] = float(m.group(1))

    # ── run tag from filename ──────────────────────────────
    # format: mMed200_mDM1_lam0p5_tag_1_banner.txt
    basename = os.path.basename(filepath)
    m = re.match(r'(mMed.+?)_tag_\d+_banner', basename)
    if m:
        result['run_tag'] = m.group(1)

    return result


#------------------------------------------------------------
# Collect all banner files from given directories
#------------------------------------------------------------
def collect_banners(outdirs):
    rows = []
    for outdir in outdirs:
        pattern = os.path.join(outdir, 'Events', 'mMed*', '*banner.txt')
        banners = sorted(glob.glob(pattern))
        if not banners:
            print(f'WARNING: no banner files found in {outdir}/Events/')
            continue
        print(f'Found {len(banners)} banner(s) in {outdir}')
        for b in banners:
            row = parse_banner(b)
            if row and row['xsec_pb'] is not None:
                # infer scenario from directory name if not set
                if row['scenario'] is None:
                    if 'S3M' in outdir:
                        row['scenario'] = 'S3M_br'
                    elif 'S3D' in outdir and 'S3M' not in outdir:
                        row['scenario'] = 'S3D_br'
                    else:
                        row['scenario'] = 'Unknown'
                rows.append(row)
            else:
                print(f'WARNING: could not parse {b}')
    return rows


#------------------------------------------------------------
# Write CSV
#------------------------------------------------------------
def write_csv(rows, filepath):
    fieldnames = [
        'scenario', 'run_tag',
        'm_med', 'm_dm', 'lambda', 'width',
        'xsec_pb', 'nevents',
    ]
    # sort by scenario, m_med, m_dm, lambda
    rows_sorted = sorted(
        rows,
        key=lambda r: (
            r['scenario'] or '',
            r['m_med']    or 0,
            r['m_dm']     or 0,
            r['lambda']   or 0
        )
    )
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows_sorted)
    print(f'Written: {filepath}  ({len(rows_sorted)} rows)')


#------------------------------------------------------------
# Pretty print to terminal
#------------------------------------------------------------
def print_table(rows):
    rows_sorted = sorted(
        rows,
        key=lambda r: (
            r['scenario'] or '',
            r['m_med']    or 0,
            r['m_dm']     or 0,
            r['lambda']   or 0
        )
    )
    hdr = f"{'Scenario':<12} {'M_med':>8} {'M_DM':>8} {'lambda':>8} {'Width':>10} {'xsec (pb)':>14} {'Events':>8}"
    print()
    print(hdr)
    print('-' * len(hdr))
    for r in rows_sorted:
        print(
            f"{str(r['scenario']):<12} "
            f"{r['m_med'] or '?':>8} "
            f"{r['m_dm']  or '?':>8} "
            f"{r['lambda'] or '?':>8} "
            f"{r['width']  or '?':>10.4f} "
            f"{r['xsec_pb']:>14.6e} "
            f"{r['nevents'] or '?':>8}"
        )
    print()


#------------------------------------------------------------
# Main
#------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description='Collect cross sections from MadGraph banner files')
    parser.add_argument(
        '--dirs', nargs='+',
        default=[
            'tChannel_S3M_br_bbMET_bMET_LO',
            'tChannel_S3D_br_bbMET_bMET_LO',
            'tChannel_S3D_S3M_br_bbMET_bMET_LO',
        ],
        help='MadGraph output directories to scan')
    parser.add_argument(
        '--output', default=None,
        help='Output CSV filename (default: xsec_<scenario>.csv per scenario)')
    args = parser.parse_args()

    # filter to directories that actually exist
    existing_dirs = [d for d in args.dirs if os.path.isdir(d)]
    if not existing_dirs:
        print('ERROR: none of the specified directories exist.')
        print('Run from the directory containing your MadGraph output folders.')
        return

    rows = collect_banners(existing_dirs)

    if not rows:
        print('No cross sections found.')
        return

    print_table(rows)

    out_dir = 'xsection'
    os.makedirs(out_dir, exist_ok=True)

    if args.output:
        write_csv(rows, os.path.join(out_dir, args.output))
    else:
        scenarios = set(r['scenario'] for r in rows)
        for scenario in sorted(scenarios):
            scenario_rows = [r for r in rows if r['scenario'] == scenario]
            write_csv(scenario_rows, os.path.join(out_dir, f'xsec_{scenario}.csv'))
        write_csv(rows, os.path.join(out_dir, 'xsec_all.csv'))


if __name__ == '__main__':
    main()
