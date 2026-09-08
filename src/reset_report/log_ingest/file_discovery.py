"""Localizacion de archivos .log dentro del directorio de entrada.

Acepta tanto "<epoch>_<YYYY-MM-DD>.log" (formato documentado originalmente)
como "<YYYY-MM-DD>.log" (formato observado en los datos reales de muestra),
sin requerir que el epoch se indique manualmente.
"""

import re
from pathlib import Path

_DATE_IN_NAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\.log$")


def find_log_file_for_date(date_str: str, input_dir: Path) -> Path:
    """Localiza el archivo de log correspondiente a una fecha (YYYY-MM-DD)
    dentro de input_dir."""
    matches = sorted(input_dir.glob(f"*{date_str}.log"))
    if not matches:
        raise FileNotFoundError(
            f"No se encontro archivo de log para la fecha {date_str} en {input_dir}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"Se encontraron multiples archivos de log para la fecha {date_str}: {matches}. "
            "Especifica un directorio de entrada mas especifico."
        )
    return matches[0]


def list_all_log_files(input_dir: Path) -> list[Path]:
    """Lista todos los .log en input_dir, ordenados por la fecha embebida en
    el nombre de archivo (no por epoch, que puede no estar presente)."""
    files = list(input_dir.glob("*.log"))

    def sort_key(path: Path) -> str:
        match = _DATE_IN_NAME_RE.search(path.name)
        return match.group(1) if match else path.name

    return sorted(files, key=sort_key)
