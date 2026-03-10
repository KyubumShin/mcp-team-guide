#!/usr/bin/env python3
"""
4-System A/B Comparison: Report Generator

Loads results from results/*.json and generates a comparison report.
- Aggregates metrics by system and tier
- Calculates mean +/- std for repeated runs
- Tests hypotheses
- Generates markdown report
"""

import json
import statistics
from pathlib import Path
from datetime import datetime
from typing import Optional

EXPERIMENT_DIR = Path(__file__).parent.parent
RESULTS_DIR = EXPERIMENT_DIR / "results"

SYSTEMS = ["omc", "hoyeon", "uam", "uam-mpl"]
TIERS = ["t1", "t2"]
HYPOTHESES = {
    "h1_tier1_ordering": "Tier 1에서 OMC >= hoyeon >= UAM >= MPL (오버헤드 순)",
    "h2_tier2_mpl_reversal": "Tier 2에서 MPL의 O(1) 컨텍스트가 다른 시스템을 역전",
    "h3_breakeven": "~15 TODO / 5+ Phase에서 MPL이 순이익",
}


def load_results() -> list[dict]:
    """Load all result JSON files."""
    combined = RESULTS_DIR / "all_results.json"
    if combined.exists():
        with open(combined) as f:
            return json.load(f)

    results = []
    for f in sorted(RESULTS_DIR.glob("*.json")):
        if f.name in ("all_results.json", "REPORT.md"):
            continue
        try:
            with open(f) as fh:
                results.append(json.load(fh))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  WARNING: Could not load {f.name}: {e}")
    return results


