"""Tests voor het uitlezen van het KvK-basisprofiel.

Het profiel hieronder is de structuur van een echt antwoord van de Basisprofiel-API,
opgehaald op 18-08-2026. De veldnamen zijn daarmee geen aanname.
"""

import pytest

from _kvk import (
    adres,
    handelsnamen,
    kvk_datum,
    profiel_kort,
    rechtsvorm,
    sbi_gesplitst,
    websites,
    werkzame_personen,
)


ECHT_PROFIEL = {
    "kvkNummer": "68750110",
    "indNonMailing": "Ja",
    "naam": "Bikerfix",
    "formeleRegistratiedatum": "20170512",
    "materieleRegistratie": {"datumAanvang": "20170512"},
    "totaalWerkzamePersonen": 1,
    "handelsnamen": [
        {"naam": "Bikerfix", "volgorde": 0},
        {"naam": "Bikerfix Assen", "volgorde": 1},
    ],
    "sbiActiviteiten": [
        {"sbiCode": "95320", "sbiOmschrijving": "Reparatie en onderhoud van motorfietsen",
         "indHoofdactiviteit": "Ja"},
        {"sbiCode": "16110", "sbiOmschrijving": "Zagen en schaven van hout",
         "indHoofdactiviteit": "Nee"},
        {"sbiCode": "25530", "sbiOmschrijving": "Metaalbewerking",
         "indHoofdactiviteit": "Nee"},
    ],
    "_embedded": {
        "eigenaar": {"rechtsvorm": "Eenmanszaak", "uitgebreideRechtsvorm": "Eenmanszaak"},
        "hoofdvestiging": {
            "vestigingsnummer": "000037162403",
            "kvkNummer": "68750110",
            "eersteHandelsnaam": "Bikerfix",
            "indHoofdvestiging": "Ja",
            "indCommercieleVestiging": "Ja",
            "totaalWerkzamePersonen": 1,
            "adressen": [{
                "type": "bezoekadres",
                "indAfgeschermd": "Nee",
                "volledigAdres": "Zwartwatersweg 83 9402SM Assen",
                "straatnaam": "Zwartwatersweg",
                "huisnummer": 83,
                "postcode": "9402SM",
                "plaats": "Assen",
                "land": "Nederland",
            }],
            "websites": ["www.bikerfix.nl"],
        },
    },
}


# ── Datumnotatie ────────────────────────────────────────────────────────────

def test_kvk_datum_naar_nederlandse_notatie():
    assert kvk_datum("20170512") == "12-05-2017"
    assert kvk_datum("20260101") == "01-01-2026"


@pytest.mark.parametrize("waarde", [None, "", "2017", "20170532xx", "abcdefgh", 20170512.0])
def test_kvk_datum_weigert_wat_geen_datum_is(waarde):
    """Beter niets tonen dan een onzinnige datum."""
    assert kvk_datum(waarde) is None


# ── Losse velden ────────────────────────────────────────────────────────────

def test_rechtsvorm_uit_de_eigenaar():
    assert rechtsvorm(ECHT_PROFIEL) == "Eenmanszaak"


def test_uitgebreide_rechtsvorm_heeft_voorkeur():
    profiel = {"_embedded": {"eigenaar": {
        "rechtsvorm": "Besloten vennootschap",
        "uitgebreideRechtsvorm": "Besloten vennootschap met gewone structuur",
    }}}
    assert rechtsvorm(profiel) == "Besloten vennootschap met gewone structuur"


def test_handelsnamen_in_de_volgorde_van_de_kvk():
    assert handelsnamen(ECHT_PROFIEL) == ["Bikerfix", "Bikerfix Assen"]


def test_handelsnamen_worden_gesorteerd_ook_als_de_kvk_ze_omgekeerd_geeft():
    profiel = {"handelsnamen": [{"naam": "Tweede", "volgorde": 1},
                                {"naam": "Eerste", "volgorde": 0}]}
    assert handelsnamen(profiel) == ["Eerste", "Tweede"]


def test_adres_van_de_hoofdvestiging():
    assert adres(ECHT_PROFIEL) == "Zwartwatersweg 83 9402SM Assen"


