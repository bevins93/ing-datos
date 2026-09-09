"""Helpers compartidos entre los distintos rule sets de acciones."""

from reset_report.parsers.models import SearchUserInfo


def is_found(info: SearchUserInfo | None) -> bool:
    return info is not None and info.found


def office_of(info: SearchUserInfo | None) -> str:
    return info.office if is_found(info) else ""
