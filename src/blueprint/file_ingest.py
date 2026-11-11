"""Controlled file ingestion from a business-user drop zone into a landing area.

Business users drop files into `<root>/<area>/upload/`. Only allowlisted areas with a
known column contract are ingested; everything else is reported, never silently loaded.

See docs/adr/ADR-004-file-ingress-allowlist-and-contract.md
"""
import csv
import hashlib
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

_DDL = """
CREATE SCHEMA IF NOT EXISTS ops;
CREATE TABLE IF NOT EXISTS ops.file_manifest (
    sha256 VARCHAR PRIMARY KEY, area VARCHAR, filename VARCHAR, ingested_at TIMESTAMP
)
"""


@dataclass
class Report:
    ingested: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    rejected: list[tuple[str, str]] = field(default_factory=list)
    ignored_areas: list[str] = field(default_factory=list)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ingest(
    con: duckdb.DuckDBPyConnection,
    root: Path,
    landing: Path,
    contracts: dict[str, tuple[str, ...]],
) -> Report:
    """Copy valid, not-yet-seen files to `<landing>/<area>/input/`.

    `contracts` maps allowlisted area name -> required column names (in order).
    """
    con.execute(_DDL)
    report = Report()
    for area_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        upload = next((d for d in area_dir.iterdir() if d.is_dir() and d.name.lower() == "upload"), None)
        if upload is None:
            continue
        if area_dir.name not in contracts:
            report.ignored_areas.append(area_dir.name)
            continue
        expected = contracts[area_dir.name]
        for f in sorted(upload.glob("*.csv")):
            with f.open(newline="", encoding="utf-8-sig") as fh:
                header = tuple(next(csv.reader(fh), ()))
            if header != expected:
                report.rejected.append((f.name, f"columns {header} != contract {expected}"))
                continue
            digest = _sha256(f)
            if con.execute("SELECT 1 FROM ops.file_manifest WHERE sha256 = ?", [digest]).fetchone():
                report.duplicates.append(f.name)
                continue
            dest_dir = landing / area_dir.name / "input"
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest_dir / f"{f.stem}__{digest[:8]}{f.suffix}")
            con.execute(
                "INSERT INTO ops.file_manifest VALUES (?, ?, ?, current_timestamp)",
                [digest, area_dir.name, f.name],
            )
            report.ingested.append(f.name)
    return report
