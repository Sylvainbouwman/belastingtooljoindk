"""Tests voor de gedeelde bouwstenen: veilige HTML en de KvK-URL-controle."""

import pytest

from _format import nl_date, nl_euro, nl_euro_heel, nl_pct
from _ui import PAGINA_CSS, is_kvk_url, veilig

from datetime import date


# ── K1: gegevens van buiten in HTML ─────────────────────────────────────────

def test_veilig_ontwapent_markup():
    """Een bedrijfsnaam of SBI-omschrijving van een API ging ongeëscaped de HTML
    in. Bij een naam met een < of & brak dat de opmaak."""
    assert veilig("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert veilig("Jansen & Zn") == "Jansen &amp; Zn"
    assert veilig('Bouw "De Hoek"') == "Bouw &quot;De Hoek&quot;"


def test_veilig_laat_gewone_tekst_ongemoeid():
    assert veilig("Handelsonderneming Bouwman B.V.") == "Handelsonderneming Bouwman B.V."
    assert veilig("46.90.1 Groothandel") == "46.90.1 Groothandel"


@pytest.mark.parametrize("leeg", [None, ""])
def test_veilig_geeft_een_streepje_bij_niets(leeg):
    assert veilig(leeg) == "—"
    assert veilig(leeg, leeg="onbekend") == "onbekend"


def test_veilig_verwerkt_ook_niet_tekst():
    assert veilig(12345678) == "12345678"


# ── K3: de API-sleutel gaat alleen naar de KvK ──────────────────────────────

@pytest.mark.parametrize("url", [
    "https://api.kvk.nl/api/v1/basisprofielen/12345678",
    "https://api.kvk.nl/test/api/v1/basisprofielen/68750110",
])
def test_kvk_url_wordt_geaccepteerd(url):
    assert is_kvk_url(url) is True


@pytest.mark.parametrize("url", [
    "https://kwaadwillend.example.com/api/v1/basisprofielen/1",
    "https://api.kvk.nl.example.com/api/v1/basisprofielen/1",
    "http://api.kvk.nl/api/v1/basisprofielen/1",          # geen https
    "https://apikvk.nl/api/v1/basisprofielen/1",
    "",
    None,
])
def test_andere_bestemming_krijgt_de_sleutel_niet(url):
    assert is_kvk_url(url) is False


# ── Duplicatie: één stijlblok voor alle pagina's ────────────────────────────

def test_stijlblok_bevat_de_klassen_die_de_paginas_gebruiken():
    """Het blok stond vijf keer gekopieerd. Deze test valt om zodra een klasse
    verdwijnt waar een pagina nog op leunt."""
    for klasse in (".bk-header", ".bk-tile", ".bk-omschrijving", ".auto-info",
                   ".auto-nr", ".badge-geldig", ".badge-ongeldig", ".badge-storing",
                   ".sbi-badge"):
        assert klasse in PAGINA_CSS, klasse


# ── Notatie ─────────────────────────────────────────────────────────────────

def test_notatie_nederlands():
    assert nl_euro(1234.5) == "€ 1.234,50"
    assert nl_euro_heel(45000) == "€ 45.000"
    assert nl_date(date(2026, 8, 18)) == "18-08-2026"
    assert nl_pct(6.5) == "6,5%"
    assert nl_pct(7.5) == "7,5%"
    assert nl_pct(22.0) == "22%"


def test_notatie_is_op_een_plek_gedefinieerd():
    """Zowel _rente als de autopagina hadden een eigen kopie. Ze moeten nu
    letterlijk dezelfde functie gebruiken."""
    import _format
    import _rente
    assert _rente.nl_euro is _format.nl_euro
    assert _rente.nl_date is _format.nl_date
