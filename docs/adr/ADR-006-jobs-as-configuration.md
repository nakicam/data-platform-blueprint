# ADR-006: Jobs as configuration

- **Status:** Proposed
- **Author:** Naki Cam (illustrative example, synthetic data)
- **Reviewer:** open

## Context
Ingestion, transformation and publishing steps depend on each other. Orchestration logic spread over scripts and UI settings is hard to review and to reproduce across environments.

## Options
| Option | Pros | Cons |
|---|---|---|
| A. One script calling steps in sequence | Easy | Dependencies implicit, no partial re-run |
| B. Orchestration clicked together in a tool UI | Quick start | Not reviewable, drifts between environments |
| C. Declarative task graph in versioned files, validated before running | Reviewable, testable, portable | A small runner or bundle tooling is needed |

## Decision
Option C. `jobs/daily.yml` declares tasks, types, parameters and `depends_on`. The runner validates (unknown dependencies, cycles, unknown task types) before anything runs, executes in dependency order, and stops on the first failure so downstream tasks never start on bad input.

## Consequences
- A job change is a pull request.
- Validation errors surface at review or test time, not at 5 am.
- The same definition can be deployed to several environments, with environment values kept outside the file.

## History
| Date | Change |
|---|---|
| 2026-11 | Created as illustrative example |
