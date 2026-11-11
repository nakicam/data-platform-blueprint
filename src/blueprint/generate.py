"""Synthetic source data. Mimics typical ERP export quirks, contains no real data."""
import csv
import random
from datetime import date, timedelta
from pathlib import Path


def generate(out_dir: Path, seed: int = 42, orders: int = 500) -> None:
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    suppliers = [f"{i:010d}" for i in range(1, 21)]
    with open(out_dir / "suppliers.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["supplier_id", "name", "country"])
        for s in suppliers:
            w.writerow([s, f"Supplier {int(s)}", rng.choice(["DE", "NL", "PL", "CZ"])])

    start = date(2025, 1, 1)
    with open(out_dir / "purchase_orders.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["order_id", "supplier_id", "ordered_on", "promised_on", "delivered_on", "amount"])
        for i in range(1, orders + 1):
            ordered = start + timedelta(days=rng.randint(0, 300))
            promised = ordered + timedelta(days=rng.randint(5, 30))
            late = rng.choice([0, 0, 0, 1, 3, 7])
            delivered = promised + timedelta(days=late) if rng.random() > 0.05 else None
            amount = round(rng.uniform(100, 20000), 2)
            supplier = rng.choice(suppliers)
            w.writerow([f"{i:012d}", supplier, ordered, promised, delivered or "", amount])
            if rng.random() < 0.03:
                # the same extract row delivered twice
                w.writerow([f"{i:012d}", supplier, ordered, promised, delivered or "", amount])
