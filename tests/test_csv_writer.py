import csv
from pathlib import Path

from reset_report.pipeline import process_log_file

FIXTURES = Path(__file__).parent / "fixtures"


def _read_csv_rows(csv_path: Path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_processing_twice_is_idempotent(tmp_path):
    output_csv = tmp_path / "tabla_reporte_bot.csv"

    process_log_file(FIXTURES / "reset_200_success.log", output_csv)
    rows_after_first = _read_csv_rows(output_csv)
    assert len(rows_after_first) == 1

    process_log_file(FIXTURES / "reset_200_success.log", output_csv)
    rows_after_second = _read_csv_rows(output_csv)

    assert len(rows_after_second) == 1
    assert rows_after_second == rows_after_first


def test_reprocessing_corrected_file_only_adds_new_rows(tmp_path):
    output_csv = tmp_path / "tabla_reporte_bot.csv"

    process_log_file(FIXTURES / "reset_200_success.log", output_csv)
    original_rows = _read_csv_rows(output_csv)
    assert len(original_rows) == 1

    process_log_file(FIXTURES / "reset_200_success_corrected.log", output_csv)
    updated_rows = _read_csv_rows(output_csv)

    assert len(updated_rows) == 2
    assert updated_rows[0] == original_rows[0]
    assert updated_rows[1]["operation_id"] == "10000000000000000000000000000002"
    assert updated_rows[1]["resultado_final"] == "Reseteo ejecutado exitosamente"


def test_other_actions_only_produces_no_rows(tmp_path):
    output_csv = tmp_path / "tabla_reporte_bot.csv"

    new_rows = process_log_file(FIXTURES / "other_actions_only.log", output_csv)

    assert new_rows == []
    assert not output_csv.exists() or _read_csv_rows(output_csv) == []
