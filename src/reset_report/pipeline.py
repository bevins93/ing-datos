"""Pipeline central: log -> bloques -> rule set que matchea -> filas -> CSV.

Este modulo no conoce ningun detalle de ninguna accion en particular: solo
recorre reset_report.rules.REGISTRY. Agregar una accion nueva no requiere
tocar este archivo (ver reset_report.rules.base.ActionRuleSet).
"""

import logging
from pathlib import Path

from reset_report.log_ingest import group_into_blocks
from reset_report.output import append_new_rows
from reset_report.report_row import ReportRow
from reset_report.rules import REGISTRY

logger = logging.getLogger(__name__)


def parse_log_file(log_path: Path) -> list[ReportRow]:
    blocks = group_into_blocks(log_path)
    rows: list[ReportRow] = []

    for block in blocks:
        rule_set = next((rs for rs in REGISTRY if rs.matches(block)), None)
        if rule_set is None:
            continue  # bloque de una accion/sistema no reportado (ignorar)

        try:
            row = rule_set.build_row(block)
        except Exception:
            logger.exception(
                "operation_id=%s: error inesperado al construir la fila con %s, se omite",
                block.operation_id,
                type(rule_set).__name__,
            )
            continue

        if row is not None:
            rows.append(row)

    return rows


def process_log_file(log_path: Path, output_csv: Path) -> list[ReportRow]:
    logger.info("Procesando %s", log_path)
    rows = parse_log_file(log_path)
    return append_new_rows(output_csv, rows)
