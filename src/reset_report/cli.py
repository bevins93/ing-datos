"""CLI de reset-report: actualiza tabla_reporte_bot.csv a partir de los logs
diarios del bot de reseteo de contrasenas.

Pensado para correr en una terminal Linux sin ningun input interactivo; toda
la configuracion se pasa por argumentos de linea de comandos.

Ejemplos:
    reset-report --date 2026-08-29 --input-dir data/input --output-dir data/output
    reset-report --date 2026-08-29 --log-path /ruta/absoluta/2026-08-29.log
    reset-report --all --input-dir data/input --output-dir data/output
"""

import argparse
import logging
import sys
from pathlib import Path

from reset_report.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, OUTPUT_CSV_FILENAME
from reset_report.log_ingest import find_log_file_for_date, list_all_log_files
from reset_report.pipeline import process_log_file


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reset-report",
        description="Actualiza tabla_reporte_bot.csv a partir de los logs diarios",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date", help="Fecha a procesar, formato YYYY-MM-DD")
    group.add_argument(
        "--all",
        action="store_true",
        help="Procesa todos los .log en --input-dir, en orden de fecha",
    )
    parser.add_argument(
        "--log-path", help="Ruta explicita a un archivo de log (solo valido con --date)"
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help=f"Directorio con los .log de entrada (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Directorio donde escribir {OUTPUT_CSV_FILENAME} (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument("--verbose", action="store_true", help="Logging en nivel DEBUG")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.log_path and args.all:
        parser.error("--log-path no se puede usar junto con --all")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    input_dir = Path(args.input_dir)
    output_csv = Path(args.output_dir) / OUTPUT_CSV_FILENAME

    if args.all:
        log_files = list_all_log_files(input_dir)
        if not log_files:
            print(f"No se encontraron archivos .log en {input_dir}", file=sys.stderr)
            return 1
    elif args.log_path:
        log_files = [Path(args.log_path)]
    else:
        try:
            log_files = [find_log_file_for_date(args.date, input_dir)]
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1

    total_new = 0
    for log_file in log_files:
        total_new += len(process_log_file(log_file, output_csv))

    print(f"Listo. {total_new} filas nuevas agregadas a {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
