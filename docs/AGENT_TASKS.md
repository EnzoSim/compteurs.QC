# Agent Tasks

This file is the Manager's assignment board for the multi-agent workflow.

## Active Assignments
| ID | Owner | Task | Inputs | Output | Status |
| --- | --- | --- | --- | --- | --- |
| A-001 | Analyst | Verify each documented assumption with reputable sources and record citations. | `docs/ASSUMPTIONS_MODEL_TECHNICAL.md` | Updated assumptions doc + `docs/SOURCES.md` | In Progress |
| W-002 | Writer | Integrate verified citations and flag gaps for the Manager. | `docs/ASSUMPTIONS_MODEL_TECHNICAL.md`, `docs/SOURCES.md` | Updated assumptions doc with verification notes | In Progress |
| M-002 | Manager | Review consistency, update statuses, and ensure verification coverage. | All above outputs | Updated `docs/AGENT_TASKS.md` | In Progress |

## Done
| ID | Owner | Task | Output | Status |
| --- | --- | --- | --- | --- |
| M-001 | Manager | Define and assign the assumptions documentation + verification workflow. | `docs/AGENT_TASKS.md`, `AGENTS.md` | Done |
| W-001 | Writer | Document every model assumption from `analyse_compteurs_eau.py` in a technical document. | `docs/ASSUMPTIONS_MODEL_TECHNICAL.md` | Done |
| V-001 | Analyst | Verify frontend implementation of tasks.md items (API_URL, health timeout, presets sync, UI mismatches, request ordering, exportJSON). | Status report per item with file refs | Done |
| V-002 | Writer | Verify backend/static serving changes (path traversal guard, API routes) from tasks.md. | Status report per item with file refs | Done |
| V-003 | Manager | Verify Dockerfile/assets copy and consolidate all verification results step-by-step. | Consolidated verification report | Done |

## Research Questions
- Which tasks.md recommendations are fully implemented in the current codebase, and which remain partial or missing?
