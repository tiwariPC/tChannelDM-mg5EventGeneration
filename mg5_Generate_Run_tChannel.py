# /usr/bin/env python3
# ================================================================================
# MADGRAPH SCAN ORCHESTRATION SCRIPT
# EXECUTION COMMANDS:
#     1. S3M Majorana - Single Mode:
#         python mg5_Generate_Run_tChannel.py --proc s3m --mode single
#     2. S3M Majorana - Grid Mode:
#         python mg5_Generate_Run_tChannel.py --proc s3m --mode grid
#     3. S3D Dirac - Single Mode:
#         python mg5_Generate_Run_tChannel.py --proc s3d --mode single
#     4. S3D Dirac - Grid Mode:
#         python mg5_Generate_Run_tChannel.py --proc s3d --mode grid
#     5. Both Systems - Single Mode:
#         python mg5_Generate_Run_tChannel.py --proc both --mode single
#     6. Both Systems - Grid Mode:
#         python mg5_Generate_Run_tChannel.py --proc both --mode grid
# CUSTOM SINGLE POINT EXAMPLE:
#     python mg5_Generate_Run_tChannel.py --proc s3m --mode single --mMED 1500 --mDM 500 --dms3d 2.5
# BACKGROUND EXECUTION (DETACHED SHIFT):
#     nohup python mg5_Generate_Run_tChannel.py --proc both --mode grid > orchestrator.log 2>&1 &
# TMUX (PERSISTENT SESSION):
#     tmux new-session -d -s mg5_Generate_Run_tChannel 'python mg5_Generate_Run_tChannel.py --proc both --mode grid 2>&1 | tee orchestrator.log'
#     tmux attach -t mg5_Generate_Run_tChannel          # reattach
#     tmux kill-session -t mg5_Generate_Run_tChannel    # stop
# ================================================================================

import itertools
import argparse
import subprocess
import os
import re
import sys
import shutil
import threading

# MG5_EXE = "/Users/ptiwari/Development/EventGen/mg5amcnlo-3x/bin/mg5_aMC"
MG5_EXE = "/home/ptiwari/EventGen/mg5amcnlo-3x/bin/mg5_aMC"


CARD_DIR = "textFiles"
LOG_DIR  = "logFiles"

parser = argparse.ArgumentParser(description="Generate and execute MadGraph scan configurations.")
parser.add_argument("--proc", choices=["s3m", "s3d", "both"], required=True, help="Process to run: s3m, s3d, or both")
parser.add_argument("--mode", choices=["single", "grid", "both"], required=True, help="Execution mode: single, grid, or both")
parser.add_argument("--mMED", type=int, default=1000, help="Mediator mass (MASS 2000005) for single mode")
parser.add_argument("--mDM",  type=int, default=100,  help="DM mass for single mode")
parser.add_argument("--dms3d", type=float, default=1.0, help="DMS3D 3 3 value for single mode")
args = parser.parse_args()

os.makedirs(CARD_DIR, exist_ok=True)
os.makedirs(LOG_DIR,  exist_ok=True)

mass_MED_vals = [10, 50, 100, 200, 500, 750, 1000, 1500, 2000, 2500]
mass_DM_vals  = [1, 10, 50, 100, 200, 500, 750, 1000, 1500, 2000]
dms3d_vals    = [1.0, 1.5, 2.0, 2.2, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]



s3m_proc = """import model DMSimpt_v2_0 -res_S3M_br --modelname
define p = g u c d s u~ c~ d~ s~ b b~
define j = p
define excl = ys3qd3 ys3qd3~ xd xd~ xs xv xc xw xc~ xw~
generate   p p > b  xm b~ xm  DMT=2 QCD=2 QED=0 @0 / excl
add process p p > b  xm xm    DMT=2 QCD=1 QED=0 @1 / excl
add process p p > b~ xm xm    DMT=2 QCD=1 QED=0 @2 / excl
add process p p > b  b  xm xm DMT=2 QCD=2 QED=0 @3 / excl
add process p p > b~ b~ xm xm DMT=2 QCD=2 QED=0 @4 / excl
output tChannel_S3M_br_bbMET_bMET_LO -nojpeg
"""

