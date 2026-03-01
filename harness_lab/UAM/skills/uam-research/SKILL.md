---
description: UAM Standalone Deep Research - independent 3-stage research outside the pipeline
---

# UAM Research (Standalone)

Run deep research independently, outside the UAM pipeline. Results are saved to `.uam/research/` and can be reused when a pipeline starts later.

## Activation

- Keyword: `uam research {topic}`, `uam investigate {topic}`, `uam survey {topic}`
- Skill: `/uam:uam-research`
- Magic keyword: `[MAGIC KEYWORD: UAM-RESEARCH]`

## Protocol

### Step 1: Scope Confirmation

```
AskUserQuestion: "어떤 주제를 조사할까요?"
Options:
  1. "{detected topic from user input}" (Recommended)
  2. "범위 직접 지정"
```

### Step 2: Conflict Check

Check for active pipeline or existing research:

```
if isUamActive(cwd):
  → "UAM 파이프라인이 진행 중입니다. /uam:uam-status로 확인하세요."
  → ABORT

if .uam/research/.lock exists:
  → "다른 연구가 진행 중입니다 (started: {timestamp}, topic: {topic})."
  → ABORT

if .uam/research/ has existing reports:
  → List existing reports to user
  → "기존 연구 보고서가 있습니다. 새 연구는 기존 결과와 병합됩니다."
```

### Step 3: Initialize

```
# Create lock file to prevent concurrent research
mkdir -p .uam/research/
# Write lock: { started_at, topic, pid }

writeState(cwd, {
  research: {
    status: 'stage1',
    started_at: new Date().toISOString(),
    mode: 'standalone',
    report_path: null
  }
})
```

### Step 4: Execute 3-Stage Research

Follow the same 3-stage protocol as Phase 1-A in the full pipeline.

**Stage 1: Broad Scan**

```
Task(subagent_type="uam-researcher", model="sonnet",
     prompt="Stage 1 Broad Scan for: {topic}. Follow Stage 1 protocol.
     Run 3-5 WebSearch queries + codebase Grep/Glob.
     Select TOP 3 findings for deep-dive.
     Output Stage 1 schema.

     Existing research to avoid duplicating:
     {list of existing .uam/research/ reports, if any}")
```

Save to `.uam/research/stage1-cache.md`.

**Stage 2: Deep-Dive**

```
Task(subagent_type="uam-researcher", model="sonnet",
     prompt="Stage 2 Deep-Dive for: {topic}.
     TOP findings from Stage 1:
     {stage 1 top 3 findings}
     Follow Stage 2 protocol. WebFetch official docs. Output Stage 2 schema.")
```

Save to `.uam/research/stage2-cache.md`.

**Stage 3: Synthesis**

```
Task(subagent_type="uam-research-synthesizer", model="sonnet",
     prompt="Synthesize research for: {topic}.
     Stage 1 Results: {stage1 output}
     Stage 2 Results: {stage2 output}
     Follow full report Output_Schema.")
```

### Step 5: Save Report

Save synthesis output to `.uam/research/{topic-slug}.md`.
Remove lock file and stage cache files.

```
writeState(cwd, {
  research: {
    status: 'completed',
    completed_at: new Date().toISOString(),
    report_path: '.uam/research/{topic-slug}.md',
    findings_count: {count},
    sources_count: {count}
  }
})
```

### Step 6: Display Summary

```
UAM Research Complete
━━━━━━━━━━━━━━━━━━━━
Topic:    {topic}
Report:   .uam/research/{topic-slug}.md
Stages:   3/3 completed
Findings: {count}
Sources:  {count}

Executive Summary:
{3-5 sentence summary from report}

Top Recommendation:
{#1 recommendation with confidence level}

This report will be automatically used when you start a UAM pipeline.
```

## Light Mode (--light)

When invoked with `--light` flag or when quick scan is sufficient:

- Execute Stage 1 only (skip Stages 2 and 3)
- Save as `.uam/research/{topic-slug}-brief.md` using brief schema
- Faster but less thorough

```
Task(subagent_type="uam-researcher", model="haiku",
     prompt="Stage 1 Broad Scan (light mode) for: {topic}. Quick survey — max 2 WebSearch queries. Output Stage 1 schema.")
```

## Error Handling

| Situation | Action |
|-----------|--------|
| Stage 1 WebSearch all fail | Internal-only scan, note in report |
| Stage 2 all WebFetch fail | Degrade to Stage 1 results only |
| Researcher agent timeout | 1 retry, then save partial results |
| User cancels mid-research | Save completed stages, remove lock |

## Pipeline Integration

When a UAM pipeline starts (`uam {task}`):
1. Pipeline checks `.uam/research/` for existing reports
2. Matching reports are loaded as context for Phase 1-A
3. Already-investigated topics are skipped (no duplicate research)
4. Stale reports (>7 days old) are marked `[STALE]` and re-investigated

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/uam:uam` | Full 5-Phase pipeline (uses research results) |
| `/uam:uam-small` | 3-Phase lightweight pipeline |
| `/uam:uam-status` | Pipeline + research status dashboard |
| `/uam:uam-cancel` | Cancel active research or pipeline |
