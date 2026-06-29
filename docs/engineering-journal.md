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
