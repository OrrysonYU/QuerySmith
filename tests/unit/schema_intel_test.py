from querysmith.schema_intel.models import ColumnInfo, SchemaSnapshot, TableInfo
from querysmith.schema_intel.retrieval import select_candidates


def test_signature_stable_and_permissions_first() -> None:
    snapshot = SchemaSnapshot(
        source="x",
        tables=[
            TableInfo(
                name="customer",
                columns=[ColumnInfo(name="email", data_type="text", sensitive=True)],
            ),
            TableInfo(name="secret", columns=[ColumnInfo(name="value", data_type="text")]),
        ],
    ).with_signature()
    assert snapshot.signature == snapshot.with_signature().signature
    subset = select_candidates(
        snapshot,
        "customer email",
        frozenset({"customer"}),
        frozenset({"customer.email"}),
    )
    assert [table.name for table in subset.tables] == ["customer"]
    assert subset.tables[0].columns == []
