# Weekly Review — Hermes Agent 使用周报 (Excel)

自动生成 Duruo & Raya 使用 Hermes Agent 的周报，每周四晚 20:00 CST 执行。
输出为 6-sheet Excel 文件 (.xlsx)，重点在 Skill 和 Memory 的优化建议。

## 架构

```
Phase 1 (20:00 CST, no_agent, 零成本)
  collect_weekly_data.py → data/weekly_data_YYYY-MM-DD.json
         │
Phase 2 (20:05 CST, agent-based, DeepSeek V4 Pro)
  Agent reads JSON + skills/ + MEMORY.md + USER.md
  → LLM analysis (topics, skills redundancy, memory)
  → generate_excel_report.py renders 6-sheet .xlsx
  → MEDIA: delivery to Feishu chat
```

## 文件结构

```
weekly-review/
├── README.md
├── scripts/
│   ├── collect_weekly_data.py          ← Phase 1: 数据采集 (no_agent, 已修复skill检测)
│   ├── generate_excel_report.py        ← 6-sheet .xlsx 生成器 (OfficeCLI)
│   ├── generate_report.py              ← (旧版HTML生成器，保留备用)
│   ├── cron_report_prompt.md           ← Phase 2 Agent prompt (LLM分析+Excel)
│   ├── pack_handoff.py                 ← 交接打包工具
│   └── audit_skills.py                 ← Skill深度审计工具
├── data/
│   ├── weekly_data_*.json              ← Phase 1 输出
│   └── llm_analysis_*.json             ← Phase 2 LLM分析结果
└── output/
    ├── weekly_report_*.xlsx            ← 最终6-sheet报告
    └── report_*.html                   ← (旧版HTML输出)
```

## Excel 报告内容 (6个Sheet)

| Sheet | 内容 | 数据来源 |
|-------|------|---------|
| 概览 | 本周统计汇总 | Phase 1 JSON |
| 主题清单 | 每条会话分类+进展 | Phase 1 + LLM分析 |
| 使用分析 | Duruo/Raya 对比 | Phase 1 JSON |
| Skill调用 | 147个Skill的调用记录 | Phase 1 + skill扫描 |
| **Skill优化** | 冗余/需增强/建议新增 | **LLM分析 (核心产出)** |
| **Memory优化** | 过长/冗余/错位/过时条目 | **LLM分析 (核心产出)** |

## Cron 作业

| 名称 | 时间 (CST) | 模式 | 模型 | 作业 ID |
|------|-----------|------|------|---------|
| weekly-review-phase1 | 周四 20:00 | no_agent (零成本) | — | a1d8269806e9 |
| weekly-review-phase2 | 周四 20:05 | agent (LLM分析) | **DeepSeek V4 Pro** | de1b74c3b9f7 |

## 手动测试

```bash
# Phase 1: 采集数据
cd ~/hermes-workspace/projects/weekly-review
python3 scripts/collect_weekly_data.py

# Phase 2: 生成Excel (含LLM分析JSON)
# (由cron自动执行，也可手动生产测试用LLM分析文件)
python3 scripts/generate_excel_report.py \
  --json data/weekly_data_$(date +%Y-%m-%d).json \
  --output output/weekly_report_test.xlsx
```

## Git 跟踪

脚本已同步到 `~/src/hermes-agent/scripts/weekly-review/`，推送至 `local/cron-scripts` 分支。

```bash
git checkout local/cron-scripts
git add scripts/weekly-review/
git commit -m "feat(scripts): weekly-review Excel report pipeline"
git push origin local/cron-scripts
```
