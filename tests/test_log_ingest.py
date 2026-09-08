from pathlib import Path

from reset_report.log_ingest import group_into_blocks
from reset_report.log_ingest.block_reader import iter_log_entries

FIXTURES = Path(__file__).parent / "fixtures"


def test_iter_log_entries_merges_continuation_lines():
    entries = list(iter_log_entries(FIXTURES / "reset_200_success.log"))
    enrichment_entries = [e for e in entries if "get_users_list_info_from_admanager" in e.message]
    assert len(enrichment_entries) == 2
    assert "Raw Response:" in enrichment_entries[0].message
    assert "Raw status_code" in enrichment_entries[0].message


def test_group_into_blocks_single_operation_id():
    blocks = group_into_blocks(FIXTURES / "reset_200_success.log")
    assert len(blocks) == 1
    assert blocks[0].operation_id == "10000000000000000000000000000001"
    assert len(blocks[0].entries) == 7


def test_group_into_blocks_multiple_operation_ids():
    blocks = group_into_blocks(FIXTURES / "other_actions_only.log")
    ids = {b.operation_id for b in blocks}
    assert ids == {
        "90000000000000000000000000000001",
        "90000000000000000000000000000002",
    }
