"""Validate the full frozen run, then compute descriptive paired statistics."""

from collections import Counter
import json
import statistics

from evaluate import ROOT, digest, file_digest, validate_completed, write_json


def summarize():
    plan = json.loads((ROOT / "plan.json").read_text())
    manifest = json.loads((ROOT / "manifest.json").read_text())
    if manifest["runner_sha256"] != file_digest(ROOT / "evaluate.py"):
        raise ValueError("Runner changed after inference")
    if manifest["plan_sha256"] != digest(plan):
        raise ValueError("Plan changed after inference")
    cases = plan["cases"]
    paths = {p.stem: p for p in (ROOT / "results").glob("*.json")}
    if len(cases) != 96 or set(paths) != {c["id"] for c in cases}:
        raise ValueError(f"Need exactly 96 planned results; found {len(paths)}")
    records = {}
    for case in cases:
        record = json.loads(paths[case["id"]].read_text())
        validate_completed(record, case, digest(manifest))
        if record["max_tokens"] != plan["decoding"]["max_tokens"]:
            raise ValueError("Unexpected token budget")
        if not 0 < record["metrics"]["generation_tokens"] <= record["max_tokens"]:
            raise ValueError("Out-of-range generated token count")
        if record["metrics"]["prompt_tokens"] != len(record["prompt_token_ids"]):
            raise ValueError("Prompt token count mismatch")
        records[case["id"]] = record
    groups = {}
    audit = []
    for language in ("en", "zh"):
        for thinking in (False, True):
            label = f"{language}-{'on' if thinking else 'off'}"
            group = sorted((r for r in records.values()
                            if r["case"]["language"] == language and r["case"]["thinking"] == thinking),
                           key=lambda r: r["case"]["row"])
            status = Counter(r["score"]["status"] for r in group)
            groups[label] = {
                "n": len(group), "correct": sum(r["score"]["correct"] for r in group),
                "delivered_integer": sum(r["score"]["prediction"] is not None for r in group),
                "length_stops": sum(r["metrics"]["finish_reason"] == "length" for r in group),
                "status_counts": dict(status),
                "mean_generated_tokens": statistics.mean(r["metrics"]["generation_tokens"] for r in group),
                "median_generated_tokens": statistics.median(r["metrics"]["generation_tokens"] for r in group),
                "mean_elapsed_seconds": statistics.mean(r["elapsed_seconds"] for r in group),
                "median_elapsed_seconds": statistics.median(r["elapsed_seconds"] for r in group),
                "median_generation_tps": statistics.median(r["metrics"]["generation_tps"] for r in group),
            }
            for correct in (True, False):
                candidates = [r for r in group if r["score"]["correct"] == correct]
                audit.extend(r["case"]["id"] for r in candidates[:3])
    paired = {}
    for a, b in (("en-off", "en-on"), ("zh-off", "zh-on"),
                 ("en-off", "zh-off"), ("en-on", "zh-on")):
        counts = Counter()
        changed = []
        for row in plan["selected_rows_zero_based"]:
            left = records[f"{row:03d}-{a}"]["score"]["correct"]
            right = records[f"{row:03d}-{b}"]["score"]["correct"]
            counts["both_correct" if left and right else "only_a" if left else "only_b" if right else "neither"] += 1
            if left != right:
                changed.append({"row": row, "a_correct": left, "b_correct": right})
        paired[f"{a}_vs_{b}"] = {"a": a, "b": b, "counts": dict(counts), "discordant_rows": changed}
    result = {
        "manifest_sha256": digest(manifest), "n_problems": 24, "n_completions": 96,
        "groups": groups, "paired": paired, "audit_case_ids": audit,
        "first_started_at": min(r["started_at"] for r in records.values()),
        "last_finished_at": max(r["finished_at"] for r in records.values()),
        "sum_inference_seconds": sum(r["elapsed_seconds"] for r in records.values()),
        "total_generated_tokens": sum(r["metrics"]["generation_tokens"] for r in records.values()),
        "process_peak_memory_gb": max(r["metrics"]["peak_memory"] for r in records.values()),
        "failed_attempt_count": len(list((ROOT / "failed_attempts").glob("*.json"))),
        "raw_result_sha256": {name: file_digest(path) for name, path in sorted(paths.items())},
    }
    write_json(ROOT / "summary.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "raw_result_sha256"}, indent=2))


if __name__ == "__main__":
    summarize()
