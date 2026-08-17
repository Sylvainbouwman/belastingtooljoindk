"""Tests voor de BTW-correctie en bijtelling van de zakelijke auto."""

from datetime import date

import pytest

from _auto_calc import (
    KORTING_NULEMISSIE,
    bijtelling,
    bijtelling_regime,
    btw_correctie,
    btw_forfait,
    is_nulemissie,
    jaarfractie,
    regime_jaar,
    tel_maanden_op,
    vervaldatum_vaste_termijn,
)


def vol_jaar(jaar):
    return date(jaar, 1, 1), date(jaar, 12, 31)


# ── Jaarfractie (bug 7) ─────────────────────────────────────────────────────

def test_vol_gewoon_jaar_is_precies_een():
    assert jaarfractie(365) == 1.0


def test_vol_schrikkeljaar_is_ook_precies_een():
    """Bug 7: 366/365 gaf 100,27% van het forfait."""
    assert jaarfractie(366) == 1.0


def test_halve_periode():
    assert jaarfractie(183) == pytest.approx(183 / 365)


def test_btw_correctie_vol_schrikkeljaar_is_exact_het_forfait():
    """Bug 7, in euro's: 2,7% van 40.000 = 1.080, niet 1.082,96."""
    bedrag, _ = btw_correctie(40_000, marge=False, dagen=366,
                              ingebruikname=date(2024, 1, 1), jaar=2024)
    assert bedrag == pytest.approx(1080.00)


# ── BTW-forfait (bug 6) ─────────────────────────────────────────────────────

def test_marge_auto_krijgt_lage_forfait():
    forfait, label = btw_forfait(marge=True, ingebruikname=date(2024, 1, 1), jaar=2025)
    assert forfait == 0.015
    assert "marge" in label


def test_nieuwe_auto_krijgt_hoge_forfait():
    forfait, _ = btw_forfait(marge=False, ingebruikname=date(2023, 6, 1), jaar=2025)
    assert forfait == 0.027


@pytest.mark.parametrize("jaar,verwacht", [
    (2020, 0.027),   # jaar van ingebruikname
    (2021, 0.027),
    (2022, 0.027),
    (2023, 0.027),
    (2024, 0.027),   # vierde jaar erna - nog steeds hoog
    (2025, 0.015),   # vijfde jaar - laag
    (2026, 0.015),
])
def test_lage_forfait_vanaf_het_vijfde_jaar_na_ingebruikname(jaar, verwacht):
    """Bug 6: deze regel ontbrak volledig, alles bleef op 2,7%."""
    forfait, _ = btw_forfait(marge=False, ingebruikname=date(2020, 7, 1), jaar=jaar)
    assert forfait == verwacht


def test_zonder_ingebruiknamedatum_blijft_het_hoge_forfait_gelden():
    """Geen datum bekend: niet gokken, het hoge forfait aanhouden."""
    forfait, _ = btw_forfait(marge=False, ingebruikname=None, jaar=2026)
    assert forfait == 0.027


def test_btw_correctie_oudere_auto_scheelt_bijna_de_helft():
    nieuw, _ = btw_correctie(50_000, False, 365, date(2024, 1, 1), 2025)
    oud, _ = btw_correctie(50_000, False, 365, date(2018, 1, 1), 2025)
    assert nieuw == pytest.approx(1350.0)
    assert oud == pytest.approx(750.0)


# ── Nulemissie herkennen ────────────────────────────────────────────────────

@pytest.mark.parametrize("co2,brandstof,verwacht", [
    (0, "Benzine", True),
    (None, "Elektriciteit", True),
    (None, "elektriciteit", True),
    (None, "Waterstof", True),
    (120, "Benzine", False),
    (None, "Diesel", False),
    (None, None, False),
])
def test_nulemissie_herkenning(co2, brandstof, verwacht):
    assert is_nulemissie(co2, brandstof) is verwacht


# ── 60-maandstermijn (bug 5) ────────────────────────────────────────────────

