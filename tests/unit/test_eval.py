import importlib.util
from pathlib import Path


def test_eval_metrics_are_computed() -> None:
    spec = importlib.util.spec_from_file_location("eval_report", Path("eval/report.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.compute_metrics(
        [
            {"status": "SUCCEEDED", "attempts": 1, "golden_defined": True, "golden_match": True},
            {"status": "BLOCKED", "attempts": 0, "adversarial": True},
        ]
    )
    assert result["unsafe_query_rejection_rate"] == 1.0
    assert result["semantic_match_rate"] == 1.0
