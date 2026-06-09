"""
File: render_html.py
Project: project-manager
Author: Victor Cheng
Email: hi@victor42.work
Description: Static HTML rendering for dashboard, recent tasks, calendar, and history.
"""

from __future__ import annotations

import calendar
import html
import json
import os
import sqlite3
from datetime import date, timedelta
from urllib.parse import quote

from compute_periods import compute_periods
from db import DATA_DIR, COVER_VALUE_MULTIPLIER, FY_START_MONTH, FY_END_MONTH, connect, format_date


def render_html(db_path: str, output_dir: str) -> tuple[str, str, str, str]:
    compute_periods(db_path)
    conn = connect(db_path)
    os.makedirs(output_dir, exist_ok=True)

    dashboard_path = os.path.join(output_dir, "dashboard.html")
    calendar_path = os.path.join(output_dir, "calendar.html")
    recent_path = os.path.join(output_dir, "recent.html")
    history_path = os.path.join(output_dir, "history.html")
    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write(render_dashboard(conn))
    with open(calendar_path, "w", encoding="utf-8") as f:
        f.write(render_calendar(conn))
    with open(recent_path, "w", encoding="utf-8") as f:
        f.write(render_recent(conn))
    with open(history_path, "w", encoding="utf-8") as f:
        f.write(render_history(conn))

    conn.close()
    return dashboard_path, calendar_path, recent_path, history_path


def render_dashboard(conn: sqlite3.Connection) -> str:
    global _chart_counter
    _chart_counter = 0
    rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT period_name, period_type, req_count, ui_pages, reports, courses, cover_value, efficiency
            FROM v_stats_by_period
            ORDER BY
              CASE period_type WHEN '月' THEN 1 WHEN 'S' THEN 2 ELSE 3 END,
              period_name
            """
        )
    ]
    months = [row for row in rows if row["period_type"] == "月"]
    fiscal_years = [row for row in rows if row["period_type"] == "财年"]
    current_fy = max(fiscal_years, key=lambda r: r["period_name"])
    fy_stacks = _compute_fy_stacks(conn, fiscal_years)
    today = date.today()
    fy_start_year = today.year if today.month >= FY_START_MONTH else today.year - 1
    fy_start = f"{fy_start_year}-04-01"
    fy_end = f"{fy_start_year + 1}-03-31"

    requester_rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT requesters AS requester, COUNT(*) AS req_count,
                   SUM(CASE WHEN actual_y IS NOT NULL THEN 1 ELSE 0 END) AS delivered_count,
                   SUM(CASE WHEN actual_y IS NULL THEN 1 ELSE 0 END) AS open_count
            FROM requirements
            WHERE type_id != '__sys__'
              AND date(received_y || '-' || printf('%02d', received_m) || '-' || printf('%02d', received_d)) >= date(?)
              AND date(received_y || '-' || printf('%02d', received_m) || '-' || printf('%02d', received_d)) <= date(?)
            GROUP BY requesters
            ORDER BY req_count DESC, requester
            LIMIT 10
            """,
            (fy_start, fy_end),
        )
    ]
    type_rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT rt.name AS type_name, COUNT(*) AS req_count
            FROM requirements r
            JOIN req_types rt ON r.type_id = rt.id
            WHERE r.type_id != '__sys__'
              AND date(r.received_y || '-' || printf('%02d', r.received_m) || '-' || printf('%02d', r.received_d)) >= date(?)
              AND date(r.received_y || '-' || printf('%02d', r.received_m) || '-' || printf('%02d', r.received_d)) <= date(?)
            GROUP BY rt.name
            ORDER BY req_count DESC, rt.name
            """,
            (fy_start, fy_end),
        )
    ]
    kpis = [
        ("需求数量", current_fy.get("req_count", 0)),
        ("UI页面", current_fy.get("ui_pages", 0)),
        ("内部提效", current_fy.get("efficiency", 0)),
        ("封面图价值", current_fy.get("cover_value", 0)),
    ]

    body = f"""
    {render_header("dashboard")}
    <main>
      <section class="kpi-grid">{''.join(render_kpi(label, value) for label, value in kpis)}</section>
      {render_metric_triple_row("需求数量", months, fiscal_years, "req_count", "件", fy_stacks, "--green")}
      {render_metric_triple_row("UI 页面数量", months, fiscal_years, "ui_pages", "页", fy_stacks, "--blue")}
      {render_metric_triple_row("内部提效", months, fiscal_years, "efficiency", "件", fy_stacks, "--purple")}
      {render_metric_triple_row("封面图价值", months, fiscal_years, "cover_value", "¥", fy_stacks, "--red")}
      {render_metric_dual_row("报表数量", "制作课程数量", fiscal_years, "reports", "courses", "件", fy_stacks, "--cyan", "--orange")}
      <section class="grid two">
        {render_bar_panel("需求方 Top 10", requester_rows, "req_count", "requester", "件")}
        {render_type_panel(type_rows)}
      </section>
    </main>
    """
    return page("项目统计", body, extra_class="dashboard", favicon="📊")


def render_calendar(conn: sqlite3.Connection) -> str:
    today = date.today()
    window_start = add_months(date(today.year, today.month, 1), -3)
    window_end = add_months(date(today.year, today.month, 1), 4) - timedelta(days=1)
    months = [add_months(window_start, index) for index in range(7)]
    schedules = [
        normalize_schedule(row)
        for row in conn.execute(
            """
            SELECT s.id, s.start_y, s.start_m, s.start_d, s.end_y, s.end_m, s.end_d,
                   s.owner, r.name AS requirement_name, p.name AS project_name
            FROM schedules s
            JOIN requirements r ON s.requirement_id = r.id
            LEFT JOIN projects p ON r.project_id = p.id
            WHERE date(s.end_y || '-' || printf('%02d', s.end_m) || '-' || printf('%02d', s.end_d)) >= date(?)
              AND date(s.start_y || '-' || printf('%02d', s.start_m) || '-' || printf('%02d', s.start_d)) <= date(?)
            ORDER BY s.start_y, s.start_m, s.start_d, s.owner, r.name
            """,
            (window_start.isoformat(), window_end.isoformat()),
        )
    ]
    owners = sorted({schedule["owner"] for schedule in schedules})
    owner_styles = {owner: f"owner-{index % 10}" for index, owner in enumerate(owners)}

    body = f"""
    {render_header("calendar")}
    <main>
      <section class="kpi-grid">
        {render_kpi("窗口开始", window_start.isoformat())}
        {render_kpi("窗口结束", window_end.isoformat())}
        {render_kpi("排期段", len(schedules))}
        {render_kpi("负责人", len(owners))}
      </section>
      <section class="legend">{''.join(render_owner_legend(owner, owner_styles[owner]) for owner in owners)}</section>
      <section class="calendar-stack">
        {''.join(render_month(month, schedules, owner_styles) for month in months)}
      </section>
      </main>
    """
    return page("排期日历", body, extra_class="calendar-page", favicon="📅")


def render_recent(conn: sqlite3.Connection) -> str:
    today = date.today()
    recent_start = today - timedelta(days=7)
    rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT r.id, r.name, p.name AS project_name, rt.name AS type_name, r.requesters,
                   r.received_y, r.received_m, r.received_d,
                   r.expected_y, r.expected_m, r.expected_d,
                   r.actual_y, r.actual_m, r.actual_d,
                   r.ui_pages, r.delivery_url, r.delivery_thumbnail
            FROM requirements r
            JOIN projects p ON r.project_id = p.id
            JOIN req_types rt ON r.type_id = rt.id
            WHERE r.type_id != '__sys__'
              AND (
                r.actual_y IS NULL
                OR date(r.actual_y || '-' || printf('%02d', r.actual_m) || '-' || printf('%02d', r.actual_d)) >= date(?)
              )
            ORDER BY
              r.actual_y IS NOT NULL,
              r.expected_y IS NULL,
              r.expected_y, r.expected_m, r.expected_d,
              r.actual_y DESC, r.actual_m DESC, r.actual_d DESC,
              r.name
            """,
            (recent_start.isoformat(),),
        )
    ]
    open_rows = [row for row in rows if row["actual_y"] is None]
    done_rows = [row for row in rows if row["actual_y"] is not None]
    body = f"""
    {render_header("recent")}
    <main>
      <section class="kpi-grid">
        {render_kpi("进行中", len(open_rows))}
        {render_kpi("7天内完成", len(done_rows))}
        {render_kpi("完成日期起点", recent_start.isoformat())}
        {render_kpi("今天", today.isoformat())}
      </section>
      {render_requirement_group("进行中", open_rows, show_actual=False)}
      {render_requirement_group("最近 7 天已完成", done_rows, show_actual=True)}
    </main>
    """
    return page("近期任务", body, extra_class="recent-page", favicon="🚀")


