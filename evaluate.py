"""Reproduce a pinned, single-completion Spark-X2.5 MGSM experiment."""

import argparse
import datetime as dt
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import re
import subprocess
import time
import unicodedata
import uuid


ROOT = Path(__file__).resolve().parent
SEED = 20260910
MODEL_REVISION = "448e61eb392c00f2c403185c5b56d5e0665bfaab"
RUNTIME_REVISION = "de2b4379fa1e2f2e1f99d84c83f0e008f651d86c"
DATA_REVISION = "b2f13d426afe3be8d69a7e739b36724db8b66bbc"
DATA_HASHES = {
    "en": "3d0e84285dfb00d40e73d264628b0b0c65ca42e7112ff115b65787b20e1214dd",
    "zh": "3d5bab964d0991527391ddcb1862f587cc9baf918ba682e6faa080ff87b95bdf",
}
INSTRUCTIONS = {
    "en": "Solve the problem step by step. End your response with a separate line in exactly this format: FINAL: <integer>. Use a base-10 integer with no commas, units, or extra text on that final line.\n\nProblem:\n",
    "zh": "请逐步解答这道题。回答的最后单独一行必须严格使用此格式：FINAL: <integer>。将 <integer> 替换为十进制整数，最后一行不要使用逗号、单位或其他文字。\n\n题目：\n",
}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def file_digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    """Atomic replacement; callers hold the run lock for shared run artifacts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def preserve_identity(path, value):
    """Never mix a changed plan/code/environment into an existing run."""
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError(f"Existing {path.name} differs; use a separate experiment directory")
    else:
        write_json(path, value)


def build_plan():
    import pyarrow.parquet as pq

    tables = {}
    for language, checksum in DATA_HASHES.items():
        path = ROOT / "data" / f"{language}-test.parquet"
        if file_digest(path) != checksum:
            raise ValueError(f"Dataset checksum mismatch: {language}")
        tables[language] = pq.read_table(path).to_pylist()
        if len(tables[language]) != 250:
            raise ValueError("Expected 250 test rows per language")
    for row in range(250):
        if tables["en"][row]["answer_number"] != tables["zh"][row]["answer_number"]:
            raise ValueError(f"Unaligned references at row {row}")
        if any(not tables[lang][row]["question"].strip() for lang in tables):
            raise ValueError(f"Empty question at row {row}")
    selected = sorted(random.Random(SEED).sample(range(250), 24))
    cases = []
    for row in selected:
        for language in ("en", "zh"):
            for thinking in (False, True):
                source = tables[language][row]
                cases.append({
                    "id": f"{row:03d}-{language}-{'on' if thinking else 'off'}",
                    "row": row, "language": language, "thinking": thinking,
                    "question": source["question"],
                    "expected": int(source["answer_number"]),
                    "messages": [{"role": "user", "content": INSTRUCTIONS[language] + source["question"]}],
                })
    random.Random(SEED).shuffle(cases)
    return {
        "schema": 1, "seed": SEED, "model": "XHToken/Spark-X2.5-1.7B",
        "model_revision": MODEL_REVISION, "runtime_revision": RUNTIME_REVISION,
        "dataset": "juletxara/mgsm", "dataset_revision": DATA_REVISION,
        "dataset_split": "test", "dataset_hashes": DATA_HASHES,
        "selected_rows_zero_based": selected, "cases": cases,
        "decoding": {"max_tokens": 1024, "temp": 0.0, "top_p": 1.0, "top_k": 0},
        "dtype": "bfloat16", "quantization": None, "fresh_cache_per_case": True,
        "pilot": {"question": "Compute 17 times 19. End with the exact line FINAL: <integer>.",
                  "expected": 323, "thinking": False, "max_tokens": 128},
        "scoring": "NFKC; completed visible answer only; sole FINAL: line must be last and contain signed ASCII integer; exact match; all 24 rows per condition remain in denominator",
        "reasoning_audit": "Per condition, inspect first three correct and first three incorrect cases in ascending dataset row order (or all if fewer); retain all outputs and classify format, arithmetic, modeling, and truncation failures separately.",
    }


def score_output(text, thinking, expected):
    normalized = unicodedata.normalize("NFKC", text)
    in_thinking = thinking
    visible = []
    invalid_tags = False
    for part in re.split(r"(<think>|</think>)", normalized):
        if part == "<think>":
            invalid_tags |= in_thinking
            in_thinking = True
        elif part == "</think>":
            invalid_tags |= not in_thinking
            in_thinking = False
        elif not in_thinking:
            visible.append(part)
    lines = [line.strip() for line in "".join(visible).splitlines() if line.strip()]
    final_lines = [line for line in lines if line.startswith("FINAL:")]
    prediction = None
    if in_thinking or invalid_tags:
        status = "unfinished_or_invalid_thinking"
    elif len(final_lines) > 1:
        status = "ambiguous_final"
    elif not lines or not re.fullmatch(r"FINAL: [+-]?[0-9]+", lines[-1]):
        status = "missing_or_malformed_final"
    else:
        prediction = int(lines[-1][7:])
        status = "correct" if prediction == expected else "wrong_integer"
    return {"prediction": prediction, "correct": status == "correct", "status": status}


def make_manifest(plan, model_path):
    runtime = ROOT / "runtime"
    revision = subprocess.check_output(["git", "-C", str(runtime), "rev-parse", "HEAD"], text=True).strip()
    if revision != RUNTIME_REVISION:
        raise ValueError("Unexpected Spark runtime revision")
    if subprocess.check_output(["git", "-C", str(runtime), "status", "--porcelain"], text=True).strip():
        raise ValueError("Spark runtime has local changes")
    packages = dict(sorted((d.metadata["Name"], d.version)
                          for d in importlib.metadata.distributions()))
    files = {p.name: {"sha256": file_digest(p), "bytes": p.stat().st_size}
             for p in sorted(model_path.iterdir()) if p.is_file()}
    required = {"config.json", "chat_template.jinja", "tokenizer.json",
                "model-00001-of-00002.safetensors", "model-00002-of-00002.safetensors"}
    if not required.issubset(files):
        raise ValueError("Incomplete local model")
    return {"plan_sha256": digest(plan), "runner_sha256": file_digest(Path(__file__)),
            "model_files": files, "packages": packages, "runtime_revision": revision,
            "python": platform.python_version(), "macos": platform.mac_ver()[0],
            "machine": platform.machine(), "device": "mlx.gpu", "dtype": "bfloat16",
            "chip": subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip(),
            "memory_bytes": int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)),
            "no_quantization": True}


def infer(model, tokenizer, case, max_tokens, record):
    import mlx.core as mx
    from mlx_lm import stream_generate
    from mlx_lm.sample_utils import make_sampler

    prompt = tokenizer.apply_chat_template(case["messages"], tokenize=False,
                                          add_generation_prompt=True,
                                          enable_thinking=case["thinking"])
    suffix = "<think>" if case["thinking"] else "</think>"
    if not prompt.endswith(suffix):
        raise ValueError("Unexpected chat template generation prefix")
    prompt_tokens = tokenizer.encode(prompt, add_special_tokens=False)
    record.update(rendered_prompt=prompt, prompt_token_ids=prompt_tokens,
                  output="", output_token_ids=[], started_at=now())
    started = time.perf_counter()
    mx.random.seed(SEED)
    final = None
    for response in stream_generate(model, tokenizer, prompt=prompt_tokens,
                                    max_tokens=max_tokens,
                                    sampler=make_sampler(temp=0.0, top_p=1.0, top_k=0)):
        record["output"] += response.text
        record["output_token_ids"].append(int(response.token))
        final = response
    if final is None or final.finish_reason not in ("stop", "length"):
        raise RuntimeError("Generation did not reach a terminal response")
    record.update(finished_at=now(), elapsed_seconds=time.perf_counter() - started,
                  output_sha256=hashlib.sha256(record["output"].encode()).hexdigest(),
                  metrics={name: getattr(final, name) for name in (
                      "prompt_tokens", "prompt_tps", "generation_tokens", "generation_tps",
                      "peak_memory", "finish_reason")},
                  score=score_output(record["output"], case["thinking"], case["expected"]))
    if len(record["output_token_ids"]) != final.generation_tokens:
        raise RuntimeError("Inconsistent generated token count")


def validate_completed(record, case, manifest_sha):
    if record.get("manifest_sha256") != manifest_sha or record.get("case") != case:
        raise ValueError("Completed record has incompatible run or case identity")
    if record.get("output_sha256") != hashlib.sha256(record["output"].encode()).hexdigest():
        raise ValueError("Completed output checksum mismatch")
    if record.get("score") != score_output(record["output"], case["thinking"], case["expected"]):
        raise ValueError("Completed record has inconsistent score")
    if record["metrics"]["finish_reason"] not in ("stop", "length"):
        raise ValueError("Completed record lacks terminal generation state")
    if len(record["output_token_ids"]) != record["metrics"]["generation_tokens"]:
        raise ValueError("Completed record has inconsistent token count")


def execute(mode, model_path, plan):
    import mlx.core as mx
    from spark_mlx_llm import load

    manifest = make_manifest(plan, model_path)
    preserve_identity(ROOT / "manifest.json", manifest)
    manifest_sha = digest(manifest)
    mx.set_default_device(mx.gpu)
    load_start = time.perf_counter()
    model, tokenizer = load(model_path, dtype="bfloat16", strict=True)
    load_seconds = time.perf_counter() - load_start
    print(json.dumps({"event": "loaded", "at": now(), "load_seconds": load_seconds}), flush=True)
    if mode == "pilot":
        if (ROOT / "pilot.json").exists():
            raise ValueError("Pilot already exists; preserve the original attempt")
        tokens = tokenizer.encode("Compute 17 times 19.", add_special_tokens=False)
        logits = model(mx.array([tokens]))[:, -1, :]
        if not bool(mx.all(mx.isfinite(logits)).item()):
            raise RuntimeError("Nonfinite pilot logits")
        del logits
        case = {"id": "pilot", "messages": [{"role": "user", "content": plan["pilot"]["question"]}],
                "thinking": False, "expected": 323}
        cases = [(case, 128, ROOT / "pilot.json")]
    else:
        cases = [(case, plan["decoding"]["max_tokens"], ROOT / "results" / f"{case['id']}.json")
                 for case in plan["cases"]]
    for index, (case, budget, path) in enumerate(cases, 1):
        if path.exists():
            validate_completed(json.loads(path.read_text()), case, manifest_sha)
            continue
        record = {"case": case, "manifest_sha256": manifest_sha,
                  "max_tokens": budget, "load_seconds_this_process": load_seconds,
                  "finite_prefill_verified": True if mode == "pilot" else None}
        try:
            infer(model, tokenizer, case, budget, record)
        except Exception as error:
            record.update(error_type=type(error).__name__, failed_at=now())
            write_json(ROOT / "failed_attempts" / f"{case['id']}-{uuid.uuid4().hex}.json", record)
            raise
        write_json(path, record)
        print(json.dumps({"event": "completed", "at": now(), "index": index, "total": len(cases),
                          "id": case["id"], "score": record["score"], "metrics": record["metrics"]}), flush=True)
        mx.clear_cache()
    print(json.dumps({"event": "finished", "mode": mode, "at": now(), "cases": len(cases)}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("plan", "pilot", "run"))
    parser.add_argument("--model", type=Path)
    args = parser.parse_args()
    with (ROOT / ".run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan = build_plan()
        preserve_identity(ROOT / "plan.json", plan)
        if args.mode == "plan":
            print(json.dumps({"cases": len(plan["cases"]), "rows": plan["selected_rows_zero_based"],
                              "plan_sha256": digest(plan), "at": now()}))
            return
        if args.model is None:
            parser.error("--model is required for inference")
        execute(args.mode, args.model.resolve(), plan)


if __name__ == "__main__":
    main()
