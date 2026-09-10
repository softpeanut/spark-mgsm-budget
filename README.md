# [HER Hack-Astron #6] Delivering integer answers within a fixed budget

A paired English/Chinese MGSM evaluation of **Spark-X2.5-1.7B** with thinking on/off,
using the official Spark MLX runtime on an Apple M3 Pro.

On these 24 fixed problem pairs, thinking increased correct delivered answers in
English from **18 to 20**, but decreased them in Chinese from **19 to 16**, at the
same 1,024-token output limit. Thinking-on produced longer outputs and more length
stops in both languages. These are descriptive results for this small, specific
sample and runtime, not a general ranking of languages or thinking modes.

## Results

| Language, thinking | Correct integer delivered | Integer delivered | Length stops | Mean generated tokens | Mean seconds/completion |
| --- | ---: | ---: | ---: | ---: | ---: |
| English, off | 18/24 (75.0%) | 21/24 | 2/24 | 285.1 | 8.00 |
| English, on | 20/24 (83.3%) | 20/24 | 4/24 | 557.5 | 15.41 |
| Chinese, off | 19/24 (79.2%) | 22/24 | 2/24 | 352.4 | 9.82 |
| Chinese, on | 16/24 (66.7%) | 17/24 | 7/24 | 659.7 | 18.30 |

Every denominator includes all 24 sampled problems in that condition. The primary
metric is one greedy completion per question, strict final-integer exact match;
there is no pass@k, self-consistency, answer retry, or removal of parse failures.
It measures answer delivery under the requested format and budget, not reasoning
soundness alone. All 96 actual completions finished; there were zero failed
inference attempts. A separate successful 17 x 19 pilot is excluded.

English thinking-on had three paired gains (rows 173, 177, 224) and one loss (41).
Chinese thinking-on had two gains (3, 65) and five losses (19, 41, 47, 177, 183).
The pairwise tables, all discordant rows and raw-file hashes are in
[summary.json](summary.json). A secondary calculation excluding the three
reference-interpretation caveats at rows 93, 177 and 241 yields **18/21, 19/21,
18/21 and 16/21**, respectively. This is labeled secondary; the primary scores
above remain unchanged.

## What the full traces show

- **Correct final answer with a false intermediate claim:** `019-zh-off` returns
  the correct 6 mph, but explicitly describes 6 miles covered in 2 hours as an
  average of 6 mph. That rate is 3 mph. Its later equation is correct without
  explicitly retracting the earlier claim. `019-en-off` also makes an intermediate
  rate error, then visibly corrects its route-time model before answering.
- **Correct reasoning without delivered answer:** `019-zh-on` correctly derives
  a one-hour remaining window and 6 mph in thinking. It then starts repeating the
  explanation and reaches the token limit before its visible final line.
- **Dropped quantities:** `003-zh-off` drops one factor of three in the sprint
  problem (180 instead of 540); `047-zh-on` computes the red ties' $600 subtotal
  but omits the blue ties' $200 from the requested total.
- **Arithmetic and unit failures:** `177-en-off` derives the individual expenses
  correctly but adds them as 6750 rather than 5650. `173-en-off` returns a monthly
  payment for a yearly question. `101-en-off` treats 15 pages as 15 days.
- **Translation can affect this comparison:** `064-zh-on` interprets 一罐汽油 as an
  unspecified canister rather than the full car tank and loops on its capacity.
  The English question says “single tank of gas.” This is a translation/prompt
  confound, not evidence that Chinese intrinsically reasons worse.

The locally frozen audit rule selects the first three correct and first three
incorrect rows per condition, sorted by dataset row (all if fewer). **All 24
selected traces were read in full**, with observations in [AUDIT.md](AUDIT.md) and
[trace-review.json](trace-review.json). Seven additional traces were inspected as
exploratory paired/reference examples and are marked separately. This is AI-assisted
trace analysis with independent arithmetic checks, not a human-review attestation
or a claim that every unaudited trace is sound.

## Fixed protocol and provenance

