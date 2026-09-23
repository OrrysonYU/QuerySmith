"""Trusted Plotly rendering from validated specs only."""

from pathlib import Path

import pandas as pd
import plotly.express as px

from querysmith.execution.executor import ExecutionOutcome
from querysmith.visualization.spec import ChartSpec, ChartType


def render_chart(spec: ChartSpec, result: ExecutionOutcome, output: Path) -> Path:
    frame = pd.DataFrame(result.rows, columns=result.columns).head(spec.limit)
    if spec.chart_type is ChartType.BAR:
        figure = px.bar(
            frame, x=spec.x.column, y=spec.y.column if spec.y else None, title=spec.title
        )
    elif spec.chart_type is ChartType.HBAR:
        figure = px.bar(
            frame,
            y=spec.x.column,
            x=spec.y.column if spec.y else None,
            orientation="h",
            title=spec.title,
        )
    elif spec.chart_type is ChartType.LINE:
        figure = px.line(
            frame, x=spec.x.column, y=spec.y.column if spec.y else None, title=spec.title
        )
    elif spec.chart_type is ChartType.PIE:
        figure = px.pie(
            frame, names=spec.x.column, values=spec.y.column if spec.y else None, title=spec.title
        )
    elif spec.chart_type is ChartType.SCATTER:
        figure = px.scatter(
            frame, x=spec.x.column, y=spec.y.column if spec.y else None, title=spec.title
        )
    else:
        raise ValueError("table charts do not produce Plotly artifacts")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(output, include_plotlyjs=True, full_html=True)
    return output
