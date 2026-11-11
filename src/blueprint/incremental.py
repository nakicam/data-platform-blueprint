"""Incremental load: watermark + upsert, idempotent, with an explicit full-reload switch.

See docs/adr/ADR-003-incremental-load-watermark-upsert.md
"""
import re
from datetime import datetime, timedelta

import duckdb

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")

_STATE_DDL = """
CREATE SCHEMA IF NOT EXISTS ops;
CREATE TABLE IF NOT EXISTS ops.watermark (
    target VARCHAR PRIMARY KEY,
    last_value TIMESTAMP,
    last_run_id VARCHAR,
    updated_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ops.load_log (
    target VARCHAR, run_id VARCHAR, mode VARCHAR,
    rows_read BIGINT, rows_merged BIGINT, logged_at TIMESTAMP
);
"""


def _check(*names: str) -> None:
    for n in names:
        if not _IDENT.match(n):
            raise ValueError(f"invalid identifier: {n!r}")


def _exists(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    schema, _, name = table.rpartition(".")
    return con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_name = ? AND table_schema = coalesce(nullif(?, ''), current_schema())",
        [name, schema],
    ).fetchone()[0] > 0


def load(
    con: duckdb.DuckDBPyConnection,
    *,
    source: str,
    target: str,
    key: str,
    watermark_col: str,
    run_id: str,
    lookback: timedelta = timedelta(0),
    full: bool = False,
) -> dict:
    """Merge rows changed since the last watermark into `target`.

    - Re-running with the same data changes nothing (upsert by key).
    - `lookback` re-reads a window before the watermark to catch late commits; harmless because of the upsert.
    - `full=True` rebuilds the target from scratch and resets the watermark.
    - On any error the transaction rolls back, so the watermark never moves past unwritten data.
    """
    _check(source, target, key, watermark_col)
    for stmt in filter(None, (s.strip() for s in _STATE_DDL.split(";"))):
        con.execute(stmt)

    row = con.execute("SELECT last_value FROM ops.watermark WHERE target = ?", [target]).fetchone()
    last: datetime | None = None if (full or row is None) else row[0]

    con.execute("BEGIN")
    try:
        if last is None:
            where, params = "TRUE", []
        else:
            where, params = f"{watermark_col} > ?", [last - lookback]
        # If a key changed several times in the window, only its latest state is merged.
        con.execute(
            f"""CREATE OR REPLACE TEMP TABLE _delta AS
                SELECT * FROM {source} WHERE {where}
                QUALIFY row_number() OVER (PARTITION BY {key} ORDER BY {watermark_col} DESC) = 1""",
            params,
        )
        n = con.execute("SELECT count(*) FROM _delta").fetchone()[0]
        meta = "SELECT *, ? AS _run_id, current_timestamp AS _loaded_at FROM _delta"
        if not _exists(con, target):
            con.execute(f"CREATE TABLE {target} AS {meta}", [run_id])
        else:
            if full:
                con.execute(f"DELETE FROM {target}")
            else:
                con.execute(f"DELETE FROM {target} WHERE {key} IN (SELECT {key} FROM _delta)")
            con.execute(f"INSERT INTO {target} {meta}", [run_id])

        new_wm = con.execute(f"SELECT max({watermark_col}) FROM _delta").fetchone()[0] or last
        con.execute(
            """INSERT OR REPLACE INTO ops.watermark
               VALUES (?, ?, ?, current_timestamp)""",
            [target, new_wm, run_id],
        )
        mode = "full" if full or row is None else "incremental"
        con.execute(
            "INSERT INTO ops.load_log VALUES (?, ?, ?, ?, ?, current_timestamp)",
            [target, run_id, mode, n, n],
        )
        con.execute("DROP TABLE _delta")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return {"target": target, "mode": mode, "rows_read": n, "watermark": new_wm}
