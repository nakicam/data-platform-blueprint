# ADR-003: Incremental load with watermark and upsert

- **Status:** Proposed
- **Author:** Naki Cam (illustrative example, synthetic data)
- **Reviewer:** open

## Context
Source systems grow; reloading everything on every run gets slow and expensive. Sources also deliver late commits and change the same record several times.

## Options
| Option | Pros | Cons |
|---|---|---|
| A. Full reload every run | Simple, always consistent | Cost and runtime grow with the source |
| B. Append only new rows by watermark | Cheap | Updates create duplicates, late commits are lost |
| C. Watermark plus upsert by business key, with lookback window | Handles updates and late data, safe to re-run | Needs state, a stable key and a change timestamp |

## Decision
Option C. Per target the watermark is stored in `ops.watermark`; each run is logged in `ops.load_log`.
- The merge is an upsert by key inside one transaction, so a failed run never moves the watermark.
- A configurable lookback re-reads a window before the watermark; the upsert makes the overlap harmless.
- An explicit `full=True` switch rebuilds the target and resets the watermark. This is the recovery path and the way to propagate source deletes.

## Consequences
- Re-running is idempotent.
- Hard deletes in the source are not seen by incremental runs; they need a soft-delete flag or a scheduled full reload.
- Sources without a reliable change timestamp cannot use this pattern.

## History
| Date | Change |
|---|---|
| 2026-11 | Created as illustrative example |
