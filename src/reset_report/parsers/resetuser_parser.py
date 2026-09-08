"""Extraccion de la linea gatillo `users_admin/resetuser`."""

import re

from reset_report.log_ingest import LogBlock
from reset_report.parsers.models import ResetUserTrigger

_RESETUSER_RE = re.compile(
    r"users_admin/resetuser\?sAMAccountName_requester=(?P<requester>[^&]+)"
    r"&sAMAccountName_target=(?P<target>[^&\s]+)\s+\"HTTP/1\.1\"\s+(?P<code>\d+)"
)


def extract_resetuser_trigger(block: LogBlock) -> ResetUserTrigger | None:
    for entry in block.entries:
        match = _RESETUSER_RE.search(entry.message)
        if match:
            return ResetUserTrigger(
                timestamp=entry.timestamp,
                requester=match.group("requester"),
                target=match.group("target"),
                http_code=match.group("code"),
            )
    return None
