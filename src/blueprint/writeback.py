"""Controlled business input (allocation shares) feeding a data product, with versioning and audit.

See docs/adr/ADR-005-controlled-writeback-with-audit.md
"""
import duckdb

_DDL = """
CREATE SCHEMA IF NOT EXISTS ops;
CREATE SCHEMA IF NOT EXISTS product;
CREATE SEQUENCE IF NOT EXISTS ops.share_version START 1;
CREATE TABLE IF NOT EXISTS ops.allocation_share (
    version BIGINT, pool VARCHAR, cost_center VARCHAR, share DECIMAL(6,5),
    set_by VARCHAR, set_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ops.allocation_audit (
    version BIGINT, pool VARCHAR, action VARCHAR, detail VARCHAR, actor VARCHAR, logged_at TIMESTAMP
)
"""

_VIEW = """
CREATE OR REPLACE VIEW product.cost_allocation AS
WITH latest AS (
    SELECT pool, max(version) AS version FROM ops.allocation_share GROUP BY pool
)
SELECT p.pool, s.cost_center, s.version AS share_version,
       round(p.amount * s.share, 2) AS allocated_amount
FROM cost_pool p
JOIN latest l USING (pool)
JOIN ops.allocation_share s ON s.pool = l.pool AND s.version = l.version
"""


def setup(con: duckdb.DuckDBPyConnection) -> None:
    for stmt in filter(None, (s.strip() for s in _DDL.split(";"))):
        con.execute(stmt)
    con.execute(_VIEW)


def set_shares(con: duckdb.DuckDBPyConnection, pool: str, shares: dict[str, float], actor: str) -> int:
    """Replace the shares of one cost pool. Rejects invalid input and records every attempt."""
    setup(con)
    total = round(sum(shares.values()), 5)
    problem = None
    if not shares:
        problem = "no shares given"
    elif any(v < 0 for v in shares.values()):
        problem = "negative share"
    elif total != 1.0:
        problem = f"shares sum to {total}, expected 1.0"
    if problem:
        con.execute(
            "INSERT INTO ops.allocation_audit VALUES (NULL, ?, 'rejected', ?, ?, current_timestamp)",
            [pool, problem, actor],
        )
        raise ValueError(problem)

    con.execute("BEGIN")
    try:
        version = con.execute("SELECT nextval('ops.share_version')").fetchone()[0]
        for cc, share in shares.items():
            con.execute(
                "INSERT INTO ops.allocation_share VALUES (?, ?, ?, ?, ?, current_timestamp)",
                [version, pool, cc, share, actor],
            )
        con.execute(
            "INSERT INTO ops.allocation_audit VALUES (?, ?, 'set', ?, ?, current_timestamp)",
            [version, pool, f"{len(shares)} cost centers", actor],
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return version
