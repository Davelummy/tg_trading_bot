from data.store import SQLiteStore
from engine.idempotency import Idempotency


def test_idempotency_check_and_add(tmp_path):
    db = tmp_path / "test.db"
    store = SQLiteStore(str(db))
    idem = Idempotency(store, user_id=1, max_keys=2)

    assert idem.check_and_add("k1")
    assert not idem.check_and_add("k1")
    assert idem.check_and_add("k2")
    assert idem.check_and_add("k3")
    assert not idem.exists("k1")
