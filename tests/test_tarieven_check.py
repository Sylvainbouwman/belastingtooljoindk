"""Tests voor de tarievencontrole tegen belastingdienst.nl.

De offline tests draaien op een vast HTML-fragment en zijn dus altijd stabiel.
De test tegen de live pagina wordt overgeslagen als er geen internet is.
"""

from datetime import date

import pytest

from _tarieven_check import (
    KOP_ALGEMEEN,
    KOP_VPB,
    controleer_nieuwe_tarieven,
    controleregel,
    parse_tarieventabel,
    vergelijk,
)
from _tarieventabellen import tarieven_uit_pagina

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

# De IB-reeks wijkt op één rij bewust van de algemene tabel af: de
# coronaverlaging naar 0,01% ging voor de inkomstenbelasting pas op 1 juli 2020
# in. Dat staat op de bronpagina in voetnoot *** ónder de tabel, dus de
# tabelvergelijking kan het niet zien. De afwijking staat hier als gegeven, met
# de brontabelrij als sleutel en de eigen rij als waarde, zodat elke andere rij
# nog wél 1-op-1 wordt getoetst.
AFWIJKINGEN_IB = {
    (date(2020, 6, 1), 0.01): (date(2020, 7, 1), 0.01),
}

NETWERKTABELLEN = [
    ("pages.Belastingrente_IB", KOP_ALGEMEEN, AFWIJKINGEN_IB),
    ("pages.Belastingrente_VpB", KOP_VPB, {}),
]


def _haal_bronpagina():
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
    return resp.text


@pytest.mark.parametrize("module,kop,afwijkingen", NETWERKTABELLEN)
def test_tarieventabel_in_de_code_komt_overeen_met_belastingdienst_nl(module, kop, afwijkingen):
    """Netwerktest: vergelijkt de hardgecodeerde tabel regel voor regel met de bron.

    Deze test heeft de twee datafouten in de VpB-tabel gevonden (1-3-2016 in
    plaats van 1-3-2015, en de ontbrekende rijen van vóór april 2014).
    """
    online = parse_tarieventabel(_haal_bronpagina(), kop)
    assert online, "tabel niet herkend - opmaak van de pagina is waarschijnlijk gewijzigd"

    verwacht = sorted((afwijkingen.get(rij, rij) for rij in online), reverse=True)
    eigen = tarieven_uit_pagina(module)
    assert eigen == verwacht, (
        f"\nin de code : {eigen}\nverwacht   : {verwacht}\nop de site : {online}"
    )


@pytest.mark.parametrize("module,kop,afwijkingen", NETWERKTABELLEN)
def test_de_bewuste_afwijkingen_bestaan_nog_op_de_bronpagina(module, kop, afwijkingen):
    """Een afwijking die de bron niet meer kent, dekt stil niets meer af.

    Zonder deze test zou AFWIJKINGEN_IB blijven staan als de Belastingdienst de
    rij van 1-6-2020 ooit wijzigt of splitst, en zou de vorige test die
    wijziging dan verkeerd uitleggen.
    """
    online = parse_tarieventabel(_haal_bronpagina(), kop)
    assert online, "tabel niet herkend - opmaak van de pagina is waarschijnlijk gewijzigd"
    for bronrij in afwijkingen:
        assert bronrij in online, (
            f"{bronrij} staat niet meer in de tabel {kop!r}; de bewuste "
            f"afwijking in {module} moet opnieuw worden beoordeeld"
        )


def test_de_ib_uitzondering_staat_nog_als_voetnoot_op_de_bronpagina():
    """De grondslag van de IB-afwijking, aan de bron zelf getoetst.

    Niet als vervanging van Stb. 2020, 200 — dat is de wettelijke grondslag —
    maar zodat opvalt wanneer de Belastingdienst de uitzondering herformuleert
    of intrekt.
    """
    import re
    tekst = " ".join(re.sub(r"<[^>]+>", " ", _haal_bronpagina()).split())
    assert ("Voor de inkomstenbelasting ging de tijdelijke verlaging in "
            "vanaf 1-7-2020") in tekst


