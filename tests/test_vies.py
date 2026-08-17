"""Tests voor de VIES BTW-controle."""

import pytest

from _vies import (
    adres_regels,
    duid_antwoord,
    parse_btw,
    rsin_uit_btw_nummer,
)


# ── Invoer opschonen ────────────────────────────────────────────────────────

@pytest.mark.parametrize("invoer,land,nummer", [
    ("NL820646660B01", "NL", "820646660B01"),
    ("nl820646660b01", "NL", "820646660B01"),
    ("NL 8206.46660.B01", "NL", "820646660B01"),
    ("BE-0123-456-789", "BE", "0123456789"),
    ("DE 123 456 789", "DE", "123456789"),
])
def test_geldige_nummers_worden_gesplitst(invoer, land, nummer):
    assert parse_btw(invoer) == (land, nummer)


@pytest.mark.parametrize("alias,verwacht", [
    ("GR123456789", "EL"),   # mensen typen GR, VIES gebruikt EL
    ("UK123456789", "XI"),
    ("GB123456789", "XI"),
])
def test_landcode_aliassen(alias, verwacht):
    land, _ = parse_btw(alias)
    assert land == verwacht


@pytest.mark.parametrize("invoer", [
    "",
    None,
    "NL",
    "XX123456789",          # geen EU-land
    "12345",                # geen landcode
    "NL" + "1" * 13,        # te lang
])
def test_ongeldige_invoer_wordt_geweigerd(invoer):
    assert parse_btw(invoer) == (None, None)


@pytest.mark.parametrize("invoer", [
    "nl<img src=x onerror=alert(1)>",
    "NL123<script>alert(1)</script>",
    "nl/../../etc/passwd",
    "NL123%0d%0aHost: evil",
])
def test_opmaaktekens_worden_geweigerd_niet_doorgelaten(invoer):
    """Deze invoer belandde voorheen zowel in de opgevraagde URL als in de HTML
    van de resultaatpagina."""
    land, nummer = parse_btw(invoer)
    assert (land, nummer) == (None, None) or all(c.isalnum() for c in nummer)


def test_resultaat_bevat_nooit_html_tekens():
    for rommel in ("nl<b>x</b>", "NL'\"><x", "nl&amp;1"):
        _, nummer = parse_btw(rommel)
        if nummer:
            assert not set(nummer) & set("<>&\"'/=%")


# ── Antwoord duiden ─────────────────────────────────────────────────────────

def test_geldig_nummer():
    uitkomst = duid_antwoord({
        "isValid": True, "userError": "VALID",
        "name": "ABN AMRO BANK N.V.",
        "address": "\nGUSTAV MAHLERLAAN 00010\n1082PP AMSTERDAM\n",
    })
    assert uitkomst["status"] == "geldig"
    assert uitkomst["naam"] == "ABN AMRO BANK N.V."
    assert "AMSTERDAM" in uitkomst["adres"]


def test_ongeldig_nummer():
    uitkomst = duid_antwoord({"isValid": False, "userError": "INVALID",
                              "name": "---", "address": "---"})
    assert uitkomst["status"] == "ongeldig"


@pytest.mark.parametrize("code", [
    "MS_UNAVAILABLE",
    "SERVICE_UNAVAILABLE",
    "MS_MAX_CONCURRENT_REQ",
    "GLOBAL_MAX_CONCURRENT_REQ",
    "TIMEOUT",
    "VAT_BLOCKED",
    "IP_BLOCKED",
    "INVALID_REQUESTER_INFO",
    "INVALID_INPUT",
])
def test_dienstfout_is_geen_ongeldig_nummer(code):
    """Bug 8: VIES antwoordt met HTTP 200 en isValid=false bij een storing.
    Dat werd getoond als 'niet geldig' - een verschil dat bij de beoordeling van
    het 0%-tarief bij ICP-leveringen uitmaakt."""
    uitkomst = duid_antwoord({"isValid": False, "userError": code,
                              "name": "---", "address": "---"})
    assert uitkomst["status"] == "storing"
    assert uitkomst["melding"]


def test_dienstfout_gaat_voor_op_isvalid():
    uitkomst = duid_antwoord({"isValid": True, "userError": "MS_UNAVAILABLE"})
    assert uitkomst["status"] == "storing"


def test_ontbrekend_userError_valt_terug_op_isvalid():
    assert duid_antwoord({"isValid": True})["status"] == "geldig"
    assert duid_antwoord({"isValid": False})["status"] == "ongeldig"
    assert duid_antwoord({})["status"] == "ongeldig"


def test_streepjes_worden_als_leeg_gelezen():
    """VIES gebruikt '---' voor 'niet verstrekt'."""
    uitkomst = duid_antwoord({"isValid": True, "name": "---", "address": "---"})
    assert uitkomst["naam"] is None
    assert uitkomst["adres"] is None


# ── Hulpfuncties ────────────────────────────────────────────────────────────

def test_adres_regels_splitst_en_ruimt_op():
    assert adres_regels("\nSTRAAT 1\n\n1234AB PLAATS\n") == ["STRAAT 1", "1234AB PLAATS"]
    assert adres_regels(None) == []
    assert adres_regels("") == []


def test_rsin_uit_nederlands_btw_nummer():
    assert rsin_uit_btw_nummer("NL", "820646660B01") == "820646660"
    assert rsin_uit_btw_nummer("BE", "0123456789") is None
    assert rsin_uit_btw_nummer("NL", "12345B01") is None


# ── Tegen de echte dienst ───────────────────────────────────────────────────

def test_echte_vies_aanroep_wordt_correct_geduid():
    """Netwerktest: bevestigt dat het antwoordformaat nog klopt."""
    requests = pytest.importorskip("requests")
    from _vies import VIES_URL

    land, nummer = parse_btw("NL820646660B01")
    try:
        resp = requests.get(VIES_URL.format(land=land, nummer=nummer), timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        pytest.skip(f"VIES niet bereikbaar: {exc}")

    assert "isValid" in data, "veldnaam gewijzigd - duid_antwoord moet worden aangepast"
    uitkomst = duid_antwoord(data)
    assert uitkomst["status"] in ("geldig", "ongeldig", "storing")
    if uitkomst["status"] == "geldig":
        assert uitkomst["naam"]