def group_results(results: list[dict]) -> dict:
    """Group results by (system, tier)."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in results:
        system = r.get("system")
        tier = r.get("tier")
        if not system or not tier:
            continue
        key = (system, tier)
        if key not in groups:
            groups[key] = []
        groups[key].append(r)
    return groups


def safe_mean(values: list) -> Optional[float]:
    """Calculate mean, ignoring None values."""
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return round(statistics.mean(valid), 1)


def safe_stdev(values: list) -> Optional[float]:
    """Calculate stdev, ignoring None values. Returns None if fewer than 2 valid values."""
    valid = [v for v in values if v is not None]
    if len(valid) < 2:
        return None
    return round(statistics.stdev(valid), 1)


def format_metric(mean_val: Optional[float], std_val: Optional[float] = None) -> str:
    """Format as 'mean +/- std' or 'mean' or 'N/A'."""
    if mean_val is None:
        return "N/A"
    if std_val is not None:
        return f"{mean_val}+/-{std_val}"
    return str(mean_val)


def aggregate_group(runs: list[dict]) -> dict:
    """Aggregate metrics across repeated runs of the same condition."""
    scores = [r.get("task_success", {}).get("score") for r in runs]
    grades = [r.get("task_success", {}).get("grade") for r in runs if r.get("task_success", {}).get("grade")]
    basic_passed = [r.get("task_success", {}).get("basic_passed") for r in runs]
    hidden_passed = [r.get("task_success", {}).get("hidden_passed") for r in runs]
    tokens = [r.get("token_efficiency", {}).get("total_tokens") for r in runs]
    times = [r.get("timing", {}).get("total_seconds") for r in runs]
    commits = [r.get("timing", {}).get("commits_count") for r in runs]
    todos = [r.get("plan_metrics", {}).get("total_todos") for r in runs]
    completed = [r.get("plan_metrics", {}).get("completed_todos") for r in runs]

    return {
        "n": len(runs),
        "score_mean": safe_mean(scores),
        "score_std": safe_stdev(scores),
        "grade_mode": max(set(grades), key=grades.count) if grades else "N/A",
        "basic_passed_mean": safe_mean(basic_passed),
        "hidden_passed_mean": safe_mean(hidden_passed),
        "tokens_mean": safe_mean(tokens),
        "tokens_std": safe_stdev(tokens),
        "time_mean": safe_mean(times),
        "time_std": safe_stdev(times),
        "commits_mean": safe_mean(commits),
        "todos_mean": safe_mean(todos),
        "completed_mean": safe_mean(completed),
    }


def evaluate_hypotheses(
    groups: dict[tuple[str, str], list[dict]],
    aggregated: dict[tuple[str, str], dict],
) -> dict:
    """Evaluate each hypothesis based on aggregated results."""
    verdicts: dict[str, dict] = {}

    # H1: Tier 1 ordering OMC >= hoyeon >= UAM >= MPL
    t1_scores: dict[str, Optional[float]] = {}
    for sys in SYSTEMS:
        key = (sys, "t1")
        if key in aggregated:
            t1_scores[sys] = aggregated[key]["score_mean"]

    if len(t1_scores) == 4 and all(v is not None for v in t1_scores.values()):
        omc = t1_scores["omc"] or 0
        hoy = t1_scores["hoyeon"] or 0
        uam = t1_scores["uam"] or 0
        mpl = t1_scores["uam-mpl"] or 0
        ordering_holds = omc >= hoy >= uam >= mpl
        verdicts["h1_tier1_ordering"] = {
            "verdict": "PASS" if ordering_holds else "FAIL",
            "scores": t1_scores,
            "detail": f"OMC({omc}) >= hoyeon({hoy}) >= UAM({uam}) >= MPL({mpl}): {ordering_holds}",
        }
    else:
        verdicts["h1_tier1_ordering"] = {
            "verdict": "INCONCLUSIVE",
            "detail": f"Insufficient data (have {len(t1_scores)}/4 systems)",
        }

    # H2: Tier 2 MPL reversal
    t2_scores: dict[str, Optional[float]] = {}
    for sys in SYSTEMS:
        key = (sys, "t2")
        if key in aggregated:
            t2_scores[sys] = aggregated[key]["score_mean"]

    if len(t2_scores) == 4 and all(v is not None for v in t2_scores.values()):
        mpl_score = t2_scores.get("uam-mpl") or 0
        others_max = max(
            t2_scores.get("omc") or 0,
            t2_scores.get("hoyeon") or 0,
            t2_scores.get("uam") or 0,
        )
        mpl_wins = mpl_score >= others_max
        verdicts["h2_tier2_mpl_reversal"] = {
            "verdict": "PASS" if mpl_wins else "FAIL",
            "scores": t2_scores,
            "detail": f"MPL({mpl_score}) >= others_max({others_max}): {mpl_wins}",
        }
    else:
        verdicts["h2_tier2_mpl_reversal"] = {
            "verdict": "INCONCLUSIVE",
            "detail": f"Insufficient data (have {len(t2_scores)}/4 systems)",
        }

    # H3: Break-even (MPL loses T1 but wins T2 vs UAM-std)
    t1_mpl = aggregated.get(("uam-mpl", "t1"), {})
    t2_mpl = aggregated.get(("uam-mpl", "t2"), {})
    t1_uam = aggregated.get(("uam", "t1"), {})
    t2_uam = aggregated.get(("uam", "t2"), {})

    needed = [
        t1_mpl.get("score_mean"),
        t2_mpl.get("score_mean"),
        t1_uam.get("score_mean"),
        t2_uam.get("score_mean"),
    ]
    if all(v is not None for v in needed):
        t1_delta = (t1_mpl["score_mean"] or 0) - (t1_uam["score_mean"] or 0)
        t2_delta = (t2_mpl["score_mean"] or 0) - (t2_uam["score_mean"] or 0)
        breakeven_exists = t1_delta < 0 and t2_delta > 0
        verdicts["h3_breakeven"] = {
            "verdict": "PASS" if breakeven_exists else "FAIL",
            "detail": f"T1 MPL-UAM delta: {t1_delta:+.1f}, T2 MPL-UAM delta: {t2_delta:+.1f}",
        }
    else:
        verdicts["h3_breakeven"] = {
            "verdict": "INCONCLUSIVE",
            "detail": "Insufficient data for MPL vs UAM comparison across tiers",
        }

    return verdicts


def generate_report(
    groups: dict[tuple[str, str], list[dict]],
    aggregated: dict[tuple[str, str], dict],
    verdicts: dict,
) -> str:
    """Generate markdown comparison report."""
    lines: list[str] = []
    lines.append("# 4-System A/B Comparison Report")
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    for h_id, h_desc in HYPOTHESES.items():
        v = verdicts.get(h_id, {})
        verdict = v.get("verdict", "INCONCLUSIVE")
        marker = "[PASS]" if verdict == "PASS" else "[FAIL]" if verdict == "FAIL" else "[?]"
        lines.append(f"- {marker} **{h_desc}**: **{verdict}**")
        if v.get("detail"):
            lines.append(f"  - {v['detail']}")
    lines.append("")

    # Results per tier
    metrics_rows = [
        ("Score",        "score_mean",        "score_std"),
        ("Grade",        "grade_mode",        None),
        ("Basic Tests",  "basic_passed_mean", None),
        ("Hidden Tests", "hidden_passed_mean",None),
        ("Tokens",       "tokens_mean",       "tokens_std"),
        ("Time (sec)",   "time_mean",         "time_std"),
        ("Commits",      "commits_mean",      None),
        ("TODOs Total",  "todos_mean",        None),
        ("TODOs Done",   "completed_mean",    None),
        ("N (runs)",     "n",                 None),
    ]

    for tier in TIERS:
        tier_label = "Tier 1 (TaskFlow)" if tier == "t1" else "Tier 2 (Bookshelf API)"
        lines.append(f"## {tier_label} Results")
        lines.append("")
        lines.append("| Metric | OMC | hoyeon | UAM-Std | UAM-MPL |")
        lines.append("|--------|-----|--------|---------|---------|")

        for label, mean_key, std_key in metrics_rows:
            row = [label]
            for sys in SYSTEMS:
                agg = aggregated.get((sys, tier), {})
                mean_val = agg.get(mean_key)
                std_val = agg.get(std_key) if std_key else None
                # For non-numeric fields (grade, n) format directly
                if mean_key in ("grade_mode", "n"):
                    row.append(str(mean_val) if mean_val is not None else "N/A")
                else:
                    row.append(format_metric(mean_val, std_val))
            lines.append(f"| {' | '.join(row)} |")

        lines.append("")

    # Hypothesis Details
    lines.append("## Hypothesis Evaluation Details")
    lines.append("")
    for h_id, h_desc in HYPOTHESES.items():
        v = verdicts.get(h_id, {})
        verdict = v.get("verdict", "INCONCLUSIVE")
        lines.append(f"### {h_id}: {verdict}")
        lines.append(f"\n**Hypothesis:** {h_desc}")
        if v.get("detail"):
            lines.append(f"\n**Result:** {v['detail']}")
        if v.get("scores"):
            lines.append("\n**Scores:**")
            for sys, score in v["scores"].items():
                lines.append(f"- {sys}: {score}")
        lines.append("")

    # Dimension Analysis
    lines.append("## Dimension Analysis")
    lines.append("")
    dimensions = [
        ("Task Success",   "Score (basic x 0.7 + hidden x 0.3) 기반 종합 성공률"),
        ("Token Efficiency", "총 토큰 사용량과 TODO당 토큰 효율"),
        ("Error Isolation",  "회귀 발생률과 오류 수정 비용"),
        ("Adaptability",     "실행 중 발견 정보 처리 및 계획 변동률"),
        ("User Experience",  "HITL 횟수 및 첫 결과 도달 시간"),
    ]
    for dim_name, dim_desc in dimensions:
        lines.append(f"### {dim_name}")
        lines.append(f"\n{dim_desc}")
        lines.append("\n*실험 완료 후 데이터 기반으로 분석 추가 예정*\n")

    # Conclusions
    lines.append("## Conclusions")
    lines.append("")
    lines.append("*실험 완료 후 작성*")
    lines.append("")

    # Appendix
    lines.append("## Appendix: Raw Results")
    lines.append("")
    lines.append("See `results/all_results.json` for complete raw data.")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("4-System A/B Comparison: Report Generation")
    print("=" * 60)

    results = load_results()
    if not results:
        print("ERROR: No results found. Run collect_metrics.py first.")
        return

    print(f"\nLoaded {len(results)} run results.")

    groups = group_results(results)
    aggregated = {key: aggregate_group(runs) for key, runs in groups.items()}
    verdicts = evaluate_hypotheses(groups, aggregated)

    report = generate_report(groups, aggregated, verdicts)

    report_path = RESULTS_DIR / "REPORT.md"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nReport generated: {report_path}")

    # Print summary
    print("\n--- Hypothesis Verdicts ---")
    for h_id in HYPOTHESES:
        v = verdicts.get(h_id, {})
        print(f"  {h_id}: {v.get('verdict', 'N/A')}")
        if v.get("detail"):
            print(f"    {v['detail']}")

    print(f"\n{'=' * 60}")


if __name__ == "__main__":
    main()
