"""Constantes y valores por defecto compartidos por el pipeline.

Ninguna ruta esta hardcodeada para una maquina en particular: los defaults de
aqui son relativos al directorio de trabajo y siempre pueden sobreescribirse
via argumentos de CLI (--input-dir/--output-dir).
"""

from pathlib import Path

DEFAULT_INPUT_DIR = Path("data/input")
DEFAULT_OUTPUT_DIR = Path("data/output")
OUTPUT_CSV_FILENAME = "tabla_reporte_bot.csv"

# Orden de columnas del CSV final. "operation_id" se agrega al final como
# llave tecnica de idempotencia (no forma parte de las columnas de negocio
# pedidas por el enunciado, pero es necesaria para detectar de forma
# inequivoca que registros ya fueron escritos).
CSV_FIELDNAMES = [
    "timestamp",
    "solicitante",
    "target",
    "accion",
    "sistema",
    "nombre_completo_solicitante",
    "nombre_completo_target",
    "oficina_solicitante",
    "oficina_target",
    "resultado_final",
    "operation_id",
]

# ADManager considera que una llamada a ResetPwd "tardo demasiado" alrededor
# de los 35 segundos antes de que el propio ADManager la corte y responda con
# un timeout (HTTP 504, reason "ADM timed out"). No se usa para *detectar* el
# 504 -- el log ya lo indica explicitamente via el campo `reason` -- pero se
# documenta aqui porque es la regla de negocio que explica por que existe ese
# codigo de respuesta.
ADMANAGER_TIMEOUT_SECONDS = 35

# Nombre de oficina (normalizado) que activa la regla de "target corporativo"
# (HTTP 202).
CORPORATIVO_OFFICE_NAME = "corporativo"

# OU_NAME (normalizado) que activa una de las reglas de 403.
RESTRICTED_TARGET_OU_NAME = "oat/cedis/by"

# Prefijos (normalizados) de DESCRIPTION que se consideran "con privilegios"
# para ejecutar un reseteo como solicitante.
PRIVILEGED_DESCRIPTION_PREFIXES = ("gerente", "admin")
