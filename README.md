# data-platform-blueprint

A modular, local-first Data & Analytics platform showcase with synthetic data, architecture decisions and tested analytics models.

> Independent learning project. All data is synthetic. No employer code, designs or data are included.

## What is in it
| Part | Purpose |
|---|---|
| `src/blueprint/generate.py` | Synthetic ERP-style extracts with realistic quirks (leading zeros, duplicate deliveries, open items) |
| `src/blueprint/pipeline.py` | Raw → enriched → product layering in DuckDB |
| `access/policy.yaml`, `src/blueprint/access.py` | Access control as reviewed code, rendered to GRANT statements |
| `src/blueprint/incremental.py` | Incremental load: watermark, upsert, lookback, full-reload switch |
| `src/blueprint/file_ingest.py` | Drop-zone file ingestion with allowlist, column contract and hash manifest |
| `src/blueprint/writeback.py` | Versioned, validated business parameters with audit, feeding a cost-allocation product |
| `src/blueprint/jobs.py`, `jobs/daily.yml` | Jobs as configuration: validated task graph, run in dependency order |
| `docs/adr/` | Architecture decision records with options and consequences |
| `tests/` | Tests for layers, deduplication, key cleaning, access policy and the patterns above |

## Run
```bash
pip install -e ".[dev]"
python -m blueprint.cli
pytest
```

## Architecture decisions
- [ADR-001: Raw layer as physical tables](docs/adr/ADR-001-raw-layer-as-tables.md)
- [ADR-002: Access control as reviewed code](docs/adr/ADR-002-access-as-code.md)
- [ADR-003: Incremental load with watermark and upsert](docs/adr/ADR-003-incremental-load-watermark-upsert.md)
- [ADR-004: File ingestion with allowlist and contract](docs/adr/ADR-004-file-ingress-allowlist-and-contract.md)
- [ADR-005: Controlled writeback with versioning and audit](docs/adr/ADR-005-controlled-writeback-with-audit.md)
- [ADR-006: Jobs as configuration](docs/adr/ADR-006-jobs-as-configuration.md)

## Status
Working local example. Not a production platform.
