import csv
from pathlib import Path

import pytest

from reset_report.config import CSV_FIELDNAMES
from reset_report.filter_by_accion import filter_rows_by_accion, main, write_csv


def _write_sample_csv(path: Path) -> None:
    rows = [
        {
            "timestamp": "2026-08-29T00:00:00Z",
            "solicitante": "req1",
            "target": "tgt1",
            "accion": "reseteo_password",
            "sistema": "ADManager",
            "nombre_completo_solicitante": "",
            "nombre_completo_target": "",
            "oficina_solicitante": "",
            "oficina_target": "",
            "resultado_final": "Reseteo ejecutado exitosamente",
            "operation_id": "op1",
        },
        {
            "timestamp": "2026-08-29T00:00:01Z",
            "solicitante": "req2",
            "target": "tgt2",
            "accion": "alta_usuario_sap",
            "sistema": "SAP",
            "nombre_completo_solicitante": "",
            "nombre_completo_target": "",
            "oficina_solicitante": "",
            "oficina_target": "",
            "resultado_final": "El alta de usuario se registro exitosamente en SAP",
            "operation_id": "op2",
        },
        {
            "timestamp": "2026-08-29T00:00:02Z",
            "solicitante": "req3",
            "target": "tgt3",
            "accion": "alta_usuario_sap",
            "sistema": "SAP",
            "nombre_completo_solicitante": "",
            "nombre_completo_target": "",
            "oficina_solicitante": "",
            "oficina_target": "",
            "resultado_final": "El puesto solicitado no existe",
            "operation_id": "op3",
        },
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def test_filter_rows_by_accion_returns_only_matching_rows(tmp_path):
    input_csv = tmp_path / "tabla_reporte_bot.csv"
    _write_sample_csv(input_csv)

    rows = filter_rows_by_accion(input_csv, "alta_usuario_sap")

    assert len(rows) == 2
    assert {r["operation_id"] for r in rows} == {"op2", "op3"}
    assert all(r["accion"] == "alta_usuario_sap" for r in rows)


def test_filter_rows_by_accion_missing_input_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        filter_rows_by_accion(tmp_path / "no_existe.csv", "alta_usuario_sap")


def test_write_csv_produces_valid_header_and_rows(tmp_path):
    input_csv = tmp_path / "tabla_reporte_bot.csv"
    _write_sample_csv(input_csv)
    output_csv = tmp_path / "solo_sap.csv"

    rows = filter_rows_by_accion(input_csv, "alta_usuario_sap")
    write_csv(rows, output_csv)

    with open(output_csv, newline="", encoding="utf-8") as f:
        written_rows = list(csv.DictReader(f))

    assert len(written_rows) == 2
    with open(output_csv, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == CSV_FIELDNAMES


def test_cli_end_to_end(tmp_path):
    input_csv = tmp_path / "tabla_reporte_bot.csv"
    _write_sample_csv(input_csv)
    output_csv = tmp_path / "solo_reseteo.csv"

    exit_code = main(
        [
            "--accion",
            "reseteo_password",
            "--input-csv",
            str(input_csv),
            "--output-csv",
            str(output_csv),
        ]
    )

    assert exit_code == 0
    with open(output_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["accion"] == "reseteo_password"


def test_cli_missing_input_csv_returns_error(tmp_path):
    exit_code = main(
        [
            "--accion",
            "alta_usuario_sap",
            "--input-csv",
            str(tmp_path / "no_existe.csv"),
            "--output-csv",
            str(tmp_path / "salida.csv"),
        ]
    )
    assert exit_code == 1
