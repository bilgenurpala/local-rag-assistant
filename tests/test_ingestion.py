import sqlite3

from ingest import load_documents, setup_database


def test_load_documents_returns_names_and_ignores_other_extensions(tmp_path):
    (tmp_path / "b.txt").write_text("second", encoding="utf-8")
    (tmp_path / "a.md").write_text("first", encoding="utf-8")
    (tmp_path / "ignored.json").write_text("{}", encoding="utf-8")

    assert load_documents(tmp_path) == [
        ("a.md", "first"),
        ("b.txt", "second"),
    ]


def test_setup_database_has_source_column_and_is_idempotent(tmp_path):
    db_path = tmp_path / "test.db"
    connection = setup_database(db_path)
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(chunks)").fetchall()
    }
    assert columns == {"id", "source", "content", "embedding"}
    connection.execute(
        "INSERT INTO chunks (source, content, embedding) VALUES (?, ?, ?)",
        ("source.md", "content", "[1.0, 0.0]"),
    )
    connection.commit()
    connection.close()

    rebuilt = setup_database(db_path)
    assert rebuilt.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 0
    rebuilt.close()


def test_setup_database_migrates_legacy_schema(tmp_path):
    db_path = tmp_path / "legacy.db"
    legacy = sqlite3.connect(db_path)
    legacy.execute(
        "CREATE TABLE chunks("
        "id INTEGER PRIMARY KEY, content TEXT NOT NULL, embedding TEXT NOT NULL)"
    )
    legacy.commit()
    legacy.close()

    migrated = setup_database(db_path)
    columns = {
        row[1] for row in migrated.execute("PRAGMA table_info(chunks)").fetchall()
    }
    assert "source" in columns
    migrated.close()
