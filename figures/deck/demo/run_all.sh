#!/usr/bin/env bash
# Rebuild the congestion demo from scratch with one command.
# Works on Linux and on Windows with WSL (Ubuntu). Needs: g++ (C++17), patch, python3 with numpy and pillow
#   (Ubuntu / WSL:  sudo apt install g++ patch python3-pip  &&  pip install numpy pillow).
#
#   bash figures/deck/demo/run_all.sh                 # work folder ~/doorflow_demo
#   bash figures/deck/demo/run_all.sh /some/folder    # or any folder
#
# 1. copies the project's simulator source (experiment-materials/网络协议方向/src/dev_src_p78) to <work>/sim, applies
#    demo_dump.patch (it only writes every robot's cell at every tick) and builds it with g++ -- once, a few minutes;
# 2. runs two 5,000-tick replays on the official room map with 250 robots, seed 9700, planner seed 101:
#    "none" (no door control) and "doorflow" (the formal settings) -> <work>/runs/{none,doorflow}/pos.bin, about 20 s;
# 3. rebuilds doorflow_demo.html, demo.gif, demo_t3000.png and demo_stats.json next to this script.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
WORK="${1:-$HOME/doorflow_demo}"
mkdir -p "$WORK" && WORK="$(cd "$WORK" && pwd)"
SRC="$REPO/experiment-materials/网络协议方向/src/dev_src_p78"
SIM="$WORK/sim"

for c in g++ patch python3; do
  command -v "$c" >/dev/null || { echo "missing: $c   (Ubuntu / WSL: sudo apt install g++ patch python3)"; exit 1; }
done
python3 -c "import numpy, PIL" 2>/dev/null || { echo "missing Python packages:  pip install numpy pillow"; exit 1; }

if [ -x "$SIM/build-linux/lifelong" ]; then
  echo "[1/3] simulator already built: $SIM/build-linux/lifelong"
else
  echo "[1/3] building the simulator in $SIM (only the first time; a few minutes)"
  rm -rf "$SIM" && cp -r "$SRC" "$SIM"
  if ! ( cd "$SIM" && patch -p0 --quiet src/CompetitionSystem.cpp < "$HERE/demo_dump.patch" \
         && tr -d '\r' < build_linux.sh > build_unix.sh && bash build_unix.sh > build.log 2>&1 ); then
    echo "build failed, see $SIM/build.log"; exit 1
  fi
fi

echo "[2/3] running the two replays (no door control, DoorFlow)"
DEMO_SIM="$SIM/build-linux/lifelong" DEMO_WORK="$WORK/runs" python3 "$HERE/run_demo.py"

echo "[3/3] building the demo page"
DEMO_WORK="$WORK/runs" python3 "$HERE/build_demo.py" > "$WORK/demo_stats.txt"
echo "done. Open this file in a browser:  $HERE/doorflow_demo.html"
