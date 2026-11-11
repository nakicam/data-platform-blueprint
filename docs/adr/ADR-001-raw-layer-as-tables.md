# ADR-001: Raw layer as physical tables, not views

- **Status:** Proposed
- **Author:** Naki Cam (illustrative example, synthetic data)
- **Reviewer:** open

## Context
Source extracts arrive as files. The raw layer must preserve what was delivered, support reprocessing and give an audit trail. Downstream layers must not depend on file locations.

## Options
| Option | Pros | Cons |
|---|---|---|
| A. Raw as views over files | No storage duplication | History depends on file retention; schema drift breaks views; no load metadata; hard to restrict access |
| B. Raw as physical tables with load metadata | Stable history, reprocessing without the source, access control per table, load lineage | Storage cost, load step required |
| C. Skip raw, load straight into enriched | Fewer layers | No traceability; every cleaning bug destroys source information |

## Decision
Option B. Raw tables store source values unchanged (as text) plus `_run_id` and `_loaded_at`. Cleaning, typing and deduplication happen in the enriched layer.

## Consequences
- Duplicates delivered by the source stay visible in raw and are removed in enriched (tested).
- Raw is readable only by platform engineers (see ADR-002).
- Storage grows; retention must be defined per source.
- Reversible, but moving from A to B later means a one-time backfill.

## History
| Date | Change |
|---|---|
| 2026-11 | Created as illustrative example |
