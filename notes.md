# 项目管理 项目备忘录

## 项目概述

本项目是本地优先的需求管理、排期管理与产出统计系统。SQLite 是唯一数据源，CLI 与 AI agent 负责数据写入和维护，静态 HTML 页面负责日常查看。

- 数据源：数据目录下的 `pm.db`
- 操作入口：`scripts/pm.py` 与 `skills/project-manager.md`
- 展示页面：`calendar.html`、`recent.html`、`history.html`、`dashboard.html`
- 缩略图：数据目录下 `thumbnails/` 中的 WebP 文件，推荐 800px 长边

## 代码与数据分离

项目代码和业务数据分开存放，通过 `.env` 或环境变量配置：

| 变量 | 说明 |
|------|------|
| `PM_DATA_DIR` | 数据目录；未设置时使用项目内 `demo/` |
| `PM_DEFAULT_PROJECT` | 创建需求时的默认项目名 |
| `PM_DEFAULT_OWNER` | 创建排期时的默认负责人 |

数据目录包含：

- `pm.db`
- `backup.sql`
- `html/`
- `thumbnails/`

## 整体架构

```
本地 SQLite（pm.db）
    │
    ├── scripts/pm.py ──────────────→ 统一 CLI
    │
    ├── requirement_ops.py ─────────→ 需求创建 / 交付 / 插入后推
    ├── schedule_ops.py ────────────→ 排期添加 / 移动 / 调整
    ├── holiday_ops.py ─────────────→ 公共假期 / 个人请假
    ├── thumbnail.py ───────────────→ 缩略图生成（缩放 + WebP + 写库）
    ├── schedule_utils.py ──────────→ 工作日与非工作日日期计算
    │
    ├── render_html.py ─────────────→ 页面生成入口
    ├── render_queries.py ──────────→ 展示层查询与聚合
    ├── render_components.py ───────→ HTML 组件 / CSS / JS
    │
    └── html/ ──────────────────────→ 静态展示页面
```

## 文件结构

```
project-manager/
├── notes.md
├── README.md / README_ZH_CN.md
├── .env.example
├── demo/
│   ├── pm.db
│   ├── backup.sql
│   ├── html/
│   └── thumbnails/
├── sql/
│   └── schema.sql
├── scripts/
│   ├── config.py              # .env、路径、默认值、业务常量
│   ├── db.py                  # SQLite 连接、备份、通用 DB 工具
│   ├── pm.py                  # 统一 CLI 入口
│   ├── requirement_ops.py     # 需求创建、交付、插入后推
│   ├── schedule_ops.py        # 排期添加、移动、调整
│   ├── holiday_ops.py         # 公共假期、个人请假
│   ├── thumbnail.py           # 缩略图生成（缩放 + WebP + 写库）
│   ├── schedule_utils.py      # 工作日、非工作日、日期拆段
│   ├── render_html.py         # HTML 页面生成入口
│   ├── render_queries.py      # 页面查询与统计聚合
│   ├── render_components.py   # 页面组件、CSS、JS
│   ├── compute_periods.py     # 统计周期日期计算
│   ├── doctor.py              # 数据健康检查
│   ├── stats.py               # 统计查询
│   ├── init.py                # 初始化数据库
│   └── output.py              # 终端表格输出
├── tests/
│   └── test_project_manager.py
└── skills/
    └── project-manager.md
```

## 表结构

### requirements（需求）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | TEXT PK | ✅ | UUID |
| `name` | TEXT | ✅ | 需求名称 |
| `project_id` | TEXT FK → projects | ✅ | 所属项目 |
| `type_id` | TEXT FK → req_types | ✅ | 需求类型 |
| `requesters` | TEXT | ✅ | 需求方；系统占位为 `__sys__` |
| `received_y/m/d` | INTEGER | ✅ | 接收日期 |
| `expected_y/m/d` | INTEGER | | 期望交付 |
| `actual_y/m/d` | INTEGER | | 实际交付 |
| `ui_pages` | INTEGER | | UI 页面数，UI设计交付前必填 |
| `delivery_url` | TEXT | | 交付物链接 |
| `delivery_thumbnail` | TEXT | | `thumbnails/` 下相对路径 |
| `notes` | TEXT | | 备注 |

### schedules（排期）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | TEXT PK | UUID |
| `requirement_id` | TEXT FK → requirements | 关联需求 |
| `start_y/m/d` | INTEGER | 开始日期 |
| `end_y/m/d` | INTEGER | 结束日期 |
| `owner` | TEXT | 负责人；`-` 表示公共假期 |

### cover_outputs（封面图输出）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | TEXT PK | UUID |
| `date_y/m/d` | INTEGER | 日期 |
| `count` | INTEGER | 数量 |

### stat_periods（统计周期）

`stat_periods` 存储周期名称与日期边界。日期由 `compute_periods.py` 自动计算，包含 12 个月、2 个学期、3 个财年。

| 字段 | 说明 |
|------|------|
| `name` | `M01-4月` ~ `M12-3月`、`S1`、`S2`、`FY-XX` |
| `type` | 月 / S / 财年 |
| `start_* / end_*` | 周期起止日期 |
| `start_before_* / end_after_*` | 起止 ±1 天，用于统计视图 JOIN |

