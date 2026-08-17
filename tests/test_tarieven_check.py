"""Tests voor de tarievencontrole tegen belastingdienst.nl.

De offline tests draaien op een vast HTML-fragment en zijn dus altijd stabiel.
De test tegen de live pagina wordt overgeslagen als er geen internet is.
"""

from datetime import date

import pytest

from _tarieven_check import (
    KOP_ALGEMEEN,
    KOP_VPB,
    parse_tarieventabel,
    vergelijk,
)

# Vereenvoudigd fragment in exact de opmaak die de Belastingdienst gebruikt,
# inclusief de valstrikken: einddatums in dezelfde cel, een sterretje achter de
# periode, "(was 7,5)" achter het percentage en een losse datum buiten de tabel.
HTML = """
<p>Pagina laatst gewijzigd op 14-8-2026.</p>
<h2>Percentages alle belastingen (m.u.v. toeslagen en vennootschapsbelasting)</h2>
<table><tbody>
  <tr><th><h3>Periode</h3></th><th><h3>Percentage</h3></th></tr>
  <tr><th>Vanaf 1-1-2026</th><td>5</td></tr>
  <tr><th>1-1-2025 tot en met 31-12-2025*</th><td>6,5</td></tr>
  <tr><th><p>1-7-2023 tot en met 31-12-2023**</p></th><td><p>6</p></td></tr>
</tbody></table>
<h2>Percentages vennootschapsbelasting</h2>
<table><tbody>
  <tr><th><h3>Periode</h3></th><th><h3>Percentage</h3></th></tr>
  <tr><th>Vanaf 1-1-2026</th><td>5 (was 7,5)</td></tr>
  <tr><th>1-3-2015 tot en met 31-8-2016</th><td>8,05</td></tr>
</tbody></table>
"""


# ── Parser ──────────────────────────────────────────────────────────────────

def test_parser_leest_alleen_ingangsdatums():
    """Bug 4: einddatums (31-12-2025) mogen niet als nieuwe periode gelden."""
    rijen = parse_tarieventabel(HTML, KOP_ALGEMEEN)
    assert rijen == [
        (date(2026, 1, 1), 5.0),
        (date(2025, 1, 1), 6.5),
        (date(2023, 7, 1), 6.0),
    ]


def test_parser_negeert_datums_buiten_de_tabel():
    """Bug 4: 'Pagina laatst gewijzigd op 14-8-2026' mag niet meetellen."""
    rijen = parse_tarieventabel(HTML, KOP_ALGEMEEN)
    assert all(d.day == 1 for d, _ in rijen)
    assert date(2026, 8, 14) not in [d for d, _ in rijen]


def test_parser_scheidt_de_twee_tabellen():
    algemeen = parse_tarieventabel(HTML, KOP_ALGEMEEN)
    vpb = parse_tarieventabel(HTML, KOP_VPB)
    assert len(algemeen) == 3
    assert len(vpb) == 2
    assert (date(2015, 3, 1), 8.05) in vpb
    assert (date(2015, 3, 1), 8.05) not in algemeen


def test_parser_neemt_het_geldende_en_niet_het_oude_percentage():
    """'5 (was 7,5)' moet 5 opleveren, niet 7,5."""
    vpb = parse_tarieventabel(HTML, KOP_VPB)
    assert vpb[0] == (date(2026, 1, 1), 5.0)


def test_parser_zwijgt_bij_onbekende_opmaak():
    assert parse_tarieventabel("<html>niets</html>", KOP_ALGEMEEN) == []
    assert parse_tarieventabel("", KOP_ALGEMEEN) == []


# ── Vergelijking ────────────────────────────────────────────────────────────

def test_geen_waarschuwing_als_tabellen_gelijk_zijn():
    eigen = [(date(2026, 1, 1), 5.00), (date(2025, 1, 1), 6.50)]
    assert vergelijk(eigen, parse_tarieventabel(HTML, KOP_ALGEMEEN)) is None


def test_waarschuwing_bij_nieuwere_periode():
    eigen = [(date(2025, 1, 1), 6.50)]
    melding = vergelijk(eigen, parse_tarieventabel(HTML, KOP_ALGEMEEN))
    assert melding is not None
    assert "01-01-2026" in melding


def test_waarschuwing_bij_herzien_percentage():
    """Belastingrente wordt met terugwerkende kracht herzien; dat moet opvallen."""
    eigen = [(date(2026, 1, 1), 7.50)]
    melding = vergelijk(eigen, parse_tarieventabel(HTML, KOP_ALGEMEEN))
    assert melding is not None
    assert "5%" in melding and "7.5%" in melding


def test_zwijgt_bij_lege_invoer():
    assert vergelijk([], [(date(2026, 1, 1), 5.0)]) is None
    assert vergelijk([(date(2026, 1, 1), 5.0)], []) is None


# ── Tegen de echte pagina ───────────────────────────────────────────────────

@pytest.mark.parametrize("module,kop", [
    ("pages.Belastingrente_IB", KOP_ALGEMEEN),
    ("pages.Belastingrente_VpB", KOP_VPB),
])
def test_tarieventabel_in_de_code_komt_overeen_met_belastingdienst_nl(module, kop):
    """Netwerktest: vergelijkt de hardgecodeerde tabel regel voor regel met de bron.

    Deze test heeft de twee datafouten in de VpB-tabel gevonden (1-3-2016 in
    plaats van 1-3-2015, en de ontbrekende rijen van vóór april 2014).
    """
    requests = pytest.importorskip("requests")
    from _tarieven_check import BELASTINGDIENST_URL

    try:
        resp = requests.get(
            BELASTINGDIENST_URL, timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; BouwmanTools)"},
        )
        resp.raise_for_status()
    except Exception as exc:
        pytest.skip(f"belastingdienst.nl niet bereikbaar: {exc}")

    online = parse_tarieventabel(resp.text, kop)
    assert online, "tabel niet herkend - opmaak van de pagina is waarschijnlijk gewijzigd"

    eigen = _tarieven_uit_pagina(module)
    assert eigen == online, (
        f"\nin de code : {eigen}\nop de site : {online}"
    )


def _tarieven_uit_pagina(modulenaam: str):
    """Leest de TARIEVEN-constante uit een Streamlit-pagina zonder die te draaien."""
    import ast
    from pathlib import Path

    pad = Path(__file__).resolve().parent.parent / (modulenaam.replace(".", "/") + ".py")
    boom = ast.parse(pad.read_text(encoding="utf-8"))
    for knoop in boom.body:
        if isinstance(knoop, ast.Assign) and getattr(knoop.targets[0], "id", "") == "TARIEVEN":
            rijen = []
            for element in knoop.value.elts:
                datum_call, pct = element.elts
                jaar, maand, dag = (a.value for a in datum_call.args)
                rijen.append((date(jaar, maand, dag), float(pct.value)))
            return sorted(rijen, reverse=True)
    raise AssertionError(f"TARIEVEN niet gevonden in {pad}")


