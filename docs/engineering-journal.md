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