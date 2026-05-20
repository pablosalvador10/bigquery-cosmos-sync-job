# AI Agent Instructions: Template-Agentic-AI-Apps-Azure

This repository is the reusable foundation for real-time agentic apps on Azure using Python, FastAPI, SSE streaming, React, Terraform, and `azd`.

## Required Reading Before Any Task

Read these first before coding:

1. `.github/instructions/system-architecture.instructions.md`
2. `.github/instructions/coding-standards.instructions.md`

These define WHAT the system is and HOW to implement safely.

## Monorepo Layout

| Path | Purpose |
|------|---------|
| `py/libs/foundrykit` | Azure AI Foundry client, AgentManager, ToolRegistry |
| `py/libs/agentkit` | YAML-driven agent spec loader || `py/libs/evalkit` | Domain-agnostic evaluation framework (evaluators, rubrics, coaching) |
| `py/libs/synthetickit` | Synthetic data generation pipeline (scenarios, quality gates) |
| `py/libs/testkit` | Shared test fakes (FakeCosmosContainer, FakeLLMClient, FakeStorage) || `py/apps/app-template` | FastAPI backend (chat, SSE streaming, storage) |
| `py/mcp/mcp-server-template` | MCP HTTP server skeleton |
| `ts/apps/ui-copilot-template` | React chat UI with SSE parsing |
| `infra/` | Terraform modules + azd deployment |

## Workflow: Understand -> Plan -> Implement

### 1) Understand (highest leverage)
- Identify layer(s): `py/`, `ts/`, `infra/`, `.github/`, `docs/`.
- Trace affected flow end-to-end before editing.
- Check reusable modules first (`py/libs/foundrykit`, `py/libs/agentkit`).

### 2) Plan
- Plan first for any non-trivial change (3+ steps or architecture impact).
- List files to modify and verification steps before implementation.
- If plan breaks, stop and re-plan immediately.

### Plan Node Default
- Default to plan mode for all non-trivial tasks.
- Use plan mode for implementation and verification, not only design.
- Treat a wrong plan as high-cost; correct it before coding.

### 3) Implement
- Keep changes minimal and local.
- Reuse existing patterns before creating new abstractions.
- Verify behavior before marking complete.

## Subagent Strategy

- Use subagents aggressively for deep research, parallel exploration, and bounded analysis.
- Keep one objective per subagent.
- For complex tasks, increase compute via multiple focused subagents.

## Verification Before Done

- Never mark complete without evidence.
- Validate with tests, logs, and lint/validation tools relevant to touched layers.
- Diff behavior between baseline and changes when relevant.
- Ask before completion: "Would a staff engineer approve this change?"

## Self-Improvement Loop

- After corrections, update `tasks/lessons.md` with root cause and prevention rule.
- Review relevant lessons at task start for repeated patterns.
- Prefer prevention rules over one-off fixes.

## Autonomous Bug Fixing

- When a bug is reported, fix it end-to-end without hand-holding.
- Start from concrete failures (tests, logs, runtime errors), then resolve root cause.
- Minimize context switching back to the user unless blocked.

## Demand Elegance (Balanced)

- For non-trivial changes, pause and check whether a cleaner design exists.
- Do not over-engineer obvious fixes; keep simple fixes simple.
- Challenge your own solution quality before presenting it.

## Task Management

1. Plan first in `tasks/todo.md` with checkable items for non-trivial work.
2. Verify plan quality before implementation; re-plan if assumptions break.
3. Track progress by marking items complete as work advances.
4. Explain changes with short high-level summaries as you implement.
5. Document results and review outcomes in `tasks/todo.md`.
6. Capture lessons in `tasks/lessons.md` after corrections.

## Core Principles

- Simplicity first: prefer the smallest clear solution.
- Reuse before create: check `py/libs`, then `py/apps`/`ts/apps`.
- Async-first backend: FastAPI handlers and I/O paths should be async.
- No unnecessary wrapper layers around existing services.
- No new dependencies without explicit approval.
- Config-driven behavior: avoid hardcoded endpoints, ports, model names, and cloud settings.
- Keep modules cohesive and small; split before files become hard to reason about.
- Add docstrings for public Python modules/classes/functions.

## Template-Specific Non-Negotiables

- Preserve SSE event contract in backend and frontend:
	- `message_start`
	- `delta`
	- `tool_event`
	- `done`
- Keep domain-neutral by default. Put sample-only logic under sample app sections.
- Keep strict separation between reusable libs (`py/libs`) and apps (`py/apps`).
- Do not commit secrets. Use `.env.example` and cloud secret references.

