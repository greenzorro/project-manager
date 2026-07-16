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

## 页面

四个自动生成的 HTML 页面：

- **排期日历** — 月视图排期，按负责人着色，节假日标记
- **近期任务** — 进行中 + 最近 7 天完成的任务，带缩略图
- **历史任务** — 全部已完成需求，缩略图卡片网格
- **统计仪表盘** — KPI 指标、月度统计、需求方 Top 10、类型分布环形图、财年对比

## 快速开始

```bash
git clone https://github.com/greenzorro/project-manager.git
cd project-manager
python3 scripts/init.py
python3 scripts/pm.py render-html
open demo/html/dashboard.html
```

项目自带 `demo/` 目录，包含虚构示例数据，clone 即可体验全部功能。

## 集成 AI Agent

系统为 agent 驱动设计。集成步骤：

1. 将 `skills/SKILL.md` 复制到 agent 的 skills 目录（如 `~/.agents/skills/project-manager/SKILL.md`）
2. 更新复制文件中的路径引用，指向你的本地 clone 位置
3. 设置 `PM_DATA_DIR` 环境变量指向数据目录（或使用 `.env` 文件）：

```bash
PM_DATA_DIR=/path/to/your/data
```

未设置 `PM_DATA_DIR` 时，默认使用项目内的 `demo/`。

## 项目结构

```
project-manager/
├── notes.md                     # 开发者备忘录
├── README.md / README_ZH_CN.md  # 文档
├── .env.example                 # 环境变量配置示例
├── demo/                        # 示例数据（未设置 PM_DATA_DIR 时默认使用）
├── sql/schema.sql               # 建表 DDL + 视图定义
├── scripts/                     # CLI 工具和渲染引擎
└── skills/                      # AI agent skill 文件
```

## 依赖

- [Pillow](https://python-pillow.org/) — 缩略图图像处理（缩放 + WebP 转换）

其余 import 均来自 Python 标准库。

```bash
pip install Pillow
```

## 自定义

仪表盘围绕一组特定的需求类型（UI设计、数据分析、课程制作、内部提效）和 4 月起的财年构建。如果你的工作流不同，需要修改 `render_html.py`、`render_queries.py`、`render_components.py` 和 `schema.sql`——封面价值公式、KPI 指标、图表标签、类型颜色都很直观。既然你已经在用 AI agent 操作系统，直接告诉它帮你适配仪表盘即可。

## 配置

| 常量 | 默认值 | 用途 |
|------|--------|------|
| `COVER_VALUE_MULTIPLIER` | 20 | 封面图价值乘数（`cover_count` × 乘数） |
| `FY_START_MONTH` | 4 | 财年起始月 |
| `FY_END_MONTH` | 3 | 财年结束月 |

定义在 `scripts/config.py`。

---

Created by [Victor42](https://victor42.work/) & [Agent Vik](https://github.com/agent-vik)
