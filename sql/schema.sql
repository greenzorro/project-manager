PRAGMA foreign_keys = ON;

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE req_types (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE requirements (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    project_id TEXT NOT NULL REFERENCES projects(id),
    type_id TEXT NOT NULL REFERENCES req_types(id),
    requesters TEXT NOT NULL CHECK(requesters != ''),
    received_y INTEGER NOT NULL,
    received_m INTEGER NOT NULL,
    received_d INTEGER NOT NULL,
    expected_y INTEGER,
    expected_m INTEGER,
    expected_d INTEGER,
    actual_y INTEGER,
    actual_m INTEGER,
    actual_d INTEGER,
    ui_pages INTEGER DEFAULT 0,
    delivery_url TEXT,
    delivery_thumbnail TEXT,
    notes TEXT
);

CREATE TABLE schedules (
    id TEXT PRIMARY KEY,
    requirement_id TEXT NOT NULL REFERENCES requirements(id),
    start_y INTEGER NOT NULL,
    start_m INTEGER NOT NULL,
    start_d INTEGER NOT NULL,
    end_y INTEGER NOT NULL,
    end_m INTEGER NOT NULL,
    end_d INTEGER NOT NULL,
    owner TEXT
);

CREATE TABLE cover_outputs (
    id TEXT PRIMARY KEY,
    date_y INTEGER NOT NULL,
    date_m INTEGER NOT NULL,
    date_d INTEGER NOT NULL,
    count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE stat_periods (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('月', 'S', '财年')),
    start_y INTEGER,
    start_m INTEGER,
    start_d INTEGER,
    end_y INTEGER,
    end_m INTEGER,
    end_d INTEGER,
    start_before_y INTEGER,
    start_before_m INTEGER,
    start_before_d INTEGER,
    end_after_y INTEGER,
    end_after_m INTEGER,
    end_after_d INTEGER
);

CREATE VIEW v_requirements AS
SELECT *,
  CASE
    WHEN actual_y IS NOT NULL THEN '✅已完成'
    WHEN name GLOB '__*' THEN '⚠️特殊'
    ELSE '🚀进行中'
  END AS status,
  julianday(
    COALESCE(actual_y, strftime('%Y','now')) || '-' ||
    printf('%02d', COALESCE(actual_m, strftime('%m','now'))) || '-' ||
    printf('%02d', COALESCE(actual_d, strftime('%d','now')))
  ) - julianday(
    received_y || '-' || printf('%02d', received_m) || '-' || printf('%02d', received_d)
  ) AS time_span,
  CASE
    WHEN actual_y IS NULL AND expected_y IS NOT NULL
      THEN julianday(
        expected_y || '-' || printf('%02d', expected_m) || '-' || printf('%02d', expected_d)
      ) - julianday('now')
  END AS days_to_delivery
FROM requirements;

CREATE VIEW v_schedules AS
SELECT s.*,
  julianday(
    s.end_y || '-' || printf('%02d', s.end_m) || '-' || printf('%02d', s.end_d)
  ) - julianday(
    s.start_y || '-' || printf('%02d', s.start_m) || '-' || printf('%02d', s.start_d)
  ) + 1 AS duration,
  r.name AS requirement_name,
  r.project_id,
  p.name AS project_name
FROM schedules s
JOIN requirements r ON s.requirement_id = r.id
LEFT JOIN projects p ON r.project_id = p.id;

CREATE VIEW v_stats_by_period AS
SELECT sp.id AS period_id, sp.name AS period_name, sp.type AS period_type,
  COUNT(DISTINCT r.id) AS req_count,
  COALESCE(SUM(CASE WHEN rt.name = 'UI设计' THEN r.ui_pages ELSE 0 END), 0) AS ui_pages,
  COALESCE(SUM(CASE WHEN rt.name = '数据分析' THEN 1 ELSE 0 END), 0) AS reports,
  COALESCE(SUM(CASE WHEN rt.name = '课程制作' THEN 1 ELSE 0 END), 0) AS courses,
  COALESCE(SUM(CASE WHEN rt.name = '内部提效' THEN 1 ELSE 0 END), 0) AS efficiency,
  (SELECT COALESCE(SUM(co.count), 0) FROM cover_outputs co
   WHERE julianday(
     co.date_y || '-' || printf('%02d', co.date_m) || '-' || printf('%02d', co.date_d)
   ) > julianday(
     sp.start_before_y || '-' || printf('%02d', sp.start_before_m) || '-' || printf('%02d', sp.start_before_d)
   )
   AND julianday(
     co.date_y || '-' || printf('%02d', co.date_m) || '-' || printf('%02d', co.date_d)
   ) < julianday(
     sp.end_after_y || '-' || printf('%02d', sp.end_after_m) || '-' || printf('%02d', sp.end_after_d)
   )) AS cover_count
FROM stat_periods sp
LEFT JOIN requirements r ON r.actual_y IS NOT NULL
  AND julianday(
    r.actual_y || '-' || printf('%02d', r.actual_m) || '-' || printf('%02d', r.actual_d)
  ) > julianday(
    sp.start_before_y || '-' || printf('%02d', sp.start_before_m) || '-' || printf('%02d', sp.start_before_d)
  )
  AND julianday(
    r.actual_y || '-' || printf('%02d', r.actual_m) || '-' || printf('%02d', r.actual_d)
  ) < julianday(
    sp.end_after_y || '-' || printf('%02d', sp.end_after_m) || '-' || printf('%02d', sp.end_after_d)
  )
LEFT JOIN req_types rt ON r.type_id = rt.id
GROUP BY sp.id;
