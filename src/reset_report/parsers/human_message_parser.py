"""Extraccion de la linea de texto plano que el propio bot escribe con el
resultado final de una accion, cuando existe.

Se observo en los 39 bloques reales de alta de usuario SAP disponibles que,
salvo cuando la accion se corta antes de cualquier llamada downstream (ej.
el 400 por employee_id no numerico), el bot siempre termina el bloque con
exactamente una linea de texto humano (sin ninguno de los prefijos de log
"de maquina" usados por el resto de las llamadas). Cuando esa linea existe,
es la fuente mas confiable de `resultado_final`: se usa verbatim en vez de
tratar de re-derivarla a partir de los datos crudos.
"""

from reset_report.log_ingest import LogBlock

_MACHINE_PREFIXES = (
    "HTTP Request:",
    "ADManagerRawClient",
    "ProactivanetRawClient",
    "SAPRawClient",
    "SAP input:",
    "Params to execute",
    ", Raw status_code",
    "ADM-Raw response",
)


def extract_final_human_message(block: LogBlock) -> str | None:
    """Devuelve la ultima linea del bloque que no tiene ningun prefijo de
    log "de maquina" conocido, o None si no hay ninguna."""
    message = None
    for entry in block.entries:
        if not entry.message.startswith(_MACHINE_PREFIXES):
            message = entry.message
    return message
