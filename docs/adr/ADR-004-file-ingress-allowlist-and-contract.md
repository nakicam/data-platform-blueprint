# ADR-004: File ingestion from business drop zones with allowlist and contract

- **Status:** Proposed
- **Author:** Naki Cam (illustrative example, synthetic data)
- **Reviewer:** open

## Context
Some reference data (mappings, organisation lists, forecasts) only exists as spreadsheets maintained by business users. They must reach the platform without becoming an uncontrolled backdoor.

## Options
| Option | Pros | Cons |
|---|---|---|
| A. Ingest everything found in the shared folder | No setup | Wrong files and broken columns reach the platform |
| B. Allowlist of areas plus column contract, manifest by content hash | Controlled, repeatable, duplicates ignored | Every new area needs a reviewed entry |
| C. Business users load through a custom UI | Best validation | Build and maintenance effort |

## Decision
Option B. Business users drop files into `<area>/upload/`. Only allowlisted areas whose header matches the contract are copied to `<area>/input/` in the landing zone. Rejected files and non-allowlisted areas are reported, never loaded silently. A SHA-256 manifest makes re-runs idempotent.

## Consequences
- Adding a source is a small reviewed change (allowlist and contract).
- Content, not file name, decides what is new; renamed copies are detected as duplicates.
- Only structure is checked, not business plausibility; that belongs in the enriched layer.

## History
| Date | Change |
|---|---|
| 2026-11 | Created as illustrative example |
