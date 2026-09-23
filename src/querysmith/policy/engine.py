"""CTE-aware SQL authorization and deterministic LIMIT enforcement."""

from hashlib import sha256

from sqlglot import exp, parse_one

from querysmith.policy.config import SqlPolicy
from querysmith.policy.parser import validate_structure
from querysmith.policy.verdicts import PolicyReason, PolicyVerdict


def _name(table: exp.Table) -> str:
    return ".".join(part for part in (table.catalog, table.db, table.name) if part).lower()


def authorize(sql: str, policy: SqlPolicy, dialect: str = "postgres") -> PolicyVerdict:
    structural = validate_structure(sql, dialect)
    if not structural.ok:
        return structural
    root = parse_one(sql, read=dialect)
    ctes = {cte.alias_or_name.lower() for cte in root.find_all(exp.CTE)}
    physical_tables: list[str] = []
    for table in root.find_all(exp.Table):
        name = _name(table)
        if table.name.lower() in ctes and not table.db and not table.catalog:
            continue
        if name not in {item.lower() for item in policy.allowed_tables}:
            return PolicyVerdict(ok=False, reason=PolicyReason.UNAUTHORIZED_TABLE, detail=name)
        physical_tables.append(name)
    for star in root.find_all(exp.Star):
        if policy.reject_select_star:
            return PolicyVerdict(ok=False, reason=PolicyReason.SELECT_STAR, detail=star.sql())
    aliases = {
        table.alias.lower(): _name(table) for table in root.find_all(exp.Table) if table.alias
    }
    for column in root.find_all(exp.Column):
        table_name = aliases.get(column.table.lower(), column.table.lower()) if column.table else ""
        if not table_name and len(set(physical_tables)) == 1:
            table_name = physical_tables[0]
        qualified = f"{table_name}.{column.name.lower()}" if table_name else column.name.lower()
        blocked = {item.lower() for item in policy.blocked_columns}
        blocked_on_referenced_table = any(
            item == f"{table}.{column.name.lower()}"
            for item in blocked
            for table in physical_tables
        )
        if (
            qualified in blocked
            or column.name.lower() in blocked
            or f"{table_name}.*" in blocked
            or blocked_on_referenced_table
        ):
            return PolicyVerdict(ok=False, reason=PolicyReason.BLOCKED_COLUMN, detail=qualified)
    allowed_functions = {item.lower() for item in policy.allowed_functions}
    for function in root.find_all(exp.Func):
        name = str(function.name or function.key).lower()
        if name and name not in allowed_functions:
            return PolicyVerdict(ok=False, reason=PolicyReason.DENIED_FUNCTION, detail=name)
    limit = root.args.get("limit")
    if limit is None and policy.require_limit:
        root.set("limit", exp.Limit(expression=exp.Literal.number(policy.max_rows)))
    elif isinstance(limit, exp.Limit) and isinstance(limit.expression, exp.Literal):
        try:
            requested = int(limit.expression.this)
        except ValueError:
            requested = policy.max_rows + 1
        if requested > policy.max_rows:
            limit.set("expression", exp.Literal.number(policy.max_rows))
    rewritten = root.sql(dialect=dialect, pretty=False)
    reparsed = validate_structure(rewritten, dialect)
    if not reparsed.ok:
        return PolicyVerdict(ok=False, reason=PolicyReason.REWRITE_FAILED)
    normalized = reparsed.normalized_sql or rewritten
    return PolicyVerdict(
        ok=True,
        normalized_sql=normalized,
        rewritten_sql=rewritten,
        sql_hash=sha256(normalized.encode()).hexdigest(),
    )
