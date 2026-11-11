from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pytest

from blueprint import file_ingest, incremental, jobs, writeback


def _source(con, rows):
    con.execute("CREATE SCHEMA IF NOT EXISTS src_erp")
    con.execute("CREATE OR REPLACE TABLE src_erp.orders (order_id VARCHAR, amount INT, changed_at TIMESTAMP)")
    for r in rows:
        con.execute("INSERT INTO src_erp.orders VALUES (?, ?, ?)", r)


T0 = datetime(2026, 1, 1, 8, 0)
KW = dict(source="src_erp.orders", target="raw.orders", key="order_id", watermark_col="changed_at")


@pytest.fixture
def con():
    c = duckdb.connect()
    c.execute("CREATE SCHEMA raw")
    return c


def test_first_run_is_full_then_only_changes(con):
    _source(con, [("A", 10, T0), ("B", 20, T0)])
    assert incremental.load(con, run_id="r1", **KW)["mode"] == "full"
    con.execute("INSERT INTO src_erp.orders VALUES ('B', 25, ?), ('C', 30, ?)", [T0 + timedelta(hours=2)] * 2)
    res = incremental.load(con, run_id="r2", **KW)
    assert res["mode"] == "incremental" and res["rows_read"] == 2
    got = dict(con.execute("SELECT order_id, amount FROM raw.orders").fetchall())
    assert got == {"A": 10, "B": 25, "C": 30}


def test_rerun_without_changes_is_noop(con):
    _source(con, [("A", 10, T0)])
    incremental.load(con, run_id="r1", **KW)
    assert incremental.load(con, run_id="r2", **KW)["rows_read"] == 0
    assert con.execute("SELECT count(*) FROM raw.orders").fetchone()[0] == 1


def test_lookback_catches_late_commit_without_duplicates(con):
    _source(con, [("A", 10, T0 + timedelta(hours=3))])
    incremental.load(con, run_id="r1", **KW)
    # committed late, but stamped inside the lookback window
    con.execute("INSERT INTO src_erp.orders VALUES ('B', 20, ?)", [T0 + timedelta(hours=2, minutes=30)])
    assert incremental.load(con, run_id="r2", **KW)["rows_read"] == 0
    res = incremental.load(con, run_id="r3", lookback=timedelta(hours=1), **KW)
    assert res["rows_read"] == 2  # A is re-read, harmlessly
    assert con.execute("SELECT count(*) FROM raw.orders").fetchone()[0] == 2


def test_latest_state_wins_within_one_delta(con):
    _source(con, [("A", 1, T0), ("A", 2, T0 + timedelta(minutes=5))])
    incremental.load(con, run_id="r1", **KW)
    assert con.execute("SELECT amount FROM raw.orders").fetchone()[0] == 2


def test_full_reload_removes_rows_gone_from_source(con):
    _source(con, [("A", 1, T0), ("B", 2, T0)])
    incremental.load(con, run_id="r1", **KW)
    con.execute("DELETE FROM src_erp.orders WHERE order_id = 'B'")
    incremental.load(con, run_id="r2", full=True, **KW)
    assert [r[0] for r in con.execute("SELECT order_id FROM raw.orders").fetchall()] == ["A"]


def test_failed_load_does_not_move_watermark(con):
    _source(con, [("A", 1, T0)])
    incremental.load(con, run_id="r1", **KW)
    con.execute("INSERT INTO src_erp.orders VALUES ('B', 2, ?)", [T0 + timedelta(hours=1)])
    con.execute("ALTER TABLE raw.orders DROP COLUMN _run_id")  # break the target schema
    with pytest.raises(Exception):
        incremental.load(con, run_id="r2", **KW)
    wm = con.execute("SELECT last_value FROM ops.watermark WHERE target = 'raw.orders'").fetchone()[0]
    assert wm == T0


def test_identifiers_are_validated(con):
    with pytest.raises(ValueError):
        incremental.load(con, run_id="x", **{**KW, "target": "raw.orders; DROP TABLE x"})


def _drop(root: Path, area: str, name: str, content: str, folder: str = "upload") -> None:
    d = root / area / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(content, encoding="utf-8")


