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
# para ejecutar un reseteo o un alta de usuario como solicitante.
PRIVILEGED_DESCRIPTION_PREFIXES = ("gerente", "admin")

# --- Alta de usuario en SAP (accion alta_usuario_sap) ---

# Valores validos (normalizados) del parametro `treatment` del endpoint
# sap/register_user.
VALID_TREATMENTS = ("señor", "señora")

# Puestos (normalizados) observados realmente en los 4 dias de log de
# muestra. Se usa como heuristica para la regla de 400 "el puesto solicitado
# no existe": NO es un catalogo oficial de SAP (no se nos proporciono uno),
# asi que cualquier `job` fuera de esta lista se trata como inexistente.
# Actualizar esta lista si aparecen puestos validos nuevos.
KNOWN_JOB_TITLES = (
    "gerente tienda",
    "subgerente tienda",
    "jefe de mantenimiento tienda",
    "supervisor mermas",
    "cons.internos tienda",
    "recibo tienda",
    "adm.sistemas tienda",
)

# Nombres de cadena (normalizados) que pueden aparecer dentro de un `job`
# solicitado como puesto "exclusivo" de esa cadena (ej. "Gerente City Club").
# Regla de negocio del PDF sin ejemplo real disponible: se interpreta que el
# nombre de la cadena aparece literalmente en el puesto solicitado, y que la
# pertenencia del solicitante a esa cadena se puede leer de su OU_NAME o
# DESCRIPTION en ADManager. Ajustar si la regla real usa otro campo.
CHAIN_EXCLUSIVE_JOB_KEYWORDS = ("city club", "soriana")
