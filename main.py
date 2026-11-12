"""Command-line entry point.

Examples:
    python main.py --csv sample_tasks.csv --as-of 2026-10-26
    python main.py --csv sample_tasks.csv --as-of 2026-10-26 --no-ai --out report.md
"""
import argparse
from datetime import date

from analyze import analyze, load_tasks
from report import generate_report


def main() -> None:
    p = argparse.ArgumentParser(description="AI weekly status and risk assistant")
    p.add_argument("--csv", default="sample_tasks.csv", help="task export CSV")
    p.add_argument("--as-of", default=date.today().isoformat(), help="report date, YYYY-MM-DD")
    p.add_argument("--no-ai", action="store_true", help="skip the LLM and use the template")
    p.add_argument("--out", help="write the report to this Markdown file")
    args = p.parse_args()

    df = load_tasks(args.csv)
    findings = analyze(df, args.as_of)
    text, source = generate_report(findings, use_ai=not args.no_ai)

    print(f"[report source: {source}]\n")
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