- Model: [XHToken/Spark-X2.5-1.7B](https://huggingface.co/XHToken/Spark-X2.5-1.7B/tree/448e61eb392c00f2c403185c5b56d5e0665bfaab),
  revision `448e61eb392c00f2c403185c5b56d5e0665bfaab`; original BF16 weights, no quantization.
- Runtime: [official Spark-MLX-LLM](https://github.com/XHToken/Spark-MLX-LLM/tree/de2b4379fa1e2f2e1f99d84c83f0e008f651d86c),
  commit `de2b4379fa1e2f2e1f99d84c83f0e008f651d86c`; MLX 0.32.2,
  MLX-LM 0.31.3, Transformers 5.17.0, Python 3.13.9. No container was used.
- Hardware: Apple M3 Pro, 36 GiB unified memory, macOS 26.6.2, `mlx.gpu`.
  This used an existing local Mac, with no GPU rental or paid inference API.
- Data: [juletxara/mgsm](https://huggingface.co/datasets/juletxara/mgsm/tree/b2f13d426afe3be8d69a7e739b36724db8b66bbc),
  revision `b2f13d426afe3be8d69a7e739b36724db8b66bbc`, English and Chinese test splits.
  Both files have 250 rows; all reference pairs aligned. Questions were not paraphrased.
- Selection: `sorted(random.Random(20260910).sample(range(250), 24))`;
  all four language/mode combinations, shuffled with a new `Random(20260910)`.
  The exact messages, expected integers and order are in [plan.json](plan.json).
  Selection and scoring were locally fixed before inference; they were not a
  public preregistration. The model did not receive the expected answers.
- Decoding: one zero-shot completion, `temp=0.0` (argmax), `top_p=1.0`,
  `top_k=0`, `max_tokens=1024`, seed 20260910, fresh KV cache per completion.
  Only the language and official chat-template `enable_thinking` flag vary.
  No tool calls or few-shot exemplars are used. This is not the model card's
  recommended sampled benchmark configuration.

Run window: **2026-09-10T09:53:37.024713+00:00 to 2026-09-10T10:14:14.287127+00:00**, totaling
**44,513 generated tokens** and approximately
**20.61 minutes** of summed completion time.
The MLX process peak was **3.652 GB**, a high-water mark
rather than per-case memory. Generated-token counts include EOS for stop completions.
Model loading is recorded separately. Latency is for this machine and workload;
no cross-device performance claim is made.

The [manifest](manifest.json) preserves environment versions and local input
hashes. [Remote verification](remote-input-verification.json) independently matches
both weight shards, the tokenizer and the two parquet files against upstream LFS
SHA256 metadata at the pinned revisions. Model weights are **not** redistributed.

The official loader passed strict weight loading and finite-logit/actual generation
checks. Transformers emitted a tokenizer AutoConfig fallback warning and a
custom-code prompt; stdin was closed and no Hugging Face checkpoint-specific
Python was executed. The model snapshot excludes `.py` files; upstream Python
source was separately fetched for inspection. The original warning remains in [pilot logs](logs/pilot.log) and
[complete run logs](logs/run.log), with only the private model path replaced by
`<MODEL_DIR>`. Numerical parity against Transformers inference was not tested.

## Scoring and limitations

[evaluate.py](evaluate.py) normalizes output using NFKC, excludes text inside
thinking, and requires the sole visible `FINAL: <signed ASCII integer>` line to
be the last nonempty line. Unclosed thinking, duplicated final markers, decimal
answers, comma-separated numbers, units or trailing prose fail the format rule.
A valid integer is compared exactly with the dataset reference; all failures stay
in the denominator. There are no ties or voting because there is only one sample.
Length stops are counted separately from numerical correctness.

The [reference audit](reference-audit.json) independently recomputes all 24
reference-compatible answers. Row 93 says speed improves by 10%: literal physics
would give `40 / 1.1 = 400/11` seconds, while its label 36 corresponds to a 10%
reduction in time. Rows 177 and 241 have weekly/monthly and distinct-books/reading-
events interpretation caveats. Scores are not relabeled to make outputs look better.
The translation observation at row 64 arose during trace review; it was not added
to the three-row secondary exclusion after observing the model's failure.

This is **24 paired problems, not 96 independent questions**, and not the full
250-question MGSM test set. Public training contamination is unknown. Greedy
single-run behavior does not establish bitwise reproducibility on other kernels
or hardware. Longer outputs are associated here with lost answer delivery, but
this run does not test alternative token limits or prove an optimal budget.
The practical next experiment is to vary the output cap while retaining these
pairs and extraction rules; no such follow-up result is claimed here.

## Reproduce and inspect

[REPRODUCE.md](REPRODUCE.md) contains installation, exact inference flags and
analysis commands. [requirements.txt](requirements.txt) pins dependencies;
[fetch_inputs.py](fetch_inputs.py) fetches the public pinned inputs. Six scorer,
paired-plan and identity-preservation tests passed. Analysis rejected an actual
partial run, then verified all 96 complete records and recomputed the final
summary. See [validation notes](logs/checks.txt).

Every [raw result](results/) includes the complete output, rendered prompt,
prompt/output token IDs, timing, stop reason, reference and score. Five full
representative traces appear below, including a clean success, wrong answers,
a correct final answer with a false intermediate claim, and a delivery failure.
All 24 prespecified audit traces are also reproduced in [AUDIT.md](AUDIT.md).

Data credit: Freda Shi et al., [Language Models are Multilingual Chain-of-Thought
Reasoners](https://arxiv.org/abs/2210.03057); MGSM packaging by
[juletx](https://github.com/juletx), based on Karl Cobbe et al.'s
[GSM8K](https://arxiv.org/abs/2110.14168). MGSM card metadata declares CC BY-SA 4.0;
original GSM8K carries an MIT notice. Selected questions are unchanged; prompts,
outputs and annotations are additions. See [LICENSE.md](LICENSE.md) for attribution
and reuse terms. This is an original local experiment and AI-assisted report.

## Representative full traces

Displayed traces omit trailing spaces at line ends for readability; the complete original text and its SHA256 remain in each raw JSON record.


<details>
<summary>003-en-off — sound_reasoning</summary>

Question: James decides to run 3 sprints 3 times a week.  He runs 60 meters each sprint.  How many total meters does he run a week?

Reference: 540; prediction: 540; score: correct; stop: stop; generated tokens: 115.

Audit: Correctly multiplies 3 sprints per session by 3 sessions per week and 60 meters per sprint: 540.

Full generated text (the opening thinking tag, if enabled, is part of the prompt):

~~~~text
Step 1: Determine the number of sprints per week.
James runs 3 sprints 3 times a week, so:
3 sprints × 3 times = 9 sprints per week.

Step 2: Determine the distance per sprint.
Each sprint is 60 meters.

Step 3: Calculate total distance per week.
Total distance = number of sprints × distance per sprint
= 9 × 60
= 540 meters.

FINAL: 540
~~~~

[Complete JSON with prompt and token IDs](results/003-en-off.json)

</details>

<details>
<summary>003-zh-off — dropped_multiplicative_factor</summary>

Question: 詹姆斯决定每周跑 3 次 3 段冲刺，每段冲刺跑 60 米。他每周一共跑多少米？

Reference: 540; prediction: 180; score: wrong_integer; stop: stop; generated tokens: 83.

Audit: Drops the three sprints per session and computes only 3*60=180 instead of 3*3*60=540.

Full generated text (the opening thinking tag, if enabled, is part of the prompt):

~~~~text
我们来逐步解答这道题：

1. **詹姆斯每周跑冲刺的次数**：3 次。
2. **每次冲刺的距离**：60 米。
3. **每周总跑距离** = 次数 × 每次距离 = 3 × 60。

计算：
3 × 60 = 180

FINAL: 180
~~~~

[Complete JSON with prompt and token IDs](results/003-zh-off.json)

</details>

<details>
<summary>019-zh-off — correct_final_with_false_intermediate_rate_claim</summary>

Question: 玛丽莎正在一条长 12 英里的小径上徒步旅行。她用了 1 小时走完前面 4 英里，然后再用一小时走完 2 英里。如果她希望平均速度达到每小时 4 英里，则要走完剩下的距离，她的速度需要达到多少（以英里每小时为单位）？

Reference: 6; prediction: 6; score: correct; stop: stop; generated tokens: 641.

Audit: The final equation 12/(2+t)=4 and speed 6/t=6 are correct. Earlier, however, it explicitly claims that the first 6 miles in 2 hours average 6 mph, whereas that rate is 3 mph. It also labels 12/2 as the elapsed-route average. The incorrect intermediate claim is not explicitly retracted, so a correct final answer does not establish a fully sound explanation.

Full generated text (the opening thinking tag, if enabled, is part of the prompt):

~~~~text
我们来逐步分析题目：

---

**已知条件：**

- 小径总长度：12 英里
- 已走部分：
  - 前 4 英里，用时 1 小时
  - 再走 2 英里，用时 1 小时
- 所以已走总距离 = 4 + 2 = **6 英里**
- 剩余距离 = 12 - 6 = **6 英里**

---

**目标：**

希望**平均速度达到每小时 4 英里**，问走完剩下的 6 英里，速度需要多少？

注意：这里的“平均速度达到每小时 4 英里”是指**整个行程的平均速度**为 4 英里/小时。

---

**步骤 1：计算总时间**

- 前 4 英里用时 1 小时
- 后 2 英里用时 1 小时
- 总时间 = 1 + 1 = **2 小时**

---

**步骤 2：计算总路程**

- 总路程 = 12 英里

---

**步骤 3：计算平均速度**

- 平均速度 = 总路程 / 总时间 = 12 英里 / 2 小时 = **6 英里/小时**

但题目说“她希望平均速度达到每小时 4 英里”，也就是说，**她希望整个行程的平均速度是 4 英里/小时**。

然而，根据已有信息，她实际走完前 6 英里用了 2 小时，平均速度是 6 英里/小时。

现在她要完成剩下的 6 英里，使得**整个行程的平均速度达到 4 英里/小时**。

---

**步骤 4：设剩余路程所需时间为 t 小时**

- 剩余路程 = 6 英里
- 剩余时间 = t 小时
- 总路程 = 12 英里
- 总时间 = 2 + t 小时
- 平均速度 = 12 / (2 + t) = 4 （目标）

解这个方程：

$$
\frac{12}{2 + t} = 4
$$

两边同乘 (2 + t)：

$$
12 = 4(2 + t)
$$

$$
12 = 8 + 4t
$$

$$
4t = 4
$$

$$
t = 1
$$

所以，剩余 6 英里需要 **1 小时**。

---

**步骤 5：求所需速度**

速度 = 路程 / 时间 = 6 英里 / 1 小时 = **6 英里/小时**

---

FINAL: 6
~~~~

[Complete JSON with prompt and token IDs](results/019-zh-off.json)

</details>

<details>
<summary>019-zh-on — correct_reasoning_but_delivery_truncated</summary>

Question: 玛丽莎正在一条长 12 英里的小径上徒步旅行。她用了 1 小时走完前面 4 英里，然后再用一小时走完 2 英里。如果她希望平均速度达到每小时 4 英里，则要走完剩下的距离，她的速度需要达到多少（以英里每小时为单位）？

Reference: 6; prediction: None; score: missing_or_malformed_final; stop: length; generated tokens: 1024.

Audit: Inside thinking, correctly solves 12/(2+t)=4, t=1 and remaining speed 6. It closes thinking and begins repeating the explanation, but reaches 1024 tokens before the visible FINAL line. The primary score is a delivery failure, not evidence of a mathematical inability on this case.

Full generated text (the opening thinking tag, if enabled, is part of the prompt):

~~~~text
我们被问到："玛丽莎正在一条长 12 英里的小径上徒步旅行。她用了 1 小时走完前面 4 英里，然后再用一小时走完 2 英里。如果她希望平均速度达到每小时 4 英里，则要走完剩下的距离，她的速度需要达到多少（以英里每小时为单位）？"

我们需要逐步解答。

首先，总距离 = 12 英里。

她走了前面 4 英里，用了 1 小时。所以速度 = 距离/时间 = 4 英里 / 1 小时 = 4 英里/小时。

然后她走了 2 英里，用了 1 小时。所以速度 = 2 英里 / 1 小时 = 2 英里/小时。

所以到目前为止，她走了 4+2=6 英里，用了 1+1=2 小时。

剩下的距离 = 12 - 6 = 6 英里。

她希望平均速度达到每小时 4 英里。注意：平均速度是指整个行程的平均速度，即总距离除以总时间。

总距离 = 12 英里。

总时间 = 已经用的时间 + 剩余时间。已经用了 2 小时。设剩余时间为 t 小时。

总时间 = 2 + t 小时。

平均速度 = 总距离 / 总时间 = 12 / (2 + t) = 4 英里/小时。

所以 12 / (2 + t) = 4 => 2 + t = 12 / 4 = 3 => t = 3 - 2 = 1 小时。

所以剩余距离 6 英里，需要 1 小时，速度 = 6 英里 / 1 小时 = 6 英里/小时。

因此，她的速度需要达到 6 英里每小时。

检查：总时间 = 2 + 1 = 3 小时，总距离 = 12 英里，平均速度 = 12/3 = 4 英里/小时，符合。

所以答案是 6。

但让我们确保问题没有其他陷阱。问题说："如果她希望平均速度达到每小时 4 英里，则要走完剩下的距离，她的速度需要达到多少（以英里每小时为单位）？" 所以我们需要给出速度。

因此，最终答案是 6。

按照要求，最后一行必须严格使用格式：FINAL: <integer>。所以 FINAL: 6。

但注意：题目要求"将 <integer> 替换为十进制整数，最后一行不要使用逗号、单位或其他文字。" 所以最后一行应该是 "FINAL: 6"。

我们逐步解答，但最终输出只有那一行。

所以，在回答中，我们可以先逐步解释，然后给出最终答案。

但注意：用户说"请逐步解答这道题。回答的最后单独一行必须严格使用此格式：FINAL: <integer>。" 所以我们需要在回答中包含逐步解答，然后最后一行是 FINAL: 6。

因此，我将写出逐步解答，然后最后一行是 FINAL: 6。

现在，逐步解答：

1. 计算已走距离和所用时间：
   已走距离 = 4 英里 + 2 英里 = 6 英里。
   已用时间 = 1 小时 + 1 小时 = 2 小时。

2. 剩余距离 = 总距离 - 已走距离 = 12 英里 - 6 英里 = 6 英里。

3. 设剩余时间为 t 小时，则总时间为 2 + t 小时。
   平均速度 = 总距离 / 总时间 = 12 / (2 + t) = 4 英里/小时。

4. 解方程：12 / (2 + t) = 4 => 2 + t = 12 / 4 = 3 => t = 1 小时。

5. 剩余距离为 6 英里，所需速度为 6 英里 / 1 小时 = 6 英里/小时。

因此，速度需要达到 6 英里每小时。

最终答案：6。

现在，按照格式输出。</think>逐步解答：

1. 计算已走距离和所用时间：
   - 已走距离：4 英里 + 2 英里 = 6 英里。
   - 已用时间：1 小时 + 1 小时 = 2 小时。

2. 计算剩余距离：
   - 总距离为
~~~~

[Complete JSON with prompt and token IDs](results/019-zh-on.json)

</details>

<details>
<summary>047-zh-on — missing_part_of_requested_total</summary>

Question: 约翰买的红色领带数量是蓝色领带数量的两倍。红色领带的价格比蓝色领带的价格高 50%。他花了 200 美元购买每条 40 美元的蓝色领带。他花了多少钱买领带？

Reference: 800; prediction: 600; score: wrong_integer; stop: stop; generated tokens: 735.

Audit: Computes five blue ties, ten red ties and the $60 red-tie price correctly, then returns $600 for red ties alone. It omits the already stated $200 spent on blue ties; requested total is $800. The same omission appears in thinking and the delivered explanation.

Full generated text (the opening thinking tag, if enabled, is part of the prompt):

~~~~text
我们被问到："约翰买的红色领带数量是蓝色领带数量的两倍。红色领带的价格比蓝色领带的价格高 50%。他花了 200 美元购买每条 40 美元的蓝色领带。他花了多少钱买领带？"

我们需要逐步解答。

首先，理解信息：

- 红色领带数量是蓝色领带数量的两倍。设蓝色领带数量为 x，则红色领带数量为 2x。
- 红色领带的价格比蓝色领带的价格高 50%。设蓝色领带价格为 p，则红色领带价格为 p + 0.5p = 1.5p。
- 他花了 200 美元购买每条 40 美元的蓝色领带。这意味着他买了多少条蓝色领带？每条蓝色领带价格是 40 美元，他总共花了 200 美元，所以蓝色领带数量 = 200 / 40 = 5 条。
- 因此，蓝色领带数量 x = 5。
- 那么红色领带数量 = 2x = 10 条。
- 红色领带价格 = 1.5 * 40 = 60 美元。
- 他买了 10 条红色领带，每条 60 美元，所以总花费 = 10 * 60 = 600 美元。

所以答案是 600。

但让我们确认问题："他花了多少钱买领带？" 可能是指总共花了多少钱。所以答案是 600。

逐步解答：

1. 设蓝色领带数量为 x 条。
2. 红色领带数量为 2x 条。
3. 蓝色领带单价为 40 美元。
4. 总花费 200 美元，所以蓝色领带数量 = 200 / 40 = 5 条。
5. 因此 x = 5，红色领带数量 = 10 条。
6. 红色领带价格比蓝色领带高 50%，所以红色领带价格 = 40 * (1 + 0.5) = 40 * 1.5 = 60 美元。
7. 总花费 = 10 * 60 = 600 美元。

最终答案：600。

按照要求，最后一行单独一行：FINAL: 600。</think>设蓝色领带数量为 \(x\) 条，则红色领带数量为 \(2x\) 条。
蓝色领带单价为 40 美元，总花费 200 美元，因此蓝色领带数量为 \(200 \div 40 = 5\) 条。
所以 \(x = 5\)，红色领带数量为 \(2 \times 5 = 10\) 条。
红色领带价格比蓝色领带高 50%，即红色领带价格为 \(40 \times (1 + 0.5) = 60\) 美元。
总花费为 \(10 \times 60 = 600\) 美元。

FINAL: 600
~~~~

[Complete JSON with prompt and token IDs](results/047-zh-on.json)

</details>
