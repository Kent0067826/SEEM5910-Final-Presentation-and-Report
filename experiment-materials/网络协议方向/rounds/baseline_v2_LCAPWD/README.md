# 基线 v2：LCAPWD = LCAP + 第 36 轮 PFC 看门狗（2026-11-02 起，用户同意并入）

- 是什么：LCAP 的全部设置，加 `ROBOT_PFC_WD=300 ROBOT_PFC_WD_DRAIN=1`（有任务、不在故障、在原格站满 300 拍、所在门 300 拍没车进 → 这一拍不执行门口规则）。第 36 轮确认 +1.73% [+0.50, +3.21]（对 LCAP，官方 8 + 留出 12，每图 20 局）。
- 程序：`bin\lifelong-p36a.exe` 或之后任何从 `src\dev_src_p37` 往后复制的程序（p37a 开看门狗、不开 ROBOT_ESCAPE 时与 p36a 逐局相同，已核对 4 局）。
- 实例表：`harness\lcap_env17_wd.json`（开发 17 实例）、`harness\lcap_env_p18confirm_wd.json`（官方 8 + roomU 留出 12）。用 `run_dev_cfg.py` 并设环境变量 `LCAP_CFG=lcap_env17_wd.json`。
- 现成结果（方法名统一为 LCAPWD，不用重跑）：
  - `regress_9700_101.jsonl`：回归用，room250 / room300 / roomZ3_194 / roomQ_254，种子 9700 × 101 = 1130 / 1194 / 752 / 1530（p37a）。
  - `dev_p103_104.jsonl`：17 实例 × 9700–9704 × 规划 103、104（取自第 36 轮 DWD300）。
  - `confirm_p18maps_11800_149_150.jsonl`：官方 8 + 留出 12 × 11800–11809 × 149、150（取自第 36 轮确认）。
- 以后新机制默认和 LCAPWD 比（新机制在看门狗之上再加）；和旧 LCAP 的比较只作参照。
- 运行器（2026-11-02 起）：模拟进程以“低于正常”优先级启动；并行数用 6（用户反映电脑卡）。
