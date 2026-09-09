"""Motor de reglas de negocio para la accion de alta de usuario en SAP
(endpoint interno sap/register_user).

`resultado_final` NUNCA contiene el status code crudo, igual que en reseteo
de password.

A diferencia de reseteo, el propio bot ya escribe casi siempre una linea de
texto humano con el resultado final del bloque (ver
reset_report.parsers.human_message_parser). Cuando existe, se usa tal cual:
es la fuente mas fiel de lo que realmente paso. Solo se deriva un mensaje a
partir de los datos crudos cuando esa linea no esta disponible (los 4
subcasos de 400 se cortan antes de cualquier llamada downstream y nunca la
tienen) o cuando el codigo tiene un texto fijo documentado (500 y 503, igual
que el 504 de reseteo).

Prioridad de evaluacion para las derivaciones de 403/404 (aplica solo cuando
no hay linea humana disponible):
  403: (a) solicitante de OAT/corporativo -> (b) oficinas distintas ->
       (c) target no es gerente -> (d) puesto exclusivo de una cadena ->
       (e) causa no determinada
  404: (a) solo target no encontrado -> (b) solo solicitante no encontrado ->
       (c) ninguno encontrado -> (d) causa no determinada

Nota de diseno (documentada porque es una interpretacion, no un hecho
verificado con un log real): las causas de 403 "el solicitante no pertenece
a City Club/Soriana" se detectan asumiendo que el nombre de la cadena
aparece literalmente dentro del `job` solicitado (ej. "Gerente City Club") y
que la pertenencia del solicitante a esa cadena se puede leer de su OU_NAME o
DESCRIPTION en ADManager. No hay un ejemplo real disponible para confirmar
esta regla; ajustar CHAIN_EXCLUSIVE_JOB_KEYWORDS o esta logica si el campo
real es distinto.
"""

import logging

from reset_report.config import (
    CHAIN_EXCLUSIVE_JOB_KEYWORDS,
    CORPORATIVO_OFFICE_NAME,
    KNOWN_JOB_TITLES,
    PRIVILEGED_DESCRIPTION_PREFIXES,
    VALID_TREATMENTS,
)
from reset_report.log_ingest import LogBlock
from reset_report.parsers import (
    RegisterUserTrigger,
    SapRawResponse,
    SearchUserInfo,
    extract_final_human_message,
    extract_register_user_trigger,
    extract_sap_raw_response,
    extract_searchuser_results,
)
from reset_report.report_row import ReportRow
from reset_report.rules.base import ActionRuleSet
from reset_report.rules.common import is_found, office_of
from reset_report.text_normalize import normalize, starts_with_any

logger = logging.getLogger(__name__)


