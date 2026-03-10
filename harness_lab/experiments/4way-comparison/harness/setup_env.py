#!/usr/bin/env python3
"""
4-System A/B Comparison: Environment Setup

Creates isolated run directories for each system × tier × repetition combination.
Each directory gets:
- Scaffold files (pyproject.toml, package structure)
- Git initialization
- Prompt file copy
- HITL responses copy
- Run manifest entry
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration
SYSTEMS = ["omc", "hoyeon", "uam", "uam-mpl"]
TIERS = ["t1", "t2"]
RUNS_PER_CONDITION = 3

EXPERIMENT_DIR = Path(__file__).parent.parent
TASKS_DIR = EXPERIMENT_DIR / "tasks"
RUNS_DIR = EXPERIMENT_DIR / "runs"
HARNESS_DIR = EXPERIMENT_DIR / "harness"

# Tier 1 task source (existing TaskFlow)
TIER1_PROMPT = Path("/Users/kbshin/project/uam_v3_test/prompt.md")
TIER1_TESTS = Path("/Users/kbshin/project/v3_eval_store")

# Tier 2 task source (Bookshelf API)
TIER2_DIR = TASKS_DIR / "tier2-bookshelf-api"


def create_run_directory(system: str, tier: str, run: int) -> dict:
    """Create a single run directory with all necessary files."""
    run_name = f"{system}-{tier}-run{run}"
    run_dir = RUNS_DIR / run_name

    # Clean if exists
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)

    # Copy scaffold based on tier
    if tier == "t1":
        # Tier 1: TaskFlow scaffold
        scaffold_src = TIER1_PROMPT.parent
        # Create minimal scaffold for TaskFlow
        pkg_dir = run_dir / "taskflow"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").touch()

        # Copy pyproject.toml from existing test if available
        existing_toml = scaffold_src / "pyproject.toml"
        if existing_toml.exists():
            shutil.copy2(existing_toml, run_dir / "pyproject.toml")
        else:
            # Create minimal pyproject.toml for TaskFlow
            (run_dir / "pyproject.toml").write_text(
                '[project]\n'
                'name = "taskflow"\n'
                'version = "0.1.0"\n'
                'requires-python = ">=3.11"\n'
                'dependencies = [\n'
                '    "pydantic>=2.5.0",\n'
                ']\n'
                '\n'
                '[project.optional-dependencies]\n'
                'dev = [\n'
                '    "pytest>=7.4.0",\n'
                '    "pytest-asyncio>=0.23.0",\n'
                ']\n'
                '\n'
                '[build-system]\n'
                'requires = ["setuptools>=68.0"]\n'
                'build-backend = "setuptools.backends._legacy:_Backend"\n'
            )
        # Copy prompt
        if TIER1_PROMPT.exists():
            shutil.copy2(TIER1_PROMPT, run_dir / "prompt.md")

    elif tier == "t2":
        # Tier 2: Bookshelf API scaffold
        scaffold_src = TIER2_DIR / "scaffold"
        if scaffold_src.exists():
            shutil.copytree(scaffold_src, run_dir, dirs_exist_ok=True)

        # Copy prompt
        prompt_src = TIER2_DIR / "prompt.md"
        if prompt_src.exists():
            shutil.copy2(prompt_src, run_dir / "prompt.md")

    # Copy HITL responses
    hitl_src = HARNESS_DIR / "hitl_responses.yaml"
    if hitl_src.exists():
        shutil.copy2(hitl_src, run_dir / "hitl_responses.yaml")

    # Git init
    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "experiment",
        "GIT_AUTHOR_EMAIL": "exp@test.com",
        "GIT_COMMITTER_NAME": "experiment",
        "GIT_COMMITTER_EMAIL": "exp@test.com",
    }
    subprocess.run(["git", "init"], cwd=run_dir, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=run_dir, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial scaffold"],
        cwd=run_dir,
        capture_output=True,
        env=git_env,
    )

    return {
        "run_name": run_name,
        "system": system,
        "tier": tier,
        "run": run,
        "directory": str(run_dir),
        "status": "ready",
    }


def setup_tier1_tests():
    """Copy Tier 1 test files to a shared location for scoring."""
    tier1_task_dir = TASKS_DIR / "tier1-taskflow"
    tier1_task_dir.mkdir(parents=True, exist_ok=True)

    # Copy prompt
    if TIER1_PROMPT.exists():
        shutil.copy2(TIER1_PROMPT, tier1_task_dir / "prompt.md")

    # Copy tests from eval store
    for eval_dir_name in ["uam_eval", "omc_eval", "hoyeon_eval"]:
        eval_src = TIER1_TESTS / eval_dir_name
        if eval_src.exists():
            # Use first available test set as reference
            tests_src = eval_src / "tests"
            tests_hidden_src = eval_src / "tests_hidden"

            if tests_src.exists() and not (tier1_task_dir / "tests").exists():
                shutil.copytree(tests_src, tier1_task_dir / "tests")
            if tests_hidden_src.exists() and not (tier1_task_dir / "tests_hidden").exists():
                shutil.copytree(tests_hidden_src, tier1_task_dir / "tests_hidden")
            break  # Use first available


def main():
    print("=" * 60)
    print("4-System A/B Comparison: Environment Setup")
    print("=" * 60)

    # Setup Tier 1 task files
    print("\n[1/3] Setting up Tier 1 (TaskFlow) test files...")
    setup_tier1_tests()

    # Create run directories
    total_runs = len(SYSTEMS) * len(TIERS) * RUNS_PER_CONDITION
    print(f"\n[2/3] Creating {total_runs} run directories...")

    manifest = {
        "experiment": "4-system-ab-comparison",
        "created_at": datetime.now().isoformat(),
        "config": {
            "systems": SYSTEMS,
            "tiers": TIERS,
            "runs_per_condition": RUNS_PER_CONDITION,
            "model": "claude-sonnet-4-6",
        },
        "runs": [],
    }

    for system in SYSTEMS:
        for tier in TIERS:
            for run in range(1, RUNS_PER_CONDITION + 1):
                run_info = create_run_directory(system, tier, run)
                manifest["runs"].append(run_info)
                print(f"  + {run_info['run_name']}")

    # Write manifest
    print("\n[3/3] Writing run manifest...")
    manifest_path = RUNS_DIR / "run_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print("Setup complete!")
    print(f"  Total runs: {len(manifest['runs'])}")
    print(f"  Manifest: {manifest_path}")
    print(f"  Run directory: {RUNS_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
