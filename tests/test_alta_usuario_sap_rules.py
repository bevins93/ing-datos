import logging
from pathlib import Path

from reset_report.log_ingest import group_into_blocks
from reset_report.rules.alta_usuario_sap_rules import AltaUsuarioSapRules

FIXTURES = Path(__file__).parent / "fixtures"
rules = AltaUsuarioSapRules()


def _row_for(filename):
    blocks = group_into_blocks(FIXTURES / filename)
    target_block = next(b for b in blocks if rules.matches(b))
    row = rules.build_row(target_block)
    assert row is not None
    return row


def test_matches_true_for_register_user_block():
    blocks = group_into_blocks(FIXTURES / "sap_200_success.log")
    assert any(rules.matches(b) for b in blocks)


def test_matches_false_for_reset_password_block():
    blocks = group_into_blocks(FIXTURES / "reset_200_success.log")
    assert all(rules.matches(b) is False for b in blocks)


def test_never_contains_raw_status_code_alone():
    for fixture in [
        "sap_200_success.log",
        "sap_208_ya_existe.log",
        "sap_400_employee_id_no_numerico.log",
        "sap_403_office_mismatch.log",
        "sap_404_target_missing.log",
        "sap_500_critical.log",
        "sap_503_service_down.log",
    ]:
        row = _row_for(fixture)
        assert row.resultado_final not in {
            "200",
            "202",
            "208",
            "400",
            "401",
            "403",
            "404",
            "500",
            "503",
        }


def test_row_shape():
    row = _row_for("sap_200_success.log")
    assert row.accion == "alta_usuario_sap"
    assert row.sistema == "SAP"
    assert row.target == "1500347603"


# --- 200: verificado con log real ---


def test_200_uses_bot_final_message_verbatim():
    row = _row_for("sap_200_success.log")
    assert row.resultado_final == (
        "Señor BRAYAN se ha registrado existosamente con el usuario 001500347603. "
        "Contraseña temporal: Sopor7.e#JEFE.MTTO.. El detalle se encuentra en el "
        "ticket cerrado REQ 2026-378980."
    )


# --- 202: sintetico, sin ejemplo real ---


def test_202_ticket_no_se_pudo_cerrar():
    row = _row_for("sap_202_ticket_no_cerrado.log")
    assert row.resultado_final == (
        "El usuario target fue registrado exitosamente, se creó el ticket "
        "control pero no pudo cerrarse."
    )


def test_202_ticket_no_se_pudo_crear():
    row = _row_for("sap_202_ticket_no_creado.log")
    assert row.resultado_final == (
        "El usuario target fue registrado exitosamente, pero no fue posible crear el ticket control"
    )


# --- 208: verificado con log real ---


def test_208_ya_existe_usa_mensaje_del_bot():
    row = _row_for("sap_208_ya_existe.log")
    assert (
        row.resultado_final == "El empleado 001500300909 ya existe en el ambiente ECC ECP de SAP."
    )


# --- 400: un subcaso verificado con log real, 3 sinteticos ---


def test_400_employee_id_no_numerico_verificado_con_log_real():
    row = _row_for("sap_400_employee_id_no_numerico.log")
    assert row.resultado_final == "El numero de empleado no es numerico"


def test_400_tratamiento_invalido():
    row = _row_for("sap_400_tratamiento_invalido.log")
    assert row.resultado_final == 'El tratamiento no es "señor" ni "señora"'


def test_400_puesto_no_existe():
    row = _row_for("sap_400_puesto_no_existe.log")
    assert row.resultado_final == "El puesto solicitado no existe"


def test_400_fallback_por_descarte():
    row = _row_for("sap_400_fallback_por_descarte.log")
    assert row.resultado_final == (
        "Todas las validaciones fueron exitosas, el servicio de SAP esta disponible, "
        "pero no se pudo ejecutar el alta por una razon desconocida "
        "(Por descarte de los casos anteriores)"
    )


# --- 401: sintetico ---