# ── De uitkomst van de controle: gecontroleerd of niet ──────────────────────
# "Geen waarschuwing" betekende voorheen twee dingen: de reeks klopt, of er is
# niets gecontroleerd. De gebruiker las het tweede als het eerste. Deze tests
# leggen vast dat de toestanden te onderscheiden zijn.

EIGEN = [(date(2026, 1, 1), 5.00), (date(2025, 1, 1), 6.50)]


def test_geslaagde_controle_zonder_afwijking(monkeypatch):
    monkeypatch.setattr("_tarieven_check._haal_pagina_op", lambda maand: HTML)
    controle = controleer_nieuwe_tarieven(EIGEN, KOP_ALGEMEEN)
    assert controle.status == "gelijk"
    assert controle.melding is None


def test_afwijking_levert_status_afwijking(monkeypatch):
    monkeypatch.setattr("_tarieven_check._haal_pagina_op", lambda maand: HTML)
    controle = controleer_nieuwe_tarieven([(date(2026, 1, 1), 7.50)], KOP_ALGEMEEN)
    assert controle.status == "afwijking"
    assert "5%" in controle.melding


def test_onbereikbare_bron_is_te_onderscheiden_van_een_geslaagde_controle(monkeypatch):
    """De kern van het punt: niet dezelfde uitkomst als een controle die slaagde."""
    def stuk(maand):
        raise ConnectionError("geen netwerk")

    monkeypatch.setattr("_tarieven_check._haal_pagina_op", stuk)
    onbereikbaar = controleer_nieuwe_tarieven(EIGEN, KOP_ALGEMEEN)

    monkeypatch.setattr("_tarieven_check._haal_pagina_op", lambda maand: HTML)
    gelijk = controleer_nieuwe_tarieven(EIGEN, KOP_ALGEMEEN)

    assert onbereikbaar.status == "onbereikbaar"
    assert onbereikbaar.status != gelijk.status
    assert onbereikbaar.melding is not None
    assert controleregel(onbereikbaar) != controleregel(gelijk)


def test_een_netwerkfout_laat_de_pagina_niet_stuklopen(monkeypatch):
    """Zichtbaar melden mag; een exceptie doorlaten naar de pagina niet."""
    def stuk(maand):
        raise TimeoutError("te lang")

    monkeypatch.setattr("_tarieven_check._haal_pagina_op", stuk)
    assert controleer_nieuwe_tarieven(EIGEN, KOP_ALGEMEEN).status == "onbereikbaar"


def test_onleesbare_pagina_meldt_dat_er_niets_is_gecontroleerd(monkeypatch):
    """Ook een gewijzigde opmaak van de bron gaf eerst stilzwijgend None terug."""
    monkeypatch.setattr("_tarieven_check._haal_pagina_op",
                        lambda maand: "<html>niets</html>")
    controle = controleer_nieuwe_tarieven(EIGEN, KOP_ALGEMEEN)
    assert controle.status == "onleesbaar"
    assert controle.melding is not None


def test_niet_gedekt_wordt_in_de_voettekst_gemeld(monkeypatch):
    """Wat de controle niet dekt, moet zij zelf zeggen — ook als zij slaagt."""
    monkeypatch.setattr("_tarieven_check._haal_pagina_op", lambda maand: HTML)
    controle = controleer_nieuwe_tarieven(EIGEN, KOP_ALGEMEEN, "voetnoot valt erbuiten")
    assert controle.status == "gelijk"
    assert "voetnoot valt erbuiten" in controleregel(controle)


def test_alleen_de_ib_pagina_geeft_niet_gedekt_mee():
    """Het onderscheid uit de code zelf, zodat het niet stil verdwijnt."""
    from pathlib import Path

    wortel = Path(__file__).resolve().parent.parent
    ib = (wortel / "pages/Belastingrente_IB.py").read_text(encoding="utf-8")
    vpb = (wortel / "pages/Belastingrente_VpB.py").read_text(encoding="utf-8")

    assert "controleer_nieuwe_tarieven(TARIEVEN, KOP_ALGEMEEN, NIET_GEDEKT)" in ib
    assert "1 juli 2020" in ib
    assert "controleer_nieuwe_tarieven(TARIEVEN, KOP_VPB)" in vpb
