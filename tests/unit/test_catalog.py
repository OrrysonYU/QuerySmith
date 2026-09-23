from querysmith.schema_intel.catalog import preserve_enrichment
from querysmith.schema_intel.models import ColumnInfo, SchemaSnapshot, TableInfo


def test_drift_merge_preserves_enrichment_and_sensitive_flags() -> None:
    previous = SchemaSnapshot(
        source="x",
        tables=[
            TableInfo(
                name="customer",
                description="People",
                columns=[
                    ColumnInfo(
                        name="email",
                        data_type="text",
                        description="PII",
                        sensitive=True,
                        sample_values=[],
                    )
                ],
            )
        ],
    ).with_signature()
    current = SchemaSnapshot(
        source="x",
        tables=[
            TableInfo(
                name="customer",
                columns=[
                    ColumnInfo(name="email", data_type="varchar"),
                    ColumnInfo(name="id", data_type="int"),
                ],
            )
        ],
    ).with_signature()
    merged = preserve_enrichment(previous, current)
    assert merged.tables[0].description == "People"
    assert merged.tables[0].columns[0].sensitive
    assert merged.signature == current.signature
