#!/bin/bash
# 打包第 41 轮（wait-v31）：说明、图、协议与分析、数据与源码压缩包
set -e
R41=/home/claude/r41; V=/home/claude/proj/v10
D=/home/claude/r41/deliver/wait-v31; S=/home/claude/r41/src
rm -rf /home/claude/r41/deliver /home/claude/r41/src
mkdir -p "$D" "$S"
cp $R41/实验结果与分析.md $R41/fig_r41_*.png "$D"/
cp $V/protocol_v31.md $V/analysis_model_r41.md $V/analysis_dev_r41.md $V/analysis_r41.md $V/analysis_r41.json $V/test_freeze_v31.json /home/claude/r40/net_credits_r41.json "$D"/
mkdir -p "$S"/source-v28 "$S"/程序 "$S"/scripts "$S"/modelscripts "$S"/batches "$S"/探索 "$S"/model_data
cp -r $V/dev_src_v28/CMakeLists.txt $V/dev_src_v28/build_linux.sh $V/dev_src_v28/compile.sh $V/dev_src_v28/default_planner $V/dev_src_v28/inc $V/dev_src_v28/linux_shim $V/dev_src_v28/python $V/dev_src_v28/src "$S"/source-v28/
cp $V/bin/lifelong-v28a "$S"/程序/
cp $V/scripts/r41_*.py $V/scripts/ana_r41*.py "$S"/scripts/
for f in flow.py netlp.py bounds.py latency.py ana_flow.py ana_bounds.py ana_latency.py ana_legs.py ana_profile.py fig_model.py fig_confirm.py dev_cap.py diag_fc.py regiongraph.py replay.py runfull.py batch_measure.py; do cp /home/claude/r40/$f "$S"/modelscripts/; done
cp $R41/pack41.sh "$S"/modelscripts/
cp -r $V/batches/regress_v28a $V/batches/r41-dev $V/batches/r41-test $V/batches/r41-short "$S"/batches/
cp $V/batches_r41dev.log $V/batches_r41test.log "$S"/batches/
cp /home/claude/r40/dev/cap.jsonl /home/claude/r40/dev/diag_fc.jsonl "$S"/探索/
cp -r $V/maps_r40 "$S"/
for f in flow.json bounds.json profiles.json legs.json latency_pairs.json; do cp /home/claude/r40/batch/$f "$S"/model_data/; done
cat > "$S"/说明.txt <<'EOF'
第 41 轮（网络建模第 3–5 步）数据与源码
source-v28/   lifelong-v28a 的源码（ROBOT_NET=1：名额 = 带宽 × 时延；ROBOT_CUT2_SIGFIX 门对去重修正）；Linux 下 bash build_linux.sh
程序/          lifelong-v28a（Linux）
scripts/      r41_common / r41_dev / r41_test / ana_r41dev / ana_r41（放在仓库 workspace/scripts/ 下运行）
modelscripts/ 建模脚本：flow.py 流量矩阵，netlp.py 最大并发流，bounds.py 上限，latency.py 时延模型，及汇总、画图、限流探索、roomFC 诊断
batches/      regress_v28a（回归）、r41-dev（开发）、r41-test（确认）、r41-short（1200 步）
探索/          cap.jsonl（写协议前的限流探索）、diag_fc.jsonl（确认后的 roomFC 诊断）
maps_r40/     确认用留出地图（生成脚本、sha256）
model_data/   建模中间结果（来自第 40 轮测量批次）
EOF
find "$S" -name __pycache__ -type d -prune -exec rm -r {} +
(cd "$S" && zip -qr "$D"/wait-v31-数据与源码.zip .)
ls -la "$D"
