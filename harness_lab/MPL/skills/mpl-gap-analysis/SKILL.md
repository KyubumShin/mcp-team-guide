---
description: Gap analysis for missing requirements - standalone pre-implementation review
---

# MPL Gap Analysis

Run gap analysis independently to identify missing requirements, AI pitfalls, and "Must NOT Do" constraints before implementation.

## When to Use

- Before starting any implementation (preventive review)
- When requirements feel incomplete or ambiguous
- To validate a plan before committing to execution
- As a second opinion on an existing decomposition

## Protocol

### Step 1: Gather Context

1. Read user's task description / requirements
2. Analyze relevant codebase areas:
   - `Glob` for affected file patterns
   - `Grep` for existing implementations and patterns
   - `lsp_document_symbols` for public API signatures
3. Read existing Pivot Points if available (`.mpl/pivot-points.md`)

### Step 2: Delegate to mpl-gap-analyzer

```
Task(subagent_type="mpl-gap-analyzer", model="haiku", prompt="""
Analyze the following for gaps:

User Request: {task description}
Pivot Points: {PPs if available, else "none"}
Codebase Context:
{relevant file structure, APIs, patterns}

Identify:
1. Missing Requirements - what the user didn't specify but is needed
2. AI Pitfalls - common mistakes an AI agent would make on this task
3. Must NOT Do - explicit constraints to prevent breaking changes
4. Recommended Questions - what to ask the user before proceeding
""")
```

### Step 3: Report

Present the gap analysis to the user with actionable items:
- CRITICAL gaps that block implementation
- Questions that need user input
- Constraints to carry forward as Pivot Points

If used within the full MPL pipeline, results feed into Step 1-B automatically.

## Constraints

- Read-only analysis: no code changes
- Orchestrator delegates analysis entirely to mpl-gap-analyzer
- Results are advisory; user decides which gaps to address

## Related

- `/mpl:mpl` runs gap analysis automatically at Step 1-B
- `/mpl:mpl-tradeoff` for risk assessment (complementary)
