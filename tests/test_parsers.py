from pathlib import Path

from reset_report.log_ingest import group_into_blocks
from reset_report.parsers import (
    extract_resetpwd_result,
    extract_resetuser_trigger,
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

    assert set(results) == {"admsistemas970", "1500335663"}
    requester_info = results["admsistemas970"]
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
