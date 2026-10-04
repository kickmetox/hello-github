"""Isolierte KI-Dokument-Wizards — 2.6.16.

Geführte Standardabläufe (Formular, Anschreiben, Kaufvertrag, Rechnung)
als strukturierte User-Abfragen — **nicht** als generischer Chat.
Standard: lokale Template-/Regel-Generierung. Optionaler LLM-Hook nur
hinter dem Wizard (``use_llm=True`` + registrierter Hook).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union

PathLike = Union[str, Path]

# Wizard-IDs (stabil für API/CLI/UI)
WIZARD_FORMULAR = "formular"
WIZARD_ANSCHREIBEN = "anschreiben"
WIZARD_KAUFVERTRAG = "kaufvertrag"
WIZARD_RECHNUNG = "rechnung"

WIZARD_KINDS: Dict[str, str] = {
    WIZARD_FORMULAR: "Formularerstellung",
    WIZARD_ANSCHREIBEN: "Anschreiben",
    WIZARD_KAUFVERTRAG: "Kaufvertrag",
    WIZARD_RECHNUNG: "Rechnungsformular",
}

# Unternehmensfelder (optional, company_mode)
COMPANY_FIELD_KEYS: tuple[str, ...] = (
    "firma",
    "adresse",
    "ust_id",
    "telefon",
    "email",
    "iban",
    "bic",
    "vertreter",
)

COMPANY_FIELD_LABELS: Dict[str, str] = {
    "firma": "Firma",
    "adresse": "Adresse",
    "ust_id": "USt-Id",
    "telefon": "Telefon",
    "email": "E-Mail",
    "iban": "IBAN",
    "bic": "BIC",
    "vertreter": "Vertreter",
}

# Typ-spezifische Felder (generisch)
KIND_FIELD_KEYS: Dict[str, tuple[str, ...]] = {
    WIZARD_FORMULAR: ("title", "beschreibung", "felder"),
    WIZARD_ANSCHREIBEN: (
        "absender",
        "empfaenger",
        "betreff",
        "anliegen",
        "ort",
        "datum",
    ),
    WIZARD_KAUFVERTRAG: (
        "verkaeufer",
        "kaeufer",
        "gegenstand",
        "preis",
        "ort",
        "datum",
    ),
    WIZARD_RECHNUNG: (
        "rechnungsnr",
        "empfaenger",
        "leistung",
        "menge",
        "einzelpreis",
        "betrag",
        "ort",
        "datum",
    ),
}

KIND_FIELD_LABELS: Dict[str, str] = {
    "title": "Formulartitel",
    "beschreibung": "Beschreibung",
    "felder": "Felder (Komma-getrennt)",
    "absender": "Absender",
    "empfaenger": "Empfänger",
    "betreff": "Betreff",
    "anliegen": "Anliegen / Inhalt",
    "ort": "Ort",
    "datum": "Datum",
    "verkaeufer": "Verkäufer",
    "kaeufer": "Käufer",
    "gegenstand": "Kaufgegenstand",
    "preis": "Kaufpreis",
    "rechnungsnr": "Rechnungsnummer",
    "leistung": "Leistung / Position",
    "menge": "Menge",
    "einzelpreis": "Einzelpreis",
    "betrag": "Gesamtbetrag",
}

# Optionaler LLM-Hook: (kind, fields, company) -> str | None
_LLM_HOOK: Optional[Callable[..., Optional[str]]] = None


def register_llm_hook(
    hook: Optional[Callable[..., Optional[str]]],
) -> None:
    """Optionalen LLM-Hook registrieren (nur Wizard-Pfad, kein freier Chat)."""
    global _LLM_HOOK
    _LLM_HOOK = hook


def get_llm_hook() -> Optional[Callable[..., Optional[str]]]:
    return _LLM_HOOK


def llm_hook_available() -> bool:
    return _LLM_HOOK is not None


@dataclass
class WizardFieldSpec:
    key: str
    label: str
    required: bool = False
    company: bool = False
    placeholder: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KiWizardDocument:
    """Editierbares InstantLens-Doc / Word-Suite-Ergebnis eines KI-Wizards."""

    kind: str
    title: str
    text: str
    fields: dict[str, str] = field(default_factory=dict)
    company_mode: bool = False
    company: dict[str, str] = field(default_factory=dict)
    mode: str = "template"
    llm_used: bool = False
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "kind_label": WIZARD_KINDS.get(self.kind, self.kind),
            "title": self.title,
            "text": self.text,
            "fields": dict(self.fields),
            "company_mode": self.company_mode,
            "company": dict(self.company),
            "mode": self.mode,
            "llm_used": self.llm_used,
            "meta": dict(self.meta),
            "word_count": len((self.text or "").split()),
            "char_count": len(self.text or ""),
        }


def list_ki_wizards() -> list[dict[str, Any]]:
    """Verfügbare isolierte KI-Wizards auflisten."""
    out: list[dict[str, Any]] = []
    for kid, label in WIZARD_KINDS.items():
        out.append(
            {
                "id": kid,
                "label": label,
                "fields": [f.to_dict() for f in wizard_field_specs(kid)],
                "company_fields": [
                    {"key": k, "label": COMPANY_FIELD_LABELS[k]}
                    for k in COMPANY_FIELD_KEYS
                ],
            }
        )
    return out


def wizard_field_specs(kind: str) -> list[WizardFieldSpec]:
    kid = _normalize_kind(kind)
    specs: list[WizardFieldSpec] = []
    for key in KIND_FIELD_KEYS.get(kid, ()):
        specs.append(
            WizardFieldSpec(
                key=key,
                label=KIND_FIELD_LABELS.get(key, key),
                required=key
                in (
                    "title",
                    "betreff",
                    "gegenstand",
                    "preis",
                    "leistung",
                    "rechnungsnr",
                ),
                placeholder=_placeholder(kid, key),
            )
        )
    return specs


def _normalize_kind(kind: str) -> str:
    k = (kind or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "form": WIZARD_FORMULAR,
        "forms": WIZARD_FORMULAR,
        "formularerstellung": WIZARD_FORMULAR,
        "letter": WIZARD_ANSCHREIBEN,
        "cover_letter": WIZARD_ANSCHREIBEN,
        "anschreiben": WIZARD_ANSCHREIBEN,
        "contract": WIZARD_KAUFVERTRAG,
        "kauf": WIZARD_KAUFVERTRAG,
        "invoice": WIZARD_RECHNUNG,
        "rechnungsformular": WIZARD_RECHNUNG,
        "rechnung": WIZARD_RECHNUNG,
    }
    kid = aliases.get(k, k)
    if kid not in WIZARD_KINDS:
        raise ValueError(
            f"Unbekannter Wizard-Typ: {kind!r}. "
            f"Erlaubt: {', '.join(WIZARD_KINDS)}"
        )
    return kid


def _placeholder(kind: str, key: str) -> str:
    today = date.today().strftime("%d.%m.%Y")
    defaults = {
        "title": "Kontaktformular",
        "beschreibung": "Bitte ausfüllen und zurücksenden.",
        "felder": "Name, E-Mail, Nachricht",
        "absender": "Max Mustermann",
        "empfaenger": "Firma Beispiel GmbH",
        "betreff": "Bewerbung / Anfrage",
        "anliegen": "Hiermit bewerbe ich mich um …",
        "ort": "Berlin",
        "datum": today,
        "verkaeufer": "Verkäufer Name",
        "kaeufer": "Käufer Name",
        "gegenstand": "Gebrauchter Laptop",
        "preis": "250,00 EUR",
        "rechnungsnr": "R-2026-001",
        "leistung": "Beratungsleistung",
        "menge": "1",
        "einzelpreis": "100,00 EUR",
        "betrag": "100,00 EUR",
    }
    return defaults.get(key, "")


def _clean_map(data: Mapping[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if not data:
        return out
    for k, v in data.items():
        if v is None:
            continue
        s = str(v).strip()
        if s:
            out[str(k).strip()] = s
    return out


def _company_block(company: Mapping[str, str]) -> str:
    if not company:
        return ""
    lines = ["## Unternehmensangaben", ""]
    for key in COMPANY_FIELD_KEYS:
        val = company.get(key, "").strip()
        if val:
            lines.append(f"**{COMPANY_FIELD_LABELS.get(key, key)}:** {val}")
    lines.append("")
    return "\n".join(lines)


def _parse_field_list(raw: str) -> list[str]:
    parts = [p.strip() for p in (raw or "").replace(";", ",").split(",")]
    return [p for p in parts if p]


def _render_formular(fields: Mapping[str, str], company: Mapping[str, str]) -> str:
    title = fields.get("title") or "Formular"
    desc = fields.get("beschreibung") or ""
    labels = _parse_field_list(fields.get("felder") or "Name, E-Mail, Nachricht")
    lines = [f"# {title}", ""]
    if desc:
        lines.extend([desc, ""])
    cb = _company_block(company)
    if cb:
        lines.append(cb.rstrip())
        lines.append("")
    lines.append("## Felder")
    lines.append("")
    for i, lab in enumerate(labels, 1):
        lines.append(f"{i}. **{lab}:** _______________________________")
    lines.extend(["", "☐ Ich stimme der Verarbeitung zu.", "", "Datum: ________    Unterschrift: ________"])
    return "\n".join(lines)


def _render_anschreiben(fields: Mapping[str, str], company: Mapping[str, str]) -> str:
    absender = fields.get("absender") or company.get("firma") or "Absender"
    emp = fields.get("empfaenger") or "Empfänger"
    betreff = fields.get("betreff") or "Betreff"
    anliegen = fields.get("anliegen") or "…"
    ort = fields.get("ort") or ""
    datum = fields.get("datum") or date.today().strftime("%d.%m.%Y")
    lines = ["# Anschreiben", ""]
    cb = _company_block(company)
    if cb:
        lines.append(cb.rstrip())
        lines.append("")
    lines.extend(
        [
            absender,
            "",
            emp,
            "",
            f"{ort}, {datum}".strip(", "),
            "",
            f"**Betreff:** {betreff}",
            "",
            "Sehr geehrte Damen und Herren,",
            "",
            anliegen,
            "",
            "Mit freundlichen Grüßen",
            "",
            absender,
        ]
    )
    if company.get("vertreter"):
        lines.append(f"i. V. {company['vertreter']}")
    return "\n".join(lines)


def _render_kaufvertrag(fields: Mapping[str, str], company: Mapping[str, str]) -> str:
    verk = fields.get("verkaeufer") or company.get("firma") or "Verkäufer"
    kauf = fields.get("kaeufer") or "Käufer"
    gegenstand = fields.get("gegenstand") or "Kaufgegenstand"
    preis = fields.get("preis") or "0,00 EUR"
    ort = fields.get("ort") or ""
    datum = fields.get("datum") or date.today().strftime("%d.%m.%Y")
    lines = [
        "# Kaufvertrag",
        "",
        f"Zwischen **{verk}** (Verkäufer) und **{kauf}** (Käufer)",
        "wird folgender Kaufvertrag geschlossen:",
        "",
    ]
    cb = _company_block(company)
    if cb:
        lines.append(cb.rstrip())
        lines.append("")
    lines.extend(
        [
            "## § 1 Kaufgegenstand",
            "",
            gegenstand,
            "",
            "## § 2 Kaufpreis",
            "",
            f"Der Kaufpreis beträgt **{preis}**.",
            "",
            "## § 3 Eigentumsübergang",
            "",
            "Das Eigentum geht mit vollständiger Zahlung auf den Käufer über.",
            "",
            "## § 4 Schlussbestimmungen",
            "",
            "Sollten einzelne Bestimmungen unwirksam sein, bleibt der Vertrag im Übrigen wirksam.",
            "",
            f"Ort, Datum: {ort}, {datum}".strip(", "),
            "",
            "________________________          ________________________",
            "Verkäufer                                           Käufer",
        ]
    )
    return "\n".join(lines)


def _render_rechnung(fields: Mapping[str, str], company: Mapping[str, str]) -> str:
    nr = fields.get("rechnungsnr") or "R-0001"
    emp = fields.get("empfaenger") or "Rechnungsempfänger"
    leistung = fields.get("leistung") or "Leistung"
    menge = fields.get("menge") or "1"
    einzel = fields.get("einzelpreis") or fields.get("betrag") or "0,00 EUR"
    betrag = fields.get("betrag") or einzel
    ort = fields.get("ort") or ""
    datum = fields.get("datum") or date.today().strftime("%d.%m.%Y")
    firma = company.get("firma") or "Rechnungssteller"
    lines = [
        "# Rechnung",
        "",
        f"**Rechnungsnummer:** {nr}",
        f"**Datum:** {datum}",
        "",
    ]
    cb = _company_block(company)
    if cb:
        lines.append(cb.rstrip())
        lines.append("")
    else:
        lines.extend([f"**Von:** {firma}", ""])
    lines.extend(
        [
            f"**An:** {emp}",
            "",
            "## Positionen",
            "",
            "| Pos. | Leistung | Menge | Einzelpreis | Betrag |",
            "| ---: | --- | ---: | ---: | ---: |",
            f"| 1 | {leistung} | {menge} | {einzel} | {betrag} |",
            "",
            f"**Gesamtbetrag:** {betrag}",
            "",
        ]
    )
    if company.get("ust_id"):
        lines.append(f"USt-IdNr.: {company['ust_id']}")
    if company.get("iban"):
        lines.append(f"Zahlungsempfänger IBAN: {company['iban']}")
        if company.get("bic"):
            lines.append(f"BIC: {company['bic']}")
    lines.extend(["", f"{ort}, {datum}".strip(", "), "", "Vielen Dank für Ihren Auftrag."])
    return "\n".join(lines)


_RENDERERS: Dict[str, Callable[[Mapping[str, str], Mapping[str, str]], str]] = {
    WIZARD_FORMULAR: _render_formular,
    WIZARD_ANSCHREIBEN: _render_anschreiben,
    WIZARD_KAUFVERTRAG: _render_kaufvertrag,
    WIZARD_RECHNUNG: _render_rechnung,
}


def _default_title(kind: str, fields: Mapping[str, str], company: Mapping[str, str]) -> str:
    label = WIZARD_KINDS.get(kind, kind)
    if kind == WIZARD_FORMULAR and fields.get("title"):
        return f"Formular — {fields['title']}"
    if kind == WIZARD_ANSCHREIBEN and fields.get("betreff"):
        return f"Anschreiben — {fields['betreff']}"
    if kind == WIZARD_KAUFVERTRAG and fields.get("gegenstand"):
        return f"Kaufvertrag — {fields['gegenstand']}"
    if kind == WIZARD_RECHNUNG and fields.get("rechnungsnr"):
        return f"Rechnung — {fields['rechnungsnr']}"
    if company.get("firma"):
        return f"{label} — {company['firma']}"
    return f"Word-Suite — {label}"


def generate_ki_document(
    kind: str,
    *,
    fields: Mapping[str, Any] | None = None,
    company: Mapping[str, Any] | None = None,
    company_mode: bool | None = None,
    title: str | None = None,
    use_llm: bool = False,
    out: PathLike | None = None,
) -> KiWizardDocument:
    """Dokument aus Wizard-Feldern erzeugen (Template oder optionaler LLM-Hook)."""
    kid = _normalize_kind(kind)
    fld = _clean_map(fields)
    # Defaults für leere Keys
    for key in KIND_FIELD_KEYS.get(kid, ()):
        if key not in fld:
            ph = _placeholder(kid, key)
            if ph:
                fld[key] = ph
    comp = _clean_map(company)
    if company_mode is None:
        company_mode = bool(comp)
    if not company_mode:
        comp = {}

    llm_used = False
    mode = "template"
    text: Optional[str] = None
    if use_llm:
        hook = get_llm_hook()
        if hook is None:
            raise ValueError(
                "LLM-Hook nicht registriert. "
                "Nutzen Sie Template-Generierung (use_llm=False) oder "
                "register_llm_hook(...)."
            )
        try:
            text = hook(kind=kid, fields=fld, company=comp)
        except TypeError:
            text = hook(kid, fld, comp)  # type: ignore[misc]
        if not text or not str(text).strip():
            raise ValueError("LLM-Hook lieferte keinen Text.")
        text = str(text)
        llm_used = True
        mode = "llm"
    else:
        text = _RENDERERS[kid](fld, comp)

    doc_title = (title or "").strip() or _default_title(kid, fld, comp)
    doc = KiWizardDocument(
        kind=kid,
        title=doc_title,
        text=text,
        fields=fld,
        company_mode=bool(company_mode and comp),
        company=comp,
        mode=mode,
        llm_used=llm_used,
        meta={
            "generator": "instantlensdoc.core.ki_wizards",
            "version": "2.6.16",
            "isolated": True,
            "free_chat": False,
        },
    )
    if out is not None:
        dest = Path(out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(doc.text, encoding="utf-8")
        doc.meta["out"] = str(dest)
    return doc


def run_ki_wizard(
    kind: str,
    *,
    fields: Mapping[str, Any] | None = None,
    company: Mapping[str, Any] | None = None,
    company_mode: bool | None = None,
    title: str | None = None,
    use_llm: bool = False,
    out: PathLike | None = None,
) -> KiWizardDocument:
    """Alias für generate_ki_document — 2.6.16."""
    return generate_ki_document(
        kind,
        fields=fields,
        company=company,
        company_mode=company_mode,
        title=title,
        use_llm=use_llm,
        out=out,
    )
