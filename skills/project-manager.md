# project-manager (Agent Skill)

本地 SQLite 项目管理。Agent 通过此 Skill 执行 CRUD、查询和页面生成。

**⚠️ 必须先读 `.env`**：每次操作前，先读取项目根目录的 `.env` 文件，获取路径和默认值：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PM_DATA_DIR` | 数据库及产物目录 | `demo/` |
| `PM_DEFAULT_PROJECT` | 默认项目名（加需求时自动填入） | — |
| `PM_DEFAULT_OWNER` | 默认执行人（加排期时自动填入） | —

**数据库**: 数据目录下的 `pm.db`（`PM_DATA_DIR` 指定或默认 `demo/`）。

## 表结构

### projects
| 字段 | 类型 |
|------|------|
| `id` | TEXT PK (UUID) |
| `name` | TEXT |

### req_types
| 字段 | 类型 |
|------|------|
| `id` | TEXT PK (UUID) |
| `name` | TEXT (e.g., UI设计, 数据分析, 课程制作, 内部提效, __sys__) |

### requirements
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | TEXT PK | ✅ | UUID |
| `name` | TEXT | ✅ | 需求名称 |
| `project_id` | TEXT FK→projects | ✅ | |
| `type_id` | TEXT FK→req_types | ✅ | |
| `received_y/m/d` | INTEGER | ✅ | 接收日期 |
| `requesters` | TEXT | ✅ | 需求方；`__sys__` 表示系统占位 |
| `expected_y/m/d` | INTEGER | | 期望交付 |
| `ui_pages` | INTEGER | | UI设计交付前必填 |
| `actual_y/m/d` | INTEGER | | 写入即标记交付 |
| `delivery_url` | TEXT | | 交付物链接 |
| `delivery_thumbnail` | TEXT | | thumbnails/ 下相对路径 |
| `notes` | TEXT | | 备注 |

### schedules
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | TEXT PK | |
| `requirement_id` | TEXT FK→requirements | |
| `start_y/m/d` | INTEGER | |
| `end_y/m/d` | INTEGER | |
| `owner` | TEXT | `-` 表示系统占位（公共假期等） |

### cover_outputs
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | TEXT PK | |
| `date_y/m/d` | INTEGER | |
| `count` | INTEGER | |

### stat_periods
日期由 `compute_periods.py` 自动计算，**不要手动改**。

## 视图

- `v_requirements` — 需求 + 状态/时间跨度（`name GLOB '__*'` 为系统特殊行）
- `v_schedules` — 排期 + duration
- `v_stats_by_period` — 按时间统计聚合（`cover_count` 为封面张数；价值 = count × `COVER_VALUE_MULTIPLIER`）

## 日期确认约定（强力约束）

**执行任何涉及排期的任务时，每一次、必须先用技术手段获取当前日期**（如 `date.today()` 或 shell `date` 命令），不得依赖记忆、推断或上下文中的 `currentDate`。确认日期后再执行后续操作。

**Red Flags — 看到这些立刻停下来，先确认日期：**
- "今天" / "下周一" / "下周" 等相对日期词
- 移动排期、插入排期、标记交付等涉及 actual_date 的操作
- 任何需要计算"第 N 个工作日"的场景

**常见借口与纠正：**

| 借口 | 纠正 |
|------|------|
| "上下文里有 currentDate" | 上下文日期可能过时或不准，必须用技术手段交叉验证 |
| "我记得今天是 X 号" | 记忆不可靠，必须用 `date` 命令确认 |
| "上一轮对话已经确认过" | 每一次涉及排期的操作都要重新确认 |
| "差不多就是这天" | 排期精确到天，差一天全错 |

## 常见操作

### 查需求
```sql
SELECT * FROM v_requirements WHERE status='🚀进行中' ORDER BY received_y DESC, received_m DESC, received_d DESC
```

系统占位（假期/请假等）状态为 `⚠️特殊`，匹配规则是名称以两个下划线开头（`GLOB '__*'`）。

### 加需求

**必须用脚本**：`create_requirement()` 自动处理默认值（project、owner、received=today）和排期分段。

```python
from requirement_ops import create_requirement

# 只加需求，不排期
req_id = create_requirement(db_path, '需求名', '<type_id>', '需求方')

# 加需求 + 自动排期（duration_days=3 表示3个工作日，自动分段）
req_id = create_requirement(db_path, '需求名', '<type_id>', '需求方',
    duration_days=3, notes='备注', project_id='<project_id>', owner='<owner>')
```

### 添加排期

**必须用脚本**：`add_schedule()` 自动跳过周末+假期+请假，跨非工作日自动分段。

```python
from schedule_ops import add_schedule
from datetime import date

add_schedule(db_path, '<requirement_id>', date(2026, 6, 3), date(2026, 6, 5))
```

### 标记交付

**必须用脚本**：`mark_delivered()` 自动校验规则（排期存在、UI设计需ui_pages>0）、自动取排期结束日、提醒缺失的url/缩略图。

```python
from requirement_ops import mark_delivered

