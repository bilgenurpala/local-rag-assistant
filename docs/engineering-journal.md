# Engineering Journal

This journal records technical decisions and their rationale, not a tutorial log.
Each entry captures *what* was decided, *why*, and the *outcome*.

---

## Sprint 0 — Setup & Infrastructure

### Decision: Use Python 3.12 instead of the system default 3.14
**Context:** The machine's default interpreter is Python 3.14. Foundry Local
depends on native libraries (onnxruntime-core, onnxruntime-genai-core).
**Decision:** Run the project on Python 3.12 via a dedicated virtual environment
(py -3.12 -m venv .venv), leaving 3.14 untouched as the system default.
**Rationale:** Native ML wheels often lag behind the newest Python release.
Choosing the established 3.12 avoids missing-wheel install failures.
**Outcome:** Confirmed correct — onnxruntime-core 1.26.0 and
onnxruntime-genai-core 0.14.1 installed without issues on 3.12.

### Decision: Install the WinML SDK variant
**Decision:** Installed oundry-local-sdk-winml (1.2.3) rather than the
cross-platform oundry-local-sdk.
**Rationale:** On Windows, the WinML variant is the official recommendation; it
enables hardware acceleration (NPU/GPU) via DirectML. The two variants conflict
(different onnxruntime-core pins), so only one is installed per environment.
**Outcome:** Verification returned non-empty output, confirming the DX12 GPU
path works.

### Decision: Isolated venv + pinned requirements
**Decision:** All dependencies live in a project-local .venv, frozen into

equirements.txt via pip freeze.
**Rationale:** Reproducibility — anyone cloning the repo can recreate the exact
environment with pip install -r requirements.txt.

### Decision: Use qwen2.5-0.5b for the setup verification
**Decision:** Verified the install with the small qwen2.5-0.5b model.
**Rationale:** The goal was to prove the end-to-end chain works
(initialize -> download -> load -> chat -> unload), not to evaluate quality.
A small, fast model gives quick feedback.
**Outcome:** Received a coherent reply offline — Foundry Local confirmed working.

### Repository conventions established
- Conventional Commits (feat / fix / docs / test / chore).
- .gitignore excludes .venv, generated *.db files, and model artifacts.
- All repository content (code, docs, README, LICENSE) is in English.

### Challenges encountered
- A project path containing spaces and a special dash broke shell commands.
  Resolved by using a clean path: C:\Programming\ai-engineering\local-rag-assistant.
- Multi-line file-creation commands failed in cmd (worked only in PowerShell).
  Resolved by confirming the active shell before running shell-specific syntax.


---

## Sprint 1 — Foundations & Component Proofs

### Clarification: Foundry Local CLI vs. Python SDK
**Context:** Running "foundry service status" in PowerShell failed with
"term not recognized." This looked alarming but was not a broken install.
**Clarification:** Foundry Local exposes two separate interfaces — a "foundry"
command-line tool (a distinct install, not on PATH here) and the Python SDK
(foundry_local_sdk, already installed in Sprint 0). They talk to the same engine.
**Resolution:** No fix needed. The project deliberately uses the Python SDK
directly (a locked-in decision: "Foundry usage — Python SDK, serverless"), so
the missing CLI is irrelevant. The catalog was inspected from Python instead.

### Decision: Write the architecture doc as narrative + diagrams (Issue #5)
**Decision:** Authored docs/architecture.md with a "Why RAG" narrative
(retrieve -> augment -> generate), a component table, two color-coded Mermaid
diagrams (ingestion pipeline + runtime loop), and design principles.
**Rationale:** The Issue asked for both the RAG rationale and the diagram. The
narrative doubles as source material for the final "what I learned" video, so it
was written to be read aloud, not just skimmed.
**Outcome:** Merged to main via PR #21 (Closes #5). Diagrams render natively on
GitHub.

### Decision: Use qwen3-embedding-0.6b as the embedding model (Issue #6)
**Context:** The device catalog (list_models) exposed 46 models; exactly two
advertise the "embedding" capability: qwen3-embedding-0.6b and qwen3-embedding-8b.
**Decision:** Chose the smaller qwen3-embedding-0.6b.
**Rationale:** Speed priority, consistent with the small-model line already set
by the chat model (qwen2.5-0.5b), and matches the internship spec's example.
Upgrading to the 8b variant later is a one-line change if accuracy proves
insufficient.
**Outcome:** Confirmed working — produced a 1024-dimension float vector for a
sample sentence.

### Technique learned: probing an unfamiliar SDK with dir() and type()
**Context:** The SDK version (1.2.3) uses a newer API than most online examples,
so guessing method names failed repeatedly.
**Approach:** Instead of guessing, inspected live objects — dir(obj) to list
available methods, type(obj) to confirm shapes — via small throwaway scripts
(prototypes/explore_catalog.py, prototypes/explore_embedding.py). These are kept
in the repo as learning artifacts.
**Outcome:** This is how list_models, the "embedding" capability field, and the
correct generate_embedding method were all discovered.

### Challenges encountered (Issue #6)
- **AttributeError: 'NoneType' object has no attribute 'download'.** Root cause:
  get_model was given a wrong alias, so it returned None. Lesson: a NoneType
  attribute error points one line up — check what got assigned to the variable.
- **AttributeError: 'EmbeddingClient' object has no attribute 'create'.** The
  OpenAI-style client.create() does not exist here. dir(client) revealed the
  real methods: generate_embedding (single string) and generate_embeddings (list).
- **ValueError: Input must be a non-empty string.** Raised inside the SDK when a
  single string was passed to the plural generate_embeddings, which expects a
  list. Fixed by using the singular generate_embedding for one text.