def test_bezoekadres_heeft_voorkeur_boven_postadres():
    profiel = {"_embedded": {"hoofdvestiging": {"adressen": [
        {"type": "postadres", "volledigAdres": "Postbus 1 1000AA Amsterdam"},
        {"type": "bezoekadres", "volledigAdres": "Damrak 1 1012LG Amsterdam"},
    ]}}}
    assert adres(profiel) == "Damrak 1 1012LG Amsterdam"


def test_afgeschermd_adres_wordt_niet_alsnog_samengesteld():
    """Bij een woonadres schermt de KvK af. Dat hoort afgeschermd te blijven."""
    profiel = {"_embedded": {"hoofdvestiging": {"adressen": [{
        "type": "bezoekadres", "indAfgeschermd": "Ja",
        "straatnaam": "Dorpsstraat", "huisnummer": 1, "plaats": "Assen",
    }]}}}
    assert adres(profiel) == "Afgeschermd op verzoek"


def test_adres_valt_terug_op_de_losse_onderdelen():
    profiel = {"_embedded": {"hoofdvestiging": {"adressen": [{
        "type": "bezoekadres", "straatnaam": "Damrak", "huisnummer": 1,
        "postcode": "1012LG", "plaats": "Amsterdam",
    }]}}}
    assert adres(profiel) == "Damrak 1 1012LG Amsterdam"


def test_werkzame_personen_als_getal():
    assert werkzame_personen(ECHT_PROFIEL) == 1
    assert werkzame_personen({"totaalWerkzamePersonen": "12"}) == 12


def test_websites():
    assert websites(ECHT_PROFIEL) == ["www.bikerfix.nl"]


# ── SBI-codes ───────────────────────────────────────────────────────────────

def test_sbi_wordt_gesplitst_in_hoofd_en_neven():
    hoofd, neven = sbi_gesplitst(ECHT_PROFIEL)
    assert [c["sbiCode"] for c in hoofd] == ["95320"]
    assert [c["sbiCode"] for c in neven] == ["16110", "25530"]


def test_sbi_zonder_activiteiten():
    assert sbi_gesplitst({}) == ([], [])


# ── Het volledige blok dat de pagina toont ──────────────────────────────────

def test_profiel_kort_op_het_echte_antwoord():
    p = profiel_kort(ECHT_PROFIEL)
    assert p["naam"] == "Bikerfix"
    assert p["rechtsvorm"] == "Eenmanszaak"
    assert p["geregistreerd"] == "12-05-2017"
    assert p["werkzame_personen"] == 1
    assert p["adres"] == "Zwartwatersweg 83 9402SM Assen"
    assert p["websites"] == ["www.bikerfix.nl"]
    assert p["vestigingsnummer"] == "000037162403"
    assert p["non_mailing"] is True
    assert p["handelsnamen"] == ["Bikerfix", "Bikerfix Assen"]


@pytest.mark.parametrize("profiel", [None, {}, {"_embedded": {}}, {"_embedded": {"eigenaar": None}}])
def test_profiel_kort_valt_niet_om_op_een_mager_antwoord(profiel):
    """De KvK laat takken weg in plaats van ze leeg mee te sturen. Dan mag er
    niets omvallen en mag er ook geen 'None' op de pagina belanden."""
    p = profiel_kort(profiel)
    assert p["rechtsvorm"] is None
    assert p["adres"] is None
    assert p["werkzame_personen"] is None
    assert p["handelsnamen"] == []
    assert p["websites"] == []
    assert p["non_mailing"] is False


def test_profiel_kort_bevat_alleen_velden_uit_een_bevraging():
    """Vangnet tegen kostenkruip: elk veld dat de pagina toont moet uit het
    basisprofiel komen. Zou er ooit een veld bijkomen dat een tweede endpoint
    nodig heeft, dan valt deze test op omdat het uit dit antwoord niet te halen is."""
    p = profiel_kort(ECHT_PROFIEL)
    gevuld = [k for k, v in p.items() if v not in (None, [], False)]
    assert set(gevuld) <= {
        "naam", "statutaire_naam", "handelsnamen", "rechtsvorm", "geregistreerd",
        "werkzame_personen", "adres", "websites", "vestigingsnummer", "non_mailing",
    }