def render_history(conn: sqlite3.Connection) -> str:
    rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT r.id, r.name, p.name AS project_name, rt.name AS type_name, r.requesters,
                   r.received_y, r.received_m, r.received_d,
                   r.actual_y, r.actual_m, r.actual_d,
                   r.ui_pages, r.delivery_url, r.delivery_thumbnail
            FROM requirements r
            JOIN projects p ON r.project_id = p.id
            JOIN req_types rt ON r.type_id = rt.id
            WHERE r.type_id != '__sys__'
              AND r.actual_y IS NOT NULL
            ORDER BY r.actual_y DESC, r.actual_m DESC, r.actual_d DESC, r.name
            """
        )
    ]
    body = f"""
    {render_header("history")}
    <main>
      <section class="kpi-grid compact">
        {render_kpi("已完成需求", len(rows))}
      </section>
      <section class="card-grid">
        {''.join(render_history_card(row) for row in rows)}
      </section>
    </main>
    """
    return page("历史任务", body, extra_class="history-page", favicon="🏁")
def render_task_title(row: dict, tag_name: str) -> str:
    name = escape(row["name"])
    url = (row["delivery_url"] or "").strip()
    if url.startswith(("http://", "https://")):
        escaped_url = escape(url)
        icon = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="margin-left: 5px; vertical-align: -1px; display: inline-block; opacity: 0.85;"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>'
        return f'<{tag_name}><a class="task-title-link" href="{escaped_url}" target="_blank" rel="noopener noreferrer">{name}{icon}</a></{tag_name}>'
    return f'<{tag_name}>{name}</{tag_name}>'

def render_history_card(row: dict) -> str:
    actual = format_date(row["actual_y"], row["actual_m"], row["actual_d"])
    image = render_card_image(row)
    requester_tag = f'<span class="tag">{escape(row["requesters"])}</span>'
    actual_tag = f'<span class="tag">{escape(actual)}</span>'
    link = render_delivery_link(row["delivery_url"])
    title_html = render_task_title(row, "h2")
    pages = row["ui_pages"] or 0
    pages_tag = f'<span class="tag ui-pages-tag">{pages}件</span>' if pages > 0 else ""
    return f"""
    <article class="history-card">
      {image}
      <div class="history-card-body">
        {title_html}
        <p>{escape(row["project_name"])} · {escape(row["type_name"])}</p>
        <div class="task-meta-tags">{requester_tag}{actual_tag}{pages_tag}</div>
        {link}
      </div>
    </article>
    """


def render_card_image(row: dict) -> str:
    thumbnail = resolve_thumbnail(row)
    if thumbnail:
        src = "../thumbnails/" + quote(thumbnail)
        return f'<div class="thumb"><img src="{src}" alt="{escape(row["name"])}"></div>'
    icon = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 5px; opacity: 0.7;"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>'
    return f'<div class="thumb placeholder"><span>{icon}无图</span></div>'


def render_requirement_group(title: str, rows: list[dict], show_actual: bool) -> str:
    if not rows:
        return panel(title, '<p class="empty-state">暂无记录</p>', "wide-panel")
    body = ['<div class="task-list">']
    for row in rows:
        received = format_date(row["received_y"], row["received_m"], row["received_d"])
        expected = format_date(row["expected_y"], row["expected_m"], row["expected_d"]) or "未设置"
        actual = format_date(row["actual_y"], row["actual_m"], row["actual_d"]) or "未完成"
        tags = [
            f'<span class="tag">{escape(row["requesters"])}</span>',
            f'<span class="tag">接收 {escape(received)}</span>',
            f'<span class="tag">预期 {escape(expected)}</span>',
        ]
        if show_actual:
            tags.append(f'<span class="tag">完成 {escape(actual)}</span>')
        pages = row["ui_pages"] or 0
        if pages > 0:
            tags.append(f'<span class="tag ui-pages-tag">{pages}件</span>')
        link = render_delivery_link(row["delivery_url"])
        title_html = render_task_title(row, "h3")
        body.append(
            f"""
            <article class="task-item">
              {render_task_thumb(row)}
              <div class="task-main">
                {title_html}
                <p>{escape(row['project_name'])} · {escape(row['type_name'])}</p>
                <div class="task-meta-tags">{''.join(tags)}</div>
                {link}
              </div>
            </article>
            """
        )
    body.append("</div>")
    return panel(title, "".join(body), "wide-panel")


def render_task_thumb(row: dict) -> str:
    thumbnail = resolve_thumbnail(row)
    if thumbnail:
        src = "../thumbnails/" + quote(thumbnail)
        return f'<div class="task-thumb"><img src="{src}" alt="{escape(row["name"])}"></div>'
    icon = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: -2px; margin-right: 4px; opacity: 0.7;"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>'
    return f'<div class="task-thumb placeholder"><span>{icon}无图</span></div>'


def render_delivery_link(value) -> str:
    if not value:
        return ""
    text = str(value).strip()
    escaped = escape(text)
    if text.startswith(("http://", "https://")):
        return ""
    return f'<span class="task-link muted-link">{escaped}</span>'


def resolve_thumbnail(row: dict) -> str | None:
    if row["delivery_thumbnail"]:
        thumbnail = str(row["delivery_thumbnail"]).split(",", 1)[0].strip()
        thumbnail_path = os.path.join(DATA_DIR, "thumbnails", thumbnail)
        if os.path.exists(thumbnail_path):
            return thumbnail
    id_thumbnail = f"{row['id']}.webp"
    id_thumbnail_path = os.path.join(DATA_DIR, "thumbnails", id_thumbnail)
    if os.path.exists(id_thumbnail_path):
        return id_thumbnail
    return None


def render_kpi(label: str, value: int) -> str:
    return f"""
    <article class="kpi">
      <span>{escape(label)}</span>
      <strong>{format_number(value)}</strong>
    </article>
    """


def render_header(active: str) -> str:
    items = [
        ("calendar", "排期日历", "calendar.html"),
        ("recent", "近期任务", "recent.html"),
        ("history", "历史任务", "history.html"),
        ("dashboard", "项目统计", "dashboard.html"),
    ]
    
    active_label = "导航菜单"
    for key, label, _ in items:
        if key == active:
            active_label = label
            break

    links = []
    for index, (key, label, href) in enumerate(items, start=1):
        class_name = ' class="active"' if key == active else ""
        links.append(f'<a href="{href}" title="快捷键 {index}" data-shortcut="{index}"{class_name}><span>{label}</span><kbd>{index}</kbd></a>')

    return f"""
    <header class="topbar">
      <div class="title-dropdown">
        <h1 class="dropdown-trigger" id="dropdownTrigger">
          {active_label}
          <svg class="dropdown-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="margin-left: 6px; vertical-align: middle; transition: transform 0.2s;"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </h1>
        <div class="dropdown-menu">
          {''.join(links)}
        </div>
      </div>
    </header>
    """


_chart_counter = 0

def _next_chart_id() -> str:
    global _chart_counter
    _chart_counter += 1
    return f"c{_chart_counter}"


def _echarts_column(chart_id: str, labels: list[str], values: list[int], unit: str, color_var: str = "--green", height: int = 200) -> str:
    return f"""<div id="{chart_id}" style="height:{height}px"></div>