class AltaUsuarioSapRules(ActionRuleSet):
    action_name = "alta_usuario_sap"
    system_name = "SAP"

    def matches(self, block: LogBlock) -> bool:
        return any("sap/register_user" in e.message for e in block.entries)

    def build_row(self, block: LogBlock) -> ReportRow | None:
        trigger = extract_register_user_trigger(block)
        if trigger is None:
            logger.warning(
                "operation_id=%s: contiene 'sap/register_user' pero no se pudo "
                "parsear la linea gatillo, se descarta el bloque",
                block.operation_id,
            )
            return None

        searchuser_results = extract_searchuser_results(block)
        requester_info = searchuser_results.get(("sAMAccountName", trigger.requester))
        target_info = searchuser_results.get(("employeeID", trigger.target_employee_id))
        sap_response = extract_sap_raw_response(block)
        final_message = extract_final_human_message(block)

        resultado_final = self._determine_resultado_final(
            trigger=trigger,
            requester_info=requester_info,
            target_info=target_info,
            sap_response=sap_response,
            final_message=final_message,
            operation_id=block.operation_id,
        )

        return ReportRow(
            timestamp=trigger.timestamp,
            solicitante=trigger.requester,
            target=trigger.target_employee_id,
            accion=self.action_name,
            sistema=self.system_name,
            nombre_completo_solicitante=(
                requester_info.nombre_completo if is_found(requester_info) else ""
            ),
            nombre_completo_target=(target_info.nombre_completo if is_found(target_info) else ""),
            oficina_solicitante=office_of(requester_info),
            oficina_target=office_of(target_info),
            resultado_final=resultado_final,
            operation_id=block.operation_id,
        )

    def _determine_resultado_final(
        self,
        trigger: RegisterUserTrigger,
        requester_info: SearchUserInfo | None,
        target_info: SearchUserInfo | None,
        sap_response: SapRawResponse | None,
        final_message: str | None,
        operation_id: str,
    ) -> str:
        code = trigger.http_code

        # 500 y 503 siempre usan un texto fijo, sin importar si el bot dejo
        # una linea humana en el log (igual que el 504 de reseteo).
        if code == "500":
            return self._handle_500(operation_id)
        if code == "503":
            return (
                "Todas las validaciones fueron exitosas, pero el servicio del lado de SAP fallo"
            )

        if final_message:
            return final_message

        handlers = {
            "200": lambda: "El alta de usuario se registro exitosamente en SAP",
            "202": lambda: (
                "El alta de usuario se registro exitosamente en SAP, pero hubo un "
                "problema con el ticket de seguimiento"
            ),
            "208": lambda: self._handle_208(trigger, sap_response),
            "400": lambda: self._handle_400(trigger),
            "401": lambda: self._handle_401(requester_info),
            "403": lambda: self._handle_403(trigger, requester_info, target_info),
            "404": lambda: self._handle_404(requester_info, target_info),
        }
        handler = handlers.get(code)
        if handler is None:
            return f"Codigo de respuesta no reconocido ({code}) al ejecutar el alta de usuario"
        return handler()

    @staticmethod
    def _handle_208(trigger: RegisterUserTrigger, sap_response: SapRawResponse | None) -> str:
        if sap_response and sap_response.mensaje:
            return sap_response.mensaje
        return (
            f"El empleado {trigger.target_employee_id} ya existe en el ambiente ECC ECP de SAP."
        )

    @staticmethod
    def _handle_400(trigger: RegisterUserTrigger) -> str:
        if not trigger.target_employee_id.isdigit():
            return "El numero de empleado no es numerico"
        if normalize(trigger.treatment) not in VALID_TREATMENTS:
            return 'El tratamiento no es "señor" ni "señora"'
        if normalize(trigger.job) not in KNOWN_JOB_TITLES:
            return "El puesto solicitado no existe"
        return (
            "Todas las validaciones fueron exitosas, el servicio de SAP esta disponible, "
            "pero no se pudo ejecutar el alta por una razon desconocida "
            "(Por descarte de los casos anteriores)"
        )

    @staticmethod
    def _handle_401(requester_info: SearchUserInfo | None) -> str:
        if is_found(requester_info) and not starts_with_any(
            requester_info.description, PRIVILEGED_DESCRIPTION_PREFIXES
        ):
            return "El usuario solicitante no es gerente ni administrador de sistemas"
        return "Acceso no autorizado por ADManager (401): causa no determinada"

    @staticmethod
    def _handle_403(
        trigger: RegisterUserTrigger,
        requester_info: SearchUserInfo | None,
        target_info: SearchUserInfo | None,
    ) -> str:
        if (
            is_found(requester_info)
            and normalize(requester_info.office) == CORPORATIVO_OFFICE_NAME
        ):
            return (
                "El usuario solicitante es de OAT, por lo que no tiene permitido "
                "ejecutar este proceso (OFFICE: corporativo)"
            )

        if is_found(requester_info) and is_found(target_info):
            requester_office = normalize(requester_info.office)
            target_office = normalize(target_info.office)
            if requester_office and target_office and requester_office != target_office:
                return (
                    f"El usuario {trigger.requester} no puede realizar esta accion para "
                    f"el usuario {trigger.target_employee_id} ya que no pertenecen a la "
                    "misma oficina"
                )

        job_normalized = normalize(trigger.job)
        if (
            job_normalized.startswith("gerente")
            and is_found(target_info)
            and not starts_with_any(target_info.description, ("gerente",))
        ):
            return (
                f"No se puede asignar el puesto {trigger.job} al usuario "
                f"{trigger.target_employee_id} debido a que no posee un puesto de "
                "Gerente en AD Manager."
            )

        for chain in CHAIN_EXCLUSIVE_JOB_KEYWORDS:
            if chain not in job_normalized:
                continue
            requester_mentions_chain = is_found(requester_info) and (
                chain in normalize(requester_info.ou_name)
                or chain in normalize(requester_info.description)
            )
            if not requester_mentions_chain:
                chain_label = chain.title()
                return (
                    f"El solicitante no pertenece a {chain_label} y solicito el alta "
                    f"de un puesto exclusivo de {chain_label}"
                )

        return "Acceso prohibido por SAP/ADManager (403): causa no determinada"

    @staticmethod
    def _handle_404(
        requester_info: SearchUserInfo | None, target_info: SearchUserInfo | None
    ) -> str:
        requester_missing = not is_found(requester_info)
        target_missing = not is_found(target_info)

        if target_missing and not requester_missing:
            return "El usuario target no existe en ADManager (buscado por employeeID)"
        if requester_missing and not target_missing:
            return "El usuario solicitante no existe en ADManager (buscado por sAMAccountName)"
        if requester_missing and target_missing:
            return "Ningun usuario existe en ADManager"
        return "Recurso no encontrado en ADManager (404): causa no determinada"

    @staticmethod
    def _handle_500(operation_id: str) -> str:
        logger.critical(
            "operation_id=%s: error interno critico e inesperado al ejecutar "
            "sap/register_user (500); requiere revision manual",
            operation_id,
        )
        return (
            "Error interno critico e inesperado del proceso de alta de usuario en SAP: "
            "requiere revision manual"
        )
