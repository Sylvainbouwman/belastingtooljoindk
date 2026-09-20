"""Toetst dat TARIEVEN van de IB-pagina overeenkomt met belastingrente-ib-reeks.txt.

Datzelfde bestand staat in de repository Berekeningen, waar een gelijkwaardige
test de JavaScript-constante ertegen legt. Beide tools gebruiken dezelfde
percentagereeks maar doen er iets anders mee: hier een aanslag met dagtelling en
aanslagtermijnen, daar de tegenbewijsregeling van art. 30i lid 3 AWR in hele
maanden. De reeks is dus gedeeld gegeven, geen gedeelde code.

Waarom een bestand ertussen en niet de twee tools rechtstreeks tegen elkaar: de
repository's zien elkaar niet, dus geen van beide kan in haar eigen CI meten wat
de ander doet. Wat elke kant wel kan, is bewijzen dat haar code overeenkomt met
een leesbare reeks die in beide repository's identiek staat. Of de twee BESTANDEN
nog gelijk zijn wordt afzonderlijk gemeten met PostbusClaude/controle_rentereeks.py.

Deze test hoort te falen zodra iemand TARIEVEN wijzigt. Dat is de bedoeling: die
wijziging moet ook in de andere tool landen.
"""

from datetime import date
from pathlib import Path

import pytest

from _tarieventabellen import TARIEVEN_IB

REEKSBESTAND = Path(__file__).resolve().parent.parent / "belastingrente-ib-reeks.txt"

# De reeks in het bestand loopt tot en met deze maand. TARIEVEN heeft bewust geen
# einddatum, want de pagina rekent na de laatste ingangsdatum door met een raming
# en zegt dat erbij. Voor de vergelijking is een eindpunt nodig.
TOT_EN_MET = (2026, 12)


def _nummer(jaar: int, maand: int) -> int:
    return jaar * 12 + maand - 1


def _regels_uit_bestand() -> list[str]:
    regels = REEKSBESTAND.read_text(encoding="utf-8").splitlines()
    return [r.strip() for r in regels if r.strip() and not r.startswith("#")]


def _regels_uit_tarieven() -> list[str]:
    """TARIEVEN_IB in dezelfde vorm als het bestand: "2012-01 2012-03 2,85"."""
    oplopend = sorted(TARIEVEN_IB)
    eind = _nummer(*TOT_EN_MET)
    uit = []
    for i, (ingang, pct) in enumerate(oplopend):
        assert ingang.day == 1, f"wijziging midden in de maand vraagt beoordeling: {ingang}"
        start = _nummer(ingang.year, ingang.month)
        if i + 1 < len(oplopend):
            volgende = oplopend[i + 1][0]
            stop = _nummer(volgende.year, volgende.month) - 1
        else:
            stop = eind
        stop = min(stop, eind)
        if stop < start:
            continue
        uit.append(
            f"{start // 12:04d}-{start % 12 + 1:02d} "
            f"{stop // 12:04d}-{stop % 12 + 1:02d} "
            f"{pct:.2f}".replace(".", ",")
        )
    return uit


def test_reeksbestand_bestaat():
    assert REEKSBESTAND.is_file(), (
        f"{REEKSBESTAND.name} ontbreekt. Zonder dat bestand meet deze test niets; "
        "haal het uit de repository Berekeningen, waar het woordelijk gelijk hoort te zijn."
    )


def test_tarieven_komen_overeen_met_het_gedeelde_reeksbestand():
    assert _regels_uit_tarieven() == _regels_uit_bestand(), (
        "TARIEVEN in pages/Belastingrente_IB.py wijkt af van belastingrente-ib-reeks.txt. "
        "Werk beide bij, werk daarna hetzelfde bestand bij in de repository Berekeningen, "
        "en draai PostbusClaude/controle_rentereeks.py om te meten dat de twee bestanden "
        "weer gelijk zijn."
    )


def test_reeks_sluit_aan_zonder_gat_of_overlap():
    # Zonder deze toets kan een aanvulling stil een maand overslaan.
    vorig_eind = None
    for regel in _regels_uit_bestand():
        vanaf, tot, _ = regel.split()
        a = _nummer(*(int(d) for d in vanaf.split("-")))
        b = _nummer(*(int(d) for d in tot.split("-")))
        assert b >= a, f"periode {vanaf} {tot} eindigt voor zij begint"
        if vorig_eind is not None:
            assert a == vorig_eind + 1, f"gat of overlap bij {vanaf}"
        vorig_eind = b
    assert vorig_eind is not None, "het reeksbestand bevat geen enkele periode"


def test_de_ib_uitzondering_van_juli_2020_staat_erin():
    # De verlaging naar 0,01 procent ging voor de meeste belastingen per 1 juni 2020 in,
    # voor de inkomstenbelasting pas per 1 juli (Verzamelspoedwet COVID-19, Stb. 2020, 200).
    # Die ene maand verschil is in september 2026 aantoonbaar een keer fout gegaan, dus
    # hij wordt hier apart vastgelegd in plaats van alleen in de reeks mee te lopen.
    regels = _regels_uit_bestand()
    assert "2020-07 2020-09 0,01" in regels, (
        "De IB-uitzondering per 1 juli 2020 staat niet meer zo in de reeks. "
        "Controleer of hier niet per ongeluk de algemene ingangsdatum van 1 juni is gezet."
    )
    assert (date(2020, 7, 1), 0.01) in TARIEVEN_IB


@pytest.mark.parametrize("jaar, maand", [(2026, 12)])
def test_de_reeks_eindigt_waar_zij_hoort(jaar, maand):
    # Het percentage wordt jaarlijks per 1 januari vastgesteld. Verleng de reeks pas
    # nadat het nieuwe percentage is teruggevonden in de bron, en dan in beide tools.
    laatste = _regels_uit_bestand()[-1].split()[1]
    assert laatste == f"{jaar:04d}-{maand:02d}"
