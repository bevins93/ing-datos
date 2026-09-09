"""Estructuras de datos crudos extraidos de un LogBlock, antes de aplicar
ninguna regla de negocio."""

from dataclasses import dataclass


@dataclass
class ResetUserTrigger:
    """Datos de la linea gatillo `users_admin/resetuser`."""

    timestamp: str
    requester: str
    target: str
    http_code: str


@dataclass
class SearchUserInfo:
    """Resultado de una llamada SearchUser para una cuenta especifica."""

    account: str
    found: bool
    first_name: str = ""
    last_name: str = ""
    office: str = ""
    description: str = ""
    ou_name: str = ""

    @property
    def nombre_completo(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


@dataclass
class ResetPwdResult:
    """Resultado de la llamada ResetPwd: o bien la respuesta normal (body con
    'status'/'statusMessage'), o un timeout de ADManager (sin body)."""

    is_timeout: bool
    status: str = ""
    status_message: str = ""


@dataclass
class RegisterUserTrigger:
    """Datos de la linea gatillo `sap/register_user`."""

    timestamp: str
    requester: str
    target_employee_id: str
    treatment: str
    job: str
    http_code: str


@dataclass
class SapRawResponse:
    """Resultado de `MT_RespAltaUsrResetPwd` dentro de `SAP raw response`."""

    estatus: str
    mensaje: str
