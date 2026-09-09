from __future__ import annotations

import json
import re
from pathlib import Path
from string import Formatter

LOCALES_DIR = Path(__file__).resolve().parent / "locales"
DEFAULT_LANGUAGE = "it"
SUPPORTED_LANGUAGES = ("it", "en")

_catalogs: dict[str, dict[str, str]] = {}
_current_language = DEFAULT_LANGUAGE
_reverse_it: dict[str, str] = {}
_template_rules: list[tuple[re.Pattern[str], str, list[str]]] = []


def _load_catalog(language: str) -> dict[str, str]:
    if language not in _catalogs:
        path = LOCALES_DIR / f"{language}.json"
        with path.open("r", encoding="utf-8") as handle:
            _catalogs[language] = json.load(handle)
    return _catalogs[language]


def _build_indexes() -> None:
    global _reverse_it, _template_rules
    italian = _load_catalog(DEFAULT_LANGUAGE)
    _reverse_it = {value: key for key, value in italian.items()}
    rules = []
    formatter = Formatter()
    for key, template in italian.items():
        if "{" not in template:
            continue
        parts = []
        names = []
        try:
            parsed = list(formatter.parse(template))
        except ValueError:
            continue
        for literal, field_name, format_spec, conversion in parsed:
            parts.append(re.escape(literal))
            if field_name is not None:
                # Field names in the catalog are simple identifiers.
                safe_name = re.sub(r"\W+", "_", field_name)
                if safe_name in names:
                    parts.append(fr"(?P={safe_name})")
                else:
                    names.append(safe_name)
                    parts.append(fr"(?P<{safe_name}>.*?)")
        try:
            rules.append((re.compile("^" + "".join(parts) + "$", re.DOTALL), key, names))
        except re.error:
            continue
    _template_rules = rules


def set_language(language: str) -> str:
    global _current_language
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE
    _load_catalog(language)
    _current_language = language
    return _current_language


def get_language() -> str:
    return _current_language


def language_display_names() -> dict[str, str]:
    # Names are intentionally self-identifying rather than translated labels.
    return {"it": "Italiano", "en": "English"}


def _render_template(template: str, values: dict[str, str]) -> str:
    # We intentionally ignore Python formatting specifications here because
    # pattern translation receives already-rendered source text.
    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        return str(values.get(name, match.group(0)))
    return re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)(?:![^}:]+)?(?::[^}]+)?\}", repl, template)


def tr(value, **kwargs):
    """Translate a semantic key or an Italian source string.

    UI code can use semantic keys directly (recommended for new code), while
    legacy UI strings are resolved through the Italian catalog. The latter
    keeps the migration from the original single-file application small and
    auditable.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return value

    italian = _load_catalog(DEFAULT_LANGUAGE)
    current = _load_catalog(_current_language)

    if value in italian:  # semantic key
        template = current.get(value, italian[value])
        if kwargs:
            try:
                return template.format(**kwargs)
            except (KeyError, ValueError):
                return template
        return template

    key = _reverse_it.get(value)
    if key is not None:
        return current.get(key, value)

    # Support already-rendered legacy f-strings by matching them against
    # translated templates containing {placeholders}.
    if _current_language != DEFAULT_LANGUAGE:
        for pattern, template_key, names in _template_rules:
            match = pattern.fullmatch(value)
            if match:
                translated = current.get(template_key, italian[template_key])
                return _render_template(translated, match.groupdict())

    return value


_build_indexes()