<script>
(function(){{
  var c=echarts.init(document.getElementById("{chart_id}"));
  c.setOption({{
    grid:{{top:24,right:12,bottom:24,left:48}},
    xAxis:{{type:"category",data:{json.dumps(labels)},axisLabel:{{fontSize:11,color:"#747474"}},axisLine:{{lineStyle:{{color:"#dadada"}}}}}},
    yAxis:{{type:"value",axisLabel:{{fontSize:11,color:"#747474"}},splitLine:{{lineStyle:{{color:"#f0f0f0"}}}}}},
    series:[{{type:"bar",data:{json.dumps(values)},label:{{show:true,position:"top",fontSize:11,color:"#747474"}},itemStyle:{{color:$c("{color_var}"),borderRadius:[4,4,0,0]}},barMaxWidth:36}}],
    tooltip:{{trigger:"axis",formatter:function(p){{return p[0].name+"&nbsp;&nbsp;"+p[0].value+"{unit}"}}}}
  }});
  window.addEventListener("resize",function(){{c.resize();}});
}})();
</script>"""


def _echarts_hbar(chart_id: str, labels: list[str], values: list[int], unit: str, height: int = 240) -> str:
    return f"""<div id="{chart_id}" style="height:{height}px"></div>
<script>
(function(){{
  var c=echarts.init(document.getElementById("{chart_id}"));
  c.setOption({{
    grid:{{top:4,right:48,bottom:4,left:4,containLabel:true}},
    xAxis:{{type:"value",axisLabel:{{fontSize:11,color:"#747474"}},splitLine:{{lineStyle:{{color:"#f0f0f0"}}}}}},
    yAxis:{{type:"category",data:{json.dumps(labels)},inverse:true,axisLabel:{{fontSize:11,color:"#747474"}},axisLine:{{lineStyle:{{color:"#dadada"}}}}}},
    series:[{{type:"bar",data:{json.dumps(values)},label:{{show:true,position:"right",fontSize:11,color:"#747474"}},itemStyle:{{color:$c("--green"),borderRadius:[0,4,4,0]}},barMaxWidth:20}}],
    tooltip:{{trigger:"axis",formatter:function(p){{return p[0].name+"&nbsp;&nbsp;"+p[0].value+"{unit}"}}}}
  }});
  window.addEventListener("resize",function(){{c.resize();}});
}})();
</script>"""


def _echarts_stacked_fy(chart_id: str, labels: list[str], s1: list[int], s2: list[int], unit: str, color_var: str = "--green", light_var: str = "--green-light") -> str:
    labs = json.dumps(labels)
    d1 = json.dumps(s1)
    d2 = json.dumps(s2)
    s1_label = f"S1 ({FY_START_MONTH}~9月)"
    s2_label = f"S2 (10~{FY_END_MONTH}月)"
    js = (
        '<div id="' + chart_id + '" style="height:200px"></div>'
        '<script>'
        '(function(){'
        'var dark=$c("' + color_var + '"),light=$c("' + light_var + '");'
        'var c=echarts.init(document.getElementById("' + chart_id + '"));'
        'c.setOption({'
        'grid:{top:36,right:12,bottom:24,left:48},'
        'legend:{data:["' + s1_label + '","' + s2_label + '"],top:0,itemWidth:10,itemHeight:10,textStyle:{fontSize:11,color:"#747474"}},'
        'xAxis:{type:"category",data:' + labs + ',axisLabel:{fontSize:11,color:"#747474"},axisLine:{lineStyle:{color:"#dadada"}}},'
        'yAxis:{type:"value",axisLabel:{fontSize:11,color:"#747474"},splitLine:{lineStyle:{color:"#f0f0f0"}}},'
        'series:['
        '{name:"' + s1_label + '",type:"bar",stack:"total",data:' + d1 + ',itemStyle:{color:dark},label:{show:true,position:"inside",fontSize:10,color:"#fff"},barMaxWidth:36},'
        '{name:"' + s2_label + '",type:"bar",stack:"total",data:' + d2 + ',itemStyle:{color:light,borderRadius:[4,4,0,0]},label:{show:true,position:"top",fontSize:11,color:"#747474"},barMaxWidth:36}'
        '],'
        'tooltip:{trigger:"axis",formatter:function(p){var t=p[0].name+"<br/>";p.forEach(function(i){t+=i.marker+i.seriesName+": "+i.value+"' + unit + '"+"<br/>"});return t.slice(0,-5);}}'
        '});'
        'window.addEventListener("resize",function(){c.resize();});'
        '})();'
        '</script>'
    )
    return js


def _fy_semester_ranges(fiscal_years: list[dict]) -> list[tuple]:
    ranges = []
    for row in fiscal_years:
        name = row["period_name"]
        fy_end_year = int(name[3:]) + 2000
        fy_start_year = fy_end_year - 1
        ranges.append((
            name,
            date(fy_start_year, FY_START_MONTH, 1), date(fy_start_year, 9, 30),
            date(fy_start_year, 10, 1), date(fy_end_year, FY_END_MONTH, 31),
        ))
    return ranges


def _compute_fy_stacks(conn: sqlite3.Connection, fiscal_years: list[dict]) -> dict:
    req_rows = [
        dict(r) for r in conn.execute("""
            SELECT r.actual_y, r.actual_m, r.actual_d, r.ui_pages, rt.name AS type_name
            FROM requirements r JOIN req_types rt ON r.type_id = rt.id
            WHERE r.actual_y IS NOT NULL
        """).fetchall()
    ]
    co_rows = [
        dict(r) for r in conn.execute(
            "SELECT date_y, date_m, date_d, count FROM cover_outputs"
        ).fetchall()
    ]

    ranges = _fy_semester_ranges(fiscal_years)
    labels = [r[0] for r in ranges]

    def _in_range(row, s, e, yk="actual_y", mk="actual_m", dk="actual_d"):
        return s <= date(row[yk], row[mk], row[dk]) <= e

    result = {}
    for key, fn in [("req_count", _count), ("ui_pages", _ui_pages), ("efficiency", _efficiency), ("cover_value", _cover), ("reports", _reports), ("courses", _courses)]:
        s1, s2 = [], []
        for _, s1_s, s1_e, s2_s, s2_e in ranges:
            s1.append(fn(req_rows, co_rows, s1_s, s1_e))
            s2.append(fn(req_rows, co_rows, s2_s, s2_e))
        result[key] = (labels, s1, s2)
    return result


def _count(req_rows, _co, s, e):
    return sum(1 for r in req_rows if s <= date(r["actual_y"], r["actual_m"], r["actual_d"]) <= e)


def _ui_pages(req_rows, _co, s, e):
    return sum(r["ui_pages"] or 0 for r in req_rows if r["type_name"] == "UI设计" and s <= date(r["actual_y"], r["actual_m"], r["actual_d"]) <= e)


def _efficiency(req_rows, _co, s, e):
    return sum(1 for r in req_rows if r["type_name"] == "内部提效" and s <= date(r["actual_y"], r["actual_m"], r["actual_d"]) <= e)


def _cover(_req_rows, co_rows, s, e):
    return sum(r["count"] * COVER_VALUE_MULTIPLIER for r in co_rows if s <= date(r["date_y"], r["date_m"], r["date_d"]) <= e)


def _reports(req_rows, _co, s, e):
    return sum(1 for r in req_rows if r["type_name"] == "数据分析" and s <= date(r["actual_y"], r["actual_m"], r["actual_d"]) <= e)


def _courses(req_rows, _co, s, e):
    return sum(1 for r in req_rows if r["type_name"] == "课程制作" and s <= date(r["actual_y"], r["actual_m"], r["actual_d"]) <= e)


def render_metric_triple_row(
    title: str,
    months: list[dict],
    fiscal_years: list[dict],
    value_key: str,
    unit: str,
    fy_stacks: dict | None = None,
    color_var: str = "--green",
) -> str:
    fy_chart = render_metric_bar(fiscal_years, value_key, "period_name", unit, color_var=color_var)
    if fy_stacks and value_key in fy_stacks:
        labels, s1, s2 = fy_stacks[value_key]
        fy_chart = _echarts_stacked_fy(_next_chart_id(), labels, s1, s2, unit, color_var, color_var + "-light")
        fy_chart = f"""<div class="panel">{fy_chart}</div>"""
    return f"""
    <section class="metric-row">
      <h2 class="metric-row-title">{escape(title)}</h2>
      <div class="grid metric23">
        {render_metric_bar(months, value_key, "period_name", unit, color_var=color_var)}
        {fy_chart}
      </div>
    </section>
    """


def render_metric_dual_row(
    title1: str,
    title2: str,
    fiscal_years: list[dict],
    key1: str,
    key2: str,
    unit: str,
    fy_stacks: dict | None = None,
    color_var1: str = "--green",
    color_var2: str = "--green",
) -> str:
    def _col(key, title, cv):
        if fy_stacks and key in fy_stacks:
            labels, s1, s2 = fy_stacks[key]
            chart = _echarts_stacked_fy(_next_chart_id(), labels, s1, s2, unit, cv, cv + "-light")
            return panel(title, chart)
        return render_metric_bar(fiscal_years, key, "period_name", unit, title, cv)
    return f"""
    <section class="metric-row">
      <div class="grid two">
        {_col(key1, title1 + " — 财年", color_var1)}
        {_col(key2, title2 + " — 财年", color_var2)}
      </div>
    </section>
    """


def render_metric_bar(
    rows: list[dict],
    value_key: str,
    label_key: str,
    unit: str,
    title: str = "",
    color_var: str = "--green",
) -> str:
    labels = [row[label_key] for row in rows]
    values = [row[value_key] or 0 for row in rows]
    chart = _echarts_column(_next_chart_id(), labels, values, unit, color_var)
    if title:
        return panel(title, chart)
    return f"""<div class="panel">{chart}</div>"""


def render_bar_panel(title: str, rows: list[dict], value_key: str, label_key: str, unit: str) -> str:
    labels = [row[label_key] for row in rows]
    values = [row[value_key] or 0 for row in rows]
    chart = _echarts_hbar(_next_chart_id(), labels, values, unit)
    return panel(title, chart)


_TYPE_COLORS = {
    "产品需求": "--green",
    "UI设计": "--blue",
    "封面设计": "--red",
    "内部提效": "--purple",
    "数据分析": "--cyan",
    "课程制作": "--orange",
    "其他": "--amber",
}


def render_type_panel(rows: list[dict]) -> str:
    names_json = json.dumps([row["type_name"] for row in rows])
    values_json = json.dumps([row["req_count"] for row in rows])
    colors_json = json.dumps({n: _TYPE_COLORS.get(n, "--green") for n in [r["type_name"] for r in rows]})
    chart_id = _next_chart_id()
    return panel("按类型统计", f"""<div id="{chart_id}" style="height:260px"></div>
