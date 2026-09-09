"""Extraccion de la linea gatillo `sap/register_user` (alta de usuario SAP).

`job` viene URL-encoded con `+` por espacios (ej. `Gerente+Tienda`);
`treatment` ya viene en texto plano ("señor"/"señora").
"""

import re
from urllib.parse import unquote_plus

from reset_report.log_ingest import LogBlock
from reset_report.parsers.models import RegisterUserTrigger

_REGISTER_USER_RE = re.compile(
    r"sap/register_user\?requester_username=(?P<requester>[^&]+)"
    r"&target_employee_id=(?P<target>[^&]+)"
    r"&treatment=(?P<treatment>[^&]+)"
    r"&job=(?P<job>[^&\s]+)\s+\"HTTP/1\.1\"\s+(?P<code>\d+)"
)


def extract_register_user_trigger(block: LogBlock) -> RegisterUserTrigger | None:
    for entry in block.entries:
        match = _REGISTER_USER_RE.search(entry.message)
        if match:
            return RegisterUserTrigger(
                timestamp=entry.timestamp,
                requester=match.group("requester"),
                target_employee_id=match.group("target"),
                treatment=unquote_plus(match.group("treatment")),
                job=unquote_plus(match.group("job")),
                http_code=match.group("code"),
            )
    return None
