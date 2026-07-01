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