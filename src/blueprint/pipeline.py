"""Three-layer pipeline: raw (as delivered) -> enriched (clean, typed) -> product (consumable)."""
from pathlib import Path

import duckdb

SCHEMAS = ("raw", "enriched", "product")


def build(con: duckdb.DuckDBPyConnection, landing: Path, run_id: str = "local") -> None:
    for s in SCHEMAS:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {s}")

    # Raw: physical tables, everything as text, plus load metadata.
    # See docs/adr/ADR-001-raw-layer-as-tables.md
    for name in ("suppliers", "purchase_orders"):
        con.execute(f"DROP TABLE IF EXISTS raw.{name}")
        con.execute(
            f"""CREATE TABLE raw.{name} AS
                SELECT *, '{run_id}' AS _run_id, current_timestamp AS _loaded_at
                FROM read_csv('{(landing / (name + '.csv')).as_posix()}', header=true, all_varchar=true)"""
        )

    con.execute(
        """CREATE OR REPLACE VIEW enriched.suppliers AS
           SELECT ltrim(supplier_id, '0') AS supplier_id, name, country
           FROM raw.suppliers"""
    )
    # Dedupe: keep one row per order, latest load first.
    con.execute(
        """CREATE OR REPLACE VIEW enriched.purchase_orders AS
           SELECT * EXCLUDE rn FROM (
             SELECT ltrim(order_id, '0') AS order_id,
                    ltrim(supplier_id, '0') AS supplier_id,
                    CAST(ordered_on AS DATE) AS ordered_on,
                    CAST(promised_on AS DATE) AS promised_on,
                    TRY_CAST(NULLIF(delivered_on, '') AS DATE) AS delivered_on,
                    CAST(amount AS DECIMAL(12,2)) AS amount,
                    row_number() OVER (PARTITION BY order_id ORDER BY _loaded_at DESC) AS rn
             FROM raw.purchase_orders
           ) WHERE rn = 1"""
    )

    con.execute(
        """CREATE OR REPLACE VIEW product.supplier_scorecard AS
           SELECT s.supplier_id,
                  s.name,
                  count(*) AS orders,
                  count(o.delivered_on) AS delivered,
                  round(avg(date_diff('day', o.promised_on, o.delivered_on)), 2) AS avg_days_late,
                  round(100.0 * count(*) FILTER (WHERE o.delivered_on <= o.promised_on)
                        / nullif(count(o.delivered_on), 0), 1) AS on_time_pct
           FROM enriched.purchase_orders o
           JOIN enriched.suppliers s USING (supplier_id)
           GROUP BY s.supplier_id, s.name"""
    )
