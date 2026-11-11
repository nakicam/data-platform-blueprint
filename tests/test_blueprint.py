from pathlib import Path

import duckdb
import pytest

from blueprint import access, generate, pipeline

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def con(tmp_path):
    generate.generate(tmp_path)
    c = duckdb.connect()
    pipeline.build(c, tmp_path)
    return c


def test_raw_is_a_physical_table_with_load_metadata(con):
    kind = con.execute(
        "SELECT table_type FROM information_schema.tables WHERE table_schema='raw' AND table_name='purchase_orders'"
    ).fetchone()[0]
    assert kind == "BASE TABLE"
    cols = {r[0] for r in con.execute("DESCRIBE raw.purchase_orders").fetchall()}
    assert {"_run_id", "_loaded_at"} <= cols


def test_enriched_removes_duplicates_and_leading_zeros(con):
    dup = con.execute(
        "SELECT count(*) FROM (SELECT order_id FROM enriched.purchase_orders GROUP BY 1 HAVING count(*) > 1)"
    ).fetchone()[0]
    assert dup == 0
    assert con.execute("SELECT count(*) FROM enriched.purchase_orders WHERE order_id LIKE '0%'").fetchone()[0] == 0


def test_raw_keeps_delivered_duplicates_for_traceability(con):
    raw = con.execute("SELECT count(*) FROM raw.purchase_orders").fetchone()[0]
    enriched = con.execute("SELECT count(*) FROM enriched.purchase_orders").fetchone()[0]
    assert raw > enriched


def test_scorecard_percentages_are_valid(con):
    bad = con.execute(
        "SELECT count(*) FROM product.supplier_scorecard WHERE on_time_pct < 0 OR on_time_pct > 100"
    ).fetchone()[0]
    assert bad == 0


def test_policy_is_valid_and_analysts_cannot_read_raw():
    roles = access.load(ROOT / "access" / "policy.yaml")
    assert access.validate(roles) == []
    assert not any("raw" in g and "analysts" in g for g in access.render(roles))


def test_policy_validation_rejects_raw_for_analysts():
    assert access.validate({"analysts": {"raw": "read"}})
