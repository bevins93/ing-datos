from pathlib import Path

from reset_report.log_ingest import group_into_blocks
from reset_report.parsers import (
    extract_final_human_message,
    extract_register_user_trigger,
    extract_resetpwd_result,
    extract_resetuser_trigger,
    extract_sap_raw_response,
    extract_searchuser_results,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _single_block(filename):
    blocks = group_into_blocks(FIXTURES / filename)
    assert len(blocks) == 1
    return blocks[0]


def test_extract_resetuser_trigger():
    block = _single_block("reset_200_success.log")
    trigger = extract_resetuser_trigger(block)

    assert trigger is not None
    assert trigger.requester == "admsistemas970"
    assert trigger.target == "1500335663"
    assert trigger.http_code == "200"


def test_extract_searchuser_results():
    block = _single_block("reset_200_success.log")
    results = extract_searchuser_results(block)

    assert set(results) == {
        ("sAMAccountName", "admsistemas970"),
        ("sAMAccountName", "1500335663"),
    }
    requester_info = results[("sAMAccountName", "admsistemas970")]
    assert requester_info.found is True
    assert requester_info.nombre_completo == "Juan Perez"
    assert requester_info.office == "0970"
    assert requester_info.description == "Gerente De Sistemas"
    assert requester_info.ou_name == "OAT/Tiendas/BackOffice"


def test_extract_resetpwd_result_success():
    block = _single_block("reset_200_success.log")
    result = extract_resetpwd_result(block)

    assert result is not None
    assert result.is_timeout is False
    assert result.status == "1"
    assert result.status_message == "Password reset successful."


def test_extract_resetpwd_result_missing_when_no_resetpwd_call():
    from reset_report.log_ingest.block_reader import LogBlock

    empty_block = LogBlock(operation_id="x")
    assert extract_resetpwd_result(empty_block) is None


def test_extract_register_user_trigger():
    block = _single_block("sap_400_employee_id_no_numerico.log")
    trigger = extract_register_user_trigger(block)

    assert trigger is not None
    assert trigger.requester == "caphum165"
    assert trigger.target_employee_id == "Caphum165"
    assert trigger.treatment == "señor"
    assert trigger.job == "Adm.Sistemas Tienda"
    assert trigger.http_code == "400"


def test_extract_sap_raw_response_success():
    block = _single_block("sap_200_success.log")
    result = extract_sap_raw_response(block)

    assert result is not None
    assert result.estatus == "S"
    assert "BRAYAN" in result.mensaje


def test_extract_final_human_message_present():
    block = _single_block("sap_200_success.log")
    message = extract_final_human_message(block)

    assert message is not None
    assert message.startswith("Señor BRAYAN se ha registrado existosamente")


def test_extract_final_human_message_absent_when_no_downstream():
    block = _single_block("sap_400_employee_id_no_numerico.log")
    assert extract_final_human_message(block) is None
