#!/usr/bin/env python3
"""
4-System A/B Comparison: Metrics Collection

Collects metrics from completed experiment runs:
- pytest results (pass/fail counts)
- Token usage (from system-specific state files)
- Timing (from git log timestamps)
- Plan metrics (from PLAN.md files)

Outputs standardized JSON per run to results/ directory.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

EXPERIMENT_DIR = Path(__file__).parent.parent
RUNS_DIR = EXPERIMENT_DIR / "runs"
RESULTS_DIR = EXPERIMENT_DIR / "results"
TASKS_DIR = EXPERIMENT_DIR / "tasks"


def run_pytest(run_dir: Path, tests_dir: Path) -> dict:
    """Run pytest and parse results."""
    if not tests_dir.exists():
        return {"passed": 0, "total": 0, "failed": 0, "errors": 0, "error": "tests dir not found"}

    # Copy tests to run directory temporarily
    temp_tests = run_dir / "_eval_tests"
    if temp_tests.exists():
        shutil.rmtree(temp_tests)
    shutil.copytree(tests_dir, temp_tests)

    try:
        result = subprocess.run(
            ["python", "-m", "pytest", str(temp_tests), "--tb=short", "-q", "--no-header"],
            cwd=run_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr

        # Parse "X passed, Y failed, Z errors"
        passed = 0
        failed = 0
        errors = 0

        match = re.search(r"(\d+) passed", output)
        if match:
            passed = int(match.group(1))
        match = re.search(r"(\d+) failed", output)
        if match:
            failed = int(match.group(1))
        match = re.search(r"(\d+) error", output)
        if match:
            errors = int(match.group(1))

        total = passed + failed + errors
        return {"passed": passed, "total": total, "failed": failed, "errors": errors}

    except subprocess.TimeoutExpired:
        return {"passed": 0, "total": 0, "failed": 0, "errors": 0, "error": "timeout"}
    except Exception as e:
        return {"passed": 0, "total": 0, "failed": 0, "errors": 0, "error": str(e)}
    finally:
        if temp_tests.exists():
            shutil.rmtree(temp_tests)


def get_git_timing(run_dir: Path) -> dict:
    """Extract timing from git log."""
    try:
        # First commit timestamp (scaffold)
        result = subprocess.run(
            ["git", "log", "--reverse", "--format=%aI", "--max-count=1"],
            cwd=run_dir,
            capture_output=True,
            text=True,
        )
        first_commit = result.stdout.strip() if result.stdout.strip() else None

        # Last commit timestamp
        result = subprocess.run(
            ["git", "log", "--format=%aI", "--max-count=1"],
            cwd=run_dir,
            capture_output=True,
            text=True,
        )
        last_commit = result.stdout.strip() if result.stdout.strip() else None

        # Commit count (excluding initial scaffold)
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=run_dir,
            capture_output=True,
            text=True,
        )
        raw_count = result.stdout.strip()
        commit_count = max(0, int(raw_count) - 1) if raw_count.isdigit() else 0

        total_seconds = None
        if first_commit and last_commit and first_commit != last_commit:
            t1 = datetime.fromisoformat(first_commit)
            t2 = datetime.fromisoformat(last_commit)
            total_seconds = int((t2 - t1).total_seconds())

        return {
            "total_seconds": total_seconds,
            "commits_count": commit_count,
        }

    except Exception as e:
        return {"total_seconds": None, "commits_count": 0, "error": str(e)}


def get_token_metrics(run_dir: Path, system: str) -> dict:
    """Extract token usage from system-specific files."""
    metrics = {
        "total_tokens": None,
        "tokens_per_todo": None,
        "context_growth_rate": None,
        "overhead_ratio": None,
    }

    try:
        if system in ("uam", "uam-mpl"):
            # UAM stores metrics in .uam/metrics.json
            metrics_file = run_dir / ".uam" / "metrics.json"
            if metrics_file.exists():
                with open(metrics_file) as f:
                    data = json.load(f)
                metrics["total_tokens"] = data.get("total_tokens")
                metrics["tokens_per_todo"] = data.get("tokens_per_todo")
                metrics["context_growth_rate"] = data.get("context_growth_rate")
                metrics["overhead_ratio"] = data.get("overhead_ratio")

        elif system == "omc":
            # OMC stores state in .omc/state/
            state_dir = run_dir / ".omc" / "state"
            if state_dir.exists():
                for f in state_dir.glob("*.json"):
                    try:
                        with open(f) as fh:
                            data = json.load(fh)
                        if "total_tokens" in data:
                            metrics["total_tokens"] = data["total_tokens"]
                            break
                    except (json.JSONDecodeError, OSError):
                        continue

        elif system == "hoyeon":
            # hoyeon: check for state file
            state_file = run_dir / ".hoyeon" / "state.json"
            if state_file.exists():
                with open(state_file) as f:
                    data = json.load(f)
                metrics["total_tokens"] = data.get("total_tokens")

    except Exception:
        pass

    return metrics


def get_plan_metrics(run_dir: Path, system: str) -> dict:
    """Parse PLAN.md or equivalent for TODO metrics."""
    metrics = {
        "total_todos": 0,
        "completed_todos": 0,
        "failed_todos": 0,
        "discovery_count": 0,
    }

    # Find plan file based on system
    plan_paths = [
        run_dir / ".uam" / "PLAN.md",
        run_dir / "PLAN.md",
        run_dir / ".omc" / "plans" / "plan.md",
    ]

    for plan_path in plan_paths:
        if plan_path.exists():
            try:
                content = plan_path.read_text(encoding="utf-8")
                # Count checkboxes
                checked = len(re.findall(r"- \[x\]", content, re.IGNORECASE))
                unchecked = len(re.findall(r"- \[ \]", content))
                failed = len(re.findall(r"- \[!\]", content)) + len(
                    re.findall(r"- \[F\]", content, re.IGNORECASE)
                )

                metrics["total_todos"] = checked + unchecked + failed
                metrics["completed_todos"] = checked
                metrics["failed_todos"] = failed
            except OSError:
                pass
            break

    # Count discoveries (UAM-MPL specific)
    discovery_path = run_dir / ".uam" / "discoveries.json"
    if discovery_path.exists():
        try:
            with open(discovery_path) as f:
                discoveries = json.load(f)
            metrics["discovery_count"] = len(discoveries) if isinstance(discoveries, list) else 0
        except (json.JSONDecodeError, OSError):
            pass

    return metrics


def calculate_score(basic: dict, hidden: dict) -> dict:
    """Calculate final score and grade."""
    basic_total = basic.get("total", 0)
    basic_passed = basic.get("passed", 0)
    hidden_total = hidden.get("total", 0)
    hidden_passed = hidden.get("passed", 0)

    basic_score = (basic_passed / basic_total * 70) if basic_total > 0 else 0
    hidden_score = (hidden_passed / hidden_total * 30) if hidden_total > 0 else 0
    total_score = round(basic_score + hidden_score, 1)

    if total_score >= 95:
        grade = "S"
    elif total_score >= 85:
        grade = "A"
    elif total_score >= 70:
        grade = "B"
    elif total_score >= 50:
        grade = "C"
    else:
        grade = "F"

    return {
        "basic_passed": basic_passed,
        "basic_total": basic_total,
        "hidden_passed": hidden_passed,
        "hidden_total": hidden_total,
        "score": total_score,
        "grade": grade,
    }


def collect_run_metrics(run_info: dict) -> dict:
    """Collect all metrics for a single run."""
    run_dir = Path(run_info["directory"])
    system = run_info["system"]
    tier = run_info["tier"]

    if not run_dir.exists():
        return {
            "system": system,
            "tier": tier,
            "run": run_info["run"],
            "error": f"Run directory not found: {run_dir}",
        }

    # Determine test directories
    if tier == "t1":
        task_dir = TASKS_DIR / "tier1-taskflow"
    else:
        task_dir = TASKS_DIR / "tier2-bookshelf-api"

    tests_dir = task_dir / "tests"
    tests_hidden_dir = task_dir / "tests_hidden"

    # Collect metrics
    basic_results = run_pytest(run_dir, tests_dir)
    hidden_results = run_pytest(run_dir, tests_hidden_dir)

    return {
        "system": system,
        "tier": tier,
        "run": run_info["run"],
        "task_success": calculate_score(basic_results, hidden_results),
        "token_efficiency": get_token_metrics(run_dir, system),
        "error_isolation": {
            "regressions_introduced": 0,  # Requires baseline comparison
            "fix_attempts": 0,            # Requires git history analysis
        },
        "timing": get_git_timing(run_dir),
        "plan_metrics": get_plan_metrics(run_dir, system),
        "collected_at": datetime.now().isoformat(),
    }


def main():
    print("=" * 60)
    print("4-System A/B Comparison: Metrics Collection")
    print("=" * 60)

    # Load manifest
    manifest_path = RUNS_DIR / "run_manifest.json"
    if not manifest_path.exists():
        print("ERROR: run_manifest.json not found. Run setup_env.py first.")
        return

    with open(manifest_path) as f:
        manifest = json.load(f)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for run_info in manifest["runs"]:
        run_name = run_info["run_name"]
        status = run_info.get("status", "unknown")

        if status != "complete":
            print(f"  Skipping {run_name} (status: {status})")
            continue

        print(f"\nCollecting metrics for {run_name}...")
        metrics = collect_run_metrics(run_info)
        results.append(metrics)

        # Save individual result
        result_path = RESULTS_DIR / f"{run_name}.json"
        with open(result_path, "w") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        score = metrics.get("task_success", {}).get("score", "N/A")
        grade = metrics.get("task_success", {}).get("grade", "N/A")
        print(f"  Score: {score} ({grade})")

    if not results:
        print("\nNo completed runs found. Mark runs as 'complete' in run_manifest.json first.")
        return

    # Save combined results
    combined_path = RESULTS_DIR / "all_results.json"
    with open(combined_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"Collection complete! {len(results)} runs processed.")
    print(f"Results: {RESULTS_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
