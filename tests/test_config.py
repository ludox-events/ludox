"""Configuration characterization using explicit temporary INI paths."""

from pathlib import Path

import pytest

from ludox import config


def test_missing_and_empty_configuration(tmp_path):
    path = tmp_path / "settings.ini"
    assert config.load_config(path) is None
    path.write_text("", encoding="utf-8")
    assert config.load_config(path) == config.AppConfig("it", 50, "ludox.db")


def test_partial_configuration_normalizes_language(tmp_path):
    path = tmp_path / "settings.ini"
    path.write_text("[general]\nlanguage = EN\n", encoding="utf-8")
    assert config.load_config(path) == config.AppConfig("en", 50, "ludox.db")


@pytest.mark.parametrize("content", [
    "not an INI file",
    "[general]\nmax_tokens=abc",
    "[general]\nmax_tokens=0",
    "[general]\nlanguage=fr",
    "[general]\ndatabase=",
    "[general]\ndatabase=missing/test.db",
    "[general]\nlanguage=it\nlanguage=en",
])
def test_invalid_configuration_returns_none(tmp_path, content):
    path = tmp_path / "settings.ini"
    path.write_text(content, encoding="utf-8")
    assert config.load_config(path) is None


def test_save_load_round_trip_does_not_create_database(tmp_path):
    path = tmp_path / "settings.ini"
    original = config.AppConfig("en", 23, " Evento ")
    config.save_config(original, path)
    assert config.load_config(path) == config.AppConfig("en", 23, "Evento.db")
    assert original.database == " Evento "
    assert not (tmp_path / "Evento.db").exists()


def test_save_load_round_trip_preserves_organization_reference(tmp_path):
    path = tmp_path / "settings.ini"
    original = config.AppConfig(
        "it",
        50,
        "ludox.db",
        active_organization_id=7,
        active_organization_name=" Ludoteca Centro ",
    )

    config.save_config(original, path)

    assert config.load_config(path) == config.AppConfig(
        "it", 50, "ludox.db", 7, "Ludoteca Centro"
    )
    saved = path.read_text(encoding="utf-8")
    assert "[organization]" in saved
    assert "active_organization_id = 7" in saved
    assert "active_organization_name = Ludoteca Centro" in saved


@pytest.mark.parametrize(
    "organization",
    [
        "active_organization_id = 1",
        "active_organization_name = Ludoteca Centro",
        "active_organization_id = invalid\nactive_organization_name = Ludoteca Centro",
        "active_organization_id = 0\nactive_organization_name = Ludoteca Centro",
    ],
)
def test_invalid_organization_reference_is_ignored(tmp_path, organization):
    path = tmp_path / "settings.ini"
    path.write_text(
        "[general]\nlanguage = en\n\n[organization]\n" + organization,
        encoding="utf-8",
    )

    assert config.load_config(path) == config.AppConfig("en", 50, "ludox.db")


@pytest.mark.parametrize("changes", [
    {"language": "fr"}, {"max_tokens": 0}, {"max_tokens": -1},
    {"max_tokens": "50"}, {"max_tokens": 1.5}, {"database": " "},
    {"active_organization_id": 1},
    {"active_organization_name": "Ludoteca"},
    {"active_organization_id": 0, "active_organization_name": "Ludoteca"},
    {"active_organization_id": True, "active_organization_name": "Ludoteca"},
])
def test_invalid_values_are_rejected_without_overwriting(tmp_path, changes):
    candidate = config.AppConfig(**changes)
    assert not config.validate_config(candidate)
    path = tmp_path / "settings.ini"
    path.write_text("keep existing content", encoding="utf-8")
    with pytest.raises(ValueError):
        config.save_config(candidate, path)
    assert path.read_text(encoding="utf-8") == "keep existing content"


def test_boolean_token_limit_is_accepted_but_not_loadable(tmp_path):
    # Preserve the current bool-is-an-int behavior rather than fixing it.
    candidate = config.AppConfig(max_tokens=True)
    assert config.validate_config(candidate)
    path = tmp_path / "settings.ini"
    config.save_config(candidate, path)
    assert config.load_config(path) is None


def test_relative_absolute_and_external_paths(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(config, "PROJECT_DIR", project)
    assert config.resolve_database_path(" local.db ") == project / "local.db"
    assert config.database_setting_from_path(project / "local.db") == "local.db"
    external = tmp_path / "external.db"
    assert config.resolve_database_path(str(external)) == external
    assert config.database_setting_from_path(external) == str(external)
    assert config.normalize_database_setting("event") == "event.db"
    assert config.normalize_database_setting("event.sqlite3") == "event.sqlite3"


def test_environment_and_user_path_expansion(tmp_path, monkeypatch):
    monkeypatch.setenv("LUDOX_TEST_FOLDER", str(tmp_path))
    assert config.resolve_database_path("${LUDOX_TEST_FOLDER}/event.db") == tmp_path / "event.db"
    # Mock home lookup, without modifying the user's HOME/USERPROFILE variables.
    original_expanduser = Path.expanduser

    def temporary_home(path):
        if path.parts and path.parts[0] == "~":
            return tmp_path.joinpath(*path.parts[1:])
        return original_expanduser(path)

    monkeypatch.setattr(Path, "expanduser", temporary_home)
    assert config.resolve_database_path("~/event.db") == tmp_path / "event.db"


def test_invalid_database_paths(tmp_path):
    directory = tmp_path / "directory.db"
    directory.mkdir()
    for value in ("", "  ", str(directory), "missing/event.db"):
        with pytest.raises(ValueError):
            config.normalize_database_setting(value)
