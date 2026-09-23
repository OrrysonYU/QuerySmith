from pathlib import Path

from querysmith.execution.executor import ExecutionOutcome
from querysmith.visualization.renderer import render_chart
from querysmith.visualization.spec import Axis, ChartSpec, ChartType


def test_trusted_renderer_writes_self_contained_html(tmp_path: Path) -> None:
    result = ExecutionOutcome(columns=["name", "total"], rows=[["A", 2], ["B", 1]], row_count=2)
    output = render_chart(
        ChartSpec(
            chart_type=ChartType.BAR, title="Totals", x=Axis(column="name"), y=Axis(column="total")
        ),
        result,
        tmp_path / "chart.html",
    )
    content = output.read_text(encoding="utf-8")
    assert "plotly" in content.lower()
    assert output.parent == tmp_path
