"""Runs jobs/daily.yml end to end on synthetic data, wiring the patterns together."""
from datetime import datetime, timedelta
from pathlib import Path

import duckdb

from . import file_ingest, incremental, jobs, writeback

CONTRACTS = {"site_list": ("site", "country")}


def _seed(ctx: dict) -> None:
    con, drop = ctx["con"], ctx["drop"]
    t0 = datetime(2026, 1, 1, 8, 0)
    con.execute("CREATE SCHEMA IF NOT EXISTS src_erp")
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("CREATE OR REPLACE TABLE src_erp.orders (order_id VARCHAR, amount INT, changed_at TIMESTAMP)")
    con.execute(
        "INSERT INTO src_erp.orders VALUES ('A', 100, ?), ('B', 250, ?), ('C', 650, ?)",
        [t0, t0, t0 + timedelta(hours=1)],
    )
    (drop / "site_list" / "upload").mkdir(parents=True, exist_ok=True)
    (drop / "site_list" / "upload" / "sites.csv").write_text("site,country\nX,DE\nY,FR\n", encoding="utf-8")


def _file_ingest(ctx: dict) -> dict:
    r = file_ingest.ingest(ctx["con"], ctx["drop"], ctx["landing"], CONTRACTS)
    return {"ingested": r.ingested, "rejected": r.rejected}


def _incremental_load(ctx: dict, lookback_minutes: int = 0, **cfg) -> dict:
    return incremental.load(
        ctx["con"], run_id=ctx["run_id"], lookback=timedelta(minutes=lookback_minutes), **cfg
    )


def _allocation_report(ctx: dict) -> list[tuple]:
    con = ctx["con"]
    con.execute("CREATE OR REPLACE TABLE cost_pool AS SELECT 'orders' AS pool, sum(amount)::DECIMAL(12,2) AS amount FROM raw.orders")
    writeback.set_shares(con, "orders", {"cc_a": 0.6, "cc_b": 0.4}, actor="demo")
    return con.execute("SELECT cost_center, allocated_amount FROM product.cost_allocation ORDER BY 1").fetchall()


REGISTRY = {
    "file_ingest": _file_ingest,
    "incremental_load": _incremental_load,
    "allocation_report": _allocation_report,
    "noop": lambda ctx, **_: None,
}


def run(workdir: Path, job_file: Path) -> dict:
    ctx = {
        "con": duckdb.connect(),
        "drop": workdir / "drop",
        "landing": workdir / "landing",
        "run_id": "demo",
    }
    _seed(ctx)
    return jobs.run(jobs.load(job_file), REGISTRY, ctx)