- **PowerShell blocked venv activation** (execution policy). Resolved with
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned.

### Decision: Implement cosine similarity by hand (Issue #7)
**Context:** The retrieval step needs to measure how close two embedding vectors
are. A library (e.g. numpy) could do this, but this is the single most important
concept in RAG.
**Decision:** Wrote cosine_similarity() manually — dot product divided by the
product of both vector norms.
**Rationale:** Understanding the math (direction, not magnitude, determines
semantic closeness) matters more here than convenience. Keeps the POC dependency-free.
**Outcome:** Confirmed working. For the query "What do cats like to drink?", the
sentence "Cats drink milk." scored highest (0.713) despite sharing no word with
the query — proving semantic (not keyword) search works.

### Challenges encountered (Issue #7)
- **Model 'qwen3-embedding-0.6b' is not loaded.** Skipping model.download() left
  the model not fully ready. Fixed by calling download() before load(), matching
  the working pattern from embedding_poc.py (#6). download() is cheap once cached.
- **NameError: name 'client' is not defined.** An edit accidentally removed the
  client = model.get_embedding_client() line. Lesson: NameError means the variable
  was never created (distinct from a NoneType error). Re-check the file with git
  diff after edits.
- **VS Code save conflict.** The on-disk and in-editor versions diverged; resolved
  via Compare, keeping the complete version.
- **Silent exit (no output).** Debugged by adding trace prints to locate where
  execution stopped.

### Decision: Store vectors as JSON text in SQLite (Issue #8)
**Context:** Embedding vectors are lists of floats, but SQLite columns hold only
simple types (text, integer, blob), not Python lists.
**Decision:** Serialize each vector to JSON text with json.dumps on write, and
parse it back with json.loads on read. Table: chunks(id, content, embedding).
**Rationale:** For this project's small scale, JSON-in-a-TEXT-column is simple and
dependency-free; a dedicated vector database would be overkill. Parameterized
INSERT (VALUES (?, ?)) is used to insert values safely.
**Outcome:** Confirmed working — a row (text + vector) was written and read back,
with the vector correctly restored to a list of numbers.

### Challenges encountered (Issue #8)
- **Silent exit (no output).** The file hadn't been saved; the script ran an empty
  version. Resolved by saving in VS Code, then re-running.
- **Duplicate rows on re-run.** Each run executes INSERT again, so repeated runs
  accumulated identical rows. Not a bug — it confirms persistence. A re-population
  strategy for ingest.py will be decided in Sprint 2.

### Decision: Use a system message to constrain the model (Issue #9)
**Context:** A RAG answer must come from retrieved context, not the model's own
guesses. A small model (qwen2.5-0.5b) is inconsistent when asked about unknown facts.
**Decision:** Put the retrieved context and a rule — "answer using ONLY the context;
if it's not there, say I don't know" — in a system message, separate from the user's question.
**Rationale:** The system role sets behaviour; separating instructions from the
question keeps the model grounded and reduces hallucination.
**Outcome:** Confirmed. For an unknown item, the no-context answer was vague/evasive;
with context + instruction, the model answered correctly and concisely ("Apache 2.0").

---

## Sprint 2 — Ingestion & Retrieval

### Decision: Author the knowledge base as chunk-friendly documents (Issue #10)
**Context:** ingest.py will split documents by paragraph (blank-line separated).
Whatever unit the splitter produces is exactly what the embedding model sees and
what the chat model receives as context — so document formatting IS retrieval design.
**Decision:** Compiled four short .md files under data/ from the official Foundry
Local docs, with three authoring rules: no markdown headings (they would become
useless tiny chunks), every paragraph self-contained and explicitly naming
"Foundry Local" (no dangling pronouns), one topic per paragraph.
**Rationale:** Each paragraph is written to answer one question type (e.g. "Is an
Azure subscription required?"), so a query's embedding lands cleanly on one chunk.
Prose is used instead of code blocks because natural-language questions embed
closer to prose than to code.
**Outcome:** ~19 paragraphs across 4 files, ready for ingestion. Content sourced
from learn.microsoft.com (June 2026 revision), including the nuance that Foundry
Local still uses the network for model/EP downloads — kept in the KB to prevent
the model from over-claiming "no internet ever".

### Decision: Idempotent rebuild for ingestion (Issue #11)
**Context:** Sprint 1 (#8) showed that re-running an INSERT script accumulates
duplicate rows. ingest.py will be re-run every time the knowledge base changes.
**Decision:** setup_database() runs CREATE TABLE IF NOT EXISTS followed by
DELETE FROM chunks, so every run starts from an empty table. Combined with
sorted document loading, the same input always produces the same database.
**Rationale:** Deleting and rebuilding ~20 rows is trivially cheap; the
alternatives (checking for duplicates, or updating changed rows) add complexity
with no benefit at this scale.
**Outcome:** Verified — two consecutive runs both ended at 20 chunks.

### Challenges encountered (Issue #11)
- **Silent exit, new cause.** The `if __name__ == "__main__":` guard was
  accidentally indented inside main(), so main() was never called. The guard
  must sit at zero indentation; in Python, indentation IS scope.
- **TypeError: Object of type CreateEmbeddingResponse is not JSON serializable.**
  generate_embedding returns a response envelope, not the raw vector. The vector
  lives at response.data[0].embedding (OpenAI-compatible response shape).
  Splitting chained access into intermediate variables made the traceback readable.

### Decision: Inject the embedding client into get_top_chunks (Issue #12)
**Context:** get_top_chunks needs an embedding client, and loading a model is
expensive. Sprint 3's Q&A loop will call this function once per user question.
**Decision:** The client is a parameter, not created inside the function. The
Sprint 1 cosine_similarity was promoted from the POC into src/retrieve.py.
**Rationale:** Create-once-pass-many keeps per-question latency low, and tests
can pass a fake client so retrieval logic is testable without the model.
**Outcome:** Three-question evaluation returned sensible rankings with scores
around 0.68–0.84.

### Learning: knowledge base wording is part of retrieval quality (Issue #12)
**Context:** "Which platforms does Foundry Local support?" missed its target
chunk — the paragraph listed the OS names but never said the word "platforms",
while generic intro paragraphs scored "a bit similar to everything".
**Resolution:** Reworded the paragraph to "supports three platforms: ...",
re-ran the idempotent ingest, and the chunk entered top-3. Full loop learned:
author docs → ingest → retrieve → evaluate → improve docs. Top-K acts as a
buffer: the answer doesn't need rank 1, it needs to be inside the top K.

### Challenges encountered (Issue #12)
- **Three questions silently merged into one.** Missing commas in the list
  literal triggered implicit string concatenation (["A" "B"] == ["AB"]) — the
  same feature used deliberately to split long SQL strings in ingest.py. No
  error is raised; only the odd output revealed it. Habit adopted: trailing
  commas on every list line.

### Decision: Test the chunking and retrieval layers before building on them (Issue #13)
**Context:** answer.py (Sprint 3) sits on top of retrieve.py, which sits on top
of ingest.py. Sprint 2 introduced the project's first pytest suite.
**Decision:** Wrote unit tests for split_into_paragraphs (ingest) and
cosine_similarity + get_top_chunks (retrieve) before starting answer.py. The
suite runs with no model and no database access — pytest.ini sets
pythonpath = src so tests import src/ modules the same way production code does.
**Rationale:** Securing the lower layers first means the answer layer is built on
a trusted foundation. Model-free, DB-free tests are fast (0.68s) and
deterministic; a suite that depends on a model is neither.
**Outcome:** 11 tests, all passing. Chunking: single paragraph, blank-line
splitting, whitespace stripping, empty text, blank-lines-only. Retrieval: cosine
similarity at four fixed points (identical=1, orthogonal=0, opposite=-1,
scale-invariant) via pytest.approx for float comparison, a zero-vector guard
test, and a ranking test for get_top_chunks. Added pytest to requirements.txt.

### Technique: fake clients and monkeypatch to test model-dependent code (Issue #13)
**Context:** get_top_chunks has two external dependencies — an embedding client
(the model) and load_chunks (the database). Both must be removed to keep the
test fast and deterministic.
**Approach:** The client is already a parameter, so it was replaced with a
FakeEmbeddingClient exposing generate_embedding (duck typing). load_chunks is
called from inside the function, so it was swapped with
monkeypatch.setattr(retrieve, "load_chunks", ...), which pytest reverts
automatically after the test. What remains under test is exactly the real work:
score, sort, return top-K.
**Outcome:** get_top_chunks ranking verified with tiny 2-D vectors, no model or
rag.db touched. This is the same injection pattern used for answer_query (#14),
and will be reused for the "I don't know" tests (#15).

### Bug fixed via red-green: zero-norm vectors in cosine_similarity (Issue #13)
**Context:** cosine_similarity divides by (norm_a * norm_b). A zero vector makes
a norm 0, raising ZeroDivisionError.
**Decision:** Wrote a failing test first (red) proving the crash, then added a
guard clause (if norm_a == 0 or norm_b == 0: return 0.0) turning it green.
**Rationale:** Seeing the red first proves the fix actually addresses the bug;
the test then stays as a regression guard. Committed separately as fix: to keep
the bug fix distinct from the test-addition commit.
**Outcome:** A zero vector now scores 0.0 (no similarity) instead of crashing.

### Challenges encountered (Issue #13)
- **Memory vs. disk drift.** The first test failed with
  ImportError: cannot import name 'chunk_text'. The function on disk is actually
  named split_into_paragraphs — the code being tested differed from the code
  recalled from memory. Diagnosed with dir(module) to list the real names.
  Lesson: tests expose the gap between the code "in my head" and the code on
  disk, caught at the very first import.

---

## Sprint 3 — Answer Generation

### Decision: Ground answers by packing retrieved context into the system message (Issue #14)
**Context:** With retrieval trusted (#13), the next step is producing a real
answer from the retrieved chunks — the first end-to-end RAG output.
**Decision:** Built src/answer.py: build_context joins the retrieved
(score, content) pairs into one ---separated block; SYSTEM_PROMPT carries the
rule "Answer using ONLY the context below; if it's not there, say I don't know"
with a {context} slot; answer_query(question, embedding_client, chat_client)
retrieves, builds context, and calls chat_client.complete_chat with the context
in the system message and the bare question in the user message.
**Rationale:** Reuses the #9 POC finding — the model follows the "ONLY the
context" rule more strictly when it is in the system role, separate from the
question. Clients are passed as parameters (dependency injection, as in #12/#13)
so #15 can test the "I don't know" behaviour without a real model.
**Outcome:** First end-to-end RAG answer, fully on-device. Q: "Do I need an Azure
subscription to use Foundry Local?" -> A: "No, you do not need an Azure
subscription to use Foundry Local." Chat model qwen2.5-0.5b, embedding model
qwen3-embedding-0.6b.

### Technique: discover an unfamiliar API before calling it (Issue #14)
**Context:** The chat client's exact call shape was unknown, and guessing SDK
method names has failed repeatedly before (#6, #7).
**Approach:** Discovered it instead of guessing — dir(client) revealed the method
(complete_chat), then inspect.signature + __doc__ revealed the arguments
(OpenAI message-dict list in, ChatCompletion out, read via
response.choices[0].message.content). dir() answers which names exist;
inspect.signature answers how to call them.
**Outcome:** answer_query worked on the first run. Also noted: setup_chat_client
does not re-initialize Foundry — the singleton manager is already initialized by
setup_embedding_client, so ordering matters (embedding setup first, then chat).

### Open items after Issue #14
- Planned "length trimming" for chunking is not implemented;
  split_into_paragraphs only splits, strips, and drops empties. Tracked as a
  separate task.
- The "I don't know" fallback has a dedicated test in Issue #15 (fake chat
  client), building directly on the injection pattern from #13/#14.

### Decision: Make "I don't know" reliable with two layers — prompt + threshold (Issue #15)
**Context:** retrieve.py always returns the top-3 chunks, even for an unrelated
question — it just returns the "least irrelevant" three. So the model always
receives some context and can fabricate an answer from that loose material. The
small model (qwen2.5-0.5b) was inconsistent about refusing.
**Decision:** Two layers, both returning one fixed sentence,
FALLBACK_ANSWER = "I don't know based on the provided documentation." (1) Prompt
layer: strengthened SYSTEM_PROMPT to "if the context does not actually answer the
question, reply with exactly <fallback>; do not use outside knowledge; do not
guess." (2) Threshold layer: in answer_query, if the top chunk's similarity is
below SIMILARITY_THRESHOLD (0.6), return FALLBACK_ANSWER without calling the chat
model at all.
**Rationale:** A single fixed sentence is both consistent (the user sees one
refusal, not a different one each time) and testable (an exact-match assertion).
The threshold layer is deterministic, fast (no inference), and testable, whereas
the prompt layer depends on the model's cooperation. Doing prompt first, then
measuring, then adding the threshold is the honest engineering order — the
threshold was only added after the prompt provably failed.
**Outcome:** Prompt alone was insufficient — of 3 unanswerable questions only 1
returned the fallback ("capital of Turkey" was answered from outside knowledge,
"best Python web framework" was fabricated). After adding the threshold, all 3
unanswerable questions returned the exact fallback without reaching the model,
while the answerable question still went through normally. Merged via PR
(Closes #15).

### Learning: choose the similarity threshold by measurement, not a guess (Issue #15)
**Context:** A threshold picked out of the air could reject good answers or admit
bad ones. Cosine scores from an embedding model are never 0 for unrelated text,
so there is no obvious natural cutoff.
**Approach:** Reused retrieve.py's __main__ diagnostic block to print top scores
for 3 answerable + 3 unanswerable questions against the real rag.db. Answerable
top scores landed at 0.687 / 0.775 / 0.835; unanswerable at 0.299 / 0.320 /
0.549. The riskiest unanswerable ("best Python web framework", 0.549) is
domain-adjacent — the docs mention Python, so it scored highest of the three.
**Outcome:** A clear gap between 0.549 and 0.687; the threshold was set to 0.6,
in the middle of the gap with a safety margin on both sides. This margin depends
on the current KB; if the document set grows, the threshold should be re-measured.

### Technique: prove the model is skipped with a spy client (Issue #15)
**Context:** The core promise of the threshold layer is "on a low score, the chat
model is never called." Asserting the returned text alone cannot distinguish
"skipped the model" from "called the model and it happened to refuse."
**Approach:** Added tests/test_answer.py with a FakeChatClient that records a
was_called flag in complete_chat (a spy), and monkeypatch.setattr(answer,
"get_top_chunks", ...) to inject fixed scores — patched on the answer module, not
retrieve, because from retrieve import get_top_chunks binds the name into
answer's namespace ("patch where it is used, not where it is defined"). Three
deterministic tests, no DB and no model: low score -> fallback and was_called is
False; empty DB -> same (guards the not top_chunks empty-list case); high score
-> was_called is True and the model's answer is returned (guards against
over-refusal).
**Outcome:** 14 tests pass in 0.57s (3 new). The threshold behaviour is now
regression-protected without any model or rag.db access.

### Challenges encountered (Issue #15)
- **Duplicate SYSTEM_PROMPT definition silently shadowing the new one.** The old
  loose prompt block was left in place directly below the new strict one. In
  Python a second assignment to the same name wins, so the strengthened prompt
  would never have run — the model would have used the old prompt. Caught by
  reading the file before running; the dead block was deleted.
- **Missing comma causing implicit string concatenation (recurrence of #12).**
  A trailing comma was dropped between two questions in the test list, so Python
  silently glued them into one string. No error is raised. Same failure mode as
  Sprint 2 (#12); reinforced the trailing-comma-on-every-line habit.
- **CRLF vs. LF phantom diff.** git status showed 22 files / ~900 lines changed
  after touching only 2 files. Root cause: the repo stores LF, the Windows working
  copy had turned to CRLF, and core.autocrlf was unset, so git treated every line
  as modified. Fixed with git config core.autocrlf true (repo-local), which
  normalizes CRLF->LF on commit; the phantom diff disappeared, leaving only the
  two real files. Lesson: check git diff --stat before committing on Windows — a
  bloated diff is a line-ending problem, not real work.
- **Temporary measurement code left in retrieve.py.** The 3 extra unanswerable
  questions added to retrieve.py's __main__ for threshold measurement were not
  part of the deliverable. Removed with git restore src/retrieve.py before
  committing so the PR diff stayed clean.

### Open items after Issue #15
- Systematic evaluation of the "I don't know" behaviour (a scored answerable /
  unanswerable question set) is deliberately deferred to Issue #17; #15 covered
  only the mechanism plus manual spot-checks.
- The threshold (0.6) is tuned to the current ~20-chunk KB and should be
  re-measured if the document set changes materially.

### Decision: Build the CLI by setting up the models once, outside the loop (Issue #16)
**Context:** With answer_query working (#14/#15), Sprint 3's required deliverable
is the interface that ties it together. The engine signature is
answer_query(question, embedding_client, chat_client) — three arguments, so the
CLI must own both clients, not create them per question.
**Decision:** Built src/main.py. main() sets up both clients once, before a
while True loop: setup_embedding_client() then setup_chat_client(), in that
order. Each iteration reads input("> ").strip(); an empty string prints a
reminder and continue-s (re-prompt, not exit); "exit"/"quit" — matched
case-insensitively via question.lower() in {"exit", "quit"} — prints "Goodbye."
and break-s; anything else is passed to answer_query and the result printed
between blank lines. Both models are unloaded on exit.
**Rationale:** Loading a model takes seconds, so setup lives outside the loop and
the clients are reused across questions — this is why only the first question of
a session is slow. The empty and exit checks are guard clauses: invalid inputs
are filtered at the top so answer_query only ever sees a real question. All
scripts run from the repository root, because rag.db and data/ are resolved
relative to the working directory.
**Outcome:** End-to-end CLI, fully on-device. "Do I need an Azure subscription to
use Foundry Local?" returned a grounded answer; "What is the capital of Turkey?"
returned the exact fallback; "exit" shut down cleanly. Merged via PR #32
(Closes #16).

### Decision: Guarantee model cleanup with try/finally (Issue #16 hardening)
**Context:** In the first version, an exception raised inside answer_query — or a
Ctrl+C — would break the loop and skip the two unload() calls, leaving the
models resident in the Foundry Local runtime.
**Decision:** Wrapped the loop in try/except (KeyboardInterrupt, EOFError) for a
graceful "Goodbye." on Ctrl+C or end-of-input, with a finally block that unloads
both models. The model variables are pre-set to None and the unloads are guarded
(if chat_model is not None) so cleanup is safe even if setup itself failed
partway.
**Rationale:** finally runs on every exit path — normal break, exception, or
interrupt — so cleanup is guaranteed rather than dependent on reaching the end
of main(). break was chosen over sys.exit() for the same reason: control falls
through to finally instead of terminating the process.
**Outcome:** The CLI now releases both models on any exit, including Ctrl+C.

### Challenges encountered (Issue #16)
- **Committed to main instead of a feature branch.** main.py was committed
  directly onto local main rather than a feat/16-cli branch. Meanwhile PR #32
  merged the same file into origin/main, so git pull reported
  "both added: src/main.py" — the same file added independently on each side,
  differing only by a single blank line. Resolved with git merge --abort then
  git reset --hard origin/main; nothing was lost because the local commits' content
  was already on origin through the PR. Lesson: read the first line of git status
  before every commit — "On branch main" means stop and create the branch first.
- **Stale index.lock blocked every git command.** An interrupted git process left
  .git/index.lock behind, so subsequent commands failed with "Another git process
  seems to be running." After confirming none actually was, the stale lock was
  removed (Remove-Item .git\index.lock) and the reset re-run.
- **Memory vs. disk drift (recurrence of #13).** At one point main.py on disk was
  missing its module docstring, imports, and the
  if __name__ == "__main__": main() guard, so running it printed nothing —
  main() was defined but never called. Re-reading the file on disk (rather than
  trusting the version held in memory) exposed the gap; the guard is what actually
  invokes main().

---

## Final hardening

### Decision: Carry source filenames through the full RAG pipeline

**Context:** The first complete version stored only chunk text and embeddings,
so users could not verify which document contributed to an answer.

**Decision:** Add a non-null `source` column with a legacy-schema migration,
return `(score, content, source)` retrieval results, label every context passage,
and print a stable de-duplicated source list. Exact fallback responses do not
print unrelated retrieved sources.

**Outcome:** Source attribution is deterministic and covered by ingestion,
retrieval, context, fallback, and formatting tests.

### Decision: Freeze and run a second evaluation set once

**Context:** The original 8/10 set had influenced four configuration changes and
was therefore a development set.

**Decision:** Author five new answerable and five new unsupported questions,
freeze their acceptance checks, and run them once without further tuning.

**Outcome:** The blind result was 7/10. It confirmed that an instruction-only
grounding rule still fails on some domain-adjacent questions. The raw answers
and scores are retained in `docs/blind-evaluation-results.json`.

---

## Sprint 4 — Quality & Delivery

### Decision: Design the evaluation set to target each defence layer (Issue #17)
**Context:** answer.py refuses in two independent ways — the similarity
threshold rejects a question before the chat model is called, and the system
prompt is meant to make the model refuse when the retrieved context does not
answer the question. A set of only obviously off-topic questions would exercise
the threshold alone and report a misleadingly high score.
**Decision:** Built a 10-question set: 5 answerable from the knowledge base, and
5 unanswerable split into "off-domain" (sourdough bread, GitHub acquisition —
expected to hit the threshold) and "domain-adjacent" (fine-tuning, mobile
support, pricing — expected to pass the threshold and be caught only by the
prompt). The pricing question is deliberately adversarial: the KB says "no
per-token costs", a partial match that does not answer a monthly-cost question.
**Rationale:** Each failing question should point at a specific layer, so a
wrong answer is diagnosable rather than just a number.
**Outcome:** The design paid off — the set isolated four distinct root causes at
four different layers (see below).

### Decision: Run the evaluation from a reproducible script (Issue #17)
**Decision:** Wrote prototypes/evaluation_run.py instead of typing the 10
questions into the CLI by hand. It calls the same answer_query() the CLI uses,
and additionally prints the top retrieval score and the elapsed time per
question. A second script, prototypes/inspect_retrieval.py, prints the chunks
retrieved for one question at an arbitrary top-K.
**Rationale:** A hand run is one-off and unrepeatable. The score column lets a
failure be attributed to the threshold vs. the model; inspect_retrieval tells a
retrieval failure apart from a generation failure. Production code (src/) was
not touched for measurement.
**Outcome:** Both scripts drove every decision in this sprint. Kept in
prototypes/ as learning artifacts, alongside a third helper, check_model.py,
that reports a model's cache state without loading it (added after a stuck
download — it distinguishes a slow download from a stuck load).

### Decision: Lower the similarity threshold from 0.6 to 0.5 (Issue #17)
**Context:** Question 3 ("Which Python version and which package?") scored 0.556
and was rejected before the model ran, although the KB answers it directly. The
two-intent question averages into a vector that matches no single paragraph
strongly.
**Decision:** Moved SIMILARITY_THRESHOLD to 0.50.
**Rationale:** Chosen from the measured score distribution, not by feel: the
scores showed a wide empty band between the highest off-domain question (0.402)
and the wrongly rejected one (0.556). 0.50 sits in the middle of that gap,
leaving ~0.1 of margin on both sides; 0.55 would have left 0.004. General rule:
place the threshold in the widest gap between the classes.
**Outcome:** Question 3 passes; no other question changed, as predicted — every
other score lies below 0.42 or above 0.62.

### Decision: Upgrade the chat model from qwen2.5-0.5b to qwen2.5-1.5b (Issue #17)
**Context:** With 0.5b, question 1 answered "Yes, you do not need an Azure
subscription" (fact right, polarity self-contradicting) and question 5 inverted
its answer outright — both on correctly retrieved context. The same question
also gave different answers across runs.
**Decision:** Moved up one rung in the same family (0.5b → 1.5b), not to a
different family. A first attempt at 7b failed to download on this machine.
**Rationale:** Staying in the qwen2.5 line keeps the tokenizer, prompt format
and instruction style constant, so any change is attributable to capacity
alone. This follows the pre-registered brief decision "start small, scale if
needed". Reasoning-tagged models were avoided: they can emit think-steps that
break the exact fallback-string match and add latency.
**Outcome:** Question 1 fixed outright. Question 5 moved from a wrong answer to
a refusal (later fixed by the prompt change). Latency rose from ~1s to 2–3s,
inside the plan's 1–3s target.

### Decision: Harden the system prompt with an explicit decision step (Issue #17)
**Context:** Question 8 ("How do I fine-tune a model?") scores 0.803 — close to
the download/load paragraph in getting_started.md — so the threshold cannot
catch it. The model filled the gap with an invented procedure. A high score
does not mean the context contains the answer.
**Decision:** Rewrote SYSTEM_PROMPT to (1) add a decide-then-answer step
("first decide whether the context explicitly states the answer"), (2) name the
failure mode ("being about a related topic is not enough"), (3) forbid
describing steps not written in the context, and (4) cap answers at three
sentences.
**Rationale:** The original prompt stated the refusal rule but gave no procedure
for applying it; the length cap shrinks the room available for fabrication.
**Outcome:** Mixed, and instructive. Question 5 was fixed as a side effect — the
decision step let the model treat an indirect statement as an answer. Question 8
shrank from a seven-step guide to three sentences but stayed ungrounded.
Question 4 got worse: the "use only the context" rule made the model more
extractive, so it pulled a wrong runtime name from the wrong paragraph and
stated it confidently. Final score: 8/10.

### Learning: Above ~0.75 the embedding score stops discriminating (Issue #17)
**Context:** Question 4 is answered verbatim by one paragraph in
what_is_foundry_local.md, yet that paragraph is not retrieved — not even in the
top 8 of 21 chunks. The first hypothesis was a multi-topic paragraph diluting
its own embedding (a violation of the Issue #10 authoring rule); the paragraph
was split and the DB rebuilt, and it still did not enter the top 8.
**Learning:** The measured scores explain why. The answerable and unanswerable
ranges overlap almost completely (an unanswerable question scores 0.803, an
answerable one 0.775), and question 4's top-8 spans only 0.056. On this
single-product corpus every chunk is somewhat similar to every query, so above
~0.75 the cosine score carries almost no signal. This is a limit of
qwen3-embedding-0.6b on this corpus, not of any one paragraph — it cannot be
fixed by rewriting documents. The threshold works only because off-domain
questions fall far away (0.32–0.40).

### Learning: Reproducibility is a property of model confidence (Issue #17)
**Context:** qwen2.5-0.5b gave two different answers to question 1 across four
runs, with byte-identical retrieval each time. qwen2.5-1.5b was run three times
and produced byte-identical answers to all ten questions.
**Learning:** Decoding is greedy in both cases, so this is not sampling. The
likely cause is that floating-point results in the accelerated execution path
vary in their last digits between runs; with 0.5b the margin between the top two
candidate tokens was small enough for that noise to flip the winner, with 1.5b
the margin exceeds the noise. So reproducibility followed from the larger
model's confidence, not from the decoder. Practical consequence: with 1.5b a
single run can be trusted as evidence; retrieval itself was deterministic to
three decimals throughout.

### Decision: Reject the query-instruction-prefix experiment (Issue #17)
**Context:** qwen3-embedding-0.6b is instruction-tuned and expects an asymmetric
setup (plain-text documents, task-prefixed queries), a plausible fix for the
discrimination problem above.
**Decision:** Tested two query prefixes against the baseline, then reverted to
no prefix.
**Rationale:** The first prefix named the subject ("...about Foundry Local...")
and raised the off-domain floor by 0.14, because the instruction text shared the
words common to every document — cutting the threshold margin from 0.18 to
0.038. A domain-neutral prefix removed that confound, and with it the apparent
gain: the fine-tuning score returned to 0.791 and the score spread narrowed
further, to 0.035. The baseline was better on both metrics.
**Outcome:** Reverted. Recorded in docs/evaluation.md §5 — a negative result
worth keeping, since it rules out query formatting as the cause of the
discrimination problem.

### Challenges encountered (Issue #17)
- **A stuck model download looked like a hang.** setup_chat_client() prints
  nothing while model.download() runs, so a multi-GB download showed a blank
  screen and did not respond to Ctrl+C (the interpreter was inside a native
  call). Diagnosed with check_model.py (is_cached=False → download, not load)
  and fixed the visibility with flushed progress prints in evaluation_run.py.
- **The first KB fix targeted the right cause but did not work.** Splitting the
  multi-topic paragraph was a correct diagnosis of an Issue #10 rule violation,
  but the answering paragraph still did not surface — the real cause was
  embedding discrimination, one layer deeper.
- **Scaling the generator made hallucination more convincing, not rarer.**
  1.5b turned 0.5b's three vague invented sentences into a seven-step,
  markdown-formatted fine-tuning guide. Grounding is a separate mechanism from
  fluency; a bigger model does not supply it.

---

### Decision: Delete the duplicated EMBEDDING_MODEL rather than abstract it (Issue #18)
**Context:** The evaluation flagged EMBEDDING_MODEL as defined in both
ingest.py and retrieve.py — a mismatch would embed queries and chunks with
different models. cosine_similarity would not notice: zip() truncates to the
shorter vector, so different dimensions are compared over their common prefix
and produce plausible nonsense with no error.
**Decision:** The copy in retrieve.py was dead code — the module never used it,
nor its foundry_local_sdk import — so both were deleted, leaving ingest.py as
the single owner. A ValueError was added to cosine_similarity on a length
mismatch, naming the cause and the fix in the message.
**Rationale:** Removing an unused definition is simpler and safer than adding an
abstraction for a constant used in one live place. The dimension guard turns the
most dangerous failure mode (silent, plausible, wrong) into a loud one.
**Outcome:** Confirmed — a new test compares vectors of different lengths and
gets the ValueError. DB_PATH is still defined in both files (both use it), so a
test now asserts the two agree instead.

### Decision: Pin the calibrated threshold with a test (Issue #18)
**Context:** No test exercised the threshold boundary, so moving
SIMILARITY_THRESHOLD from 0.6 to 0.5 in Issue #17 passed the suite silently.
**Decision:** Added boundary tests written against the constant (a score equal
to the threshold reaches the model, a score just below does not) plus one test
that pins the value 0.5 itself.
**Rationale:** The boundary tests protect the "<" semantics; the pinned-value
test protects the calibration — 0.5 was derived from a measured distribution,
so changing it should force a deliberate edit and a reason, not a silent tweak.
**Outcome:** Suite grew from 14 to 21 tests, all passing in ~0.6s. It still
loads no models: every external client is faked or monkeypatched, a direct
payoff of the Issue #12 "inject the client" decision.

### Challenges encountered (Issue #18)
- **A stale .git/index.lock blocked every commit.** Left by an interrupted git
  operation; commits failed with "Another git process seems to be running".
  Resolved by removing the lock file once no git process was active.
- **The #18 branch was cut from a main that lacked the #17 merge**, so its
  commits sat on the wrong base and the diff would have re-included all of #17.
  Fixed with git rebase --onto origin/main, taking care that during a rebase
  --theirs refers to the replayed branch, not to main.

---

## Sprint 5 — Documentation & Project Delivery

### Decision: Turn the README into the project's primary technical entry point (Issue #19)
**Context:** The repository contained working code and detailed engineering
notes, but a reviewer still had to inspect several files to understand what the
system did, how to run it, and what its measured limitations were.
**Decision:** Rewrote the README around the complete user journey: project
purpose, final configuration, architecture, setup, ingestion, web and CLI usage,
API examples, testing, evaluation results, privacy behaviour, limitations, and
repository structure. Added Mermaid sequence and flow diagrams instead of
decorative emoji.
**Rationale:** A capstone repository should be understandable without a live
demo. The README therefore acts as both onboarding material and a concise
technical reference, while deeper reasoning remains in the journal and reports.
**Outcome:** The repository now exposes the complete system from first setup to
validated results, including the 26-chunk knowledge base, 38-test suite, 8/10
development evaluation, and 7/10 frozen blind evaluation.

### Decision: Separate concise onboarding from the full technical report (Issue #19)
**Context:** The README needed to stay navigable, but the project also required a
durable explanation of architecture, experiments, failure analysis, and
engineering trade-offs.
**Decision:** Added `docs/technical-report.md` as the long-form record and linked
it with the architecture, evaluation, blind-evaluation, and engineering-journal
documents. The report describes the final pipeline, data model, model choices,
evaluation method, known limitations, and recommended next steps.
**Rationale:** Different readers need different levels of detail. The README
answers "what is this and how do I run it?", while the report answers "why was it
built this way and what evidence supports the decisions?"
**Outcome:** Project delivery no longer depends on oral explanation. Decisions,
results, and limitations can be reviewed asynchronously from the repository.

### Challenges encountered (Issue #19)
- **Windows dependency encoding.** The generated requirements file was stored in
  an encoding that common tooling did not read reliably. It was re-encoded as
  UTF-8, and pytest was added explicitly so a fresh environment could reproduce
  the test suite.
- **Platform-specific runtime packages.** The WinML package is correct for the
  development machine but not for every operating system. A separate
  cross-platform requirements file documents the alternative without installing
  conflicting SDK variants together.
- **Documentation drift.** Counts and configuration values appeared in several
  files. Final verification checked the README, report, evaluation records, and
  implementation against the same 26 chunks, Top-K 3, threshold 0.5, and model
  aliases.

---

## Sprint 6 — Public Demo & Learning Presentation

### Decision: Publish a UI-only demo instead of moving local inference to the cloud (Issue #20)
**Context:** Reviewers needed a link they could open without installing models,
but hosting the real assistant would contradict the project's local-first
privacy and offline design.
**Decision:** Published a separate public interface preview with representative
example responses. The page labels itself as a UI demo and links back to the
complete repository. The README explains that real retrieval and generation run
only in the local application.
**Rationale:** A public preview can demonstrate information architecture,
responsive design, and interaction without pretending to provide the local
runtime through a hosted service.
**Outcome:** The project now has a shareable visual demonstration while keeping
the model, knowledge base, prompts, and inference on the device.

### Decision: Structure the final presentation around engineering decisions (Issue #20)
**Context:** A feature inventory would not explain what was learned during the
internship or show how the project improved through measurement and debugging.
**Decision:** Use the engineering journal as the presentation's source of truth.
The narrative follows the progression from environment setup and component
proofs to RAG architecture, grounded answering, evaluation, testing, web
delivery, and the limits discovered along the way.
**Rationale:** The strongest evidence of learning is not the final interface
alone; it is the chain of hypotheses, measurements, failed experiments, fixes,
and documented trade-offs that produced it.
**Outcome:** The final communication artifact can explain both what was built and
how engineering judgement developed across the project.

### Learning: A local AI product is more than a local model (Issue #20)
**Context:** The first verification task proved that a model could answer on the
device, but the completed project required many additional layers.
**Learning:** A useful local AI application combines environment compatibility,
model lifecycle management, document design, embeddings, retrieval, grounding,
fallback behaviour, evaluation, automated tests, APIs, responsive UI,
documentation, and honest communication of limitations.
**Outcome:** The project evolved from a model proof-of-concept into a tested,
documented, and explainable local AI system.

---

## Sprint 7 — Documentation Web Application

### Decision: Expose the existing RAG pipeline through FastAPI (Issue #37)
**Context:** The CLI proved the complete local workflow, but it was not the best
interface for readers learning Foundry Local or for reviewers exploring the
project.
**Decision:** Added `src/web.py` with health, source-listing, and question-answering
endpoints. The API calls the same ingestion, retrieval, and answer-generation
services used by the CLI instead of creating a second RAG implementation.
**Rationale:** One domain pipeline prevents interface-specific behaviour from
drifting. FastAPI adds a thin transport layer while preserving the tested local
AI logic.
**Outcome:** `GET /api/health`, `GET /api/sources`, and `POST /api/ask` provide a
browser-ready interface to the local knowledge base and Foundry Local models.

### Decision: Load and reuse Foundry Local models for the server session (Issue #37)
**Context:** Model download and loading are expensive compared with an individual
question. Repeating setup inside every request would make the API unnecessarily
slow and waste device resources.
**Decision:** Initialize the embedding and chat clients lazily, cache them in the
application process, and reuse them across requests. Cleanup remains explicit
when the server session ends.
**Rationale:** This applies the same create-once-pass-many principle learned in
Issue #12 and used by the CLI in Issue #16.
**Outcome:** The first request owns initialization cost; later questions reuse
the loaded local models and avoid repeated setup.

### Decision: Combine learning content and question answering on one page (Issue #37)
**Context:** A chat box without context would demonstrate interaction but would
not teach what Foundry Local is, how local RAG works, or what privacy guarantees
are realistic.
**Decision:** Built a responsive documentation page covering the product
overview, architecture, Python quickstart, offline behaviour, privacy, and a
suggested-question chat panel. The page connects directly to the FastAPI
endpoints.
**Rationale:** Users can first read the controlled documentation and then ask
questions about the same knowledge domain, making the retrieval behaviour easier
to understand.
**Outcome:** The project gained a desktop and mobile web experience while
retaining the CLI for direct technical use.

### Decision: Keep source attribution in the API but hide internal filenames in chat (Issue #37)
**Context:** Source filenames are valuable for diagnostics and API consumers,
but displaying raw names such as `what_is_foundry_local.md` inside every chat
answer made the interface look like an implementation trace.
**Decision:** Preserve the structured `sources` field in API responses and the
backend pipeline, but omit internal filenames from the visible chat message.
**Rationale:** Traceability and presentation are separate concerns. The system
should retain evidence without forcing storage details into the primary user
experience.
**Outcome:** API consumers still receive deterministic source metadata, while
the browser displays a clean answer.

### Challenges encountered (Issue #37)
- **Local runtime boundary.** The browser UI can be hosted anywhere, but the real
  Foundry Local runtime, models, SQLite database, and documents remain on the
  user's device. The architecture and interface copy were written to avoid
  implying that the hosted page runs the private model.
- **Responsive chat layout.** The fixed desktop side panel had to become a
  readable single-column flow on narrow screens without hiding suggestions or
  the question form.
- **Regression coverage.** API serialization, health behaviour, static assets,
  question handling, and source metadata were added to the automated suite. The
  complete suite reached 38 passing tests.
