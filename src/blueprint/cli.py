import sys
import tempfile
from pathlib import Path

import duckdb

from . import access, generate, pipeline

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    roles = access.load(ROOT / "access" / "policy.yaml")
    errors = access.validate(roles)
    if errors:
        print("\n".join(errors))
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        landing = Path(tmp)
        generate.generate(landing)
        con = duckdb.connect()
        pipeline.build(con, landing)
        for row in con.execute(
            "SELECT supplier_id, orders, avg_days_late, on_time_pct FROM product.supplier_scorecard "
            "ORDER BY on_time_pct DESC LIMIT 5"
        ).fetchall():
            print(row)
    print("\n".join(access.render(roles)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
