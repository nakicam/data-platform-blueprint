# data-platform-blueprint

A modular, local-first Data & Analytics platform showcase with synthetic data, architecture decisions and tested analytics models.

> Independent learning project. All data is synthetic. No employer code, designs or data are included.

## What is in it
| Part | Purpose |
|---|---|
| `src/blueprint/generate.py` | Synthetic ERP-style extracts with realistic quirks (leading zeros, duplicate deliveries, open items) |
| `src/blueprint/pipeline.py` | Raw → enriched → product layering in DuckDB |
| `access/policy.yaml`, `src/blueprint/access.py` | Access control as reviewed code, rendered to GRANT statements |
| `docs/adr/` | Architecture decision records with options and consequences |
| `tests/` | Tests for layers, deduplication, key cleaning and access policy |

## Run
```bash
pip install -e ".[dev]"
python -m blueprint.cli
pytest
```

## Architecture decisions
- [ADR-001: Raw layer as physical tables](docs/adr/ADR-001-raw-layer-as-tables.md)
- [ADR-002: Access control as reviewed code](docs/adr/ADR-002-access-as-code.md)

## Status
Working local example. Not a production platform.
