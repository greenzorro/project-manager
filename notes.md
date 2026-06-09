# 项目管理 项目备忘录

## 项目概述

以本地 SQLite 为唯一数据源，CLI + AI agent 负责写入和维护，本地静态 HTML 负责日常展示。

- 数据源：`pm.db`（位于数据目录，见下方架构说明）
- 操作入口：`scripts/pm.py` + `skills/project-manager.md`
- 展示层：`calendar.html`、`recent.html`、`history.html`、`dashboard.html`
- 缩略图：本地 WebP，800px 长边

## 代码与数据分离

项目代码和数据分开存放，通过 `PM_DATA_DIR` 环境变量控制。

- 设置了 `PM_DATA_DIR`：数据目录为指定路径
- 未设置：自动使用项目内的 `demo/` 目录（含示例数据，clone 即用）

数据目录内包含：`pm.db`、`backup.sql`、`html/`、`thumbnails/`

## 整体架构

```
本地 SQLite（唯一数据源）── 位于数据目录
    │
    ├── scripts/pm.py ─────────→ doctor / stats / render-html / schedule move
    │
    ├── Agent(project-manager) ←→ CRUD / 查询 / 交付 / 缩略图 / 排期
    │
    ├── html/ ─────────────────→ 日历 / 近期任务 / 历史任务 / 仪表盘
```

## 文件结构

```
project-manager/
├── notes.md                   # 本文件
├── .env.example               # PM_DATA_DIR 配置示例
│
├── demo/                      # 示例数据（未设置 PM_DATA_DIR 时使用）
│   ├── pm.db
│   ├── backup.sql
│   ├── html/                  # 预生成的演示页面
│   └── thumbnails/
│
├── sql/
│   └── schema.sql             # 建表 DDL + VIEW 定义
│
├── scripts/
│   ├── pm.py                  # 统一 CLI 入口，只做参数解析和分发
│   ├── db.py                  # 数据库连接、路径解析、常量
│   ├── doctor.py              # 数据健康检查
│   ├── stats.py               # 统计查询
│   ├── schedule_ops.py        # 排期写库操作
│   ├── render_html.py         # 静态 HTML 展示层生成
│   ├── output.py              # 终端表格输出
│   ├── init.py                # 初始化：建表 + stat_periods 种子数据
│   ├── compute_periods.py     # 统计周期日期计算
│   └── schedule_utils.py      # 排期后移 + 周末拆分
│
└── skills/
    └── project-manager.md     # 本地数据 Skill（CRUD、查询、排期后移）
```

## 表结构

### requirements（需求）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | TEXT PK (UUID) | ✅ | |
| `name` | TEXT | ✅ | 需求名称 |
| `project_id` | TEXT FK → projects | ✅ | 所属项目 |
| `type_id` | TEXT FK → req_types | ✅ | 需求类型 |
| `received_y/m/d` | INTEGER | ✅ | 接收日期 |
| `requesters` | TEXT | ✅ | 需求方（单个名称；系统占位为 `__sys__`） |
| `ui_pages` | INTEGER | | UI 页面数（UI设计交付前必填） |
| `expected_y/m/d` | INTEGER | | 期望交付 |
| `actual_y/m/d` | INTEGER | | 实际交付（写入即标记交付） |
| `delivery_url` | TEXT | | 交付物链接 |
| `delivery_thumbnail` | TEXT | | thumbnails/ 下相对路径 |
| `notes` | TEXT | | 备注 |

### schedules（排期）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | TEXT PK (UUID) | |
| `requirement_id` | TEXT FK → requirements | 关联需求 |
| `start_y/m/d` | INTEGER | 开始日期 |
| `end_y/m/d` | INTEGER | 结束日期 |
| `owner` | TEXT | 负责人（`-` 表示系统占位，如公共假期） |

### cover_outputs（封面图输出）

| 字段 | 类型 |
|------|------|
| `id` | TEXT PK (UUID) |
| `date_y/m/d` | INTEGER |
| `count` | INTEGER |

### stat_periods（统计周期）

只存 id/name/type，日期由 `compute_periods.py` 计算写回。17 条：12 月 + 2 学期 + 3 财年（当前财年 + 前 2 个）。

| 字段 | 说明 |
|------|------|
| `name` | M01-4月 ~ M12-3月, S1, S2, FY-{start} ~ FY-{end} |
| `type` | 月 / S / 财年 |
| `start_* / end_*` | 周期起止日期 |
| `start_before_* / end_after_*` | 起止 ±1 天（v_stats_by_period JOIN 用） |

## 统计周期日期规则

所有周期（月/S/财年）锚定同一个当前财年，未来周期数据为 0。

财年起始月由 `db.py` 中的 `FY_START_MONTH`（默认 4）和 `FY_END_MONTH`（默认 3）定义。学期为 S1（4~9月）和 S2（10~3月），月份从 M01（4月）到 M12（3月）。

```python
# 财年：FY_START_MONTH 月 ~ 次年 FY_END_MONTH 月。FY-XX 中 XX = 结束年
def _fiscal_dates(name):  # FY-25 -> 2024-04-01 ~ 2025-03-31
    fy_end_year = int(name[3:]) + 2000
    return (fy_end_year-1, FY_START_MONTH, 1), (fy_end_year, FY_END_MONTH, last_day)

# 当前财年起始年
def _current_fy_start(today):  # 6月 -> 今年FY_START_MONTH月；1月 -> 去年FY_START_MONTH月
    return today.year if today.month >= FY_START_MONTH else today.year - 1
```

