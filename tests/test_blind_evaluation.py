from pathlib import Path
import sys

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "prototypes")
)

from blind_evaluation_run import Case, automatic_pass


def test_answerable_case_requires_all_frozen_terms():
    case = Case("question", True, ("device", "local"))

    assert automatic_pass(case, "Processed locally on the device.")
    assert not automatic_pass(case, "Processed on the device.")


def test_unanswerable_case_requires_exact_fallback():
    case = Case("question", False)

    assert automatic_pass(
        case, "I don't know based on the provided documentation."
    )
    assert not automatic_pass(case, "I do not know.")