<script>
(function(){{
  var names={names_json},values={values_json},cmap={colors_json};
  var data=names.map(function(n,i){{return{{name:n,value:values[i],itemStyle:{{color:$c(cmap[n])}}}}}});
  var c=echarts.init(document.getElementById("{chart_id}"));
  c.setOption({{
    tooltip:{{trigger:"item",formatter:function(p){{return p.name+": "+p.value+"件 ("+p.percent+"%)"}}}},
    legend:{{bottom:0,itemWidth:10,itemHeight:10,textStyle:{{fontSize:11,color:"#747474"}}}},
    series:[{{type:"pie",radius:["45%","70%"],center:["50%","45%"],avoidLabelOverlap:false,
      label:{{show:true,fontSize:11,color:"#747474"}},emphasis:{{label:{{show:true,fontSize:14,fontWeight:"bold"}}}},
      data:data,
      itemStyle:{{borderRadius:4,borderColor:"#fff",borderWidth:2}}
    }}]
  }});
  window.addEventListener("resize",function(){{c.resize();}});
}})();
</script>""")


def render_owner_legend(owner: str, owner_class: str) -> str:
    return f'<span class="legend-item"><i class="{owner_class}"></i>{escape(owner)}</span>'


def render_month(month_start: date, schedules: list[dict], owner_styles: dict[str, str]) -> str:
    _, days_in_month = calendar.monthrange(month_start.year, month_start.month)
    first_weekday = month_start.weekday()
    cells = ['<div class="weekday">一</div><div class="weekday">二</div><div class="weekday">三</div><div class="weekday">四</div><div class="weekday">五</div><div class="weekday muted">六</div><div class="weekday muted">日</div>']
    cells.extend('<div class="day empty"></div>' for _ in range(first_weekday))
    for day in range(1, days_in_month + 1):
        current = date(month_start.year, month_start.month, day)
        day_events = [
            schedule for schedule in schedules
            if schedule["start"] <= current <= schedule["end"]
        ]
        classes = ["day"]
        if current.weekday() >= 5:
            classes.append("weekend")
        chips = "".join(render_event_chip(schedule, owner_styles[schedule["owner"]]) for schedule in day_events[:4])
        more = f'<span class="more">+{len(day_events) - 4}</span>' if len(day_events) > 4 else ""
        cells.append(
            f"""
            <div class="{' '.join(classes)}" data-date="{current.isoformat()}">
              <div class="date-num">{day}</div>
              <div class="events">{chips}{more}</div>
            </div>
            """
        )
    title = f"{month_start.year}年{month_start.month}月"
    month_val = f"{month_start.year}-{month_start.month:02d}"
    return f"""
    <section class="month-panel" data-month="{month_val}">
      <h2>{title}</h2>
      <div class="month-grid">{''.join(cells)}</div>
    </section>
    """


def render_event_chip(schedule: dict, owner_class: str) -> str:
    title = schedule["requirement_name"]
    return f'<span class="event-chip {owner_class}" title="{escape(title)} | {escape(schedule["owner"])}">{escape(title)}</span>'


def normalize_schedule(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "requirement_name": row["requirement_name"],
        "project_name": row["project_name"],
        "owner": row["owner"],
        "start": date(row["start_y"], row["start_m"], row["start_d"]),
        "end": date(row["end_y"], row["end_m"], row["end_d"]),
    }


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def panel(title: str, content: str, class_name: str = "") -> str:
    classes = f"panel {class_name}".strip()
    return f'<section class="{classes}"><h2>{escape(title)}</h2>{content}</section>'


def page(title: str, body: str, extra_class: str = "", favicon: str = "") -> str:
    favicon_link = f'<link rel="icon" href="data:image/svg+xml,<svg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 100 100\'><text y=\'.9em\' font-size=\'90\'>{favicon}</text></svg>">' if favicon else ""
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {favicon_link}
  <title>{escape(title)}</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js"></script>
  <script>window.$c=(name)=>getComputedStyle(document.documentElement).getPropertyValue(name).trim();</script>
  <style>{html_css()}</style>
</head>
<body class="{escape(extra_class)}">
{body}
<script>{html_js()}</script>
</body>
</html>
"""