`compute_periods.py` 在每次需要时重算全部 17 个周期并写回。

## SQL VIEW

- `v_requirements`：状态、time_span、days_to_delivery
- `v_schedules`：duration、关联需求名和项目名
- `v_stats_by_period`：需求数/UI页面/报表/课程/封面价值/内部提效，按交付日期归入各周期

## 展示层

```bash
python scripts/pm.py render-html
```

输出到数据目录下的 `html/`：

- `calendar.html`：排期日历。窗口为过去 2 个月 + 当前月 + 未来 2 个月，打开时默认滚动到当前月。
- `recent.html`：近期任务。展示完成日期为空或最近 7 天内完成的需求，按完成状态分组；缩略图使用正方形 cover、center top 布局，交付链接直接可点击。
- `history.html`：历史任务。全量展示完成日期不为空的需求，以缩略图为核心，自适应卡片网格布局；交付链接直接可点击。
- `dashboard.html`：统计仪表盘。展示 KPI（需求数量/UI页面/封面图价值/内部提效）、月度统计、需求方 Top 10、按类型统计（环形饼图）、报表/课程财年统计。

HTML 页面是数据库快照；数据库变更后重新运行 `render-html` 刷新。

导航顺序：日历 / 近期任务 / 历史任务 / 仪表盘。快捷键：`1` 日历，`2` 近期任务，`3` 历史任务，`4` 仪表盘。

缩略图解析规则：

1. 优先使用 `requirements.delivery_thumbnail` 的第一个文件名。
2. 如果文件不存在，回退到 `thumbnails/{requirement_id}.webp`。
3. 如果仍不存在，显示类型占位。

## 排期后移

CLI 和 agent 通过 `scripts/schedule_ops.py` + `scripts/schedule_utils.py` 处理排期后移：

- `add_business_days(date, days)`：跳过周六日，计算新日期
- `split_cross_weekend(start, end)`：跨周末自动拆为多段
- 第一段 UPDATE 原记录，后续段 INSERT 新记录

触发词：「把张三从 X 号起的任务往后推 N 天」。

## 使用指南

### 统一 CLI

```bash
python scripts/pm.py doctor
python scripts/pm.py stats requester
python scripts/pm.py compute-periods
python scripts/pm.py render-html
python scripts/pm.py schedule move --owner 张三 --from 2026-06-05 --days 3
python scripts/pm.py schedule move --owner 张三 --from 2026-06-05 --days 3 --apply
```

- `doctor`：检查数据库完整性、外键、关键必填字段、日期合法性、视图可查询和实际 schema 约束。
- `stats requester`：按需求方统计需求数、已交付数、进行中数，默认排除 `__sys__` 系统占位需求。
- `compute-periods`：重算 `stat_periods` 日期。
- `render-html`：生成 `calendar.html`、`recent.html`、`history.html`、`dashboard.html` 四个静态展示页面。
- `schedule move`：排期后移；默认只预览，必须加 `--apply` 才写入本地数据库。

### 初始化

```bash
python scripts/init.py
```

创建空数据库 + schema + 17 条 stat_periods + 计算日期。财年按当前日期动态生成（current_fy - 2 ~ current_fy，共 3 个财年）。

### 添加需求

告诉 agent：「加个需求：XXX，YYY项目，UI设计，6月5号收到，预计6月12号交付」。agent 写入 requirements 表。

### 标记交付

告诉 agent：「把 XXX 需求标记为已交付」。agent 写入 actual_y/m/d。

**交付日期确定**：若交付时未指定日期，系统默认取该需求在 `schedules` 中的最大结束日期作为实际交付日期；若该需求未在日历中排期，则拒绝交付并提示用户排期缺失。

**约束**：UI设计类必须先填 `ui_pages > 0` 才能交付；`delivery_url` 和 `delivery_thumbnail` 为空时会提醒但不阻止。

### 添加缩略图

告诉 agent 图片路径，自动缩放至 800px 长边 WebP，存入数据目录的 `thumbnails/`，更新 `delivery_thumbnail`。

### 排期后移

告诉 agent：「把张三从 6 月 5 号起的任务往后推 3 个工作日」。agent 先调用 `python scripts/pm.py schedule move --owner 张三 --from 2026-06-05 --days 3` 预览，确认后加 `--apply` 写入本地数据库。

### 刷新展示层

```bash
python scripts/pm.py render-html
```

## 业务常量

定义在 `scripts/db.py`：

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `COVER_VALUE_MULTIPLIER` | 20 | 封面图价值乘数 |
| `FY_START_MONTH` | 4 | 财年起始月 |
| `FY_END_MONTH` | 3 | 财年结束月 |

## 决策记录

| 议题 | 决策 |
|------|------|
| 存储 | SQLite，单文件 |
| ID | UUID |
| 日期格式 | y/m/d 三列拆分 |
| 计算字段 | SQL VIEW（3 个） |
| 统计周期 | 同财年锚定，未来周期为 0 |
| 财年定义 | FY_START_MONTH 月 ~ 次年 FY_END_MONTH 月，命名用结束年 |
| 本地展示层 | 静态 HTML 快照，按需生成 |
| 代码与数据分离 | PM_DATA_DIR 环境变量，默认 demo/ |
| 排期后移 | 跳过周末，自动拆段 |
| 缩略图 | 800px 长边 WebP |
| 数据校验 | 外键约束 + NOT NULL |