## Task and Lessons Hygiene

- For complex tasks, track actionable checkboxes in `tasks/todo.md`.
- After corrections, record short prevention notes in `tasks/lessons.md`.
- Keep `tasks/todo.md` updated while implementing, not only at the end.

## Documentation Connections

- System and coding rules start at:
	- `.github/instructions/system-architecture.instructions.md`
	- `.github/instructions/coding-standards.instructions.md`
- Area-specific guidance is in `.github/instructions/*.instructions.md`.
- Task execution and learning artifacts are:
	- `tasks/todo.md`
	- `tasks/lessons.md`

## Key Patterns

- **ToolRegistry**: Register agent tools with `@registry.register` — auto-traces via OpenTelemetry.
- **AgentSpec**: Define agents in YAML, load with `load_agent_spec()` from agentkit.
- **FoundryClient**: Singleton via `get_foundry_client()` — never create multiple instances.
- **Storage protocol**: All backends implement `add_message()` / `list_messages()`. Add new ones via `get_storage()` factory.
- **Pydantic models**: All request/response types typed via Pydantic `BaseModel`.
- **EvalRubric**: Run evaluators via `EvalRubric.evaluate(ctx)` — weighted scoring with quality gates.
- **Evaluator protocol**: Custom evaluators implement `dimension` + `evaluate()`. Seven built-in evaluators included.
- **SyntheticPipeline**: Generate test data via `run_pipeline(config)` — 3-stage: prepare → synthesize → annotate.
- **testkit fakes**: Use `FakeCosmosContainer`, `FakeLLMClient`, `FakeStorage` from testkit in all tests.

## Context Loading Architecture

| Tier | Location | Loaded | Best For |
|------|----------|--------|----------|
| 0 | This file | Every turn | Global rules, architecture overview |
| 1 | `instructions/*.instructions.md` | By keyword/glob match | Conventions, contracts, patterns |
| 2 | `skills/{name}/SKILL.md` | On demand by keyword | Step-by-step workflows |
| 3 | `documents/` | Explicit read only | Bulky reference material |

## Skill Routing

When a task matches one of these patterns, the corresponding skill provides step-by-step guidance:

- Adding an endpoint → `add-api-endpoint`
- Registering a tool → `tool-registration`
- Adding storage backend → `storage-backend`
- Creating an agent → `agent-authoring`
- Adding chat UI feature → `add-chat-feature`
- Setting up evaluations → `evaluation-pipeline`
- Generating synthetic test data → `synthetic-data-pipeline`
- Setting up test infrastructure → `test-infrastructure`
- Deploying to Azure → `azure-deployment`
- Adding Azure resource → `add-azure-resource`
- Running locally with Docker → `docker-local-dev`
- Writing tests → `write-backend-tests`
- Working with Cosmos DB → `cosmos-db-patterns`
- Building MCP server → `mcp-server-development`
- Extending the template → `extend-template`
- Debugging errors → `troubleshooting`
- Setting up tracing/observability → `observability-setup`
- Using/extending foundrykit → `foundrykit-library`
- Using/extending agentkit → `agentkit-library`
- Using/extending evalkit → `evalkit-library`
- Using/extending synthetickit → `synthetickit-library`
- Using/extending testkit → `testkit-library`
- Validating the full stack → `e2e-validation`
- Load testing endpoints → `load-testing`
- Smoke testing after deployment → `smoke-testing`

## Scoped Guidance

- Backend conventions: `.github/instructions/backend.instructions.md`
- Frontend conventions: `.github/instructions/frontend.instructions.md`
- Infra conventions: `.github/instructions/infrastructure.instructions.md`
- Python best practices: `.github/instructions/py_bestpractice.instructions.md`
- Python model conventions: `.github/instructions/py_models.instructions.md`
- Python FastAPI conventions: `.github/instructions/py_fastapi.instructions.md`
- Python testing: `.github/instructions/py_testing.instructions.md`
- TypeScript best practices: `.github/instructions/ts_bestpractice.instructions.md`
- Documentation philosophy: `.github/instructions/documentation.instructions.md`

## When In Doubt

When you need information about Azure services, Terraform syntax, or best practices that
isn't covered in this repo's skills/instructions, consult the authoritative sources
instruction at `.github/instructions/authoritative-sources.instructions.md`.
That file maps every Azure concern to the right MCP tool or reference source.

## Decision Filter

Before finalizing, ask:
- Is this the simplest correct solution?
- Does it reuse existing foundation modules?
- Is impact limited to necessary files?
- Would this pass staff-level code review?
