"""Compare completed evaluation runs without calling a model API."""

import argparse
import json
import sys
import zlib

from . import __version__
from .core import compare, load_run, markdown_report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compare evaluation JSONL by ID and gate regressions."
    )
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    parser.add_argument("--metric", action="append", required=True, metavar="NAME:lower|higher")
    parser.add_argument("--id-key", default="id")
    parser.add_argument(
        "--tolerance", type=float, default=0.0, help="Absolute per-sample tolerance in metric units"
    )
    parser.add_argument("--max-details", type=int, default=100)
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    metrics = {}
    for item in args.metric:
        name, sep, direction = item.rpartition(":")
        if not sep or not name or direction not in ("lower", "higher") or name in metrics:
            parser.error("--metric must be a unique NAME:lower or NAME:higher")
        metrics[name] = direction
    try:
        report = compare(
            load_run(args.baseline),
            load_run(args.candidate),
            metrics,
            tolerance=args.tolerance,
            id_key=args.id_key,
            max_details=args.max_details,
        )
    except (OSError, ValueError, EOFError, zlib.error, OverflowError) as exc:
        print("eval-delta: " + str(exc), file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False))
    elif args.format == "markdown":
        print(markdown_report(report), end="")
    else:
        print(
            f"{'PASS' if report['passed'] else 'FAIL'} | {report['paired']} paired samples | {len(report['missing_in_candidate'])} missing | {len(report['new_in_candidate'])} new"
        )
        for name, stats in report["metrics"].items():
            print(
                f"{json.dumps(name)} ({stats['direction']}): mean change {stats['mean_change']}, {stats['regressions']} regressions, {stats['improvements']} improvements"
            )
    return int(not report["passed"])
