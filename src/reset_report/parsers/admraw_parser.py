"""Extraccion del resultado de la llamada ResetPwd (`ADM-Raw response`).

Dos formatos observados en los logs reales:

  - Respuesta normal (incluso cuando el reseteo *fallo* en ADManager):
      ADM-Raw response | status: 200 | body: [{'statusMessage': '...', 'status': '0', ...}]
    El body es un literal de Python (comillas simples), no JSON estricto.

  - Timeout de ADManager (sin body):
      ADM-Raw response | status: 504 | reason: ADM timed out | timeout_type: ReadTimeout | url: ...
"""

import ast
import logging
import re

from reset_report.log_ingest import LogBlock
from reset_report.parsers.models import ResetPwdResult

logger = logging.getLogger(__name__)

_TIMEOUT_RE = re.compile(
    r"ADM-Raw response \| status: \d+ \| reason:\s*(?P<reason>.+?)\s*\|\s*timeout_type:"
)
_BODY_RE = re.compile(r"ADM-Raw response \| status: \d+ \| body:\s*(?P<body>\[.*\])", re.DOTALL)


def extract_resetpwd_result(block: LogBlock) -> ResetPwdResult | None:
    for entry in block.entries:
        timeout_match = _TIMEOUT_RE.search(entry.message)
        if timeout_match:
            return ResetPwdResult(is_timeout=True, status_message=timeout_match.group("reason"))

        body_match = _BODY_RE.search(entry.message)
        if body_match:
            try:
                body = ast.literal_eval(body_match.group("body"))
            except (ValueError, SyntaxError):
                logger.warning(
                    "operation_id=%s: no se pudo parsear body de ADM-Raw response",
                    block.operation_id,
                )
                continue

            if not body:
                continue

            result = body[0]
            return ResetPwdResult(
                is_timeout=False,
                status=str(result.get("status", "")),
                status_message=result.get("statusMessage", "") or "",
            )

    return None
