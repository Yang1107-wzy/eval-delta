"""Deterministic paired comparisons of numeric evaluation metrics."""

import gzip
import json
import math
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from statistics import fmean


def _object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("Duplicate JSON property.")
        obj[key] = value
    return obj


def _constant(_):
    raise ValueError("Nonfinite JSON number.")


def _safe_float(text):
    """Reject decimal literals which lose decimal digits on a float round-trip."""
    value = float(text)
    try:
        exact = Decimal(text)
    except InvalidOperation:
        raise ValueError("Unsupported decimal literal.") from None
    if not math.isfinite(value) or Decimal(str(value)) != exact:
        raise ValueError("Number cannot round-trip through float without decimal digit loss.")
    return value


def load_run(path):
    """Read object JSONL; reject ambiguous JSON before comparing runs."""
    path = Path(path)
    rows = []
    with (
        gzip.open(path, "rt", encoding="utf-8")
        if path.suffix == ".gz"
        else path.open(encoding="utf-8")
    ) as f:
        for line, text in enumerate(f, 1):
            try:
                row = json.loads(
                    text,
                    object_pairs_hook=_object,
                    parse_constant=_constant,
                    parse_float=_safe_float,
                )
                if not isinstance(row, dict):
                    raise ValueError("Each row must be an object.")
            except (ValueError, RecursionError):
                raise ValueError(
                    f"Invalid JSON object or unsupported numeric precision at line {line}."
                ) from None
            rows.append(row)
    return rows


def _index(rows, metrics, id_key):
    indexed = {}
    for line, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Row {line} must be an object.")
        identifier = row.get(id_key)
        if (
            isinstance(identifier, bool)
            or not isinstance(identifier, (str, int))
            or identifier == ""
        ):
            raise ValueError(f"Row {line} requires a nonempty string or integer ID.")
        key = json.dumps(identifier, ensure_ascii=True)
        if key in indexed:
            raise ValueError(f"Duplicate ID at row {line}.")
        for metric in metrics:
            value = row.get(metric)
            try:
                valid = (
                    not isinstance(value, bool)
                    and isinstance(value, (int, float))
                    and math.isfinite(value)
                )
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError(f"Row {line} has a missing or nonfinite numeric metric.")
        indexed[key] = row
    return indexed


def compare(baseline, candidate, metrics, *, tolerance=0.0, id_key="id", max_details=100):
    """Align by typed ID, compare absolute per-case change, summarize paired means.

    A pass requires nonempty identical ID sets and zero per-case regressions.
    Metric directions are 'lower' or 'higher'. Tolerance is in metric units.
    Detailed rows are capped; counts and aggregate metrics cover all paired IDs.
    """
    if not metrics or any(direction not in ("lower", "higher") for direction in metrics.values()):
        raise ValueError("Provide at least one metric with direction lower or higher.")
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Tolerance must be finite and nonnegative.")
    if max_details < 0:
        raise ValueError("max_details must be nonnegative.")
    left, right = _index(baseline, metrics, id_key), _index(candidate, metrics, id_key)
    shared = sorted(left.keys() & right.keys())
    missing = sorted(left.keys() - right.keys())
    added = sorted(right.keys() - left.keys())
    result = {
        "schema_version": 1,
        "paired": len(shared),
        "baseline_rows": len(left),
        "candidate_rows": len(right),
        "missing_in_candidate": [left[k][id_key] for k in missing],
        "new_in_candidate": [right[k][id_key] for k in added],
        "tolerance": tolerance,
        "metrics": {},
        "details": [],
        "passed": bool(shared) and not missing and not added,
    }
    for metric, direction in metrics.items():
        stats = {
            "direction": direction,
            "baseline_mean": None,
            "candidate_mean": None,
            "mean_change": None,
            "regressions": 0,
            "improvements": 0,
            "unchanged": 0,
        }
        old_values, new_values, changes = [], [], []
        for key in shared:
            old, new = left[key][metric], right[key][metric]
            exact_change = Fraction(str(new)) - Fraction(str(old))
            try:
                change = float(exact_change)
            except OverflowError:
                raise ValueError(
                    "Metric difference overflow; rescale your metric values."
                ) from None
            if not math.isfinite(change):
                raise ValueError("Metric difference overflow; rescale your metric values.")
            worsening = exact_change if direction == "lower" else -exact_change
            exact_tolerance = Fraction(str(tolerance))
            status = (
                "regression"
                if worsening > exact_tolerance
                else "improvement"
                if worsening < -exact_tolerance
                else "unchanged"
            )
            stats[
                {
                    "regression": "regressions",
                    "improvement": "improvements",
                    "unchanged": "unchanged",
                }[status]
            ] += 1
            old_values.append(old)
            new_values.append(new)
            changes.append(change)
            if status == "regression" and len(result["details"]) < max_details:
                result["details"].append(
                    {
                        "id": left[key][id_key],
                        "metric": metric,
                        "baseline": old,
                        "candidate": new,
                        "change": change,
                        "status": status,
                    }
                )
        if shared:
            try:
                stats.update(
                    baseline_mean=fmean(old_values),
                    candidate_mean=fmean(new_values),
                    mean_change=fmean(changes),
                )
            except OverflowError:
                raise ValueError("Metric mean overflow; rescale your metric values.") from None
            if not all(
                math.isfinite(stats[key])
                for key in ("baseline_mean", "candidate_mean", "mean_change")
            ):
                raise ValueError("Metric mean overflow; rescale your metric values.")
        if stats["regressions"]:
            result["passed"] = False
        result["metrics"][metric] = stats
    return result


def _escape(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def markdown_report(report):
    """Format a compact report suitable for a GitHub Actions job summary."""
    lines = [
        "# Evaluation delta",
        "",
        f"Result: **{'PASS' if report['passed'] else 'FAIL'}**",
        f"Paired samples: {report['paired']}; missing: {len(report['missing_in_candidate'])}; new: {len(report['new_in_candidate'])}.",
        "",
        "| Metric | Direction | Baseline mean | Candidate mean | Change | Regressions |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for name, stats in report["metrics"].items():
        values = [
            name,
            stats["direction"],
            stats["baseline_mean"],
            stats["candidate_mean"],
            stats["mean_change"],
            stats["regressions"],
        ]
        lines.append(
            "| "
            + " | ".join(
                _escape("—" if v is None else f"{v:.6g}" if isinstance(v, float) else v)
                for v in values
            )
            + " |"
        )
    if report["details"]:
        lines.extend(
            [
                "",
                "## Regression samples",
                "",
                "| ID | Metric | Baseline | Candidate | Change |",
                "| --- | --- | ---: | ---: | ---: |",
            ]
        )
        for row in report["details"]:
            lines.append(
                "| "
                + " | ".join(
                    _escape(row[k]) for k in ("id", "metric", "baseline", "candidate", "change")
                )
                + " |"
            )
    return "\n".join(lines) + "\n"