## 视图

- `v_requirements`：需求状态、time_span、days_to_delivery
- `v_schedules`：排期 duration、需求名、项目名
- `v_stats_by_period`：需求数、UI 页面、报表、课程、封面价值、内部提效

## 日期与统计规则

业务常量定义在 `scripts/config.py`：

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `COVER_VALUE_MULTIPLIER` | 20 | 封面图价值乘数 |
| `FY_START_MONTH` | 4 | 财年起始月 |
| `FY_END_MONTH` | 3 | 财年结束月 |

财年以结束年命名：`FY-25` 表示 `2024-04-01` 到 `2025-03-31`。S1 为 4 月到 9 月，S2 为 10 月到次年 3 月。`compute_periods.py` 每次运行都会按当前日期重算全部统计周期。

## 排期规则

排期计算以工作日为基础：

- 周六、周日不是工作日。
- 公共假期记录在 `schedules` 表，`owner='-'`，需求名为 `__公共假期__`。
- 个人请假记录在 `schedules` 表，需求名为 `__请假__`，`owner` 为请假人。
- 新增排期、移动排期、调整排期会跳过周末、公共假期和对应负责人的个人请假。
- 跨非工作日的排期会拆成多个连续工作日段。
- 批量移动必须先 dry-run 预览，再显式 apply 写入。

## 展示层

```bash
python scripts/pm.py render-html
```

输出到数据目录下的 `html/`：

- `calendar.html`：排期日历。窗口为当前月前 3 个月到未来 3 个月，按负责人着色，打开时自动滚动到当前月。
- `recent.html`：近期任务。展示进行中需求和最近 7 天完成的需求，支持备注、缩略图和交付链接。
- `history.html`：历史任务。展示所有已完成需求，以缩略图卡片布局呈现。
- `dashboard.html`：统计仪表盘。展示 KPI、月度统计、财年对比、需求方 Top 10、类型分布。

HTML 页面是数据库快照；数据库变更后运行 `render-html` 刷新。

导航顺序：日历 / 近期任务 / 历史任务 / 仪表盘。快捷键：`1` 日历，`2` 近期任务，`3` 历史任务，`4` 仪表盘。

缩略图解析规则：

1. 优先使用 `requirements.delivery_thumbnail` 的第一个文件名。
2. 如果文件不存在，回退到 `thumbnails/{requirement_id}.webp`。
3. 如果仍不存在，显示类型占位。

## CLI

### 健康检查与展示

```bash
python scripts/pm.py doctor
python scripts/pm.py stats requester
python scripts/pm.py compute-periods
python scripts/pm.py render-html
```

### 需求

```bash
python scripts/pm.py requirement create \
  --name 需求名 --type UI设计 --requester 张三 --project 官方网站 \
  --owner 小王 --duration-days 3 --start 2026-06-10

python scripts/pm.py requirement deliver 需求名 --url https://example.com
python scripts/pm.py requirement thumbnail 需求名 交付缩略图.webp
python scripts/pm.py requirement thumbnail 需求名 --source 源图路径.png

python scripts/pm.py requirement insert \
  --name 新需求 --type 数据分析 --requester 张三 --before 目标需求 \
  --owner 小王 --duration-days 1 --push-days 1
```

### 排期

```bash
python scripts/pm.py schedule add 需求名 --start 2026-06-10 --end 2026-06-12 --owner 小王
python scripts/pm.py schedule move --owner 小王 --from 2026-06-10 --days 3    # 后移 3 天
python scripts/pm.py schedule move --owner 小王 --from 2026-06-10 --days -3   # 前移 3 天
python scripts/pm.py schedule move --owner 小王 --from 2026-06-10 --days 3 --apply
python scripts/pm.py schedule adjust <schedule_id> --days 2    # 延长 2 天
python scripts/pm.py schedule adjust <schedule_id> --days -2   # 缩短 2 天
```

### 假期与请假

```bash
python scripts/pm.py holiday add --start 2026-10-01 --end 2026-10-07
python scripts/pm.py holiday leave --owner 小王 --start 2026-08-04 --end 2026-08-05
```

Agent 操作规范详见 `skills/project-manager.md`。

## 初始化与测试

```bash
python scripts/init.py
python -m unittest discover -s tests
python -m py_compile scripts/*.py tests/*.py
```

`init.py` 创建空数据库、加载 schema、写入系统统计周期并计算周期日期。测试基于 `demo/pm.db` 的临时副本运行，不修改正式数据。

## 决策记录

| 议题 | 决策 |
|------|------|
| 存储 | SQLite 单文件 |
| ID | UUID |
| 日期格式 | y/m/d 三列 |
| 计算字段 | SQL VIEW |
| 数据目录 | `PM_DATA_DIR`，默认 `demo/` |
| 财年定义 | 4 月到次年 3 月，按结束年命名 |
| 展示层 | 静态 HTML 快照 |
| 排期 | 工作日感知，自动跳过周末、公共假期、个人请假 |
| 缩略图 | 本地 WebP |
| 数据校验 | 外键约束、NOT NULL、doctor 检查、单元测试 |
