# project-manager (Agent Skill)

本地 SQLite 项目管理。Agent 通过此 Skill 执行 CRUD、查询和页面生成。

**⚠️ 必须先读 `.env`**：每次操作前，先读取项目根目录的 `.env` 文件，获取 `PM_DATA_DIR` 的值作为数据库路径。若 `.env` 不存在或未设置 `PM_DATA_DIR`，回退到 `demo/pm.db`。**禁止不读 `.env` 直接使用 `demo/pm.db`。**

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

- `v_requirements` — 需求 + 状态/时间跨度
- `v_schedules` — 排期 + duration
- `v_stats_by_period` — 按时间统计聚合

## 常见操作

### 查需求
```sql
SELECT * FROM v_requirements WHERE status='🚀进行中' ORDER BY received_y DESC, received_m DESC, received_d DESC
```

### 加需求
```sql
INSERT INTO requirements (id, name, project_id, type_id, received_y, received_m, received_d, expected_y, expected_m, expected_d)
VALUES ('<UUID>', '需求名', '<project_id>', '<type_id>', 2026, 6, 3, 2026, 6, 10);
```

### 标记交付

写入 `actual_y/m/d` 即标记。**规则**：
1. 若未指定日期，取 `schedules` 中该需求的最大 `end` 日期
2. 若 schedules 无记录，拒绝交付并提示排期
3. UI设计类必须 `ui_pages > 0`，否则拒绝
4. `delivery_url`/`delivery_thumbnail` 为空时提醒但不阻止

```sql
-- 查最后排期结束日期
SELECT end_y, end_m, end_d FROM schedules WHERE requirement_id = '<id>'
ORDER BY end_y DESC, end_m DESC, end_d DESC LIMIT 1;

-- 检查属性
SELECT type_id, ui_pages, delivery_url, delivery_thumbnail FROM requirements WHERE id='<id>';

-- 写入
UPDATE requirements SET actual_y=<y>, actual_m=<m>, actual_d=<d> WHERE id='<id>';
```

### 添加排期
```sql
INSERT INTO schedules (id, requirement_id, start_y, start_m, start_d, end_y, end_m, end_d, owner)
VALUES ('<UUID>', '<requirement_id>', 2026, 6, 3, 2026, 6, 5, '张三');
```

### 添加缩略图

缩放至 800px 长边 WebP，写入 `thumbnails/`，更新 `delivery_thumbnail`。

```sql
UPDATE requirements SET delivery_thumbnail='<文件名>.webp' WHERE id='<id>';
```

### 排期后移

**触发词**：「把张三从 6月5号起的任务往后推 3 天」

**流程**：
1. 查 `owner=某人 AND start>=某天` 的排期
2. 用 `add_business_days()` 跳过周末算新日期
3. 用 `split_cross_weekend()` 拆分跨周末的排期
4. 第一段 UPDATE 原记录，后续段 INSERT 新记录

**规则**：跳过周末，跨周末自动拆段，不修改非目标 owner。

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