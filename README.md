# project-manager

[🇬🇧 EN](https://github.com/greenzorro/project-manager/blob/main/README.md) | [🇨🇳 中文](https://github.com/greenzorro/project-manager/blob/main/README_ZH_CN.md)

A lightweight, local-first requirement management and output tracking system. SQLite as the sole data source, AI agent handles all data operations, static HTML provides daily visualization.

> Read about the design philosophy behind this project: [What is an AI-Native Data System?](https://victor42.eth.limo/post-en/ai-native-data-system)

## Why use this?

- **Zero infrastructure**: Single SQLite file, no server, no signup, no cloud
- **Agent-native**: Designed to be operated by AI agents (like [opencode](https://github.com/anomalyco/opencode))—just talk to it
- **Unified workflow**: Manage requirements, schedules, deliveries, and cover outputs in one place
- **Beautiful dashboards**: Auto-generated HTML with calendar view, task tracking, and interactive ECharts statistics
- **Data sovereignty**: Everything stays on your machine

Ask an agent to install and wire this repo on your machine (see `# For Agent` below). After that, you mostly **talk to the agent** for CRUD/scheduling and **open the HTML dashboards** yourself.

## Pages

Four auto-generated HTML pages (under your data dir’s `html/`, or `demo/html/` for the sample set):

- **Calendar** — Monthly schedule view with color-coded owners and holiday markers
- **Recent Tasks** — In-progress tasks and recently completed items with thumbnails
- **History** — Full archive of completed requirements with screenshot cards
- **Dashboard** — KPI metrics, monthly stats, top requesters, type breakdown, fiscal year comparisons

## Customization

The dashboard is built around a specific set of requirement types (UI design, data analysis, course production, internal efficiency) and a fiscal year starting in April. If your workflow differs, ask the agent to adapt `render_html.py`, `render_queries.py`, `render_components.py`, and `schema.sql`—cover value formula, KPI metrics, chart labels, and type colors.

## Configuration

| Constant | Default | Purpose |
|----------|---------|---------|
| `COVER_VALUE_MULTIPLIER` | 20 | Cover image value multiplier (`cover_count` × multiplier) |
| `FY_START_MONTH` | 4 | Fiscal year start month |
| `FY_END_MONTH` | 3 | Fiscal year end month |

Defined in `scripts/config.py`.

---

Created by [Victor42](https://victor42.work/) & [Agent Vik](https://github.com/agent-vik)

# For Agent

Stand up this local SQLite project-manager on the current machine, wire the skill, smoke-test with `demo/`, then operate via CLI / skill. After setup, routine CRUD and scheduling are your job until the human takes over product decisions.

## Prerequisites

- Python 3
- `pip install Pillow` (only non-stdlib dependency)
- Write access to a data directory (default: repo `demo/`)

## Steps

1. Clone and enter the repo. Install Pillow.
2. Initialize / render sample data:
   ```bash
   python3 scripts/init.py
   python3 scripts/pm.py render-html
   ```
   Open `demo/html/dashboard.html` (or the HTML under `PM_DATA_DIR`) to verify pages render.
3. For real data (not demo): copy `.env.example` → `.env`, set `PM_DATA_DIR` to an absolute data path, and re-run init/render against that tree. Read `.env` before every later operation.
4. Install the agent skill: copy `skills/project-manager.md` (and/or `skills/SKILL.md` in this checkout) into the agent skills directory and point any path inside it at this clone.
5. Day-to-day: use `python3 scripts/pm.py -h` and the skill doc for requirements, schedules, delivery marks, holidays, and `render-html`. Prefer the skill’s date-confirmation rule before any schedule mutation.
6. When the human only needs dashboards: regenerate HTML and stop—browsing calendar/history/dashboard is a human task.

## Hand off to the human

- Choosing real project names, owners, and business meaning of requirement types
- Viewing HTML dashboards in a browser
- Any customization of fiscal year / cover multiplier / chart taxonomy (they can ask you later)

## Red lines

- Do not point `PM_DATA_DIR` at the wrong machine path or overwrite production `pm.db` without confirmation
- Do not invent schedule dates from chat memory—confirm “today” with a real clock/`date` command when the skill requires it
- Schema and ops detail: `notes.md` and `skills/`; keep README changes out of those contracts unless asked
