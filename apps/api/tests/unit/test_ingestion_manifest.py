from pathlib import Path

import pytest


def _write_csv(path: Path, header: list[str]) -> None:
    path.write_text(",".join(header) + "\n")


def test_validate_source_directory_passes_with_all_required_files(tmp_path: Path) -> None:
    from app.ingestion.manifest import REQUIRED_FILES, validate_source_directory

    for spec in REQUIRED_FILES.values():
        _write_csv(tmp_path / spec["filename"], spec["columns"])

    validate_source_directory(tmp_path)  # should not raise


def test_validate_source_directory_reports_missing_file(tmp_path: Path) -> None:
    from app.ingestion.manifest import IngestionValidationError, validate_source_directory

    with pytest.raises(IngestionValidationError) as exc_info:
        validate_source_directory(tmp_path)

    assert "olist_customers_dataset.csv" in str(exc_info.value)


def test_validate_source_directory_reports_missing_column(tmp_path: Path) -> None:
    from app.ingestion.manifest import (
        REQUIRED_FILES,
        IngestionValidationError,
        validate_source_directory,
    )

    for spec in REQUIRED_FILES.values():
        _write_csv(tmp_path / spec["filename"], spec["columns"])

    # Corrupt one file's header by dropping a required column.
    customers_spec = REQUIRED_FILES["customers"]
    broken_columns = [c for c in customers_spec["columns"] if c != "customer_state"]
    _write_csv(tmp_path / customers_spec["filename"], broken_columns)

    with pytest.raises(IngestionValidationError) as exc_info:
        validate_source_directory(tmp_path)

    assert "customer_state" in str(exc_info.value)
