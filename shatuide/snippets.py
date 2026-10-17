"""Code-Snippets und Vorlagen."""

from __future__ import annotations

SNIPPETS: list[dict[str, str]] = [
    {
        "trigger": "ifmain",
        "label": "if __name__ == '__main__'",
        "detail": "Hauptprogramm-Schutz",
        "code": "if __name__ == \"__main__\":\n    main()\n",
    },
    {
        "trigger": "main",
        "label": "def main",
        "detail": "main-Funktion mit Aufruf",
        "code": "def main() -> None:\n    pass\n\n\nif __name__ == \"__main__\":\n    main()\n",
    },
    {
        "trigger": "cls",
        "label": "class",
        "detail": "Klassen-Gerüst",
        "code": "class Name:\n    def __init__(self) -> None:\n        pass\n",
    },
    {
        "trigger": "defn",
        "label": "def",
        "detail": "Funktion mit Type Hints",
        "code": "def name(arg: str) -> None:\n    pass\n",
    },
    {
        "trigger": "tryex",
        "label": "try/except",
        "detail": "Fehlerbehandlung",
        "code": "try:\n    pass\nexcept Exception as exc:\n    raise\n",
    },
    {
        "trigger": "forr",
        "label": "for",
        "detail": "for-Schleife",
        "code": "for item in items:\n    pass\n",
    },
    {
        "trigger": "pytest",
        "label": "pytest",
        "detail": "pytest-Testfunktion",
        "code": "def test_name() -> None:\n    assert True\n",
    },
    {
        "trigger": "argp",
        "label": "argparse",
        "detail": "Kommandozeilen-Parser",
        "code": (
            "import argparse\n\n"
            "def main() -> None:\n"
            "    parser = argparse.ArgumentParser(description=__doc__)\n"
            "    parser.add_argument(\"pfad\")\n"
            "    args = parser.parse_args()\n"
            "    print(args.pfad)\n\n"
            "if __name__ == \"__main__\":\n"
            "    main()\n"
        ),
    },
    {
        "trigger": "fastapi",
        "label": "FastAPI-Route",
        "detail": "GET-Endpunkt",
        "code": (
            "from fastapi import FastAPI\n\n"
            "app = FastAPI()\n\n"
            "@app.get(\"/\")\n"
            "def read_root() -> dict[str, str]:\n"
            "    return {\"status\": \"ok\"}\n"
        ),
    },
    {
        "trigger": "flask",
        "label": "Flask-Route",
        "detail": "kleine Flask-App",
        "code": (
            "from flask import Flask\n\n"
            "app = Flask(__name__)\n\n"
            "@app.get(\"/\")\n"
            "def index() -> str:\n"
            "    return \"ok\"\n\n"
            "if __name__ == \"__main__\":\n"
            "    app.run(debug=True)\n"
        ),
    },
    {
        "trigger": "djangomodel",
        "label": "Django-Model",
        "detail": "Model-Gerüst",
        "code": (
            "from django.db import models\n\n"
            "class Eintrag(models.Model):\n"
            "    titel = models.CharField(max_length=200)\n"
            "    erstellt = models.DateTimeField(auto_now_add=True)\n\n"
            "    def __str__(self) -> str:\n"
            "        return self.titel\n"
        ),
    },
    {
        "trigger": "graphql",
        "label": "GraphQL-Anfrage",
        "detail": "HTTP-Datei für GraphQL",
        "code": (
            "POST https://example.test/graphql\n"
            "Content-Type: application/json\n"
            "\n"
            "{\"query\": \"{ __typename }\"}\n"
        ),
    },
    {
        "trigger": "todo",
        "label": "TODO",
        "detail": "Aufgabe im Code",
        "code": "# TODO: \n",
    },
]


def all_snippets() -> list[dict[str, str]]:
    return list(SNIPPETS)


def matching(prefix: str) -> list[dict[str, str]]:
    if not prefix:
        return []
    low = prefix.lower()
    return [item for item in SNIPPETS if item["trigger"].startswith(low) or item["label"].lower().startswith(low)]
