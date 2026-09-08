"""Escritura idempotente y acumulativa de tabla_reporte_bot.csv.

La llave de idempotencia es `operation_id`: en cada corrida se cargan los
`operation_id` ya presentes en el CSV de salida y solo se agregan (append)
las filas nuevas. Nunca se reescriben ni se eliminan filas existentes, lo
que permite reprocesar el log de cualquier dia (por ejemplo uno corregido)
sin duplicar registros.
"""

import csv
import logging
from dataclasses import asdict
from pathlib import Path

from reset_report.config import CSV_FIELDNAMES
from reset_report.report_row import ReportRow

logger = logging.getLogger(__name__)


def load_existing_operation_ids(csv_path: Path) -> set[str]:
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return set()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["operation_id"] for row in reader if row.get("operation_id")}


def append_new_rows(csv_path: Path, rows: list[ReportRow]) -> list[ReportRow]:
    """Agrega a csv_path unicamente las filas cuyo operation_id no exista ya
    en el archivo. Nunca reescribe ni elimina filas existentes.

    Devuelve la lista de filas efectivamente escritas.
    """
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids = load_existing_operation_ids(csv_path)

    new_rows: list[ReportRow] = []
    seen_in_batch: set[str] = set()
    for row in rows:
        if row.operation_id in existing_ids or row.operation_id in seen_in_batch:
            continue
        seen_in_batch.add(row.operation_id)
        new_rows.append(row)

    needs_header = not csv_path.exists() or csv_path.stat().st_size == 0

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        if needs_header:
            writer.writeheader()
        for row in new_rows:
            writer.writerow(asdict(row))

    logger.info(
        "%s: %d filas nuevas agregadas (%d ya existian)",
        csv_path,
        len(new_rows),
        len(rows) - len(new_rows),
    )
    return new_rows
