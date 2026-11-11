# ADR-005: Controlled writeback of business parameters with versioning and audit

- **Status:** Proposed
- **Author:** Naki Cam (illustrative example, synthetic data)
- **Reviewer:** open

## Context
A data product (cost allocation) depends on parameters that only the business knows, here allocation shares per cost pool. They change over time and must be traceable.

## Options
| Option | Pros | Cons |
|---|---|---|
| A. Shares hard-coded in the transformation | Simple | Every change is a code release |
| B. Editable table without checks | Flexible | Invalid shares silently corrupt results; no history |
| C. Versioned table written through a validating function, with audit log | Valid by construction, reproducible, traceable | Writers must use the function, not raw SQL |

## Decision
Option C. `set_shares` validates (non-empty, no negatives, sum equals 1), writes a new version atomically and logs the attempt. Rejected attempts are audited too. The product view always uses the latest version per pool and exposes the version it used.

## Consequences
- Past results can be reproduced from a version number.
- Direct write permission on the share table must be withheld from business roles (see ADR-002).
- Approval workflows are not part of this decision.

## History
| Date | Change |
|---|---|
| 2026-11 | Created as illustrative example |
