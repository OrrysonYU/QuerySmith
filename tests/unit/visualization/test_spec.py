import pytest
from pydantic import ValidationError

from querysmith.execution.executor import ExecutionOutcome
from querysmith.visualization.spec import Axis, ChartSpec, ChartType, validate_chart


def test_pie_downgrades_and_html_rejected() -> None:
    result = ExecutionOutcome(columns=["x", "y"], rows=[[str(i), i] for i in range(9)], row_count=9)
    verdict = validate_chart(
        ChartSpec(chart_type=ChartType.PIE, title="Safe", x=Axis(column="x"), y=Axis(column="y")),
        result,
    )
    assert verdict.spec and verdict.spec.chart_type is ChartType.BAR
    with pytest.raises(ValidationError):
        ChartSpec(chart_type=ChartType.BAR, title="<script>x</script>", x=Axis(column="x"))