def test_401_solicitante_sin_privilegio():
    row = _row_for("sap_401_sin_privilegio.log")
    assert (
        row.resultado_final == "El usuario solicitante no es gerente ni administrador de sistemas"
    )


# --- 403: 2 subcasos verificados con log real, 3 sinteticos ---


def test_403_oficinas_distintas_verificado_con_log_real():
    row = _row_for("sap_403_office_mismatch.log")
    assert row.resultado_final == (
        "El usuario gerencia354 no puede realizar esta accion para el usuario "
        "julianmae ya que no pertenecen a la misma oficina"
    )


def test_403_target_no_es_gerente_verificado_con_log_real():
    row = _row_for("sap_403_target_no_gerente.log")
    assert row.resultado_final == (
        "No se puede asignar el puesto gerente tienda al usuario 000971000019 "
        "debido a que no posee un puesto de Gerente en AD Manager."
    )


def test_403_solicitante_de_oat_corporativo():
    row = _row_for("sap_403_oat_corporativo.log")
    assert row.resultado_final == (
        "El usuario solicitante es de OAT, por lo que no tiene permitido "
        "ejecutar este proceso (OFFICE: corporativo)"
    )


def test_403_solicitante_no_pertenece_a_city_club():
    row = _row_for("sap_403_city_club.log")
    assert row.resultado_final == (
        "El solicitante no pertenece a City Club y solicito el alta de un "
        "puesto exclusivo de City Club"
    )


def test_403_solicitante_no_pertenece_a_soriana():
    row = _row_for("sap_403_soriana.log")
    assert row.resultado_final == (
        "El solicitante no pertenece a Soriana y solicito el alta de un puesto exclusivo de Soriana"
    )


def test_403_unknown_cause_fallback():
    row = _row_for("sap_403_unknown_cause.log")
    assert row.resultado_final == "Acceso prohibido por SAP/ADManager (403): causa no determinada"


# --- 404: sintetico (los 3 subcasos, incluyendo "ninguno existe" agregado
# por consistencia con reseteo de password, no mencionado en el PDF) ---


def test_404_target_no_existe():
    row = _row_for("sap_404_target_missing.log")
    assert (
        row.resultado_final == "El usuario target no existe en ADManager (buscado por employeeID)"
    )


def test_404_solicitante_no_existe():
    row = _row_for("sap_404_requester_missing.log")
    assert row.resultado_final == (
        "El usuario solicitante no existe en ADManager (buscado por sAMAccountName)"
    )


def test_404_ningun_usuario_existe():
    row = _row_for("sap_404_both_missing.log")
    assert row.resultado_final == "Ningun usuario existe en ADManager"


# --- 500: sintetico, siempre critico ---


def test_500_critical_is_logged_as_critical(caplog):
    with caplog.at_level(logging.CRITICAL, logger="reset_report.rules.alta_usuario_sap_rules"):
        row = _row_for("sap_500_critical.log")

    assert row.resultado_final == (
        "Error interno critico e inesperado del proceso de alta de usuario en SAP: "
        "requiere revision manual"
    )
    assert any(record.levelno == logging.CRITICAL for record in caplog.records)


# --- 503: sintetico, texto fijo ---


def test_503_servicio_sap_fallo():
    row = _row_for("sap_503_service_down.log")
    assert row.resultado_final == (
        "Todas las validaciones fueron exitosas, pero el servicio del lado de SAP fallo"
    )


def test_unrecognized_code_fallback():
    from reset_report.log_ingest.block_reader import LogBlock, LogEntry

    block = LogBlock(operation_id="op-unknown-sap")
    block.entries.append(
        LogEntry(
            timestamp="2026-01-01T00:00:00.000000Z",
            operation_id="op-unknown-sap",
            message=(
                "HTTP Request: http://apitools.com:8000/v2/sap/register_user"
                "?requester_username=a&target_employee_id=123&treatment=señor"
                '&job=Recibo+Tienda "HTTP/1.1" 418'
            ),
        )
    )
    row = rules.build_row(block)
    assert row is not None
    assert row.resultado_final == (
        "Codigo de respuesta no reconocido (418) al ejecutar el alta de usuario"
    )
