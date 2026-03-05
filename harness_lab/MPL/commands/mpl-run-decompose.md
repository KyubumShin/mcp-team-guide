---
description: MPL Decomposition Protocol - Phase Decomposition, Verification Planning, Critic Simulation
---

# MPL Decomposition: Steps 3 through 3-C

This file contains Steps 3, 3-B, and 3-C of the MPL orchestration protocol.
Load this when transitioning from pre-execution analysis to phase decomposition.

---

## Step 3: Phase Decomposition

```
Task(subagent_type="mpl-decomposer", model="opus",
     prompt="""
     You are the Phase Decomposer for MPL.
     Break the user request into ordered micro-phases.

     ## Input
     ### User Request
     {user_request}
     ### Pivot Points
     {pivot_points content from .mpl/pivot-points.md}
     ### Maturity Mode
     {maturity_mode}
     ### Codebase Analysis
     {codebase_analysis JSON from .mpl/mpl/codebase-analysis.json}

     ### Phase 0 Enhanced Artifacts
     #### Complexity
     {complexity_report from .mpl/mpl/phase0/complexity-report.json}
     #### Phase 0 Summary
     {phase0_summary from .mpl/mpl/phase0/summary.md}
     #### Detailed Artifacts (if generated)
     {api_contracts from .mpl/mpl/phase0/api-contracts.md — if exists}
     {examples from .mpl/mpl/phase0/examples.md — if exists}
     {type_policy from .mpl/mpl/phase0/type-policy.md — if exists}
     {error_spec from .mpl/mpl/phase0/error-spec.md — always exists}

     ### Gap Analysis
     {gap_analysis from .mpl/mpl/gap-analysis.md}

     ### Tradeoff Analysis (Recommended Execution Order)
     {tradeoff_analysis from .mpl/mpl/tradeoff-analysis.md}

     ## Task
     Break the user request into ordered phases. Use Phase 0 artifacts to inform decomposition decisions — they contain pre-analyzed API contracts, usage patterns, type policies, and error specifications. Use the Tradeoff Analysis's Recommended Execution Order to guide phase ordering. Output YAML only.
     Each phase: id, name, scope, impact (create/modify/affected_tests/affected_config),
     interface_contract (requires/produces), success_criteria (typed: command/test/file_exists/grep/description),
     estimated_complexity (S/M/L).
     Also: architecture_anchor (tech_stack, directory_pattern, naming_convention), shared_resources.
     """)
```

### After Receiving Output

1. Parse YAML, validate phase count vs maturity mode sizing
2. Save to `.mpl/mpl/decomposition.yaml`
3. Initialize `.mpl/mpl/phase-decisions.md` with empty Active/Summary/Archived sections
4. Create `.mpl/mpl/phases/phase-N/` directories for each phase
5. Update MPL state with `phase_details` (all phases as `"pending"`)
6. Update pipeline state: `current_phase: "mpl-phase-running"`
7. Report: `"[MPL] Decomposition: N phases generated. Phase 1: {name}"`

---

## Step 3-B: Verification Planning

After decomposition, create per-phase verification plans with A/S/H-item classification.

```
Task(subagent_type="mpl-verification-planner", model="sonnet",
     prompt="""
     ## Input
     ### Phase Decomposition
     {decomposition YAML from .mpl/mpl/decomposition.yaml}
     ### Pivot Points
     {pivot_points}
     ### Codebase Analysis
     {codebase_analysis}
     ### Gap Analysis
     {gap_analysis}

     Classify all criteria into A/S/H items per phase.
     """)
```

### After Receiving Output
1. Validate 6 required sections via validate-output hook
2. Parse A/S/H items and attach to each phase_definition as `verification_plan` field
3. Save full plan to `.mpl/mpl/verification-plan.md`
4. Note phases with H-items (these will trigger Side Interviews during execution)
5. Report: `[MPL] Verification Plan: {A_count} A-items, {S_count} S-items, {H_count} H-items across {phase_count} phases.`

---

## Step 3-C: Critic Simulation

Pre-mortem simulation before committing to execution.

```
Task(subagent_type="mpl-critic", model="opus",
     prompt="""
     ## Input
     ### Pivot Points
     {pivot_points}
     ### Phase Decomposition
     {decomposition YAML}
     ### Gap Analysis
     {gap_analysis}
     ### Tradeoff Analysis
     {tradeoff_analysis}
     ### Verification Plan
     {verification_plan}

     Perform pre-mortem simulation. Identify risks and design drift vectors.
     """)
```

### After Receiving Output
1. If any HIGH severity risks:
   - Present to user via AskUserQuestion:
     Options: "Proceed as planned" | "Modify phases" | "Re-decompose"
   - "Modify phases": apply specific changes, re-run 3-B verification planning
   - "Re-decompose": return to Step 3 with critic feedback
2. Save to `.mpl/mpl/critic-report.md`
3. Report: `[MPL] Critic: {risk_count} risks ({high_count} HIGH). Assessment: {READY|READY_WITH_CAVEATS|NOT_READY}.`

---
