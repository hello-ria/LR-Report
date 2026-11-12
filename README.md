# Weekly status and risk assistant (prototype)

Turns a task export (CSV) into a weekly status report, a list of risks and a small dashboard.

**Design choice:** Python (pandas) computes every number: overdue tasks, blockers,
dependency risks, workload and a Red/Amber/Green rule. The AI only writes the
summary and suggests RAID log entries from the findings, so it cannot change the facts.
Without an API key, a rule-based template writes the report instead.

## Setup

    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here   # optional

## Run

    # command line (sample data is a made-up project, as of 2026-10-26)
    python main.py --csv sample_tasks.csv --as-of 2026-10-26 --out report.md
    python main.py --no-ai --as-of 2026-10-26      # force the template

    # dashboard
    streamlit run app.py

## CSV format

Columns: `id, task, owner, start, due, status, percent_complete, depends_on, notes`

- `status` is one of Done, In Progress, Not Started, Blocked
- `depends_on` lists task ids separated by `;` (for example `T06;T07`)
- Dates are `YYYY-MM-DD`

## Files

- `analyze.py` - loads the CSV and computes findings
- `report.py` - AI write-up with an offline template fallback
- `main.py` - command-line tool
- `app.py` - Streamlit dashboard
- `sample_tasks.csv` - fake 22-task project

## Ideas to extend

- Read a Jira export instead of the CSV
- Add critical path calculation from `depends_on`
- Let you accept or reject suggested RAID entries and save them to a file
- Add tests for the health rule
