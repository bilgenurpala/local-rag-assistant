import builtins

import main


class FakeModel:
    def __init__(self):
        self.unloaded = False

    def unload(self):
        self.unloaded = True


def test_cli_reprompts_on_empty_input_and_unloads_models(monkeypatch, capsys):
    embedding_model = FakeModel()
    chat_model = FakeModel()
    answers = iter(["", "exit"])

    monkeypatch.setattr(
        main,
        "setup_embedding_client",
        lambda: (embedding_model, object()),
    )
    monkeypatch.setattr(
        main,
        "setup_chat_client",
        lambda: (chat_model, object()),
    )
    monkeypatch.setattr(builtins, "input", lambda prompt: next(answers))

    main.main()

    output = capsys.readouterr().out
    assert "Please type a question." in output
    assert "Goodbye." in output
    assert embedding_model.unloaded
    assert chat_model.unloaded


def test_cli_unloads_embedding_model_if_chat_setup_fails(monkeypatch):
    embedding_model = FakeModel()
    monkeypatch.setattr(
        main,
        "setup_embedding_client",
        lambda: (embedding_model, object()),
    )
    monkeypatch.setattr(
        main,
        "setup_chat_client",
        lambda: (_ for _ in ()).throw(RuntimeError("load failed")),
    )

    try:
        main.main()
    except RuntimeError:
        pass

    assert embedding_model.unloaded
