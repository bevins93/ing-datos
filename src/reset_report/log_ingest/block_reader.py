"""Lectura de archivos de log y agrupacion en bloques por operation_Id.

Cada linea "con prefijo" tiene la forma:
    <timestamp ISO8601 Z> | INFO [operation_Id=<hash>] | <mensaje>

No toda linea fisica del archivo es un evento independiente: una linea con
prefijo puede venir seguida de lineas de continuacion SIN su propio timestamp
(por ejemplo el bloque `Params to execute POST to SearchUser: ..., Raw
Response: {...}` que continua la linea `... invoked`). Esas lineas se
concatenan al mensaje de la ultima linea con prefijo leida hasta encontrar
la siguiente linea que si empiece con un timestamp ISO8601 valido.
"""

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_PREFIX_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T[\d:.]+Z)\s*\|\s*INFO\s*\[operation_Id=(?P<opid>[0-9a-fA-F]+)\]"
    r"\s*\|\s*(?P<msg>.*)$"
)


@dataclass
class LogEntry:
    """Un registro logico del log: la linea con prefijo mas cualquier linea
    de continuacion sin prefijo que le siga."""

    timestamp: str
    operation_id: str
    message: str


@dataclass
class LogBlock:
    """Todas las entradas que comparten un mismo operation_Id, en orden
    cronologico de aparicion en el archivo."""

    operation_id: str
    entries: list[LogEntry] = field(default_factory=list)

    @property
    def first_timestamp(self) -> str | None:
        return self.entries[0].timestamp if self.entries else None

    def full_text(self) -> str:
        return "\n".join(e.message for e in self.entries)


def iter_log_entries(log_path: Path) -> Iterator[LogEntry]:
    """Genera LogEntry en el orden en que aparecen en el archivo.

    Es defensivo: lineas de continuacion antes de cualquier linea con
    prefijo se descartan con una advertencia (no deberian ocurrir en un log
    bien formado, pero no deben tumbar el proceso).
    """
    current: LogEntry | None = None

    with open(log_path, encoding="utf-8", errors="replace") as f:
        for lineno, raw_line in enumerate(f, start=1):
            line = raw_line.rstrip("\n")
            match = _PREFIX_RE.match(line)
            if match:
                if current is not None:
                    yield current
                current = LogEntry(
                    timestamp=match.group("ts"),
                    operation_id=match.group("opid"),
                    message=match.group("msg"),
                )
            else:
                if current is None:
                    if line.strip():
                        logger.warning(
                            "%s:%d: linea de continuacion sin entrada previa, se ignora",
                            log_path,
                            lineno,
                        )
                    continue
                current.message += "\n" + line

    if current is not None:
        yield current


def group_into_blocks(log_path: Path) -> list[LogBlock]:
    """Agrupa las entradas de un archivo de log por operation_Id, preservando
    el orden de primera aparicion de cada operation_Id."""
    blocks: dict[str, LogBlock] = {}

    for entry in iter_log_entries(log_path):
        block = blocks.setdefault(entry.operation_id, LogBlock(operation_id=entry.operation_id))
        block.entries.append(entry)

    return list(blocks.values())
