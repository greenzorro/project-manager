"""
File: render_components.py
Project: project-manager
Description: Shared HTML components, page shell, CSS, and JavaScript assets.
"""

from __future__ import annotations

import html


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
.task-notes {
  margin-top: 6px;
  font-size: 12px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
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
