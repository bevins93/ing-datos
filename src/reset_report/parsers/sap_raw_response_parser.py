"""Extraccion de `SAP raw response`, la respuesta del alta de usuario en SAP.

Formato real observado:
    SAP input: Ambiente='ECC' ... , SAP raw response: {'MT_RespAltaUsrResetPwd':
    {'Estatus': 'S', 'Mensaje': '...'}}

Es un literal de Python (comillas simples), no JSON estricto.
"""

import ast
import logging
import re

from reset_report.log_ingest import LogBlock
from reset_report.parsers.models import SapRawResponse

logger = logging.getLogger(__name__)

_SAP_RAW_RESPONSE_RE = re.compile(r"SAP raw response:\s*(?P<body>\{.*\})", re.DOTALL)


def extract_sap_raw_response(block: LogBlock) -> SapRawResponse | None:
    for entry in block.entries:
        match = _SAP_RAW_RESPONSE_RE.search(entry.message)
        if not match:
            continue

        try:
            body = ast.literal_eval(match.group("body"))
        except (ValueError, SyntaxError):
            logger.warning(
                "operation_id=%s: no se pudo parsear 'SAP raw response'", block.operation_id
            )
            continue

        payload = body.get("MT_RespAltaUsrResetPwd")
        if not isinstance(payload, dict):
            logger.warning(
                "operation_id=%s: 'SAP raw response' sin MT_RespAltaUsrResetPwd",
                block.operation_id,
            )
            continue

        return SapRawResponse(
            estatus=str(payload.get("Estatus", "")),
            mensaje=payload.get("Mensaje", "") or "",
        )

    return None