def html_js() -> str:
    return """
(() => {
  // 1. 键盘快捷键导航
  const shortcuts = {
    "1": "calendar.html",
    "2": "recent.html",
    "3": "history.html",
    "4": "dashboard.html"
  };
  window.addEventListener("keydown", (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    const target = event.target;
    if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
    const href = shortcuts[event.key];
    if (!href) return;
    event.preventDefault();
    if (!location.pathname.endsWith("/" + href)) {
      location.href = href;
    }
  });

  // 2. 浏览器端动态判定高亮今天 & 自动滚动当前月
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  
  const todayStr = `${year}-${month}-${day}`;
  const currentMonthStr = `${year}-${month}`;

  // 动态高亮今天
  const todayEl = document.querySelector(`.day[data-date="${todayStr}"]`);
  if (todayEl) {
    todayEl.classList.add("today");
  }

  // 动态滚动定位当前月
  const currentMonthEl = document.querySelector(`.month-panel[data-month="${currentMonthStr}"]`);
  if (currentMonthEl) {
    currentMonthEl.scrollIntoView({block: "start"});
  }

  // 3. 页面标题下拉菜单点击展开（支持移动端/触屏）
  const trigger = document.getElementById("dropdownTrigger");
  const dropdown = document.querySelector(".title-dropdown");
  if (trigger && dropdown) {
    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.toggle("open");
    });
    document.addEventListener("click", () => {
      dropdown.classList.remove("open");
    });
  }
})();
"""


