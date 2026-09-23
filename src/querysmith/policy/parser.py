"""Fail-closed SQL structural validation."""

from sqlglot import exp, parse
from sqlglot.errors import ParseError

from querysmith.policy.verdicts import PolicyReason, PolicyVerdict

_FORBIDDEN = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.Command,
    exp.Transaction,
    exp.Lock,
)


def validate_structure(sql: str, dialect: str = "postgres") -> PolicyVerdict:
    if not sql.strip():
        return PolicyVerdict(ok=False, reason=PolicyReason.PARSE_ERROR, detail="empty SQL")
    try:
        statements = parse(sql, read=dialect)
    except (ParseError, ValueError) as exc:
        return PolicyVerdict(ok=False, reason=PolicyReason.PARSE_ERROR, detail=type(exc).__name__)
    if len(statements) != 1:
        return PolicyVerdict(ok=False, reason=PolicyReason.MULTI_STATEMENT)
    root = statements[0]
    if not isinstance(root, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        return PolicyVerdict(ok=False, reason=PolicyReason.NON_SELECT)
    if any(root.find(node_type) is not None for node_type in _FORBIDDEN):
        return PolicyVerdict(ok=False, reason=PolicyReason.FORBIDDEN_NODE)
    if root.find(exp.Into) or root.find(exp.Lock):
        return PolicyVerdict(ok=False, reason=PolicyReason.FORBIDDEN_NODE)
    normalized = root.sql(dialect=dialect, pretty=False, normalize=True)
    return PolicyVerdict(ok=True, normalized_sql=normalized)
