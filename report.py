"""Turn analysis findings into a weekly status report.

Uses an LLM when ANTHROPIC_API_KEY is set and the `anthropic` package is
installed. Otherwise it falls back to a rule-based template, so the prototype
always works offline.
"""
from __future__ import annotations

import json
import os

MODEL = os.environ.get("STATUS_MODEL", "claude-sonnet-5-5")

SYSTEM_PROMPT = (
    "You are a program management assistant. Write a concise weekly status "
    "report for a manager from the JSON findings you are given. Use ONLY the "
    "facts in the JSON. Do not invent numbers, dates, names or causes. "
    "If a cause is not in the notes, say it is unknown and suggest asking the owner."
)

USER_PROMPT = """Findings (computed by code, treat as ground truth):

{findings}

Write the report in Markdown with these sections:
1. Overall health (one sentence, include the RAG status)
2. Progress (2-3 sentences)
3. Top risks and issues (max 4 bullets, each with owner and impact)
4. Suggested RAID log entries (type, description, owner, proposed next step)
5. Actions needed this week (max 4 bullets)
Keep it under 350 words."""


def llm_report(findings: dict) -> str | None:
    """Return an AI-written report, or None if AI is unavailable."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
    except ImportError:
        return None
    try:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=MODEL,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": USER_PROMPT.format(findings=json.dumps(findings, indent=2)),
            }],
        )
        return msg.content[0].text
    except Exception as exc:  # network, auth, model name, etc.
        print(f"[warn] AI call failed ({exc}); using template report.")
        return None


def _table(rows: list[dict], cols: list[str]) -> str:
    if not rows:
        return "_None_\n"
    head = "| " + " | ".join(cols) + " |\n"
    sep = "|" + "|".join("---" for _ in cols) + "|\n"
    body = "".join("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |\n" for r in rows)
    return head + sep + body


def template_report(f: dict) -> str:
    """Rule-based report; no AI needed."""
    lines = [
        f"# Weekly status report ({f['as_of']})",
        "",
        f"**Overall health: {f['health']}** - " + "; ".join(f["health_reasons"]) + ".",
        "",
        "## Progress",
        f"{f['done']} of {f['total_tasks']} tasks are done and average completion is "
        f"{f['percent_complete']}%. Status mix: "
        + ", ".join(f"{k} {v}" for k, v in f["status_counts"].items()) + ".",
        "",
        "## Overdue tasks",
        _table(f["overdue"], ["id", "task", "owner", "due", "days_late", "notes"]),
        "## Blocked tasks",
        _table(f["blocked"], ["id", "task", "owner", "due", "notes"]),
        "## Due in the next 7 days",
        _table(f["due_next_7_days"], ["id", "task", "owner", "due", "status"]),
        "## Suggested RAID log entries",
    ]
    raid = []
    for t in f["overdue"]:
        raid.append(
            f"- **Issue**: {t['task']} ({t['id']}) is {t['days_late']} days late. "
            f"Owner: {t['owner']}. Next step: agree a recovery date."
            + (f" Note: {t['notes']}." if t["notes"] else "")
        )
    for t in f["blocked"]:
        if t["id"] not in {o["id"] for o in f["overdue"]}:
            raid.append(
                f"- **Issue**: {t['task']} ({t['id']}) is blocked. Owner: {t['owner']}. "
                f"Next step: find the blocker and escalate."
                + (f" Note: {t['notes']}." if t["notes"] else "")
            )
    for t in f["dependency_risks"]:
        raid.append(
            f"- **Risk**: {t['task']} ({t['id']}) may slip because it depends on "
            f"{', '.join(t['caused_by'])}. Owner: {t['owner']}. "
            f"Next step: confirm a revised start date."
        )
    lines.append("\n".join(raid) if raid else "_No new entries suggested._")
    lines += ["", "## Workload by owner", _table(f["owner_load"], ["owner", "open_tasks", "overdue", "blocked"])]
    return "\n".join(lines)


def generate_report(findings: dict, use_ai: bool = True) -> tuple[str, str]:
    """Return (report_markdown, source) where source is 'ai' or 'template'."""
    if use_ai:
        text = llm_report(findings)
        if text:
            return text, "ai"
    return template_report(findings), "template"
