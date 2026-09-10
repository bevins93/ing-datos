"""CLI utilitario: extrae de tabla_reporte_bot.csv solo las filas de una
accion especifica (ej. alta_usuario_sap) a un CSV aparte.

No vuelve a procesar logs ni aplica ninguna regla de negocio: es una
proyeccion/filtro puro sobre un CSV ya generado por `reset-report`. Util
para revisar una sola accion sin tener que buscarla a mano entre todas las
filas del reporte completo.

Uso:
    reset-report-filter --accion alta_usuario_sap \\
        --output-csv data/output/tabla_reporte_bot_alta_usuario_sap.csv

    reset-report-filter --accion reseteo_password \\
        --input-csv data/output/tabla_reporte_bot.csv \\
        --output-csv data/output/tabla_reporte_bot_reseteo_password.csv
"""

import argparse
import csv
import sys
from pathlib import Path

from reset_report.config import CSV_FIELDNAMES, DEFAULT_OUTPUT_DIR, OUTPUT_CSV_FILENAME


def filter_rows_by_accion(input_csv: Path, accion: str) -> list[dict]:
    if not input_csv.exists():
        raise FileNotFoundError(f"No existe {input_csv}")

    with open(input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader if row.get("accion") == accion]


def write_csv(rows: list[dict], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reset-report-filter",
        description=(
            "Extrae a un CSV aparte solo las filas de una accion especifica "
            "de tabla_reporte_bot.csv (no reprocesa logs)."
        ),
    )
    parser.add_argument(
        "--accion",
        required=True,
        help="Valor de la columna 'accion' a filtrar (ej. alta_usuario_sap, reseteo_password)",
    )
    parser.add_argument(
        "--input-csv",
        default=str(DEFAULT_OUTPUT_DIR / OUTPUT_CSV_FILENAME),
        help="CSV de entrada ya generado por reset-report (default: %(default)s)",
    )
    parser.add_argument("--output-csv", required=True, help="Ruta del CSV filtrado a generar")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    input_csv = Path(args.input_csv)
    output_csv = Path(args.output_csv)

    try:
        rows = filter_rows_by_accion(input_csv, args.accion)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    write_csv(rows, output_csv)
    print(f"{len(rows)} filas con accion='{args.accion}' escritas en {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
