from querysmith.agent.state import Intent
from querysmith.execution.executor import ExecutionOutcome
from querysmith.validation.shape import ShapeStatus, validate_shape


def test_empty_is_not_success_and_top_n_is_enforced() -> None:
    intent = Intent(metric="total", expected_columns=["total"], top_n=1)
    assert validate_shape(ExecutionOutcome(columns=["total"]), intent).status is ShapeStatus.EMPTY
    result = ExecutionOutcome(columns=["total"], rows=[[1], [2]], row_count=2)
    assert validate_shape(result, intent).status is ShapeStatus.MISMATCH
