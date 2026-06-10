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

## Pages

Four auto-generated HTML pages:

- **Calendar** — Monthly schedule view with color-coded owners and holiday markers
- **Recent Tasks** — In-progress tasks and recently completed items with thumbnails
- **History** — Full archive of completed requirements with screenshot cards
- **Dashboard** — KPI metrics, monthly stats, top requesters, type breakdown, fiscal year comparisons

## Quick Start

```bash
git clone https://github.com/greenzorro/project-manager.git
cd project-manager
python3 scripts/init.py
python3 scripts/pm.py render-html
open demo/html/dashboard.html
```

The project ships with a `demo/` directory containing fictional sample data—explore all features immediately.

## Setup with AI Agent

The system is designed for agent-driven operation. To integrate:

1. Copy `skills/SKILL.md` to your agent's skills directory (e.g., `~/.agents/skills/project-manager/SKILL.md`)
2. Update the path reference in the copied file to point to your local clone
3. Set `PM_DATA_DIR` environment variable to your data directory (or use `.env`):

```bash
PM_DATA_DIR=/path/to/your/data
```

Without `PM_DATA_DIR`, the system uses `demo/` inside the project.

## Project Structure

```
project-manager/
├── notes.md                     # Developer memo
├── README.md / README_ZH_CN.md  # Documentation
├── .env.example                 # Environment configuration
├── demo/                        # Sample data (no PM_DATA_DIR → used by default)
├── sql/schema.sql               # DDL and view definitions
├── scripts/                     # CLI tools and rendering engine
└── skills/                      # AI agent skill files
```

## Dependencies

Zero external dependencies. All imports are from the Python standard library.

## Customization

The dashboard is built around a specific set of requirement types (UI design, data analysis, course production, internal efficiency) and a fiscal year starting in April. If your workflow differs, you'll want to customize `render_html.py`, `render_queries.py`, `render_components.py`, and `schema.sql`—the cover value formula, KPI metrics, chart labels, and type colors are all straightforward to modify. Since you're already using an AI agent to operate the system, you can just ask it to adapt the dashboard to your needs.

## Configuration

| Constant | Default | Purpose |
|----------|---------|---------|
| `COVER_VALUE_MULTIPLIER` | 20 | Cover image value multiplier |
| `FY_START_MONTH` | 4 | Fiscal year start month |
| `FY_END_MONTH` | 3 | Fiscal year end month |

Defined in `scripts/config.py`.

---

Created by [Victor42](https://victor42.work/) & [Agent Vik](https://github.com/agent-vik)
