"""Report the cache state of a chat model without loading it.

Used to tell a slow download apart from a stuck load. Pass an alias on
the command line, otherwise the project's configured CHAT_MODEL is used:

    python prototypes/check_model.py qwen2.5-7b
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from foundry_local_sdk import Configuration, FoundryLocalManager

from answer import CHAT_MODEL

ALIAS = sys.argv[1] if len(sys.argv) > 1 else CHAT_MODEL


def main() -> None:
    config = Configuration(app_name="local_rag_assistant")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    print("cached models:")
    for cached in manager.catalog.get_cached_models():
        print(f"  {cached.alias}")

    model = manager.catalog.get_model(ALIAS)
    if model is None:
        print(f"\n{ALIAS}: not found in catalog")
        return

    print(f"\n{ALIAS}")
    print(f"  is_cached      = {model.is_cached}")
    print(f"  is_loaded      = {model.is_loaded}")
    print(f"  context_length = {model.context_length}")


if __name__ == "__main__":
    main()
