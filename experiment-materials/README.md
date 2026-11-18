# SEEM5910 实验资料

课程报告以[仓库根目录中的 v97](../Robot_Traffic_Course_Report_v97.docx)为准。本目录收录本地「5910 实验」中较新的报告和实验资料，以及核对现有报告所需的早期原始证据。

## 第二部分 网络建模与优化思路

- [第 29 轮建模研究](网络协议方向/报告源/网络建模研究_第29轮.md)、[补充笔记](网络协议方向/报告源/网络建模研究_第29轮补充.md)和[建模测量记录](网络协议方向/rounds/p29)对应拓扑、门口和实际运动三个层次。
- [格子地图到房间网络](网络协议方向/报告源/图/en/en_03_map_to_network.png)、[门口通行规则](网络协议方向/报告源/图/en/en_06_door_rule.png)和[门 6 回放](网络协议方向/报告源/图/en/en_07_door6_filmstrip.png)可用来解释节点、共享链路和放行顺序。
- [正式版本源码](archive/workspace/dev_src_v36)、[执行器核对](archive/workspace/executor_check_r37.md)及[门控设置脚本](archive/workspace/scripts/r47_common.py)可用于核对选路、派单和执行的分工。[LoRR 许可证](work/lorr-start-kit/LICENSE)

## 第三部分 关键迭代与实验图解

- **正式评测**见 [r52b 实验协议](archive/workspace/protocol_r52b_baseline.md)、[640 局原始记录](archive/workspace/batches/r52b-baseline/rows.jsonl)、[汇总](archive/workspace/analysis_r52b.md)和[正式结果图](archive/rounds/wait-v42/fig_r52b_baseline.png)。八个实例四种方法各跑 20 局，可用来区分整套程序的提升与门控在修复后对照组上的增益。
- **关键迭代**可从[前 75 轮通读笔记](网络协议方向/报告源/通读/第1-75轮_通读笔记.md)、[协议方向通读笔记](网络协议方向/报告源/通读/协议方向_通读笔记.md)和[数字核对表](网络协议方向/报告源/通读/数字核对表.md)入手。第 36 轮[看门狗实验](网络协议方向/rounds/p36)是单独的确认。第 78 轮[开发结果](网络协议方向/rounds/p78/实验结果与分析.md)仍待确认。
- **较新的模型分析与图稿**见[第 115–117 轮分析](archive/protocol_direction/readability)、[更新日志](网络协议方向/日志)和[英文图](网络协议方向/报告源/图/en)。第 115–117 轮为离线分析。11 月 13–14 日日志主要记录报告、图稿和讲稿修订。

## 来源与复现

`archive/` 下的文件取自本地实验库提交 `d918211c7343681fe923787341117a25f0a94555`，沿用原相对路径。[实例配置和地图](网络协议方向/harness/data)来自本地实验目录。历史运行脚本保留了原 Linux 路径，原运行二进制 `lifelong-v36a` 未找到。原始结果和源码可供核对，重新跑正式批次需要先配置路径并构建程序。