s3d_proc = """import model DMSimpt_v2_0 -res_S3D_br --modelname
define p = g u c d s u~ c~ d~ s~ b b~
define j = p
define excl = ys3qd3 ys3qd3~ xm xs xv xc xw xc~ xw~
generate   p p > b  xd b~ xd~ DMT=2 QCD=2 QED=0 @0 / excl
add process p p > b  xd xd~   DMT=2 QCD=1 QED=0 @1 / excl
add process p p > b~ xd xd~   DMT=2 QCD=1 QED=0 @2 / excl
output tChannel_S3D_br_bbMET_bMET_LO -nojpeg
"""

def extract_output_name(proc_string):
    match = re.search(r"output\s+([^\s\-]+)", proc_string)
    if match:
        return match.group(1)
    raise ValueError("Could not extract output folder name.")

# Decoupled masses (1e9) and zeroed couplings from restrict_S3M_br / restrict_S3D_br.
# S3M active: PDG 52 (Xm). S3D active: PDG 57 (Xd). Both share same inactive mediators/states.
_DECOUPLE_MASSES = [
    51, 53, 56, 58,
    1000001, 1000002, 1000003, 1000004, 1000005, 1000006,
    1000011, 1000012, 1000013, 1000014, 1000015, 1000016,
    2000001, 2000002, 2000003, 2000004, 2000006,
    2000011, 2000013, 2000015,
    5910001, 5910002, 5910003, 5910004, 5910005, 5910006,
    5910011, 5910012, 5910013, 5910014, 5910015, 5910016,
    5920001, 5920002, 5920003, 5920004, 5920005, 5920006,
    5920011, 5920013, 5920015,
]

_ZERO_COUPLINGS = [
    ("DMF1E", [(1,1),(2,2),(3,3)]),
    ("DMF1L", [(1,1),(2,2),(3,3)]),
    ("DMF3D", [(1,1),(2,2),(3,3)]),
    ("DMF3Q", [(1,1),(2,2),(3,3)]),
    ("DMF3U", [(1,1),(2,2),(3,3)]),
    ("DMS1E", [(1,1),(2,2),(3,3)]),
    ("DMS1L", [(1,1),(2,2),(3,3)]),
    ("DMS3D", [(1,1),(2,2)]),       # (3,3) is active — set per point
    ("DMS3Q", [(1,1),(2,2),(3,3)]),
    ("DMS3U", [(1,1),(2,2),(3,3)]),
]

def run_card_settings(dm_pdg):
    inactive_dm = 57 if dm_pdg == 52 else 52
    lines = [
        "  set run_card ebeam1 6800\n",
        "  set run_card ebeam2 6800\n",
        "  set run_card nevents 10000\n",
        "  set param_card DECAY 2000005 Auto\n",
        "  set param_card DECAY 51 0.0\n",
        "  set param_card DECAY 52 0.0\n",
        "  set param_card DECAY 53 0.0\n",
        "  set param_card DECAY 56 0.0\n",
        "  set param_card DECAY 57 0.0\n",
        "  set param_card DECAY 58 0.0\n",
        f"  set param_card MASS {inactive_dm} 1.0e9\n",
    ]
    for pdg in _DECOUPLE_MASSES:
        lines.append(f"  set param_card MASS {pdg} 1.0e9\n")
    for block, indices in _ZERO_COUPLINGS:
        for i, j in indices:
            lines.append(f"  set param_card {block} {i} {j} 0.0\n")
    return "".join(lines)

def format_run_name(mMED, mDM, dms3d):
    lam_str = str(dms3d).replace('.', 'p')
    return f"mMed{mMED}_mDM{mDM}_lam{lam_str}"

def make_point_card(output_name, dir_exists, mMED, mDM, dms3d, dm_pdg):
    run_name = format_run_name(mMED, mDM, dms3d)
    launch_line = f"launch {output_name} --name={run_name}\n" if dir_exists else f"launch --name={run_name}\n"
    return (run_name, "".join([
        launch_line,
        run_card_settings(dm_pdg),
        f"  set param_card MASS 2000005 {mMED}\n",
        f"  set param_card MASS {dm_pdg} {mDM}\n",
        f"  set param_card DMS3D 3 3 {dms3d}\n",
    ]))

def grid_points():
    for mMED, mDM, dms3d in itertools.product(mass_MED_vals, mass_DM_vals, dms3d_vals):
        if mMED > mDM:
            yield mMED, mDM, dms3d

_INTERESTING = re.compile(
    r"(Running Survey|Cross-section|finished|ERROR|launch|"
    r"mMed|mDM|lam|Results|Generating|==)"
)

