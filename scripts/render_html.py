"""
File: render_html.py
Project: project-manager
Author: Victor Cheng
Email: hi@victor42.work
Description: Static HTML rendering for dashboard, recent tasks, calendar, and history.
"""

from __future__ import annotations

import calendar
import json
import os
import sqlite3
from datetime import date
from urllib.parse import quote

from compute_periods import compute_periods
from db import DATA_DIR, FY_END_MONTH, FY_START_MONTH, connect, format_date
from render_components import escape, format_number, page, panel, render_header, render_kpi
from render_queries import query_calendar_data, query_dashboard_data, query_history_rows, query_recent_rows


_chart_counter = 0


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
    data = query_dashboard_data(conn)
    months = data["months"]
    fiscal_years = data["fiscal_years"]
    current_fy = data["current_fy"]
    fy_stacks = data["fy_stacks"]
    requester_rows = data["requester_rows"]
    type_rows = data["type_rows"]
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
    data = query_calendar_data(conn)
    window_start = data["window_start"]
    window_end = data["window_end"]
    months = data["months"]
    schedules = data["schedules"]
    owners = data["owners"]
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
    data = query_recent_rows(conn)
    today = data["today"]
    recent_start = data["recent_start"]
    open_rows = data["open_rows"]
    done_rows = data["done_rows"]
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
    rows = query_history_rows(conn)
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
        expected = format_date(row["expected_y"], row["expected_m"], row["expected_d"])
        actual = format_date(row["actual_y"], row["actual_m"], row["actual_d"]) or "未完成"
        tags = [
            f'<span class="tag">{escape(row["requesters"])}</span>',
            f'<span class="tag">接收 {escape(received)}</span>',
        ]
        if expected:
            tags.append(f'<span class="tag">预期 {escape(expected)}</span>')
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
                {_render_notes(row)}
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


def _render_notes(row: dict) -> str:
    notes = (row.get("notes") or "").strip()
    if not notes:
        return ""
    return f'<div class="task-notes">{escape(notes)}</div>'


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