def test_file_ingest_allowlist_contract_and_dedupe(tmp_path):
    con = duckdb.connect()
    root, landing = tmp_path / "drop", tmp_path / "landing"
    contracts = {"site_list": ("site", "country")}
    _drop(root, "site_list", "a.csv", "site,country\nX,DE\n", folder="Upload")
    _drop(root, "site_list", "bad.csv", "site\nX\n")
    _drop(root, "not_listed", "z.csv", "a,b\n1,2\n")

    rep = file_ingest.ingest(con, root, landing, contracts)
    assert rep.ingested == ["a.csv"]
    assert [n for n, _ in rep.rejected] == ["bad.csv"]
    assert rep.ignored_areas == ["not_listed"]
    assert len(list((landing / "site_list" / "input").glob("a__*.csv"))) == 1

    again = file_ingest.ingest(con, root, landing, contracts)
    assert again.ingested == [] and again.duplicates == ["a.csv"]


def _pool(con):
    con.execute("CREATE OR REPLACE TABLE cost_pool (pool VARCHAR, amount DECIMAL(12,2))")
    con.execute("INSERT INTO cost_pool VALUES ('it', 1000.00)")


def test_writeback_versions_and_allocates():
    con = duckdb.connect()
    _pool(con)
    writeback.setup(con)
    writeback.set_shares(con, "it", {"cc1": 0.5, "cc2": 0.5}, actor="user_a")
    v2 = writeback.set_shares(con, "it", {"cc1": 0.25, "cc2": 0.75}, actor="user_b")
    rows = dict(con.execute("SELECT cost_center, allocated_amount FROM product.cost_allocation").fetchall())
    assert rows == {"cc1": 250, "cc2": 750}
    assert con.execute("SELECT max(share_version) FROM product.cost_allocation").fetchone()[0] == v2
    assert con.execute("SELECT count(*) FROM ops.allocation_audit WHERE action = 'set'").fetchone()[0] == 2


def test_writeback_rejects_bad_input_and_audits():
    con = duckdb.connect()
    _pool(con)
    writeback.setup(con)
    with pytest.raises(ValueError):
        writeback.set_shares(con, "it", {"cc1": 0.5, "cc2": 0.4}, actor="user_a")
    with pytest.raises(ValueError):
        writeback.set_shares(con, "it", {"cc1": 1.5, "cc2": -0.5}, actor="user_a")
    assert con.execute("SELECT count(*) FROM ops.allocation_share").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM ops.allocation_audit WHERE action = 'rejected'").fetchone()[0] == 2


def test_job_order_respects_dependencies():
    job = jobs.load(Path(__file__).parents[1] / "jobs" / "daily.yml")
    seq = jobs.order(job)
    assert seq.index("load_orders") < seq.index("refresh_allocation") < seq.index("publish")


def test_daily_job_runs_end_to_end(tmp_path):
    from blueprint import demo

    res = demo.run(tmp_path, Path(__file__).parents[1] / "jobs" / "daily.yml")
    assert res["ingest_files"]["ingested"] == ["sites.csv"]
    assert res["load_orders"]["mode"] == "full"
    assert res["refresh_allocation"] == [("cc_a", 600), ("cc_b", 400)]


def test_job_validation_errors():
    with pytest.raises(ValueError, match="unknown task"):
        jobs.order({"tasks": [{"key": "a", "type": "t", "depends_on": ["x"]}]})
    with pytest.raises(ValueError, match="cycle"):
        jobs.order({"tasks": [{"key": "a", "type": "t", "depends_on": ["b"]},
                              {"key": "b", "type": "t", "depends_on": ["a"]}]})


def test_failing_task_stops_downstream():
    ran = []

    def ok(ctx, **_): ran.append("ok")

    def boom(ctx, **_): raise RuntimeError("x")

    job = {"tasks": [{"key": "a", "type": "boom"}, {"key": "b", "type": "ok", "depends_on": ["a"]}]}
    with pytest.raises(RuntimeError):
        jobs.run(job, {"ok": ok, "boom": boom}, {})
    assert ran == []