def test_tel_maanden_op_respecteert_maandlengte():
    assert tel_maanden_op(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert tel_maanden_op(date(2023, 1, 31), 1) == date(2023, 2, 28)
    assert tel_maanden_op(date(2024, 3, 15), 12) == date(2025, 3, 15)


def test_vervaldatum_is_zestig_maanden_na_de_maand_van_toelating():
    assert vervaldatum_vaste_termijn(date(2021, 3, 15)) == date(2026, 4, 1)
    assert vervaldatum_vaste_termijn(date(2021, 3, 1)) == date(2026, 4, 1)
    assert vervaldatum_vaste_termijn(None) is None


def test_regime_blijft_het_toelatingsjaar_binnen_de_termijn():
    """Bug 5: het percentage werd op het berekeningsjaar bepaald in plaats van
    op de datum eerste toelating."""
    det = date(2021, 6, 1)
    for jaar in (2021, 2022, 2023, 2024, 2025):
        assert regime_jaar(det, jaar, date(jaar, 1, 1)) == 2021


def test_regime_valt_terug_op_het_lopende_jaar_na_de_termijn():
    det = date(2021, 6, 1)
    assert regime_jaar(det, 2027, date(2027, 1, 1)) == 2027


def test_ev_uit_2021_houdt_twaalf_procent_in_2025():
    """Bug 5 in euro's: een EV van 2021 hield 12% tot 40.000, maar kreeg het
    16%/30.000-regime van 2025 opgelegd."""
    van, tot = vol_jaar(2025)
    bedrag, label = bijtelling(35_000, co2=0, brandstof="Elektriciteit",
                               berekeningsjaar=2025, van=van, tot=tot,
                               eerste_toelating=date(2021, 6, 1))
    assert bedrag == pytest.approx(35_000 * 0.12)
    assert "12%" in label


def test_ev_regime_splitst_op_de_vervaldatum():
    """Loopt de 60-maandstermijn midden in het jaar af, dan geldt daarna het
    percentage van het lopende jaar."""
    det = date(2021, 6, 15)                       # vervalt 1-7-2026
    assert vervaldatum_vaste_termijn(det) == date(2026, 7, 1)
    van, tot = vol_jaar(2026)
    bedrag, label = bijtelling(35_000, 0, "Elektriciteit", 2026, van, tot, det)

    dagen_voor = (date(2026, 6, 30) - van).days + 1
    dagen_na = (tot - date(2026, 7, 1)).days + 1
    verwacht = (35_000 * 0.12 * dagen_voor / 365) + (35_000 * 0.22 * dagen_na / 365)
    assert bedrag == pytest.approx(verwacht)
    assert "12%" in label and "22%" in label and "daarna" in label


def test_zonder_toelatingsdatum_geldt_het_berekeningsjaar():
    van, tot = vol_jaar(2025)
    bedrag, _ = bijtelling(35_000, 0, "Elektriciteit", 2025, van, tot, eerste_toelating=None)
    assert bedrag == pytest.approx(30_000 * 0.16 + 5_000 * 0.22)


# ── Plafond en standaardpercentage ──────────────────────────────────────────

def test_benzineauto_krijgt_het_standaardpercentage():
    grondslag, label = bijtelling_regime(40_000, nulemissie=False, jaar=2025)
    assert grondslag == pytest.approx(40_000 * 0.22)
    assert label == "22%"


def test_standaardpercentage_was_25_procent_voor_2017():
    grondslag, label = bijtelling_regime(40_000, nulemissie=False, jaar=2016)
    assert grondslag == pytest.approx(40_000 * 0.25)
    assert label == "25%"


def test_ev_onder_het_plafond():
    grondslag, _ = bijtelling_regime(25_000, nulemissie=True, jaar=2024)
    assert grondslag == pytest.approx(25_000 * 0.16)


def test_ev_boven_het_plafond_rekent_het_meerdere_tegen_het_standaardtarief():
    grondslag, label = bijtelling_regime(50_000, nulemissie=True, jaar=2024)
    assert grondslag == pytest.approx(30_000 * 0.16 + 20_000 * 0.22)
    assert "22% daarboven" in label


def test_ev_zonder_plafond_in_2017_en_2018():
    for jaar in (2017, 2018):
        grondslag, _ = bijtelling_regime(80_000, nulemissie=True, jaar=jaar)
        assert grondslag == pytest.approx(80_000 * 0.04)


def test_korting_vervalt_vanaf_2026():
    assert 2026 not in KORTING_NULEMISSIE
    grondslag, label = bijtelling_regime(30_000, nulemissie=True, jaar=2026)
    assert grondslag == pytest.approx(30_000 * 0.22)
    assert label == "22%"


def test_nulemissiepercentages_lopen_op_zoals_de_wet_voorschrijft():
    """De reeks 4/4/4/8/12/16/16/16/16 - bewaakt tegen per ongeluk terugdraaien."""
    verwacht = {2017: 4.0, 2018: 4.0, 2019: 4.0, 2020: 8.0,
                2021: 12.0, 2022: 16.0, 2023: 16.0, 2024: 16.0, 2025: 16.0}
    assert {j: p for j, (p, _) in KORTING_NULEMISSIE.items()} == verwacht


def test_plafonds_dalen_zoals_de_wet_voorschrijft():
    verwacht = {2017: None, 2018: None, 2019: 50_000, 2020: 45_000,
                2021: 40_000, 2022: 35_000, 2023: 30_000, 2024: 30_000, 2025: 30_000}
    assert {j: c for j, (_, c) in KORTING_NULEMISSIE.items()} == verwacht


def test_label_toont_geen_regimewissel_als_het_percentage_gelijk_blijft():
    """Een benzineauto houdt 22% voor en na de vervaldatum; dat hoeft de
    gebruiker niet als 'wissel' te zien."""
    det = date(2020, 1, 14)                       # vervalt 1-2-2025
    van, tot = vol_jaar(2025)
    _, label = bijtelling(14_110, co2=100, brandstof="Benzine",
                          berekeningsjaar=2025, van=van, tot=tot, eerste_toelating=det)
    assert label == "22%"
