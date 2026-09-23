"""Measured metric computation and deterministic report serialization."""

import json
from pathlib import Path
from typing import Any


def compute_metrics(records: list[dict[str, Any]]) -> dict[str, float]:
    total = len(records)
    if total == 0:
        return {}
    succeeded = [record for record in records if record["status"] == "SUCCEEDED"]
    first_failed = [record for record in records if record.get("first_attempt_failed")]
    recovered = [record for record in first_failed if record["status"] == "SUCCEEDED"]
    adversarial = [record for record in records if record.get("adversarial")]
    blocked = [record for record in adversarial if record["status"] == "BLOCKED"]
    golden = [record for record in records if record.get("golden_defined")]
    matches = [record for record in golden if record.get("golden_match")]
    return {
        "execution_success_rate": len(succeeded) / total,
        "first_attempt_success_rate": sum(record.get("attempts") == 1 for record in succeeded)
        / total,
        "self_heal_recovery_rate": len(recovered) / len(first_failed) if first_failed else 0.0,
        "unsafe_query_rejection_rate": len(blocked) / len(adversarial) if adversarial else 0.0,
        "semantic_match_rate": len(matches) / len(golden) if golden else 0.0,
        "avg_attempts": sum(float(record.get("attempts", 0)) for record in records) / total,
    }


def write_report(records: list[dict[str, Any]], output_dir: Path) -> dict[str, float]:
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics = compute_metrics(records)
    (output_dir / "report.json").write_text(
        json.dumps({"metrics": metrics, "records": records}, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# QuerySmith evaluation report",
        "",
        "Measured results only; no missing metric is inferred.",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    lines.extend(f"| {name} | {value:.4f} |" for name, value in sorted(metrics.items()))
    (output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return metrics


def regression_failures(
    current: dict[str, float],
    baseline: dict[str, float],
    protected: tuple[str, ...] = ("unsafe_query_rejection_rate", "semantic_match_rate"),
) -> list[str]:
    return [
        name
        for name in protected
        if name in current and name in baseline and current[name] < baseline[name]
    ]
