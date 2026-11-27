"""Build web/messages.py from the catalogues in tools/i18n/.

The tool is a development helper. It reads the Chinese source texts that were
extracted from the console and the English translations, checks that every key
exists in both languages and writes the message module the runtime uses.

    python -X utf8 tools/i18n_build_messages.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "i18n"
OUTPUT = ROOT / "web" / "messages.py"
PLACEHOLDER = re.compile(r"\{([A-Za-z0-9_]+)\}")


def read(name):
    return json.loads((SOURCE / name).read_text(encoding="utf-8"))


def collect():
    """Merge the catalogues and report the keys that lack one language."""
    chinese = {}
    chinese.update(read("index.zh-CN.json"))
    chinese.update(read("app.zh-CN.json"))
    english = {}
    english.update(read("index.en.json"))
    english.update(read("app.en.json"))
    # The API messages are keyed by their Chinese text, so that the server can
    # localize a value it already sends.
    for text, translation in read("server.en.json").items():
        english[text] = translation
        chinese[text] = text
    missing_chinese = sorted(set(english) - set(chinese))
    missing_english = sorted(set(chinese) - set(english))
    if missing_chinese or missing_english:
        for key in missing_chinese:
            print("no Chinese text for {!r}".format(key), file=sys.stderr)
        for key in missing_english:
            print("no English text for {!r}".format(key), file=sys.stderr)
        raise SystemExit("the catalogues do not agree")
    return {key: {"en": english[key], "zh-CN": chinese[key]} for key in sorted(chinese)}


def render(messages):
    lines = [
        '"""The console messages in English and Simplified Chinese.',
        "",
        "Every key exists in both languages. The browser receives this catalogue",
        "from /api/i18n.js, and the server uses it to localize the `error` and",
        "`message` fields of an API answer.",
        '"""',
        "",
        "import json",
        "import re",
        "",
        "LANGUAGES = (\"en\", \"zh-CN\")",
        "DEFAULT_LANGUAGE = \"zh-CN\"",
        "PLACEHOLDER = re.compile(r\"\\{([A-Za-z0-9_]+)\\}\")",
        "",
        "MESSAGES = {",
    ]
    for key, value in messages.items():
        lines.append("    {!r}: {{".format(key))
        lines.append("        \"en\": {!r},".format(value["en"]))
        lines.append("        \"zh-CN\": {!r},".format(value["zh-CN"]))
        lines.append("    },")
    lines.append("}")
    lines.append("")
    lines.append("")
    lines.append("def normalize_language(value):")
    lines.append("    \"\"\"Return the supported language for a request, or the default.\"\"\"")
    lines.append("    text = str(value or \"\").strip().lower()")
    lines.append("    if not text:")
    lines.append("        return DEFAULT_LANGUAGE")
    lines.append("    if text.startswith(\"zh\"):")
    lines.append("        return \"zh-CN\"")
    lines.append("    if text.startswith(\"en\"):")
    lines.append("        return \"en\"")
    lines.append("    return DEFAULT_LANGUAGE")
    lines.append("")
    lines.append("")
    lines.append("def message(key, language):")
    lines.append("    \"\"\"Return one message in the requested language, or the key itself.\"\"\"")
    lines.append("    entry = MESSAGES.get(key)")
    lines.append("    if not entry:")
    lines.append("        return key")
    lines.append("    return entry.get(normalize_language(language), entry[DEFAULT_LANGUAGE])")
    lines.append("")
    lines.append("")
    lines.append("def localize(value, language):")
    lines.append("    \"\"\"Localize a message that the server sends to the browser.\"\"\"")
    lines.append("    if not isinstance(value, str) or not value:")
    lines.append("        return value")
    lines.append("    entry = MESSAGES.get(value)")
    lines.append("    if not entry:")
    lines.append("        return value")
    lines.append("    return entry.get(normalize_language(language), entry[DEFAULT_LANGUAGE])")
    lines.append("")
    lines.append("")
    lines.append("def catalogue_script():")
    lines.append("    \"\"\"The catalogue as a JavaScript file for the browser.\"\"\"")
    lines.append("    payload = json.dumps(MESSAGES, ensure_ascii=False, sort_keys=True)")
    lines.append("    return \"window.NPT_MESSAGES = \" + payload + \";\\n\"")
    lines.append("")
    lines.append("")
    lines.append("def placeholders(key):")
    lines.append("    \"\"\"The parameter names one message expects.\"\"\"")
    lines.append("    entry = MESSAGES.get(key) or {}")
    lines.append("    return sorted(set(PLACEHOLDER.findall(entry.get(\"en\", \"\"))))")
    lines.append("")
    return "\n".join(lines)


def main():
    messages = collect()
    OUTPUT.write_text(render(messages), encoding="utf-8")
    print("wrote {} messages".format(len(messages)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