# 自动取排期最后一天
mark_delivered(db_path, '<req_id>', delivery_url='https://...')

# 指定交付日期
from datetime import date
mark_delivered(db_path, '<req_id>', actual_date=date(2026, 6, 10))
```

### 公共假期

公共假期和请假在 `schedules` 表中以特殊方式存储：
- **公共假期**: `owner='-'`，`requirement_id` 指向 `__公共假期__`
- **个人请假**: `requirement_id` 指向 `__请假__`，`owner` 为对应人员

#### 查假期
```sql
SELECT r.name AS type, s.start_y, s.start_m, s.start_d, s.end_y, s.end_m, s.end_d, s.owner
FROM schedules s JOIN requirements r ON s.requirement_id=r.id
WHERE s.owner='-' OR r.name='__请假__'
ORDER BY s.start_y, s.start_m, s.start_d;
```

#### 加公共假期

**触发词**：「加个假期 10月1日到7日」「国庆放假」

**⚠️ 必须用脚本，不要手写 SQL**：`add_holiday_and_push()` 会自动后推所有受影响的排期。

```python
from holiday_ops import add_holiday_and_push
from datetime import date

add_holiday_and_push(db_path, date(2026, 10, 1), date(2026, 10, 7))
```

#### 加请假

**触发词**：「张三 8月4-5号请假」「加个请假」

**⚠️ 必须用脚本，不要手写 SQL**：`add_holiday_and_push(holiday=False)` 会自动后推受影响排期。

```python
add_holiday_and_push(db_path, date(2026, 8, 4), date(2026, 8, 5), holiday=False, owner='张三')
```

### 添加缩略图

**推荐方式（一条命令生成）**：从源图缩放至 800px 长边 WebP，写入 `thumbnails/`，并自动更新 `delivery_thumbnail` 字段。

```bash
python scripts/pm.py requirement thumbnail "<需求名或id>" --source "<源图路径>"
```

可选参数：`--max-size 800`（长边像素上限）、`--quality 85`（WebP 质量）。

生成的文件名自动取需求名 slug（CJK 字符保留，标点/空格剔除），输出到 `<DATA_DIR>/thumbnails/<slug>.webp`。

**Python 调用**：

```python
from thumbnail import generate_thumbnail

filename = generate_thumbnail(db_path, '<需求名或id>', '<源图路径>')
# 等价于：缩放 → WebP → 写 thumbnails/ → 更新 DB
```

**仅写库（不生成图）**：如果缩略图文件已存在，只更新数据库字段：

```python
from requirement_ops import set_delivery_thumbnail

set_delivery_thumbnail(db_path, '<req_id>', '<文件名>.webp')
```

### 排期移动

**触发词**：「把张三从 6月5号起的任务往后推 3 天」「把张三的任务提前 2 天」

**⚠️ 先 dry-run 后执行**：先用 `plan_schedule_move()` 预览变更，确认后再 `apply_schedule_move()`。正数后移，负数前移。

### 排期调整

**触发词**：「把 XX 任务延长 2 天」「把 XX 排期缩短 2 天」

```python
from schedule_ops import adjust_schedule_end

adjust_schedule_end(db_path, '<schedule_id>', 2)   # 延长 2 个工作日
adjust_schedule_end(db_path, '<schedule_id>', -2)  # 缩短 2 个工作日
```

### 插入新任务并后推

**触发词**：「加个需求 XX，插到 YY 前面，占用 N 天，后面的往后推」

**必须用脚本**：`insert_and_push()` 一步完成加需求+排期+后推。

```python
from requirement_ops import insert_and_push

insert_and_push(db_path, '新需求名', '<type_id>', '需求方',
    insert_before_req_name='目标需求名', duration_days=1, push_days=1)
```

### 排期操作注意事项

**Agent 必须遵守的原则**：

1. **先 dry-run 后执行** — 排期批量移动先用 `plan_schedule_move()` 看预览，确认无误再 `apply_schedule_move()`。
2. **脚本 > 手动 SQL** — 所有写操作都必须用脚本函数，禁止手写 SQL 执行这些操作。需求创建/交付/插入用 `requirement_ops.py`，假期/请假用 `holiday_ops.py`，排期添加/移动/调整用 `schedule_ops.py`。脚本保证假期感知、分段正确、校验完整。
3. **写后自动刷新** — 以下写操作完成后必须自动执行 `python scripts/pm.py render-html` 刷新页面：
   - 加需求 / 加排期 / 标记交付 / 加假期 / 加请假 / 排期移动 / 排期调整 / 插入新任务并后推 / 添加缩略图
   - 查需求和统计查询等只读操作不需要刷新

### 统计查询
```sql
SELECT * FROM v_stats_by_period WHERE period_type='月' ORDER BY period_name;
```

### 刷新页面
```bash
python scripts/pm.py render-html
```

## 不要做的事

1. 不要手动写 `stat_periods` 日期字段
2. 不要手动计算状态/时间跨度 — 查视图
3. 不要 `DELETE` 被排期引用的项目
