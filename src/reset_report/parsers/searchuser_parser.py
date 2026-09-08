"""Extraccion de las respuestas SearchUser de ADManager.

La respuesta cruda (`Raw Response: {...}`) es JSON valido (comillas dobles),
a diferencia del body de ResetPwd que es un literal de Python con comillas
simples.
"""

import json
import logging
import re

from reset_report.log_ingest import LogBlock
from reset_report.parsers.models import SearchUserInfo

logger = logging.getLogger(__name__)

_FILTER_ACCOUNT_RE = re.compile(r"'filter':\s*'\(sAMAccountName:equal:([^)]+)\)'")
_RAW_RESPONSE_RE = re.compile(r"Raw Response:\s*(.*?)\n\n, Raw status_code", re.DOTALL)


def extract_searchuser_results(block: LogBlock) -> dict[str, SearchUserInfo]:
    """Devuelve {sAMAccountName: SearchUserInfo} para cada cuenta consultada
    via SearchUser dentro del bloque."""
    results: dict[str, SearchUserInfo] = {}

    for entry in block.entries:
        filter_match = _FILTER_ACCOUNT_RE.search(entry.message)
        if not filter_match:
            continue
        account = filter_match.group(1)

        raw_match = _RAW_RESPONSE_RE.search(entry.message)
        if not raw_match:
            logger.warning(
                "operation_id=%s: SearchUser de %s sin 'Raw Response' parseable",
                block.operation_id,
                account,
            )
            continue

        raw_text = raw_match.group(1).strip()
        if not raw_text:
            logger.warning(
                "operation_id=%s: SearchUser de %s trajo 'Raw Response' vacio",
                block.operation_id,
                account,
            )
            continue

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning(
                "operation_id=%s: no se pudo parsear JSON de SearchUser para %s",
                block.operation_id,
                account,
            )
            continue

        users = data.get("UsersList") or []
        if not users:
            results[account] = SearchUserInfo(account=account, found=False)
            continue

        user = users[0]
        results[account] = SearchUserInfo(
            account=account,
            found=True,
            first_name=user.get("FIRST_NAME", "") or "",
            last_name=user.get("LAST_NAME", "") or "",
            office=user.get("OFFICE", "") or "",
            description=user.get("DESCRIPTION", "") or "",
            ou_name=user.get("OU_NAME", "") or "",
        )

    return results
