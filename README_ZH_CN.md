# project-manager

[🇬🇧 EN](https://github.com/greenzorro/project-manager/blob/main/README.md) | [🇨🇳 中文](https://github.com/greenzorro/project-manager/blob/main/README_ZH_CN.md)

轻量级、本地优先的需求管理与产出统计系统。SQLite 为唯一数据源，AI agent 负责所有数据操作，静态 HTML 负责日常展示。

> 了解这套系统的设计理念：[什么是AI原生的数据系统？](https://victor42.eth.limo/post/ai-native-data-system)

## 核心价值

- **零基础设施**：单文件 SQLite，无需服务器、注册或云服务
- **Agent 原生**：专为 AI agent 操作设计（如 [opencode](https://github.com/anomalyco/opencode)），对话即可管理
- **统一工作流**：需求、排期、交付、封面图产出集中管理
- **精美看板**：自动生成 HTML 仪表盘，含日历视图、任务追踪、ECharts 交互统计
- **数据主权**：所有数据完全在本地

日常增删改和排期跟 Agent 对话即可；看板用浏览器自己打开。

## 页面

四个自动生成的 HTML 页面（在数据目录的 `html/` 下；示例数据为 `demo/html/`）：

- **排期日历** — 月视图排期，按负责人着色，节假日标记
- **近期任务** — 进行中 + 最近完成的任务，带缩略图
- **历史任务** — 全部已完成需求，缩略图卡片网格
- **统计仪表盘** — KPI 指标、月度统计、需求方 Top、类型分布、财年对比

## 自定义

仪表盘围绕一组特定的需求类型（UI设计、数据分析、课程制作、内部提效）和 4 月起的财年构建。若工作流不同，让 Agent 帮你改 `render_html.py`、`render_queries.py`、`render_components.py` 和 `schema.sql`——封面价值公式、KPI、图表标签、类型颜色都很直观。

## 配置

| 常量 | 默认值 | 用途 |
|------|--------|------|
| `COVER_VALUE_MULTIPLIER` | 20 | 封面图价值乘数（`cover_count` × 乘数） |
| `FY_START_MONTH` | 4 | 财年起始月 |
| `FY_END_MONTH` | 3 | 财年结束月 |

定义在 `scripts/config.py`。改排期前请自己确认「今天」的日期。

---

Created by [Victor42](https://victor42.work/) & [Agent Vik](https://github.com/agent-vik)