def html_css() -> str:
    return """
:root {
  --bg: #f5f5fa;
  --panel: #ffffff;
  --text: #202522;
  --muted: #747474;
  --subtle: #bababa;
  --line: rgba(218, 218, 218, 0.72);
  --soft-line: rgba(218, 218, 218, 0.5);
  --soft-bg: #f8f8fb;
  --chip-bg: #fafafa;
  --weekend-bg: #fff9ed;
  --green: #2A9D8F;
  --green-light: #93D5C8;
  --green-dark: #219789;
  --blue: #0177b8;
  --blue-light: #66B5D6;
  --amber: #c28a00;
  --amber-light: #DDC066;
  --red: #df7988;
  --red-light: #EFA8B2;
  --purple: #6b69d6;
  --purple-light: #A59EE8;
  --cyan: #0E8FB2;
  --cyan-light: #7DC8E0;
  --orange: #e07b39;
  --orange-light: #F0B58A;
  --shadow: 0 4px 8px rgba(0, 0, 0, 0.04), 0 0 2px rgba(0, 0, 0, 0.06), 0 0 1px rgba(0, 0, 0, 0.04);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.45;
}
a { color: var(--blue); text-decoration: none; }
.topbar {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  padding: 18px 28px;
  background: rgba(245, 245, 250, 0.75);
  backdrop-filter: blur(10px);
}
.title-dropdown {
  position: relative;
  display: inline-block;
}
.dropdown-trigger {
  margin: 0;
  font-size: 28px;
  font-weight: 720;
  letter-spacing: 0;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
  color: var(--text);
  padding: 4px 10px;
  margin-left: -10px;
  border-radius: 8px;
  transition: background-color 0.2s;
}
.dropdown-trigger:hover {
  background: rgba(0, 0, 0, 0.04);
}
.dropdown-arrow {
  color: var(--muted);
  opacity: 0.8;
  margin-left: 6px;
  vertical-align: middle;
  transition: transform 0.2s;
}
.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 6px;
  min-width: 180px;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(15px);
  -webkit-backdrop-filter: blur(15px);
  border: 1px solid var(--line);
  border-radius: 10px;
  box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.08), 0 8px 16px -6px rgba(0, 0, 0, 0.06);
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  z-index: 100;
  opacity: 0;
  visibility: hidden;
  transform: translateY(-8px);
  transition: opacity 0.2s ease, transform 0.2s ease, visibility 0.2s;
}
.dropdown-menu a {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 14px;
  font-size: 14px;
  font-weight: 580;
  color: var(--text) !important;
  border-radius: 6px;
  text-decoration: none;
  transition: all 0.15s;
}
.dropdown-menu a kbd {
  font-family: inherit;
  font-size: 10px;
  font-weight: 600;
  color: var(--muted);
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 4px;
  padding: 1px 5px;
  box-shadow: 0 1px 0 rgba(0, 0, 0, 0.02);
  transition: all 0.15s;
}
.dropdown-menu a:hover {
  background: var(--soft-bg);
  color: var(--blue) !important;
}
.dropdown-menu a:hover kbd {
  background: rgba(1, 119, 184, 0.06);
  border-color: rgba(1, 119, 184, 0.12);
  color: var(--blue);
}
.dropdown-menu a.active {
  background: rgba(1, 119, 184, 0.08);
  color: var(--blue) !important;
  font-weight: 680;
}
.dropdown-menu a.active kbd {
  background: rgba(1, 119, 184, 0.1);
  border-color: rgba(1, 119, 184, 0.15);
  color: var(--blue);
}
.title-dropdown:hover .dropdown-menu,
.title-dropdown.open .dropdown-menu {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}
.title-dropdown:hover .dropdown-arrow,
.title-dropdown.open .dropdown-arrow {
  transform: rotate(180deg);
}
h2 { margin: 0 0 14px; font-size: 17px; letter-spacing: 0; }
main { max-width: 1440px; margin: 0 auto; padding: 24px 28px 48px; }
.grid { display: grid; gap: 16px; margin-top: 16px; }
.grid.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.grid.metric23 { grid-template-columns: 2fr 1fr; }
.metric-row { margin-top: 16px; }
.metric-row-title {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 680;
  letter-spacing: 0;
  color: var(--text);
}
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-bottom: 16px; }
.kpi-grid.compact { grid-template-columns: minmax(180px, 260px); }
.kpi, .panel, .month-panel {
  background: var(--panel);
  border-radius: 8px;
  box-shadow: var(--shadow);
}
.kpi { padding: 14px 16px; }
.kpi span { display: block; color: var(--muted); font-size: 13px; }
.kpi strong { display: block; margin-top: 6px; font-size: 24px; font-weight: 720; }
.panel { padding: 18px; overflow: hidden; }
.wide-panel { margin-top: 16px; }

table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 9px 8px; border-bottom: 1px solid var(--soft-line); text-align: left; vertical-align: top; }
th { color: var(--muted); font-weight: 650; }
.legend { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 16px; }
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  background: var(--panel);
  border-radius: 999px;
  font-size: 12px;
}
.legend-item i { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.calendar-stack { display: grid; gap: 16px; }
.month-panel { padding: 16px; scroll-margin-top: 84px; }
.month-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 6px; }
.weekday {
  color: var(--muted);
  font-size: 12px;
  font-weight: 650;
  padding: 0 4px 4px;
}
.weekday.muted { color: var(--amber); }
.day {
  min-height: 112px;
  border: 1px solid var(--line);
  border-radius: 7px;
  padding: 7px;
  background: var(--chip-bg);
  overflow: hidden;
}
.day.empty { background: transparent; border: 0; }
.day.weekend { background: var(--weekend-bg); }
.day.today { outline: 2px solid var(--green); outline-offset: -2px; }
.date-num { color: var(--muted); font-size: 12px; font-weight: 680; margin-bottom: 4px; }
.events { display: flex; flex-direction: column; gap: 4px; }
.event-chip, .owner-pill {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-radius: 5px;
  padding: 3px 6px;
  font-size: 12px;
  color: #fff;
}
.owner-pill { padding: 4px 8px; }
.more { color: var(--muted); font-size: 12px; padding-left: 2px; }
.owner-0 { background: var(--green); }
.owner-1 { background: var(--blue); }
.owner-2 { background: var(--amber); }
.owner-3 { background: var(--purple); }
.owner-4 { background: var(--red); }
.owner-5 { background: #8ea885; }
.owner-6 { background: #0177b8; }
.owner-7 { background: #6b69d6; }
.owner-8 { background: #df7988; }
.owner-9 { background: var(--green-dark); }
.task-list { display: grid; gap: 10px; }
.task-item {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr);
  align-items: start;
  gap: 16px;
  padding: 13px 0;
  border-bottom: 1px solid var(--soft-line);
}
.task-item:last-child { border-bottom: 0; }
.task-main { min-width: 0; }
.task-item h3 { margin: 0 0 5px; font-size: 15px; letter-spacing: 0; }
.task-item p { margin: 0; color: var(--muted); font-size: 13px; }
.task-meta-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.task-title-link {
  color: var(--blue);
  text-decoration: none;
}
.task-title-link:hover {
  text-decoration: underline;
}
.task-link {
  display: block;
  margin-top: 5px;
  overflow-wrap: anywhere;
  font-size: 12px;
}
.muted-link { color: var(--muted); }
.task-thumb {
  width: 76px;
  aspect-ratio: 1;
  border-radius: 7px;
  background: var(--soft-bg);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.task-thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center center;
  display: block;
}
.task-thumb.placeholder span {
  color: var(--muted);
  font-size: 12px;
  border: 1px dashed var(--line);
  border-radius: 999px;
  padding: 4px 7px;
  background: var(--chip-bg);
}
.tag {
  display: inline-block;
  padding: 4px 7px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--chip-bg);
  color: var(--muted);
  font-size: 12px;
}
.empty-state { margin: 0; color: var(--muted); }
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.history-card {
  background: var(--panel);
  border-radius: 8px;
  box-shadow: var(--shadow);
  overflow: hidden;
}
.thumb {
  position: relative;
  aspect-ratio: 4 / 3;
  background: var(--soft-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center center;
  display: block;
}
.thumb.placeholder span {
  color: var(--muted);
  font-size: 13px;
  border: 1px dashed var(--line);
  border-radius: 999px;
  padding: 5px 9px;
  background: var(--chip-bg);
}
.task-thumb.placeholder, .thumb.placeholder {
  background: repeating-linear-gradient(
    -45deg,
    #fcfcfd,
    #fcfcfd 10px,
    var(--soft-bg) 10px,
    var(--soft-bg) 20px
  ) !important;
}
.history-card-body { padding: 12px; }
.history-card h2 {
  margin: 0 0 7px;
  font-size: 15px;
  line-height: 1.35;
  letter-spacing: 0;
}
.history-card p {
  margin: 0 0 5px;
  color: var(--muted);
  font-size: 12px;
}
@media (max-width: 980px) {
  .grid.two, .grid.three, .grid.metric23, .kpi-grid { grid-template-columns: 1fr; }
  .topbar { align-items: flex-start; padding: 16px; }
  main { padding: 16px; }
  .month-grid { gap: 4px; }
  .day { min-height: 88px; padding: 5px; }
  .event-chip { font-size: 11px; }
  .task-item { grid-template-columns: 72px minmax(0, 1fr); }
  .task-thumb { width: 72px; }
}
"""


def escape(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def format_number(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)
