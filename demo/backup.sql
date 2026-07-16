BEGIN TRANSACTION;
CREATE TABLE cover_outputs (
    id TEXT PRIMARY KEY,
    date_y INTEGER NOT NULL,
    date_m INTEGER NOT NULL,
    date_d INTEGER NOT NULL,
    count INTEGER NOT NULL DEFAULT 0
);
INSERT INTO "cover_outputs" VALUES('cov-01',2026,5,8,3);
INSERT INTO "cover_outputs" VALUES('cov-02',2026,5,15,2);
INSERT INTO "cover_outputs" VALUES('cov-03',2026,5,22,4);
INSERT INTO "cover_outputs" VALUES('cov-04',2026,6,5,1);
INSERT INTO "cover_outputs" VALUES('cov-05',2026,6,12,3);
INSERT INTO "cover_outputs" VALUES('cov-h01',2025,7,3,5);
INSERT INTO "cover_outputs" VALUES('cov-h02',2025,8,14,3);
INSERT INTO "cover_outputs" VALUES('cov-h03',2025,9,25,6);
INSERT INTO "cover_outputs" VALUES('cov-h04',2025,11,10,4);
INSERT INTO "cover_outputs" VALUES('cov-h05',2026,1,20,2);
INSERT INTO "cover_outputs" VALUES('cov-h06',2026,2,15,5);
INSERT INTO "cover_outputs" VALUES('cov-f1',2024,6,5,4);
INSERT INTO "cover_outputs" VALUES('cov-f2',2024,8,20,3);
INSERT INTO "cover_outputs" VALUES('cov-f3',2024,11,15,5);
INSERT INTO "cover_outputs" VALUES('cov-f4',2025,1,10,3);
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
INSERT INTO "projects" VALUES('proj-001','官方网站');
INSERT INTO "projects" VALUES('proj-002','数据平台');
INSERT INTO "projects" VALUES('proj-003','在线教育');
CREATE TABLE req_types (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
INSERT INTO "req_types" VALUES('__sys__','__sys__');
INSERT INTO "req_types" VALUES('type-ui','UI设计');
INSERT INTO "req_types" VALUES('type-data','数据分析');
INSERT INTO "req_types" VALUES('type-course','课程制作');
INSERT INTO "req_types" VALUES('type-internal','内部提效');
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
INSERT INTO "requirements" VALUES('req-001','首页 Banner 改版','proj-001','type-ui','Alice',2026,5,10,2026,5,20,2026,5,15,3,'https://victor42.work/','demo_01.webp','配合618大促视觉升级');
INSERT INTO "requirements" VALUES('req-002','用户留存分析报告','proj-002','type-data','Bob',2026,5,12,2026,5,25,2026,5,20,NULL,'https://victor42.work/','demo_02.webp','周度留存漏斗，覆盖Q1-Q2');
INSERT INTO "requirements" VALUES('req-003','Python入门课程','proj-003','type-course','Charlie',2026,5,15,2026,6,5,NULL,NULL,NULL,NULL,NULL,NULL,'12课时，含练习与项目实战');
INSERT INTO "requirements" VALUES('req-004','自动化部署脚本','proj-002','type-internal','Alice',2026,5,18,2026,6,5,2026,6,4,NULL,'https://victor42.work/',NULL,'CI/CD流水线自动化');
INSERT INTO "requirements" VALUES('req-005','课程详情页重设计','proj-003','type-ui','David',2026,5,20,2026,6,15,NULL,NULL,NULL,5,NULL,NULL,'移动端优先，暗色模式支持');
INSERT INTO "requirements" VALUES('req-006','销售数据看板','proj-002','type-data','Bob',2026,6,1,2026,6,20,2026,6,14,NULL,'https://victor42.work/','demo_03.webp','实时大屏展示，含同比环比');
INSERT INTO "requirements" VALUES('req-007','JavaScript进阶课程','proj-003','type-course','Eve',2026,6,3,2026,6,30,NULL,NULL,NULL,NULL,NULL,NULL,'ES6+、异步编程、模块化');
INSERT INTO "requirements" VALUES('req-hist-01','官网首页重构','proj-001','type-ui','Alice',2025,6,10,2025,7,1,2025,6,28,8,'https://victor42.work/',NULL,'S1 交付');
INSERT INTO "requirements" VALUES('req-hist-02','季度营收分析','proj-002','type-data','Bob',2025,7,5,2025,7,20,2025,7,18,NULL,'https://victor42.work/',NULL,'S1 交付');
INSERT INTO "requirements" VALUES('req-hist-03','Excel 效率课','proj-003','type-course','Charlie',2025,8,1,2025,8,25,2025,8,22,NULL,'https://victor42.work/',NULL,'S1 交付');
INSERT INTO "requirements" VALUES('req-hist-04','双11活动页','proj-001','type-ui','David',2025,9,15,2025,10,10,2025,10,8,12,'https://victor42.work/',NULL,'S2 交付');
INSERT INTO "requirements" VALUES('req-hist-05','用户画像报告','proj-002','type-data','Eve',2025,10,1,2025,11,1,2025,10,28,NULL,'https://victor42.work/',NULL,'S2 交付');
INSERT INTO "requirements" VALUES('req-hist-06','年终数据盘点','proj-002','type-data','Alice',2025,12,1,2026,1,15,2026,1,10,NULL,'https://victor42.work/',NULL,'S2 交付');
INSERT INTO "requirements" VALUES('req-hist-07','SQL 入门课程','proj-003','type-course','Bob',2026,1,5,2026,2,1,2026,1,28,NULL,'https://victor42.work/',NULL,'S2 交付');
INSERT INTO "requirements" VALUES('req-hist-08','自动化周报脚本','proj-002','type-internal','Charlie',2026,2,10,2026,3,1,2026,2,25,NULL,'https://victor42.work/',NULL,'S2 交付');
INSERT INTO "requirements" VALUES('req-hist-09','移动端适配','proj-001','type-ui','David',2026,3,1,2026,3,20,2026,3,18,5,'https://victor42.work/',NULL,'S2 交付');
INSERT INTO "requirements" VALUES('req-fy25-01','首版品牌网站','proj-001','type-ui','Alice',2024,5,10,2024,6,1,2024,5,28,10,'https://victor42.work/',NULL,'S1 交付');
INSERT INTO "requirements" VALUES('req-fy25-02','月度经营分析','proj-002','type-data','Bob',2024,6,15,2024,7,10,2024,7,5,NULL,'https://victor42.work/',NULL,'S1 交付');
INSERT INTO "requirements" VALUES('req-fy25-03','Excel 基础课','proj-003','type-course','Charlie',2024,8,1,2024,9,1,2024,8,28,NULL,'https://victor42.work/',NULL,'S1 交付');
INSERT INTO "requirements" VALUES('req-fy25-04','产品页改版','proj-001','type-ui','David',2024,10,10,2024,11,10,2024,11,5,6,'https://victor42.work/',NULL,'S2 交付');
INSERT INTO "requirements" VALUES('req-fy25-05','竞品数据报告','proj-002','type-data','Bob',2024,12,1,2025,1,10,2025,1,8,NULL,'https://victor42.work/',NULL,'S2 交付');
INSERT INTO "requirements" VALUES('req-fy25-06','内部流程自动化','proj-002','type-internal','Eve',2025,2,1,2025,3,1,2025,2,25,NULL,'https://victor42.work/',NULL,'S2 交付');
INSERT INTO "requirements" VALUES('req-fy27-01','月报模板优化','proj-002','type-internal','Alice',2026,4,1,2026,4,20,2026,4,18,NULL,'https://victor42.work/',NULL,'FY-27 4月交付');
INSERT INTO "requirements" VALUES('req-sys-holiday','__公共假期__','proj-002','__sys__','__sys__',2026,4,1,NULL,NULL,NULL,NULL,NULL,NULL,0,NULL,NULL,NULL);
INSERT INTO "requirements" VALUES('req-sys-leave','__请假__','proj-002','__sys__','__sys__',2026,4,1,NULL,NULL,NULL,NULL,NULL,NULL,0,NULL,NULL,NULL);
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
INSERT INTO "schedules" VALUES('sch-001','req-001',2026,5,12,2026,5,15,'小王');
INSERT INTO "schedules" VALUES('sch-002','req-002',2026,5,18,2026,5,20,'小王');
INSERT INTO "schedules" VALUES('sch-003','req-003',2026,5,21,2026,5,22,'小王');
INSERT INTO "schedules" VALUES('sch-004','req-004',2026,6,1,2026,6,4,'小王');
INSERT INTO "schedules" VALUES('sch-005','req-005',2026,6,8,2026,6,12,'小王');
INSERT INTO "schedules" VALUES('sch-007','req-006',2026,6,15,2026,6,18,'小王');
INSERT INTO "schedules" VALUES('sch-008','req-007',2026,6,22,2026,6,26,'小王');
INSERT INTO "schedules" VALUES('sch-h01','req-hist-01',2025,6,12,2025,6,13,'小王');
INSERT INTO "schedules" VALUES('sch-h02','req-hist-01',2025,6,23,2025,6,27,'小王');
INSERT INTO "schedules" VALUES('sch-h03','req-hist-02',2025,7,7,2025,7,11,'小王');
INSERT INTO "schedules" VALUES('sch-h04','req-hist-03',2025,8,4,2025,8,8,'小王');
INSERT INTO "schedules" VALUES('sch-h05','req-hist-04',2025,9,17,2025,9,19,'小王');
INSERT INTO "schedules" VALUES('sch-h06','req-hist-04',2025,10,6,2025,10,8,'小王');
INSERT INTO "schedules" VALUES('sch-h07','req-hist-05',2025,10,6,2025,10,10,'小王');
INSERT INTO "schedules" VALUES('sch-h08','req-hist-06',2025,12,3,2025,12,5,'小王');
INSERT INTO "schedules" VALUES('sch-h09','req-hist-06',2026,1,5,2026,1,9,'小王');
INSERT INTO "schedules" VALUES('sch-h10','req-hist-07',2026,1,7,2026,1,9,'小王');
INSERT INTO "schedules" VALUES('sch-h11','req-hist-08',2026,2,12,2026,2,13,'小王');
INSERT INTO "schedules" VALUES('sch-h12','req-hist-09',2026,3,3,2026,3,6,'小王');
INSERT INTO "schedules" VALUES('sch-f1','req-fy25-01',2024,5,13,2024,5,17,'小王');
INSERT INTO "schedules" VALUES('sch-f2','req-fy25-02',2024,6,17,2024,6,21,'小王');
INSERT INTO "schedules" VALUES('sch-f3','req-fy25-03',2024,8,5,2024,8,9,'小王');
INSERT INTO "schedules" VALUES('sch-f4','req-fy25-04',2024,10,14,2024,10,18,'小王');
INSERT INTO "schedules" VALUES('sch-f5','req-fy25-05',2024,12,3,2024,12,6,'小王');
INSERT INTO "schedules" VALUES('sch-f6','req-fy25-06',2025,2,3,2025,2,7,'小王');
INSERT INTO "schedules" VALUES('sch-fy27-01','req-fy27-01',2026,4,2,2026,4,3,'小王');
INSERT INTO "schedules" VALUES('7599aa1f-f508-4a1c-a9e5-1d007c0a792d','req-fy25-01',2024,5,20,2024,5,24,'小王');
INSERT INTO "schedules" VALUES('72d2f7ea-893c-4d30-a7ac-f3c3fdbb2dba','req-fy25-02',2024,6,24,2024,6,28,'小王');
INSERT INTO "schedules" VALUES('b9e48afc-7d72-4e21-943a-973703859586','req-fy25-02',2024,7,1,2024,7,3,'小王');
INSERT INTO "schedules" VALUES('c93d03cb-10a6-4dce-95ec-fb5c03e487e2','req-fy25-03',2024,8,12,2024,8,16,'小王');
INSERT INTO "schedules" VALUES('f3a4a909-e9ea-4d37-8c29-de69fcd628e2','req-fy25-03',2024,8,19,2024,8,23,'小王');
INSERT INTO "schedules" VALUES('9a85b101-ece4-4525-a46a-520c14c545df','req-fy25-03',2024,8,26,2024,8,26,'小王');
INSERT INTO "schedules" VALUES('d7b3a9c3-4bb6-45fc-834d-ede1fd735f21','req-fy25-04',2024,10,21,2024,10,25,'小王');
INSERT INTO "schedules" VALUES('49cdc5d5-fef7-4d2a-97a4-64944b7b7f62','req-fy25-04',2024,10,28,2024,11,1,'小王');
INSERT INTO "schedules" VALUES('01434d45-f3de-4c41-aa23-c17d0da9c539','req-fy25-05',2024,12,9,2024,12,13,'小王');
INSERT INTO "schedules" VALUES('48244251-46f5-4f0a-857c-c22930ab1055','req-fy25-05',2024,12,16,2024,12,20,'小王');
INSERT INTO "schedules" VALUES('fcc416da-8cbc-49a3-bb24-8a8e12ed9624','req-fy25-05',2024,12,23,2024,12,27,'小王');
INSERT INTO "schedules" VALUES('d8c2d92b-f142-4006-8c26-a41d110d5ab1','req-fy25-05',2024,12,30,2025,1,3,'小王');
INSERT INTO "schedules" VALUES('051fa2fc-8ec3-4470-ace4-8218be249950','req-fy25-05',2025,1,6,2025,1,7,'小王');
INSERT INTO "schedules" VALUES('9981301d-607c-4c35-b372-40cedd739955','req-fy25-06',2025,2,10,2025,2,14,'小王');
INSERT INTO "schedules" VALUES('8f84519f-2587-42a9-b2d2-4c3f87708cbc','req-fy25-06',2025,2,17,2025,2,21,'小王');
INSERT INTO "schedules" VALUES('05d86d81-2512-4acd-bc4d-5f57487702b8','req-fy25-06',2025,2,24,2025,2,24,'小王');
INSERT INTO "schedules" VALUES('70d68850-b3a6-4fb7-b18d-4b72f9dfd675','req-hist-01',2025,6,16,2025,6,20,'小王');
INSERT INTO "schedules" VALUES('8ecfc0e6-a84a-4d6d-bf7b-706e48ab2c7a','req-hist-02',2025,7,14,2025,7,16,'小王');
INSERT INTO "schedules" VALUES('50ce593f-f0b0-4daf-ab53-4c6a0729a805','req-hist-03',2025,8,11,2025,8,15,'小王');
INSERT INTO "schedules" VALUES('d0cf26f6-498e-4667-a56a-94d347c571f0','req-hist-03',2025,8,18,2025,8,20,'小王');
INSERT INTO "schedules" VALUES('0e07c226-427a-4bd5-9013-ae492c02f730','req-hist-04',2025,9,22,2025,9,26,'小王');
INSERT INTO "schedules" VALUES('7c2bab4d-b6d2-46f5-958e-0c64125becce','req-hist-04',2025,9,29,2025,9,30,'小王');
INSERT INTO "schedules" VALUES('cfd7bfe6-f26f-4227-bef8-42f96faa808c','req-hist-05',2025,10,13,2025,10,17,'小王');
INSERT INTO "schedules" VALUES('bb04211a-ae76-4123-ad2b-fa1e2ed24b18','req-hist-05',2025,10,20,2025,10,24,'小王');
INSERT INTO "schedules" VALUES('6ce2587d-fb48-4960-8c8f-1ac63c98247f','req-hist-06',2025,12,8,2025,12,12,'小王');
INSERT INTO "schedules" VALUES('cac235f1-3699-4065-8215-8996efe8c476','req-hist-06',2025,12,15,2025,12,19,'小王');
INSERT INTO "schedules" VALUES('3c409f1f-e64f-4e3e-a5fb-022940f13033','req-hist-07',2026,1,12,2026,1,16,'小王');
INSERT INTO "schedules" VALUES('a0321790-cb21-42ea-9577-e27b840c10eb','req-hist-07',2026,1,19,2026,1,23,'小王');
INSERT INTO "schedules" VALUES('cb599acd-5ad1-4e1d-ad9f-75f00f38f689','req-hist-07',2026,1,26,2026,1,26,'小王');
INSERT INTO "schedules" VALUES('978a7ece-156a-4bc3-a63a-740d89d75c9b','req-hist-08',2026,2,16,2026,2,20,'小王');
INSERT INTO "schedules" VALUES('e0e25742-50aa-4d50-819d-e0733b5b81c6','req-hist-08',2026,2,23,2026,2,24,'小王');
INSERT INTO "schedules" VALUES('429d0096-57a5-41af-89fe-def01a33ca8a','req-hist-09',2026,3,9,2026,3,13,'小王');
INSERT INTO "schedules" VALUES('755cc472-871b-491e-be7f-78051fd956c3','req-hist-09',2026,3,16,2026,3,17,'小王');
INSERT INTO "schedules" VALUES('e22555b8-52b9-4032-87df-43e6a44010d3','req-fy27-01',2026,4,6,2026,4,10,'小王');
INSERT INTO "schedules" VALUES('34eb7d81-75b0-4bee-a07a-a7ec82335e18','req-fy27-01',2026,4,13,2026,4,17,'小王');
INSERT INTO "schedules" VALUES('82a10b64-2376-4987-a01d-a34da2d0e553','req-003',2026,5,25,2026,5,28,'小王');
INSERT INTO "schedules" VALUES('sch-sys-01','req-sys-holiday',2026,5,29,2026,5,31,'-');
INSERT INTO "schedules" VALUES('sch-sys-02','req-sys-leave',2026,6,5,2026,6,5,'小王');
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
INSERT INTO "stat_periods" VALUES('009a79cf-0216-4230-9f1a-9297963d8732','M01-4月','月',2026,4,1,2026,4,30,2026,3,31,2026,5,1);
INSERT INTO "stat_periods" VALUES('62715ec0-a33a-4013-8ff6-836c55c631d5','M02-5月','月',2026,5,1,2026,5,31,2026,4,30,2026,6,1);
INSERT INTO "stat_periods" VALUES('fc8703d3-125e-4569-9cf2-833ec5ac7c2c','M03-6月','月',2026,6,1,2026,6,30,2026,5,31,2026,7,1);
INSERT INTO "stat_periods" VALUES('eb21382d-271a-47c3-a65a-4ace228bc788','M04-7月','月',2026,7,1,2026,7,31,2026,6,30,2026,8,1);
INSERT INTO "stat_periods" VALUES('bee2b554-58ec-42b4-9fae-8b5102b8151f','M05-8月','月',2026,8,1,2026,8,31,2026,7,31,2026,9,1);
INSERT INTO "stat_periods" VALUES('c87a17f6-14c5-48e3-9f93-4adfbe4421f7','M06-9月','月',2026,9,1,2026,9,30,2026,8,31,2026,10,1);
INSERT INTO "stat_periods" VALUES('021c3675-1965-4771-8303-1bfc9ca8682e','M07-10月','月',2026,10,1,2026,10,31,2026,9,30,2026,11,1);
INSERT INTO "stat_periods" VALUES('6d35bce1-efb2-4d3a-9a60-f456093e2f62','M08-11月','月',2026,11,1,2026,11,30,2026,10,31,2026,12,1);
INSERT INTO "stat_periods" VALUES('1279e8c7-2b0e-4246-9b63-471090103339','M09-12月','月',2026,12,1,2026,12,31,2026,11,30,2027,1,1);
INSERT INTO "stat_periods" VALUES('b1970353-d559-482d-b5aa-88810a21f8e6','M10-1月','月',2027,1,1,2027,1,31,2026,12,31,2027,2,1);
INSERT INTO "stat_periods" VALUES('2398fa49-743c-4bf2-b6d7-5acc9a990548','M11-2月','月',2027,2,1,2027,2,28,2027,1,31,2027,3,1);
INSERT INTO "stat_periods" VALUES('b092fd08-b6b5-4127-9307-e6325a17b293','M12-3月','月',2027,3,1,2027,3,31,2027,2,28,2027,4,1);
INSERT INTO "stat_periods" VALUES('a106e64a-4c96-4150-bcc9-bf9047270c02','S1','S',2026,4,1,2026,9,30,2026,3,31,2026,10,1);
INSERT INTO "stat_periods" VALUES('d8bd3650-b6f9-40f8-9ee3-0d9aa99e0fd8','S2','S',2026,10,1,2027,3,31,2026,9,30,2027,4,1);
INSERT INTO "stat_periods" VALUES('de7d531a-b13f-4150-9c3e-312cd46bf292','FY-25','财年',2024,4,1,2025,3,31,2024,3,31,2025,4,1);
INSERT INTO "stat_periods" VALUES('74a5b5ce-543b-43ce-8206-3c0fa525a912','FY-26','财年',2025,4,1,2026,3,31,2025,3,31,2026,4,1);
INSERT INTO "stat_periods" VALUES('befee4f8-c2fe-47ac-89a9-25e0e0e920b1','FY-27','财年',2026,4,1,2027,3,31,2026,3,31,2027,4,1);
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
COMMIT;
