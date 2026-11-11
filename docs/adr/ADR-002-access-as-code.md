# ADR-002: Access control as reviewed code

- **Status:** Proposed
- **Author:** Naki Cam (illustrative example, synthetic data)
- **Reviewer:** open

## Context
Access to data layers must be traceable and consistent. Manual grants drift and cannot be reviewed.

## Options
| Option | Pros | Cons |
|---|---|---|
| A. Manual grants by admins | Fast | No history, no review, drift |
| B. Policy file rendered to grants, changed via pull request | Reviewable, versioned, testable | Needs a deployment step |
| C. Per-table permissions maintained by hand | Most granular | Does not scale, error-prone |

## Decision
Option B, at schema granularity per role. `access/policy.yaml` is validated by tests (for example: analysts never read raw) and rendered to GRANT statements.

## Consequences
- Every access change has an author, a reviewer and a date.
- Finer granularity (table, column) can be added later without changing the principle.
- A rendering step per target platform is required; the current renderer is a generic example.

## History
| Date | Change |
|---|---|
| 2026-11 | Created as illustrative example |
