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

Defined in `scripts/config.py`. Confirm calendar dates yourself before schedule changes.

---

Created by [Victor42](https://victor42.work/) & [Agent Vik](https://github.com/agent-vik)

---

# For Agent

Stand up this local SQLite project-manager, wire the skill, then **operate** requirements/schedules/HTML via CLI or skill.

## Prerequisites

- Python 3
- `pip install Pillow`
- Write access to a data directory (default: repo `demo/`)

## Install / first-time setup

1. Clone and enter the repo; install Pillow.
2. Sample data:
   ```bash
   python3 scripts/init.py
   python3 scripts/pm.py render-html
   ```
   Open `demo/html/dashboard.html` to verify.
3. Real data: copy `.env.example` → `.env`, set `PM_DATA_DIR`, re-run init/render. **Read `.env` before every later operation.**
4. Install skill: copy `skills/project-manager.md` and/or `skills/SKILL.md` into the agent skills directory; fix paths to this clone.

## Usage

Entrypoint: `python3 scripts/pm.py <command> …` (optional `--db-path`).

| Command | Purpose |
|---------|---------|
| `doctor` | DB / model consistency |
| `compute-periods` | Recompute stat period dates |
| `render-html` | Regenerate dashboard/calendar HTML |
| `stats` | Local stats |
| `requirement create/deliver/insert/thumbnail` | Requirement writes |
| `schedule add/adjust/move` | Schedule mutations |
| `holiday …` | Public holiday / personal leave |

Also follow the installed skill for conversational CRUD. **Before any schedule mutation**, confirm “today” with a real clock/`date` command (skill red flag).

After data changes that should appear on dashboards: `python3 scripts/pm.py render-html`.

## Hand off to the human

- Business meaning of projects/owners/types
- Viewing HTML in a browser
- Dashboard taxonomy customization requests

## Red lines

- Do not point `PM_DATA_DIR` at the wrong path or overwrite production `pm.db` without confirmation
- Do not invent schedule dates from chat memory
- Schema/ops: `notes.md` and `skills/`
