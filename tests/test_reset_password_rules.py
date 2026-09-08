import logging
from pathlib import Path

from reset_report.log_ingest import group_into_blocks
from reset_report.rules.reset_password_rules import AdManagerResetPasswordRules

FIXTURES = Path(__file__).parent / "fixtures"
rules = AdManagerResetPasswordRules()


def _row_for(filename):
    blocks = group_into_blocks(FIXTURES / filename)
    assert len(blocks) == 1
    row = rules.build_row(blocks[0])
    assert row is not None
    return row


def test_matches_true_for_resetuser_block():
    blocks = group_into_blocks(FIXTURES / "reset_200_success.log")
    assert rules.matches(blocks[0]) is True


def test_matches_false_for_other_actions():
    blocks = group_into_blocks(FIXTURES / "other_actions_only.log")
    assert all(rules.matches(b) is False for b in blocks)


def test_never_contains_raw_status_code_alone():
    # resultado_final nunca debe ser exactamente el codigo crudo.
    for fixture in [
        "reset_200_success.log",
        "reset_403_office_mismatch.log",
        "reset_404_target_missing.log",
        "reset_429_tokens_exhausted.log",
        "reset_500_critical.log",
        "reset_503_admanager_failure.log",
        "reset_504_timeout.log",
    ]:
        row = _row_for(fixture)
        assert row.resultado_final not in {"200", "202", "403", "404", "429", "500", "503", "504"}


def test_200_success():
    row = _row_for("reset_200_success.log")
    assert row.resultado_final == "Reseteo ejecutado exitosamente"
    assert row.nombre_completo_solicitante == "Juan Perez"
    assert row.nombre_completo_target == "Maria Lopez"
    assert row.oficina_solicitante == "0970"
    assert row.oficina_target == "0970"


def test_202_target_corporativo():
    row = _row_for("reset_202_corporativo.log")
    assert row.resultado_final == "El usuario target pertenece a Corporativo (oficina: CORPORATIVO)"


def test_403_office_mismatch():
    row = _row_for("reset_403_office_mismatch.log")
    assert row.resultado_final == (
        "El usuario solicitante y el usuario target no pertenecen a la misma oficina"
    )


def test_403_no_privilege():
    row = _row_for("reset_403_no_privilege.log")
    assert row.resultado_final == "El usuario solicitante no tiene privilegios para ejecutar el reseteo"


def test_403_restricted_ou():
    row = _row_for("reset_403_restricted_ou.log")
    assert row.resultado_final == "El usuario target pertenece a una oficina restringida (OAT/Cedis/BY)"


def test_403_unknown_cause_fallback():
    row = _row_for("reset_403_unknown_cause.log")
    assert row.resultado_final == "Acceso prohibido por ADManager (403): causa no determinada"


def test_404_target_missing():
    row = _row_for("reset_404_target_missing.log")
    assert row.resultado_final == "El usuario objetivo no se encontro en ADManager"
    assert row.nombre_completo_target == ""
    assert row.nombre_completo_solicitante == "Sofia Torres"


def test_404_requester_missing():
    row = _row_for("reset_404_requester_missing.log")
    assert row.resultado_final == "El usuario solicitante no se encontro en ADManager"
    assert row.nombre_completo_solicitante == ""


def test_404_both_missing():
    row = _row_for("reset_404_both_missing.log")
    assert row.resultado_final == "Ningun usuario se encontro en ADManager"


def test_429_tokens_exhausted():
    row = _row_for("reset_429_tokens_exhausted.log")
    assert row.resultado_final == "No se pudo ejecutar el reseteo: se agotaron los tokens de ADManager"


def test_500_critical_is_logged_as_critical(caplog):
    with caplog.at_level(logging.CRITICAL, logger="reset_report.rules.reset_password_rules"):
        row = _row_for("reset_500_critical.log")

    assert row.resultado_final == (
        "Error interno critico e inesperado del proceso de reseteo: requiere revision manual"
    )
    assert any(record.levelno == logging.CRITICAL for record in caplog.records)


def test_503_concatenates_admanager_message():
    row = _row_for("reset_503_admanager_failure.log")
    assert row.resultado_final.startswith("El reseteo fallo en ADManager:")
    assert "No such user matched" in row.resultado_final


def test_504_timeout():
    row = _row_for("reset_504_timeout.log")
    assert row.resultado_final == (
        "El reseteo no se pudo confirmar: ADManager no respondio a tiempo (timeout)"
    )


def test_unrecognized_code_fallback():
    from reset_report.log_ingest.block_reader import LogBlock, LogEntry

    block = LogBlock(operation_id="op-unknown")
    block.entries.append(
        LogEntry(
            timestamp="2026-01-01T00:00:00.000000Z",
            operation_id="op-unknown",
            message=(
                "HTTP Request: http://apitools.com:8000/v3/users_admin/resetuser"
                "?sAMAccountName_requester=a&sAMAccountName_target=b \"HTTP/1.1\" 418"
            ),
        )
    )
    row = rules.build_row(block)
    assert row is not None
    assert row.resultado_final == "Codigo de respuesta no reconocido (418) al ejecutar el reseteo"
