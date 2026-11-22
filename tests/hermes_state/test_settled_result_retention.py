"""A settled result sheds its transcript copies once it can no longer answer an exact retry.

``settle_session_input`` writes one result per settled turn under
``gateway.admission.result.v1.<id>`` and used to keep every one of them, transcript copies included,
for the life of its session: only a *retired* session's tombstones were reclaimed, so one long-lived
chat carried one full result per turn forever (751 rows / 127 MB on the reference install, 96% of it
the per-turn ``messages`` copies).

``RETRY_HORIZON_S`` already bounds which retries get a byte-exact reply. Past it the row is trimmed,
**not deleted**: a terminal admission with no stored result is a storage fault to ``finish_result``'s
precheck and to hosted-task recovery, and bot receipts degrade a settled turn to ``ambiguous``
without a ``final_response``. These tests pin the stamp, the trim, and those invariants.
"""
import json
import time

import pytest

from gateway.session_results import admission_result, finish_result
from hermes_state import SessionDB
from hermes_state_mutation_retirement import RETRY_HORIZON_S, trim_settled_results
from hermes_state_runtime import admit_session_input, begin_runtime_epoch, claim_session_input
from hermes_state_terminal import RESULT_PREFIX, settled_key


@pytest.fixture()
def store(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    db.create_session("s", "api_server")
    epoch = begin_runtime_epoch(db, instance_id="t")
    yield db, epoch
    db.close()


def _settle(db, epoch, request_id="r1", history=None):
    admit_session_input(db, epoch=epoch, principal_id="api", session_id="s",
                        request_id=request_id, payload={"text": "ask"})
    row = claim_session_input(db, epoch=epoch, session_id="s")
    messages = history or [{"role": "assistant", "content": "done"}]
    finish_result(db, epoch=epoch, row=row, response="done", outcome="completed",
                  result={"result": {"final_response": "done", "messages": messages,
                                     "completed": True, "model": "m", "estimated_cost_usd": .25,
                                     "_turn_user_row": {"role": "user", "content": "ask"}},
                          "usage": {"input_tokens": 3}})
    return row["admission_id"]


def _raw(db, admission_id):
    with db._read_ctx() as conn:
        row = conn.execute("SELECT value FROM state_meta WHERE key=?",
                           (RESULT_PREFIX + admission_id,)).fetchone()
    return None if row is None else row[0]


def _stamp_of(db, admission_id):
    with db._read_ctx() as conn:
        row = conn.execute("SELECT value FROM state_meta WHERE key=?",
                           (settled_key(admission_id),)).fetchone()
    return None if row is None else int(row[0])


def _backdate(db, admission_id, seconds):
    db._execute_write(lambda conn: conn.execute(
        "UPDATE state_meta SET value=? WHERE key=?",
        (str(int(time.time()) - seconds), settled_key(admission_id))))


def _trim(db):
    return db._execute_write(lambda conn: trim_settled_results(conn))


def test_settlement_stamps_beside_the_result_without_touching_it(store):
    db, epoch = store
    admission_id = _settle(db, epoch)
    assert _stamp_of(db, admission_id) == pytest.approx(time.time(), abs=60)
    # The stamp is a sibling key: the stored-result payload keeps exactly what it stored.
    assert "settled_at" not in json.loads(_raw(db, admission_id))
    assert admission_result(db, admission_id)["result"]["messages"] == [
        {"role": "assistant", "content": "done"}]


def test_past_horizon_trims_transcript_copies_and_keeps_every_reader_field(store):
    db, epoch = store
    admission_id = _settle(db, epoch, history=[{"role": "assistant", "content": "done"},
                                               {"role": "user", "content": "x" * 4000}])
    _backdate(db, admission_id, RETRY_HORIZON_S + 60)
    before = len(_raw(db, admission_id))
    assert _trim(db) == 1
    after_raw = _raw(db, admission_id)
    assert before > len(after_raw)                        # the copies were the weight
    after = json.loads(after_raw)
    assert after["result"]["messages"] == []              # transcript copies gone
    assert "_turn_user_row" not in after["result"]
    assert after["result"]["final_response"] == "done"    # what receipts report
    assert after["usage"] == {"input_tokens": 3}          # what runs/ledger report
    assert after["result"]["completed"] is True
    # The row still exists: "terminal admission, no stored result" is a storage fault to two readers.
    assert admission_result(db, admission_id) is not None


def test_result_inside_horizon_is_not_touched(store):
    db, epoch = store
    admission_id = _settle(db, epoch)
    assert _trim(db) == 0
    assert admission_result(db, admission_id)["result"]["messages"] == [
        {"role": "assistant", "content": "done"}]


def test_legacy_row_without_a_stamp_is_stamped_not_trimmed(store):
    db, epoch = store
    admission_id = _settle(db, epoch)
    db._execute_write(lambda conn: conn.execute(
        "DELETE FROM state_meta WHERE key=?", (settled_key(admission_id),)))
    assert _stamp_of(db, admission_id) is None
    assert _trim(db) == 0
    assert _stamp_of(db, admission_id) is not None
    assert admission_result(db, admission_id)["result"]["messages"]


def test_a_settled_but_empty_reply_keeps_its_transcript(store):
    """The Bot delivery fallback rebuilds an empty reply from ``messages``; keep that copy."""
    db, epoch = store
    admit_session_input(db, epoch=epoch, principal_id="api", session_id="s",
                        request_id="empty", payload={"text": "ask"})
    row = claim_session_input(db, epoch=epoch, session_id="s")
    finish_result(db, epoch=epoch, row=row, response="", outcome="completed",
                  result={"result": {"final_response": "", "messages": [
                      {"role": "assistant", "content": "the only copy of the reply"}]},
                          "usage": {"input_tokens": 3}})
    _backdate(db, row["admission_id"], RETRY_HORIZON_S + 60)
    assert _trim(db) == 0
    assert admission_result(db, row["admission_id"])["result"]["messages"] == [
        {"role": "assistant", "content": "the only copy of the reply"}]


def test_an_unreadable_row_does_not_block_the_pass(store):
    db, epoch = store
    admission_id = _settle(db, epoch)
    db._execute_write(lambda conn: conn.execute(
        "INSERT INTO state_meta(key,value) VALUES(?,?)", (RESULT_PREFIX + "broken", "{not json")))
    db._execute_write(lambda conn: conn.execute(
        "INSERT INTO state_meta(key,value) VALUES(?,?)",
        (settled_key("broken"), str(int(time.time()) - RETRY_HORIZON_S - 60))))
    _backdate(db, admission_id, RETRY_HORIZON_S + 60)
    assert _trim(db) == 1


def test_trim_is_idempotent(store):
    db, epoch = store
    admission_id = _settle(db, epoch)
    _backdate(db, admission_id, RETRY_HORIZON_S + 60)
    assert _trim(db) == 1
    assert _trim(db) == 0


def test_compaction_rewrite_does_not_extend_lifetime(store):
    db, epoch = store
    admission_id = _settle(db, epoch)
    _backdate(db, admission_id, RETRY_HORIZON_S + 60)
    stamped = _stamp_of(db, admission_id)
    # A retirement's compaction re-encodes the row; the settlement stamp must survive it.
    from hermes_state_mutation_retirement import _compact_result
    db._execute_write(lambda conn: _compact_result(conn, admission_id))
    assert _stamp_of(db, admission_id) == stamped


def test_maybe_trim_settled_results_throttles_and_runs_without_auto_prune(store):
    db, epoch = store
    admission_id = _settle(db, epoch)
    _backdate(db, admission_id, RETRY_HORIZON_S + 60)
    first = db.maybe_trim_settled_results(vacuum=False)
    assert first["trimmed"] == 1 and not first["skipped"]
    again = db.maybe_trim_settled_results(vacuum=False)
    assert again["skipped"] and again["trimmed"] == 0
    assert json.loads(_raw(db, admission_id))["result"]["messages"] == []
