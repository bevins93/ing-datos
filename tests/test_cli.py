import csv
import shutil
from pathlib import Path

from reset_report.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_date_flag_processes_matching_file(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    shutil.copy(FIXTURES / "reset_200_success.log", input_dir / "2026-08-29.log")

    exit_code = main(
        [
            "--date",
            "2026-08-29",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    csv_path = output_dir / "tabla_reporte_bot.csv"
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["resultado_final"] == "Reseteo ejecutado exitosamente"


def test_cli_missing_date_returns_error(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    exit_code = main(
        [
            "--date",
            "2099-01-01",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 1


def test_cli_all_flag_processes_every_log(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    shutil.copy(FIXTURES / "reset_200_success.log", input_dir / "2026-08-29.log")
    shutil.copy(FIXTURES / "reset_403_office_mismatch.log", input_dir / "2026-08-30.log")

    exit_code = main(["--all", "--input-dir", str(input_dir), "--output-dir", str(output_dir)])

    assert exit_code == 0
    csv_path = output_dir / "tabla_reporte_bot.csv"
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
