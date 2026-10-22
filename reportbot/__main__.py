"""Command line:  python -m reportbot <folder with PDFs> [-o report.xlsx] [--ai]"""

import argparse
import sys
from pathlib import Path

from .extract import extract
from .report import write_report
from .validate import check


def run(folder, output, use_ai=False):
    records = [extract(p) for p in sorted(Path(folder).glob("*.pdf"))]
    ai_notes = []
    if use_ai:
        import anthropic
        from .ai import ai_complete
        client = anthropic.Anthropic()
        for r in records:
            if r.method == "rules (incomplete)":
                try:
                    ai_notes += [dict(file=r.file, specimen=r.specimen_id or "?", issue=n)
                                 for n in ai_complete(r, client)]
                except anthropic.AuthenticationError:
                    sys.exit("AI step: no valid API key (set ANTHROPIC_API_KEY), run without --ai")
                except (anthropic.RateLimitError, anthropic.APIStatusError, anthropic.APIConnectionError) as err:
                    ai_notes.append(dict(file=r.file, specimen=r.specimen_id or "?", issue=f"AI step failed: {err}"))
    status, issues = check(records)
    write_report(records, status, issues + ai_notes, output)
    return records, status, issues + ai_notes


def main():
    ap = argparse.ArgumentParser(description="Read tensile test reports (PDF) and write an Excel summary.")
    ap.add_argument("folder", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("output/test_summary.xlsx"))
    ap.add_argument("--ai", action="store_true", help="read free-text reports with Claude (needs an API key)")
    args = ap.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    records, status, issues = run(args.folder, args.output, args.ai)
    print(f"{len(records)} reports read")
    for r in sorted(records, key=lambda r: r.file):
        st, why = status[r.file]
        print(f"  {st:<7} {r.specimen_id or '?':<8} {r.file:<30} {why}")
    print(f"{len(issues)} issue(s) to review. Report: {args.output}")


if __name__ == "__main__":
    main()
