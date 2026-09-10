# Reproduce the experiment

The reference run uses Apple M3 Pro, 36 GiB unified memory, macOS 26.6.2,
Python 3.13.9, BF16 weights, and the original official Spark MLX implementation.
It uses no paid cloud service. Inference parity against Transformers was not
tested; conclusions describe this pinned MLX configuration.

The complete dependency versions are in `manifest.json` and `requirements.txt`.
The runtime is an unmodified checkout of:

```
https://github.com/XHToken/Spark-MLX-LLM.git
de2b4379fa1e2f2e1f99d84c83f0e008f651d86c
```

Keep the published reference outputs intact. For a fresh inference run, copy the
five source/dependency files into an empty directory (the commands below use
`replay/`). This also permits a different host's environment manifest without
mixing it into the original results. Run on a compatible Apple Silicon Mac.

```sh
mkdir replay
cp evaluate.py analyze.py test_evaluate.py fetch_inputs.py requirements.txt replay/
cd replay
git clone https://github.com/XHToken/Spark-MLX-LLM.git runtime
git -C runtime checkout de2b4379fa1e2f2e1f99d84c83f0e008f651d86c
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --no-deps ./runtime
.venv/bin/python fetch_inputs.py --model ./model-cache
.venv/bin/python -m unittest -v test_evaluate.py
.venv/bin/python evaluate.py plan
.venv/bin/python -u evaluate.py pilot --model ./model-cache < /dev/null > pilot.log 2>&1
.venv/bin/python -u evaluate.py run --model ./model-cache < /dev/null > run.log 2>&1
.venv/bin/python analyze.py
```

The public model and data were downloaded without an HF token. HF account login
is needed for publishing the contest Discussion; it does not affect these input
bytes. `fetch_inputs.py` downloads exactly the two pinned dataset files and the
pinned model snapshot. `evaluate.py plan` verifies both dataset SHA256 values
and all 250 English/Chinese reference pairs before selecting any examples.

Original inference commands used the same flags shown above; only the local
model directory and log destination have been replaced with portable paths.
The pilot is a separate 128-token, thinking-off calculation of 17 x 19, excluded
from every benchmark statistic. The 96-case run is 24 problem indices x two
languages x two thinking modes. Each completion gets 1,024 generated tokens,
one greedy sample (`temp=0`, `top_p=1`, `top_k=0`), seed 20260910 and a fresh KV
cache. There are no tools, few-shot examples, answer retries, or majority voting.
This is not the model card's recommended sampled decoding recipe.

`plan.json` includes the exact messages, question text, row IDs, references and
execution order. `manifest.json` records software/hardware and every model-file
hash; model weights are not included. Each `results/*.json` contains the rendered
chat prompt, prompt and output token IDs, complete output, score, stop reason,
timings and the manifest digest. A stopped run can be resumed with the same `run`
command; altered inputs/code/environment or conflicting writers are rejected.
Completed cases are validated and skipped. Failed inference attempts, if any,
are preserved separately and must be disclosed; they are not hidden extra samples.

MLX-LM's generation count includes a terminal EOS token for `stop` completions.
Peak memory is the process high-water mark, not isolated per-case allocation.
The wall duration covers chat encoding and generation; model load is separate.
Throughput and latency depend on this Mac and its load, and are not a cross-device
performance benchmark. Greedy decoding alone does not prove bitwise reproducibility
on another device, library version, or kernel implementation.

During tokenizer loading, Transformers printed a custom-AutoConfig prompt and a
fallback configuration warning. Standard input was closed; no Hugging Face
checkpoint-specific Python was executed. The model snapshot excludes `.py` files;
upstream source was separately fetched for inspection. Spark's official MLX class
loaded the original weights
with strict validation. The full sanitized warnings are retained in the logs.

The extraction rule is frozen in `score_output`: NFKC normalization, completed
visible answer only, and a sole `FINAL: <signed ASCII integer>` line at the end.
An unfinished thinking block, duplicate final markers, a unit, a thousands comma,
or trailing prose does not pass. Parse failures remain in the full denominator.
A length stop is also counted separately, including when it happens after a valid
final line. This measures correct answer delivery under the requested format;
it does not equate every format failure with inability to solve the mathematics.

`analyze.py` refuses a partial or identity-inconsistent run. It recomputes scores,
token-count checks and paired descriptive counts before writing `summary.json`.
The reasoning audit uses the first three correct and first three incorrect rows
in each condition, sorted by dataset row ID (or all if fewer). All raw completions
remain available; the audit is a subset, not proof that every other trace is sound.

See `LICENSE.md` for dataset attribution and the terms for this experiment.
