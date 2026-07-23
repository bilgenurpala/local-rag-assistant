# Technical Report — Local RAG Assistant

Microsoft internship capstone project.
Repository: [bilgenurpala/local-rag-assistant](https://github.com/bilgenurpala/local-rag-assistant)

---

## 1. Summary

This project builds a question-answering assistant that answers questions about
Microsoft Foundry Local's documentation using only that documentation, and runs
entirely on one device. Retrieval, generation and storage are all local: after a
one-time model download there is no network call, no cloud account and no API
key.

The system follows the Retrieval-Augmented Generation pattern. A question is
embedded, compared against pre-embedded document chunks stored in SQLite, and
the closest chunks are handed to a local chat model as context with an
instruction to answer from that context alone. When nothing relevant is found,
the assistant returns a fixed refusal rather than guessing.

Measured against a ten-question test set, the final configuration answers 8 of
10 correctly. Both failures are confident wrong answers rather than refusals,
which is the more damaging failure mode and is the project's main open problem.
Section 7 explains why neither is fixable by tuning what is already there.

The engineering result of most interest is not the score. It is the finding
that on a single-product corpus the similarity score stops discriminating above
roughly 0.75, and that scaling the generator from 0.5B to 1.5B parameters made
ungrounded answers more convincing without making them more grounded. Both are
developed in section 7.

---

## 2. Problem and goals

A language model answers from what it saw during training. For a narrow,
fast-moving domain — the internal details of one specific product — that
produces two failures: the model does not know, and when it does not know it
tends to invent something plausible. Retraining the model on the target
documents was out of scope for a project of this size and duration.

The goals were therefore:

1. Answer questions about Foundry Local from a controlled document set.
2. Refuse, explicitly, when the document set does not contain the answer.
3. Run fully offline on consumer hardware.
4. Do all of the above with a process — issues, branches, tests, journal — that
   would hold up in a professional setting.

Goal 2 is the one that makes the project a RAG project rather than a chatbot.
An assistant that answers everything is easy; an assistant that reliably knows
the boundary of its own knowledge base is the hard part, and it is where both
remaining failures sit.

---

## 3. Approach

### Why RAG

RAG addresses the problem without touching the model's weights. The relevant
text is supplied at question time in three steps — retrieve the closest chunks,
augment the prompt with them, generate an answer constrained to them. Because
every answer is tied to a retrieved passage, the answer can in principle be
traced back to its source, and the refusal rule has something concrete to test
against.

### Why on-device

Running through Foundry Local rather than a hosted API was a deliberate
constraint, not a convenience. Documents and questions never leave the machine,
there is no per-request cost, and behaviour does not change underneath the
project when a provider updates a model. The trade-off is real: the largest
models are unavailable, and section 7 shows that the ceiling this imposes is
visible in the results.

The full design rationale and the two data-flow diagrams are in
[`architecture.md`](architecture.md).

---

## 4. System design

| Component | Responsibility | File |
|---|---|---|
| Ingestion | Chunk documents, embed, store | `src/ingest.py` |
| Data layer | Persist text chunks and vectors | SQLite (`rag.db`) |
| Retrieval | Embed the query, score chunks, return top-K | `src/retrieve.py` |
| Generation | Build context, apply the grounding rule, call the model | `src/answer.py` |
| Interface | Interactive question loop | `src/main.py` |

**Preparation.** `ingest.py` reads every `.md` and `.txt` file in `data/`,
splits each on blank lines into paragraph chunks, embeds each chunk with
`qwen3-embedding-0.6b`, and writes `(source, content, embedding)` rows to SQLite
with the vector serialised as JSON text. The source filename is carried through
retrieval into the final answer. The table is cleared and rebuilt on every run,
so ingestion is idempotent.

**Runtime.** `answer_query()` embeds the question, scores it against every
stored chunk with a hand-written cosine similarity, and takes the top 3. If the
best score is below the similarity threshold, it returns the fixed fallback
string without calling the chat model at all. Otherwise the three chunks are
joined into one context block, placed in a system message alongside the
grounding instruction, and sent to `qwen2.5-1.5b` with the question as the user
message.

There are therefore **two independent defence layers**: the threshold, which
acts before the model, and the system prompt, which acts inside it. The
evaluation set was designed to exercise them separately (section 6), because a
test set that only triggers the first would report a misleadingly high score.

### Final configuration

| Layer | Setting |
|---|---|
| Chat model | `qwen2.5-1.5b` |
| Embedding model | `qwen3-embedding-0.6b` (1024-dim) |
| Similarity threshold | `0.5` |
| Top-K | `3` |
| Knowledge base | 26 chunks across 5 files |
| Vector storage | JSON text in SQLite, brute-force cosine similarity |
| System prompt | Explicit decision step, three-sentence limit, source labels |

Every one of these values except Top-K was changed at least once as a result of
measurement. The path is in section 6.

---

## 5. Implementation decisions

The full record with context and outcomes is in
[`engineering-journal.md`](engineering-journal.md). The decisions that shaped
the system most:

**Python 3.12 rather than the machine default 3.14.** Foundry Local depends on
native `onnxruntime` libraries, and native ML wheels lag behind new Python
releases. Choosing the established version avoided install failures that would
have been diagnosed as SDK problems.

**Cosine similarity written by hand rather than imported.** Similarity is the
single concept the whole retrieval step rests on. Implementing it — dot product
over the product of the norms — made it clear that direction, not magnitude,
carries the meaning. It also kept the proof-of-concept dependency-free. The
function was later promoted from the prototype into `src/retrieve.py`.

**Vectors stored as JSON text in SQLite.** SQLite columns hold simple types, not
Python lists, so each vector is serialised with `json.dumps` and parsed back
with `json.loads`. At 26 chunks a dedicated vector database would have added a
dependency and a deployment step in exchange for nothing measurable.

**Brute-force search.** Every chunk is scored on every query. This is
deliberate: it is exact, it has no index to rebuild, and at this scale it is not
the bottleneck. Retrieval accounts for a small fraction of a 2–3 second answer.

**The embedding client is a parameter, not a global.** `get_top_chunks(query,
client)` receives the client rather than creating one. Loading a model is
expensive and the CLI calls this function once per question, so the client is
created once at startup and reused. The same choice makes retrieval testable: a
fake client can be passed in and the scoring logic tested without loading a
model.

**The knowledge base was authored, not scraped.** Five short Markdown files were
compiled from the official documentation under three rules: no headings, one
topic per paragraph, every paragraph self-contained and naming "Foundry Local"
explicitly rather than using pronouns. The reasoning is that the chunker splits
on blank lines, so whatever a paragraph contains is exactly what the embedding
model sees and what the chat model receives. **Document formatting is retrieval
design.** This was confirmed during Sprint 2: a paragraph that listed operating
systems without ever using the word "platforms" failed to retrieve for "which
platforms does Foundry Local support?", and entered the top 3 after a one-phrase
rewrite.

**Idempotent ingestion.** An earlier prototype accumulated duplicate rows on
each run. `setup_database()` now clears the table before inserting, so the same
input always produces the same database. Rebuilding ~20 rows is cheap; detecting
and updating changed rows would have been more code for no benefit at this
scale.

**Grounding lives in the system message.** The retrieved context and the rule
that constrains the model are placed in the system role, separate from the
user's question, so the instruction is not competing with the question for the
model's attention.

---

## 6. Evaluation

Full method, per-question results and failure analysis are in
[`evaluation.md`](evaluation.md). Summarised here.

Ten questions: five answerable from the knowledge base, five not. The
unanswerable half is split deliberately. Two are off-domain (sourdough bread,
the GitHub acquisition) and should be stopped by the threshold. Three are
domain-adjacent (fine-tuning, mobile support, monthly price) and are expected to
clear the threshold, so that only the system prompt can catch them. The pricing
question is adversarial by design: the knowledge base says Foundry Local has "no
per-token costs", which partially matches a question about monthly cost without
answering it.

Questions were run through `prototypes/evaluation_run.py`, which calls the same
`answer_query()` the CLI uses and additionally records the top retrieval score
and elapsed time. Recording the score is what makes a failure attributable: a
low score means the threshold rejected the question before the model ran, a high
score with a wrong answer means the model failed on context it was given.

### The path to 8/10

| Stage | Change | Score |
|---|---|---|
| 0 | Baseline: `qwen2.5-0.5b`, threshold `0.6` | 5 / 10 (+1 partial) |
| 1 | Threshold `0.6` → `0.5` | 6 / 10 (+1 partial) |
| 2 | Knowledge base: split a multi-topic paragraph | 6 / 10 |
| 3 | Chat model `qwen2.5-0.5b` → `qwen2.5-1.5b` | 7 / 10 |
| 4 | System prompt hardened | **8 / 10** |

Stage 1 was not a guess. One answerable question scored 0.556 and was being
rejected, while the highest-scoring off-domain question reached 0.402. The
threshold was moved to the middle of that empty band, leaving roughly 0.1 of
margin on each side; 0.55 would have left 0.004. No other question changed
behaviour, as predicted.

Stage 2 changed nothing. The hypothesis — that a multi-topic paragraph had a
diluted embedding — was a correct reading of the authoring rule but was not the
cause; section 7 explains what was. It is reported because the diagnosis was
right and the fix still failed, which is worth distinguishing from a wrong
diagnosis.

### Performance

| Configuration | Typical answer | Longest |
|---|---|---|
| `qwen2.5-0.5b` | 0.8 – 1.5s | 3.0s |
| `qwen2.5-1.5b` | 2.0 – 3.3s | 12.0s before the prompt change, 4.2s after |

The project plan targeted 1–3 seconds. The final configuration sits at the top
of that band. Latency scales with output length rather than question difficulty,
which produced a perverse result before the prompt change: the slowest answer in
the whole set was the fully ungrounded fine-tuning guide. Questions rejected by
the threshold return in 0.3 seconds, which independently confirms that the check
short-circuits before the chat model is invoked.

---

## 7. Findings

These are the results that generalise beyond this repository.

### Similarity scores stop discriminating on a single-product corpus

Across the whole evaluation the answerable and unanswerable score ranges overlap
almost completely:

```
answerable:     0.835  0.775  0.761  0.556
unanswerable:          0.803  0.778  0.620      0.402  0.320
```

An unanswerable question outranks an answerable one. For the question the system
gets wrong, the top eight chunks span 0.823 down to 0.767 — a range of 0.056
across eight paragraphs, one of which answers the question verbatim and does not
appear in the top eight at all.

Every chunk in this knowledge base describes one product in one prose register,
so every chunk is somewhat similar to every query. **Above roughly 0.75 the
score carries almost no information.** The threshold works not because it
separates relevant from irrelevant, but because genuinely off-domain questions
land far away at 0.32–0.40. It is a domain filter, not a relevance filter, and
it should not be described as the latter.

This is a property of the embedding model on this corpus. It cannot be fixed by
rewriting documents, which is why stage 2 above changed nothing.

### A larger generator made ungrounded output more convincing, not more grounded

The fine-tuning question is answered by nothing in the knowledge base but scores
0.803 because it is semantically close to the paragraph about downloading and
loading models. With `qwen2.5-0.5b` the model produced three vague sentences.
With `qwen2.5-1.5b` it produced a seven-step, formatted guide complete with
"validation set" and "learning rates".

The larger model fixed two genuine generation errors — a self-contradictory
answer and an inverted one — so the upgrade was correct. But on the grounding
failure it did not help; it raised the fluency of a wrong answer. **Scaling the
generator improves generation, not grounding.** Grounding is a retrieval and
prompt property.

### Hardening the prompt fixed one question and broke another

The rewritten system prompt added an explicit decision step, named the failure
mode, forbade describing steps absent from the context, and capped answers at
three sentences. It had three effects, only one of them intended:

- A question that had been *wrongly refused* was fixed. The context answered it
  indirectly and the model had been unsure whether it was permitted to answer.
  Not every refusal comes from missing information; some come from the model
  being unsure of its licence to speak.
- The fine-tuning question was not fixed. The answer shrank but stayed
  ungrounded.
- A third question got *worse*, moving from a hedge to a confident false claim.
  Instructing the model to use only what the context states made it more
  extractive, and extraction from the wrong paragraph produces a crisper wrong
  answer.

Prompt changes are not local. Each one should be re-measured across the whole
set, not only on the question that motivated it.

### The remaining failure is composition, not fabrication

The fine-tuning answer invents no facts. Downloading and loading are both
genuinely in the retrieved context. The model assembles real elements into a
claim the documentation never makes. The prompt rule — never describe a step not
written in the context — is not technically violated. This distinction matters
because instruction-based defences target fabrication, and composition slips
underneath them.

### Reproducibility was a property of the model's confidence

`qwen2.5-0.5b` produced two different answers to the same question across four
runs, with byte-identical retrieval each time. `qwen2.5-1.5b` produced
byte-identical answers to all ten questions across three runs. Decoding is
greedy in both cases, so this is not sampling. The likely cause is
floating-point variation in the hardware-accelerated path: with the smaller
model the margin between the top two candidate tokens was narrow enough for that
noise to change the winner.

The practical consequence is methodological. With the 0.5B model a single run
proved nothing and every result had to be repeated; with the 1.5B model a single
run can be certified. Retrieval was deterministic throughout, to three decimal
places, in every configuration.

### A negative result worth keeping

`qwen3-embedding-0.6b` is instruction-tuned, and models in that family are
normally trained asymmetrically — documents as plain text, queries prefixed with
a task instruction. This project embeds both sides as plain text, which was a
plausible explanation for the discrimination problem above, and only the query
side would need to change, so no re-ingestion was required.

Two prefixes were tested. The first appeared to help and did not: its
instruction text contained the words common to every document in the corpus,
which pulled every query — including the bread question — towards the knowledge
base, raising the off-domain floor from 0.320 to 0.462 and cutting the
threshold's safety margin from 0.18 to 0.038. A domain-neutral prefix removed
that artefact, and the apparent gain disappeared with it. Score spread did not
improve. The change was reverted.

The result is recorded because it rules something out: query formatting is not
the cause of the discrimination problem.

---

## 8. Limitations

- **Both remaining failures are confident wrong answers, not refusals.** For a
  documentation assistant this is worse than a refusal, because a user cannot
  tell the failure from a success.
- **Source attribution identifies retrieved files, not exact sentences.** The
  filename now travels from ingestion through retrieval and appears in the
  answer. The deterministic list makes answers auditable, but it does not prove
  that every generated claim is supported by those files.
- **Retrieval is purely semantic.** An exact term in the question cannot outrank
  a semantically diffuse match.
- **The original test set is a development set.** Four of the five configuration
  changes were chosen while looking at those ten questions. A later frozen blind
  set scored 7/10 and confirms that grounding remains the main weakness.
- **Model choice was constrained by the hardware.** `qwen2.5-7b` could not be
  downloaded on the development machine, which is why the ladder stopped at
  1.5B. For software intended to run on end-user hardware, which model can
  actually be obtained and loaded is part of the result, not a footnote to it.
- **Only the Windows path is tested.** The SDK is installed here as
  `foundry-local-sdk-winml`; other platforms use a different package, which was
  not verified.
- **Single user, single machine.** Every chunk is scanned on every query. This is
  correct at 26 chunks and is not intended to scale.

---

## 9. Future work

In the order the evidence supports:

1. **Hybrid retrieval.** The strongest lever against the discrimination problem
   in section 7, and against the one question whose answering paragraph is never
   retrieved. Combining keyword matching with vector similarity would let an
   exact term such as "ONNX Runtime" outrank a semantically diffuse match. The
   remaining catalogue alternative, `qwen3-embedding-8b`, was rejected as
   disproportionate: an 8-billion-parameter model to search 21 paragraphs
   contradicts the project's premise, and a 7B download had already failed on
   this machine.
2. **A quote-first grounding check.** Ask the model to first quote the sentence
   that answers the question and return the fallback when it cannot. This
   attacks the composition failure mechanically rather than by instruction,
   which section 7 shows instruction alone does not reach.
3. **Evidence-level citations.** Source filenames are now present. The next step
   is to associate each generated claim with the exact supporting passage.
4. **Web interface.** A page of Foundry Local documentation with an assistant
   beside it, so a reader who gets stuck on a term can ask in place. A thin
   shell over `answer_query()`; the CLI already provides everything it needs.

---

## 10. Process

The project ran as five sprints tracked on a GitHub Projects board, with each
work item as an issue. Every issue was implemented on its own branch and merged
through a pull request linked with `Closes #N`. Commits follow Conventional
Commits.

Automated tests live under `tests/` and run with `pytest`. They cover chunking,
retrieval scoring, the similarity threshold boundary and context passing. Two
defects were found during evaluation and fixed with tests written against them:
the embedding model name had been defined in two files, where changing one alone
would have silently compared vectors of different dimensions — `zip()` stops at
the shorter sequence and raises nothing — and no test pinned the threshold, so
changing it from 0.6 to 0.5 had passed the suite silently.

The engineering journal records decisions with their context, rationale and
outcome rather than a narrative of the work. It was written as it went, which is
why this report could be assembled from it rather than reconstructed afterwards.

---

## 11. Conclusion

The system meets its functional goals: it answers questions about Foundry Local
from a controlled document set, refuses when the set does not contain the
answer, and runs offline on a single machine within the 1–3 second latency
target.

Final hardening added deterministic source filenames and a frozen blind
evaluation. The blind set scored 7/10, so the system refuses many unsupported
questions but does not yet do so reliably for every domain-adjacent question.

The more useful outcome is where it fails and why. Both remaining failures are
retrieval and grounding problems, and neither is reachable by the levers the
project has left — a larger generator makes ungrounded answers more fluent, a
better-worded document cannot fix a score band that carries no information, and
a stricter prompt trades one failure for another. That is a sharper result than
8/10, and it points at the two changes worth making next: hybrid retrieval, and
a grounding check that verifies rather than instructs.