def _tail_log(log_path, stop_event, prefix):
    import time
    while not os.path.exists(log_path):
        if stop_event.is_set():
            return
        time.sleep(0.5)
    with open(log_path) as f:
        f.seek(0, 2)
        while not stop_event.is_set():
            line = f.readline()
            if not line:
                time.sleep(0.3)
                continue
            line = line.rstrip()
            if line and _INTERESTING.search(line):
                print(f"  [{prefix}] {line}", flush=True)

def execute_madgraph(card_name, active_mode):
    if not os.path.exists(MG5_EXE):
        sys.exit(f"Error: MadGraph binary missing at {MG5_EXE}")

    log_name = os.path.join(LOG_DIR, f"madgraph_{os.path.basename(card_name).replace('.txt', '.log')}")
    prefix = "S3M" if "S3M" in card_name else "S3D"
    print(f"[START] {card_name} → {log_name}", flush=True)

    stop_event = threading.Event()
    tailer = threading.Thread(target=_tail_log, args=(log_name, stop_event, prefix), daemon=True)
    tailer.start()

    with open(log_name, "w") as log_file:
        result = subprocess.run([MG5_EXE, "-f", card_name], stdout=log_file, stderr=subprocess.STDOUT)

    stop_event.set()
    tailer.join(timeout=2)

    if result.returncode != 0:
        raise RuntimeError(f"MG5 exited {result.returncode} — check {log_name}")
    print(f"  [DONE] {card_name}", flush=True)

def reset_param_card(output_name):
    cards_dir = os.path.join(output_name, "Cards")
    default = os.path.join(cards_dir, "param_card_default.dat")
    active  = os.path.join(cards_dir, "param_card.dat")
    if os.path.exists(default):
        shutil.copy2(default, active)

def run_single_point(base_proc, base_filename, output_name, dir_exists, mMED, mDM, dms3d):
    prefix = "S3M" if "S3M" in base_filename else "S3D"
    dm_pdg = 52 if prefix == "S3M" else 57
    if dir_exists:
        reset_param_card(output_name)
    run_name, card_body = make_point_card(output_name, dir_exists, mMED, mDM, dms3d, dm_pdg)
    card_basename = f"point_{run_name}_{base_filename}"
    card_filename = card_basename  # write to cwd so MG5 resolves output dir correctly
    with open(card_filename, "w") as f:
        if not dir_exists:
            f.write(base_proc)
        f.write(card_body)
    print(f"  [{prefix}] running {run_name} (DM PDG={dm_pdg})", flush=True)
    try:
        execute_madgraph(card_filename, prefix)
    finally:
        dest = os.path.join(CARD_DIR, card_basename)
        if os.path.exists(card_filename):
            os.replace(card_filename, dest)

def write_and_run(base_proc, base_filename):
    output_name = extract_output_name(base_proc)
    dir_exists = os.path.isdir(output_name)
    modes_to_run = ["single", "grid"] if args.mode == "both" else [args.mode]

    for active_mode in modes_to_run:
        if active_mode == "single":
            if args.mMED <= args.mDM:
                raise ValueError(f"Kinematic violation: mMED ({args.mMED}) <= mDM ({args.mDM})")
            run_single_point(base_proc, base_filename, output_name, dir_exists,
                             args.mMED, args.mDM, args.dms3d)
        elif active_mode == "grid":
            failed = []
            points = list(grid_points())
            prefix = "S3M" if "S3M" in base_filename else "S3D"
            print(f"[{prefix}] grid: {len(points)} points", flush=True)
            for i, (mMED, mDM, dms3d) in enumerate(points, 1):
                run_name = format_run_name(mMED, mDM, dms3d)
                print(f"  [{prefix}] point {i}/{len(points)}: {run_name}", flush=True)
                try:
                    run_single_point(base_proc, base_filename, output_name, dir_exists,
                                     mMED, mDM, dms3d)
                    dir_exists = True
                except Exception as e:
                    print(f"  [{prefix}] SKIP {run_name}: {e}", flush=True)
                    failed.append(run_name)
            if failed:
                print(f"[{prefix}] failed points ({len(failed)}): {', '.join(failed)}", flush=True)

procs_to_run = []
if args.proc in ["s3m", "both"]:
    procs_to_run.append((s3m_proc, "run_S3M_scan.txt"))
if args.proc in ["s3d", "both"]:
    procs_to_run.append((s3d_proc, "run_S3D_scan.txt"))

threads = [threading.Thread(target=write_and_run, args=(proc_string, filename), name=filename)
           for proc_string, filename in procs_to_run]
for t in threads:
    t.start()
for t in threads:
    t.join()
