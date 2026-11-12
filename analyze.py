"""Deterministic analysis of a task export.

All numbers in the status report come from this module, not from an AI model.
The AI step (report.py) only turns these findings into readable writing.
"""
from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = [
    "id", "task", "owner", "start", "due",
    "status", "percent_complete", "depends_on", "notes",
]
VALID_STATUSES = {"Done", "In Progress", "Not Started", "Blocked"}


def load_tasks(path_or_buffer) -> pd.DataFrame:
    """Read and validate a task CSV."""
    df = pd.read_csv(path_or_buffer)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(missing)}")

    df["start"] = pd.to_datetime(df["start"])
    df["due"] = pd.to_datetime(df["due"])
    df["percent_complete"] = pd.to_numeric(df["percent_complete"]).fillna(0)
    df["depends_on"] = df["depends_on"].fillna("").astype(str)
    df["notes"] = df["notes"].fillna("").astype(str)

    bad = set(df["status"]) - VALID_STATUSES
    if bad:
        raise ValueError(f"Unknown status values: {sorted(bad)}. Use {sorted(VALID_STATUSES)}")
    return df


def _row(r: pd.Series, as_of: pd.Timestamp) -> dict:
    return {
        "id": r["id"],
        "task": r["task"],
        "owner": r["owner"],
        "due": r["due"].strftime("%Y-%m-%d"),
        "days_late": max(int((as_of - r["due"]).days), 0),
        "status": r["status"],
        "notes": r["notes"],
    }


def analyze(df: pd.DataFrame, as_of) -> dict:
    """Return a JSON-friendly dict of findings for the given date."""
    as_of = pd.Timestamp(as_of).normalize()
    open_tasks = df[df["status"] != "Done"]

    overdue = open_tasks[open_tasks["due"] < as_of].sort_values("due")
    blocked = df[df["status"] == "Blocked"]
    due_soon = open_tasks[
        (open_tasks["due"] >= as_of) & (open_tasks["due"] <= as_of + pd.Timedelta(days=7))
    ].sort_values("due")

    # A task is at risk if something it depends on is overdue or blocked.
    problem_ids = set(overdue["id"]) | set(blocked["id"])
    dependency_risks = []
    for _, r in open_tasks.iterrows():
        deps = [d.strip() for d in r["depends_on"].split(";") if d.strip()]
        hit = [d for d in deps if d in problem_ids]
        if hit:
            item = _row(r, as_of)
            item["caused_by"] = hit
            dependency_risks.append(item)

    owner_load = []
    for owner, grp in df.groupby("owner"):
        grp_open = grp[grp["status"] != "Done"]
        owner_load.append({
            "owner": owner,
            "open_tasks": int(len(grp_open)),
            "overdue": int((grp_open["due"] < as_of).sum()),
            "blocked": int((grp_open["status"] == "Blocked").sum()),
        })

    # Simple, explainable health rule.
    reasons = []
    if len(overdue) >= 3:
        reasons.append(f"{len(overdue)} tasks are overdue")
    if len(blocked) >= 2:
        reasons.append(f"{len(blocked)} tasks are blocked")
    if reasons:
        health = "Red"
    else:
        if len(overdue):
            reasons.append(f"{len(overdue)} task(s) overdue")
        if len(blocked):
            reasons.append(f"{len(blocked)} task(s) blocked")
        if dependency_risks:
            reasons.append(f"{len(dependency_risks)} task(s) depend on late or blocked work")
        health = "Amber" if reasons else "Green"
        if not reasons:
            reasons.append("No overdue or blocked work")

    return {
        "as_of": as_of.strftime("%Y-%m-%d"),
        "total_tasks": int(len(df)),
        "done": int((df["status"] == "Done").sum()),
        "percent_complete": round(float(df["percent_complete"].mean()), 1),
        "status_counts": {k: int(v) for k, v in df["status"].value_counts().items()},
        "health": health,
        "health_reasons": reasons,
        "overdue": [_row(r, as_of) for _, r in overdue.iterrows()],
        "blocked": [_row(r, as_of) for _, r in blocked.iterrows()],
        "due_next_7_days": [_row(r, as_of) for _, r in due_soon.iterrows()],
        "dependency_risks": dependency_risks,
        "owner_load": owner_load,
    }
