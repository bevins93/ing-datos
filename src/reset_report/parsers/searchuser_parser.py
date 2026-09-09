"""Extraccion de las respuestas SearchUser de ADManager.

La respuesta cruda (`Raw Response: {...}`) es JSON valido (comillas dobles),
a diferencia del body de ResetPwd/SAP raw response que es un literal de
Python con comillas simples.

SearchUser se consulta con distintos campos de filtro segun la accion:
reseteo de password filtra por `sAMAccountName`, alta de usuario en SAP
filtra al target por `employeeID`. Por eso el resultado se indexa por la
tupla (campo_filtro, valor), no solo por el valor.
"""

import json
import logging
import re

from reset_report.log_ingest import LogBlock
from reset_report.parsers.models import SearchUserInfo

logger = logging.getLogger(__name__)

_FILTER_RE = re.compile(r"'filter':\s*'\((?P<field>[a-zA-Z]+):equal:(?P<value>[^)]+)\)'")
_RAW_RESPONSE_RE = re.compile(r"Raw Response:\s*(.*?)\n\n, Raw status_code", re.DOTALL)

SearchUserKey = tuple[str, str]


def extract_searchuser_results(block: LogBlock) -> dict[SearchUserKey, SearchUserInfo]:
    """Devuelve {(campo_filtro, valor): SearchUserInfo} para cada consulta
    SearchUser dentro del bloque (ej. ("sAMAccountName", "admsistemas970") o
    ("employeeID", "1500347603"))."""
    results: dict[SearchUserKey, SearchUserInfo] = {}

    for entry in block.entries:
        filter_match = _FILTER_RE.search(entry.message)
        if not filter_match:
            continue
        field = filter_match.group("field")
        value = filter_match.group("value")
        key = (field, value)

        raw_match = _RAW_RESPONSE_RE.search(entry.message)
        if not raw_match:
            logger.warning(
                "operation_id=%s: SearchUser de %s=%s sin 'Raw Response' parseable",
                block.operation_id,
                field,
                value,
            )
            continue

        raw_text = raw_match.group(1).strip()
        if not raw_text:
            logger.warning(
                "operation_id=%s: SearchUser de %s=%s trajo 'Raw Response' vacio",
                block.operation_id,
                field,
                value,
            )
            continue

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning(
                "operation_id=%s: no se pudo parsear JSON de SearchUser para %s=%s",
                block.operation_id,
                field,
                value,
            )
            continue

        users = data.get("UsersList") or []
        if not users:
            results[key] = SearchUserInfo(account=value, found=False)
            continue

        user = users[0]
        results[key] = SearchUserInfo(
            account=value,
            found=True,
            first_name=user.get("FIRST_NAME", "") or "",
            last_name=user.get("LAST_NAME", "") or "",
            office=user.get("OFFICE", "") or "",
            description=user.get("DESCRIPTION", "") or "",
            ou_name=user.get("OU_NAME", "") or "",
        )

    return results
