# Evaluation

Sprint 4 evaluation of the local RAG assistant (Issue #17).

This document records how the assistant was measured, what it got wrong, why,
and which changes were made in response. It is a record of an iterative
process, not a single test run: five measured configurations are reported,
including one change that was tried and reverted.

---

## 1. Method

Ten questions were run through the assistant end to end. Five are answerable
from the knowledge base in `data/`; five are not, and must produce the fixed
fallback answer `"I don't know based on the provided documentation."`

The questions were not run by hand through the CLI. `prototypes/evaluation_run.py`
calls the same `answer_query()` the CLI uses, and additionally records the top
retrieval score and the elapsed time per question. This makes every run
reproducible and lets a failure be attributed to a specific layer: a low score
means the similarity threshold rejected the question before the model was
called, a high score with a wrong answer means the model failed on context it
was given.

A second script, `prototypes/inspect_retrieval.py`, prints the chunks retrieved
for a single question at an arbitrary top-K. It is the diagnostic used to tell
a retrieval failure apart from a generation failure.

### Question set design

The set is designed to probe the two defence layers separately.

`src/answer.py` refuses in two different ways. The similarity threshold rejects
a question before the chat model is ever called; the system prompt is supposed
to make the model refuse when the retrieved context does not contain the
answer. A test set made only of obviously off-topic questions would exercise
the threshold and nothing else, and would report a misleadingly high score.

The unanswerable half is therefore split:

- **Off-domain** (sourdough bread, GitHub acquisition) — expected to be caught
  by the threshold.
- **Domain-adjacent** (fine-tuning, mobile platform support, pricing) — expected
  to pass the threshold and to be caught only by the system prompt.

The pricing question is deliberately adversarial: the knowledge base states
that Foundry Local has "no per-token costs", which partially matches a question
about monthly cost without answering it.

Two of the answerable questions (Azure subscription, supported platforms) had
been used during development in the `__main__` blocks of `src/answer.py` and
`src/retrieve.py`. They were kept because they are the knowledge base's
flagship questions, but they were not blind at the time of evaluation.

---

## 2. Final configuration

| Layer | Setting |
|---|---|
| Chat model | `qwen2.5-1.5b` |
| Embedding model | `qwen3-embedding-0.6b` |
| Similarity threshold | `0.5` |
| Top-K | `3` |
| Knowledge base | 21 chunks across 4 files |
| System prompt | Hardened (explicit decision step, three-sentence limit) |

---

## 3. Results

Final run. `score` is the cosine similarity of the best-matching chunk.

| # | Question | Expected | Actual | Score | Time | Pass |
|---|---|---|---|---|---|---|
| 1 | Do I need an Azure subscription to use Foundry Local? | No — runs on local hardware | "No, Foundry Local does not require an Azure subscription. It runs entirely on local hardware..." | 0.835 | 2.8s | ✅ |
| 2 | Which platforms does Foundry Local support? | Windows, macOS on Apple silicon, Linux | "Foundry Local supports Windows, macOS on Apple silicon, and Linux." | 0.775 | 2.4s | ✅ |
| 3 | Which Python version is required, and which package on Windows? | 3.11+, `foundry-local-sdk-winml` | "Python 3.11 or later is required. You should install the `foundry-local-sdk-winml` package on Windows." | 0.556 | 2.8s | ✅ |
| 4 | What runtime does Foundry Local use for inference? | ONNX Runtime | "Triton Inference Server is used by Foundry Local for inference." | 0.823 | 2.4s | ❌ |
| 5 | Is Foundry Local suitable for serving many concurrent users? | No — single user; vLLM/Triton for that | "No, Foundry Local is not designed as a server inference stack for many concurrent users..." | 0.761 | 3.0s | ✅ |
| 6 | How do I make sourdough bread? | Fallback | Fallback | 0.320 | 0.3s | ✅ |
| 7 | Which company acquired GitHub? | Fallback | Fallback | 0.402 | 0.3s | ✅ |
| 8 | How do I fine-tune a model in Foundry Local? | Fallback | "Fine-tuning a model in Foundry Local involves downloading the model from the catalog... and loading it into memory..." | 0.803 | 4.2s | ❌ |
| 9 | Does Foundry Local support Android or iOS? | Fallback | Fallback | 0.778 | 2.4s | ✅ |
| 10 | How much does Foundry Local cost per month? | Fallback | Fallback | 0.620 | 2.3s | ✅ |

**Result: 8 / 10.** Both failures are answered incorrectly with confidence
rather than refused, which is the more damaging failure mode.

### How the score changed across configurations

| Stage | Change | Score |
|---|---|---|
| 0 | Baseline: `qwen2.5-0.5b`, threshold `0.6` | 5 / 10 (+1 partial) |
| 1 | Threshold `0.6` → `0.5` | 6 / 10 (+1 partial) |
| 2 | Knowledge base: split multi-topic paragraph | 6 / 10 |
| 3 | Chat model `qwen2.5-0.5b` → `qwen2.5-1.5b` | 7 / 10 |
| 4 | System prompt hardened | **8 / 10** |

Stage 2 did not change the score. It was made in response to a correct
diagnosis but did not fix the problem it targeted; see §4.2.

---

## 4. Failure analysis

Four distinct root causes were isolated, each at a different layer. Two were
fixed, two remain open.

### 4.1 Threshold set too high — fixed

Question 3 scored 0.556 and was rejected before the model was called, even
though the knowledge base answers it directly. The question carries two intents
("which Python version" and "which package"), so the averaged query vector
matches no single paragraph strongly.

The measured score distribution showed a wide empty band: the highest
off-domain question scored 0.402, the wrongly rejected question 0.556. The
threshold was moved to 0.50, the middle of that gap, leaving roughly 0.1 of
margin on both sides. Choosing 0.55 would have left a margin of 0.004.

Effect: question 3 passes. No other question changed behaviour, as predicted —
every other score lies either below 0.42 or above 0.62.

### 4.2 Retrieval does not surface the answering paragraph — open

Question 4 is answered verbatim by one paragraph in
`data/what_is_foundry_local.md`: *"Foundry Local runs inference through ONNX
Runtime."* That paragraph is **not retrieved**, and not even in the top 8 of 21
chunks. The eight chunks that outrank it do not answer the question.

The first hypothesis was that the paragraph was multi-topic — it also covered
package size and model caching — which violates the authoring rule set in
Issue #10 ("one topic per paragraph") and dilutes its embedding. The paragraph
was split in two and the database rebuilt. **The paragraph still did not enter
the top 8.** The diagnosis was right, the fix was not.

The measured score spread explains why. For question 4 the top eight chunks
span 0.823 down to 0.767 — a range of 0.056 across eight paragraphs. Across the
whole evaluation, the answerable and unanswerable score ranges overlap almost
completely:

```
answerable:     0.835  0.775  0.761  0.556
unanswerable:          0.803  0.778  0.620      0.402  0.320
```

The unanswerable fine-tuning question (0.803) outranks the answerable platforms
question (0.775). **Above roughly 0.75, the similarity score carries almost no
discriminating information on this knowledge base.** Every chunk describes one
product in a similar prose register, so every chunk is somewhat similar to every
query. The threshold works only because genuinely off-domain questions fall far
away, at 0.32–0.40.

This is a limit of the embedding model on this corpus, not of any single
paragraph. It cannot be fixed by rewriting documents.

### 4.3 Generation errors on retrieved context — fixed

With `qwen2.5-0.5b`, question 1 produced *"Yes, you do not need an Azure
subscription"* — the fact correct, the polarity contradicting it — and question
5 inverted the answer entirely, replying "Yes" where the context says Foundry
Local is not designed for concurrent users. In both cases retrieval had placed
the correct paragraph first.

Moving to `qwen2.5-1.5b` fixed question 1 outright. Question 5 changed from a
wrong answer to a refusal, and was then fixed by the prompt change in §4.4.

### 4.4 Ungrounded generation — partially fixed, open

Question 8 asks how to fine-tune a model. The knowledge base contains nothing
about fine-tuning, but the question scores 0.803 because it is semantically
close to the `download` / `load` paragraph in `data/getting_started.md`. The
threshold cannot catch this: **a high similarity score does not mean the
context contains the answer.**

The original system prompt stated the refusal rule but gave the model no
procedure for applying it. It was rewritten to add an explicit decision step
("first decide whether the context explicitly states the answer"), to name the
failure mode ("being about a related topic is not enough"), to forbid
describing steps not present in the context, and to cap answers at three
sentences.

The change had two effects, neither of them the intended one:

- **Question 5 was fixed.** The model had been refusing a question whose answer
  the context states indirectly ("not designed as a server inference stack").
  The explicit decision step gave it licence to treat an indirect statement as
  an answer. Not every refusal comes from missing information; some come from
  the model being unsure whether it is permitted to answer.
- **Question 8 was not fixed.** The answer shrank from seven steps to three
  sentences but remained ungrounded.
- **Question 4 became worse.** The answer went from a hedge ("its own internal
  infrastructure") to a confident false claim ("Triton Inference Server is used
  by Foundry Local"). Instructing the model to use only what the context states
  made it more extractive — and extraction from the wrong paragraph produces a
  crisper wrong answer.

Question 8's remaining failure changed character and is worth stating precisely.
The model no longer invents facts: `download` and `load` are both genuinely in
the context. It assembles real elements into a claim the documentation never
makes. This is a *composition* failure rather than a fabrication, and the
prompt rule ("never describe a step not written in the context") is not
technically violated by it.

Scaling the generator made this worse before the prompt change: `qwen2.5-1.5b`
produced a seven-step, markdown-formatted fine-tuning guide complete with
"validation set" and "learning rates", where `qwen2.5-0.5b` had produced three
vague sentences. **A larger generator did not improve grounding; it made
ungrounded output more convincing.**

---

## 5. Reverted experiment: query instruction prefix

`qwen3-embedding-0.6b` is instruction-tuned. Models in this family are trained
asymmetrically: documents are embedded as plain text, queries are prefixed with
a task instruction. The project embeds both sides as plain text, which was a
plausible explanation for the poor discrimination described in §4.2.

Two prefixes were tested against the unmodified baseline. Only the query side
changes, so no re-ingestion is required.

| Measurement | No prefix (baseline) | Domain-named prefix | Neutral prefix |
|---|---|---|---|
| Off-domain floor (sourdough) | **0.320** | 0.462 | 0.354 |
| Domain-adjacent (fine-tuning) | 0.803 | 0.736 | 0.791 |
| Score spread, question 4 top-8 | **0.056** | 0.066 | 0.035 |
| Answering paragraph in top 8 | no | no | no |

The first prefix — *"Given a question about Foundry Local, retrieve the
documentation paragraph that answers it"* — raised the off-domain floor by
0.14, cutting the threshold's safety margin from 0.18 to 0.038. The instruction
text itself contained the words common to every document in the corpus, pulling
every query, including the bread question, towards the knowledge base. The
apparent improvement on the fine-tuning question came from the same artefact.

A domain-neutral prefix removed that confound: the off-domain floor returned to
0.354 and the fine-tuning score returned to 0.791 — that is, the earlier gain
disappeared along with the artefact. Discrimination did not improve, and the
score spread narrowed further, to 0.035.

The baseline is better on both metrics that matter, so the change was reverted.
The experiment is recorded because the negative result is informative: query
formatting is not the cause of the discrimination problem in §4.2.

---

## 6. Reproducibility

`qwen2.5-0.5b` was not reproducible on this workload. Question 1 produced two
different answers across four runs — twice a correct-but-contradictory answer,
twice a refusal — with byte-identical retrieval each time.

`qwen2.5-1.5b` was run three times consecutively and produced byte-identical
answers to all ten questions, varying only in latency.

Decoding is greedy in both cases, so the difference is not sampling. The likely
cause is that floating-point results in the hardware-accelerated execution path
vary in their last digits between runs. With `qwen2.5-0.5b` the margin between
the top two candidate tokens was small enough for that noise to change which
token won; with `qwen2.5-1.5b` the margin is wider than the noise.

**Reproducibility here is a property of the model's confidence, not of the
decoder.** This has a practical consequence for evaluation: with the 0.5b model
a single run proved nothing and every result needed repetition, whereas the
1.5b results can be certified from one run.

Retrieval was fully deterministic throughout: identical scores to three decimal
places across all runs in every configuration.

---

## 7. Performance

| Configuration | Typical answer | Longest answer |
|---|---|---|
| `qwen2.5-0.5b` | 0.8 – 1.5s | 3.0s |
| `qwen2.5-1.5b` | 2.0 – 3.3s | 12.0s (before prompt hardening) |

The project plan targets 1–3 seconds per answer. The final configuration sits
at the top of that band. Latency scales with output length rather than with
question difficulty, which produced a perverse result before the prompt change:
the slowest answer in the set (11.8s) was the fully hallucinated fine-tuning
guide. The three-sentence limit brought that case down to 4.2s.

Questions rejected by the threshold return in 0.3s, confirming that the check
short-circuits before the chat model is called.

---

## 8. Defects found during evaluation

**`EMBEDDING_MODEL` is defined twice**, in `src/ingest.py` and
`src/retrieve.py`. Changing one without the other would embed queries with a
different model than the stored chunks. Nothing detects this: `zip(vec_a, vec_b)`
in `cosine_similarity` stops at the shorter sequence, so vectors of different
dimensions are silently compared over their common prefix and produce
meaningless scores without raising an error.

Fixed in #18. The copy in `src/retrieve.py` turned out to be dead code — the
module never used it — so it was deleted rather than abstracted, leaving
`src/ingest.py` as the single owner. `cosine_similarity` now raises `ValueError`
on a length mismatch, naming the cause and the fix in the message.

**No test pins the threshold boundary.** `tests/test_answer.py` uses 0.32 for
the low case and 0.83 for the high case, both far from the threshold, so
changing `SIMILARITY_THRESHOLD` from 0.6 to 0.5 passed the suite silently.

Fixed in #18 with two tests written against the constant (a score equal to the
threshold reaches the model, a score just below it does not) and one that pins
the calibrated value itself, so changing it requires a deliberate edit.

---

## 9. Open issues and recommended next steps

**Question 4 — the answering paragraph is not retrieved.** The only remaining
lever in the Foundry Local catalogue is `qwen3-embedding-8b`. It was not tested:
an 8-billion-parameter embedding model to search 21 paragraphs contradicts the
project's premise of lightweight on-device operation, and a `qwen2.5-7b`
download had already failed to complete on this machine. A more proportionate
direction would be a hybrid of keyword and vector matching, where an exact term
like "ONNX Runtime" can outrank a semantically diffuse match.

**Question 8 — composition hallucination.** Prompt hardening reduced the
severity but did not eliminate it. A second grounding check — asking the model
to first quote the sentence that answers the question, and returning the
fallback when it cannot — would attack the mechanism directly rather than
instructing against the outcome.

**Model selection is constrained by the device.** `qwen2.5-7b` could not be
downloaded on this machine, which is why the chat model ladder stopped at 1.5b.
For a product that runs on end-user hardware, which model can actually be
obtained and loaded is part of the result, not a footnote to it.

**The question set is now a development set.** Four of the five configurations
above were chosen while looking at these ten questions, so the 8/10 figure
measures a system that has been tuned against them. A second set of ten
questions, written to the same design and run once against the frozen
configuration, is needed before the number can be read as a general quality
estimate.
