"""Motor de reglas de negocio para la accion de reseteo de contrasena en
ADManager (endpoint interno users_admin/resetuser).

`resultado_final` NUNCA contiene el status code crudo de nuestra propia API:
siempre es un mensaje humano, construido combinando ese status code con la
informacion real de ADManager ya extraida por reset_report.parsers.

Prioridad de evaluacion documentada explicitamente porque afecta el mensaje
final cuando mas de una causa aplicaria en teoria (ver README para el caso
real que valida este orden):
  403: (a) oficinas distintas -> (b) solicitante sin privilegios ->
       (c) target en OU restringida -> (d) causa no determinada
  404: (a) solo target no encontrado -> (b) solo solicitante no encontrado ->
       (c) ninguno encontrado -> (d) causa no determinada
"""

import logging

from reset_report.config import PRIVILEGED_DESCRIPTION_PREFIXES, RESTRICTED_TARGET_OU_NAME
from reset_report.log_ingest import LogBlock
from reset_report.parsers import (
    ResetPwdResult,
    SearchUserInfo,
    extract_resetpwd_result,
    extract_resetuser_trigger,
    extract_searchuser_results,
)
from reset_report.report_row import ReportRow
from reset_report.rules.base import ActionRuleSet
from reset_report.text_normalize import normalize, starts_with_any

logger = logging.getLogger(__name__)


def _is_found(info: SearchUserInfo | None) -> bool:
    return info is not None and info.found


def _office_of(info: SearchUserInfo | None) -> str:
    return info.office if _is_found(info) else ""


def _message_from_admanager_body(resetpwd_result: ResetPwdResult | None, fallback: str) -> str:
    if resetpwd_result is not None and not resetpwd_result.is_timeout:
        message = resetpwd_result.status_message
        if message:
            return f"El reseteo fallo en ADManager: {message}"
    return fallback


class AdManagerResetPasswordRules(ActionRuleSet):
    action_name = "reseteo_password"
    system_name = "ADManager"

    def matches(self, block: LogBlock) -> bool:
        return any("users_admin/resetuser" in e.message for e in block.entries)

    def build_row(self, block: LogBlock) -> ReportRow | None:
        trigger = extract_resetuser_trigger(block)
        if trigger is None:
            logger.warning(
                "operation_id=%s: contiene 'users_admin/resetuser' pero no se pudo "
                "parsear la linea gatillo, se descarta el bloque",
                block.operation_id,
            )
            return None

        searchuser_results = extract_searchuser_results(block)
        requester_info = searchuser_results.get(("sAMAccountName", trigger.requester))
        target_info = searchuser_results.get(("sAMAccountName", trigger.target))
        resetpwd_result = extract_resetpwd_result(block)

        resultado_final = self._determine_resultado_final(
            http_code=trigger.http_code,
            requester_info=requester_info,
            target_info=target_info,
            resetpwd_result=resetpwd_result,
            operation_id=block.operation_id,
        )

        return ReportRow(
            timestamp=trigger.timestamp,
            solicitante=trigger.requester,
            target=trigger.target,
            accion=self.action_name,
            sistema=self.system_name,
            nombre_completo_solicitante=(
                requester_info.nombre_completo if _is_found(requester_info) else ""
            ),
            nombre_completo_target=(target_info.nombre_completo if _is_found(target_info) else ""),
            oficina_solicitante=_office_of(requester_info),
            oficina_target=_office_of(target_info),
            resultado_final=resultado_final,
            operation_id=block.operation_id,
        )

    def _determine_resultado_final(
        self,
        http_code: str,
        requester_info: SearchUserInfo | None,
        target_info: SearchUserInfo | None,
        resetpwd_result: ResetPwdResult | None,
        operation_id: str,
    ) -> str:
        handlers = {
            "200": lambda: self._handle_200(resetpwd_result),
            "202": lambda: self._handle_202(target_info),
            "403": lambda: self._handle_403(requester_info, target_info),
            "404": lambda: self._handle_404(requester_info, target_info),
            "429": lambda: "No se pudo ejecutar el reseteo: se agotaron los tokens de ADManager",
            "500": lambda: self._handle_500(operation_id),
            "503": lambda: self._handle_503(resetpwd_result),
            "504": lambda: self._handle_504(),
        }
        handler = handlers.get(http_code)
        if handler is None:
            return f"Codigo de respuesta no reconocido ({http_code}) al ejecutar el reseteo"
        return handler()

    @staticmethod
    def _handle_200(resetpwd_result: ResetPwdResult | None) -> str:
        if resetpwd_result is not None and not resetpwd_result.is_timeout:
            if resetpwd_result.status == "1":
                return "Reseteo ejecutado exitosamente"
            return _message_from_admanager_body(
                resetpwd_result, "El reseteo fallo en ADManager: causa no determinada"
            )
        return "El reseteo no se completo: no se encontro confirmacion de ADManager (ResetPwd)"

    @staticmethod
    def _handle_202(target_info: SearchUserInfo | None) -> str:
        if _is_found(target_info) and target_info.office:
            return f"El usuario target pertenece a Corporativo (oficina: {target_info.office})"
        return "El usuario target pertenece a Corporativo"

    @staticmethod
    def _handle_403(
        requester_info: SearchUserInfo | None, target_info: SearchUserInfo | None
    ) -> str:
        if _is_found(requester_info) and _is_found(target_info):
            requester_office = normalize(requester_info.office)
            target_office = normalize(target_info.office)
            if requester_office and target_office and requester_office != target_office:
                return "El usuario solicitante y el usuario target no pertenecen a la misma oficina"

        if _is_found(requester_info) and not starts_with_any(
            requester_info.description, PRIVILEGED_DESCRIPTION_PREFIXES
        ):
            return "El usuario solicitante no tiene privilegios para ejecutar el reseteo"

        if _is_found(target_info) and normalize(target_info.ou_name) == RESTRICTED_TARGET_OU_NAME:
            return "El usuario target pertenece a una oficina restringida (OAT/Cedis/BY)"

        return "Acceso prohibido por ADManager (403): causa no determinada"

    @staticmethod
    def _handle_404(
        requester_info: SearchUserInfo | None, target_info: SearchUserInfo | None
    ) -> str:
        requester_missing = not _is_found(requester_info)
        target_missing = not _is_found(target_info)

        if target_missing and not requester_missing:
            return "El usuario objetivo no se encontro en ADManager"
        if requester_missing and not target_missing:
            return "El usuario solicitante no se encontro en ADManager"
        if requester_missing and target_missing:
            return "Ningun usuario se encontro en ADManager"
        return "Recurso no encontrado en ADManager (404): causa no determinada"

    @staticmethod
    def _handle_500(operation_id: str) -> str:
        logger.critical(
            "operation_id=%s: error interno critico e inesperado al ejecutar resetuser (500); "
            "ADManager no reporta ninguna causa identificable, requiere revision manual",
            operation_id,
        )
        return "Error interno critico e inesperado del proceso de reseteo: requiere revision manual"

    @staticmethod
    def _handle_503(resetpwd_result: ResetPwdResult | None) -> str:
        return _message_from_admanager_body(
            resetpwd_result, "El reseteo fallo en ADManager (503): sin detalle adicional disponible"
        )

    @staticmethod
    def _handle_504() -> str:
        return "El reseteo no se pudo confirmar: ADManager no respondio a tiempo (timeout)"
