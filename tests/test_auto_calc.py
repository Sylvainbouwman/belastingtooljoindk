"""Tests voor de BTW-correctie en bijtelling van de zakelijke auto."""

from datetime import date

import pytest

from _auto_calc import (
    KORTING_GEVERIFIEERD_TOT_EN_MET,
    KORTING_NULEMISSIE,
    bijtelling,
    bijtelling_regime,
    bijtelling_youngtimer,
    btw_correctie,
    btw_forfait,
    is_nulemissie,
    is_plafondvrij,
    is_youngtimer,
    jaarfractie,
    maandfractie,
    regime_jaar,
    standaardpercentage,
    tel_maanden_op,
    vervaldatum_vaste_termijn,
    waarschuwing_regimejaar,
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
    van, tot = vol_jaar(2024)
    bedrag, _ = btw_correctie(40_000, marge=False, van=van, tot=tot,
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
    van, tot = vol_jaar(2025)
    nieuw, _ = btw_correctie(50_000, False, van, tot, date(2024, 1, 1), 2025)
    oud, _ = btw_correctie(50_000, False, van, tot, date(2018, 1, 1), 2025)
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
    # Tot de vervaldatum het regime van 2021 (12% tot 40.000), daarna dat van
    # 2026: 18% tot 30.000 en 22% over het meerdere.
    na_grondslag = 30_000 * 0.18 + 5_000 * 0.22
    verwacht = (35_000 * 0.12 * dagen_voor / 365) + (na_grondslag * dagen_na / 365)
    assert bedrag == pytest.approx(verwacht)
    assert "12%" in label and "18%" in label and "daarna" in label


def test_zonder_toelatingsdatum_geldt_het_berekeningsjaar():
    van, tot = vol_jaar(2025)
    bedrag, _ = bijtelling(35_000, 0, "Elektriciteit", 2025, van, tot, eerste_toelating=None)
    assert bedrag == pytest.approx(30_000 * 0.17 + 5_000 * 0.22)


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


def test_korting_geldt_ook_in_2026():
    """Stond eerder als "korting vervalt vanaf 2026" in de tool. Op de jaarpagina
    van 2026 staat 18% tot en met een cataloguswaarde van EUR 30.000; de tool
    rekende een nulemissieauto uit 2026 dus 22% en daarmee te hoog."""
    grondslag, label = bijtelling_regime(30_000, nulemissie=True, jaar=2026)
    assert grondslag == pytest.approx(30_000 * 0.18)
    assert "18%" in label


def test_nulemissiepercentages_lopen_op_zoals_de_wet_voorschrijft():
    """De reeks 4/4/4/8/12/16/16/16/17/18, op 18-08-2026 nagelopen op de
    jaarpagina's van belastingdienst.nl. Bewaakt tegen per ongeluk terugdraaien."""
    verwacht = {2017: 4.0, 2018: 4.0, 2019: 4.0, 2020: 8.0, 2021: 12.0,
                2022: 16.0, 2023: 16.0, 2024: 16.0, 2025: 17.0, 2026: 18.0}
    assert {j: p for j, (p, _) in KORTING_NULEMISSIE.items()} == verwacht


def test_plafonds_dalen_zoals_de_wet_voorschrijft():
    verwacht = {2017: None, 2018: None, 2019: 50_000, 2020: 45_000, 2021: 40_000,
                2022: 35_000, 2023: 30_000, 2024: 30_000, 2025: 30_000, 2026: 30_000}
    assert {j: c for j, (_, c) in KORTING_NULEMISSIE.items()} == verwacht


def test_label_toont_geen_regimewissel_als_het_percentage_gelijk_blijft():
    """Een benzineauto houdt 22% voor en na de vervaldatum; dat hoeft de
    gebruiker niet als 'wissel' te zien."""
    det = date(2020, 1, 14)                       # vervalt 1-2-2025
    van, tot = vol_jaar(2025)
    _, label = bijtelling(14_110, co2=100, brandstof="Benzine",
                          berekeningsjaar=2025, van=van, tot=tot, eerste_toelating=det)
    assert label == "22%"


# ── Maandmethode BTW-correctie ──────────────────────────────────────────────

def test_officieel_rekenvoorbeeld_van_de_belastingdienst():
    """Het voorbeeld op "Btw en privegebruik auto van de zaak": een auto die op
    1 september tot het bedrijf gaat horen geeft 4/12 x 2,7% x EUR 45.000 =
    EUR 405. Met de oude dagmethode kwam daar EUR 406,08 uit."""
    bedrag, _ = btw_correctie(45_000, marge=False,
                              van=date(2026, 9, 1), tot=date(2026, 12, 31),
                              ingebruikname=date(2026, 9, 1), jaar=2026)
    assert bedrag == pytest.approx(405.00)


def test_maandfractie_hele_maanden():
    assert maandfractie(date(2026, 1, 1), date(2026, 12, 31)) == pytest.approx(1.0)
    assert maandfractie(date(2026, 9, 1), date(2026, 12, 31)) == pytest.approx(4 / 12)
    assert maandfractie(date(2026, 1, 1), date(2026, 1, 31)) == pytest.approx(1 / 12)


def test_maandfractie_vol_schrikkeljaar_blijft_een():
    """366 dagen mag geen 100,27% opleveren."""
    assert maandfractie(date(2024, 1, 1), date(2024, 12, 31)) == pytest.approx(1.0)


def test_maandfractie_deelmaand_telt_naar_rato():
    """Een periode die halverwege september begint mag geen hele maand opleveren."""
    fractie = maandfractie(date(2026, 9, 16), date(2026, 12, 31))
    assert fractie == pytest.approx((15 / 30 + 3) / 12)
    assert fractie < 4 / 12


def test_maandfractie_binnen_een_maand():
    assert maandfractie(date(2026, 3, 1), date(2026, 3, 15)) == pytest.approx(15 / 31 / 12)


# ── Waterstof en zonnecellen: geen plafond ──────────────────────────────────

@pytest.mark.parametrize("brandstof,verwacht", [
    ("Waterstof", True), ("waterstof", True),
    ("Elektriciteit", False), ("Benzine", False), (None, False),
])
def test_plafondvrije_brandstof(brandstof, verwacht):
    assert is_plafondvrij(brandstof) is verwacht


def test_waterstofauto_krijgt_het_lage_percentage_zonder_plafond():
    """De jaarpagina's 2022 t/m 2026: het verlaagde percentage geldt voor auto's
    op waterstof over de hele catalogusprijs. De tool paste het plafond toe en
    rekende daarmee te hoog."""
    van, tot = vol_jaar(2026)
    bedrag, label = bijtelling(80_000, co2=0, brandstof="Waterstof",
                               berekeningsjaar=2026, van=van, tot=tot,
                               eerste_toelating=date(2026, 1, 1))
    assert bedrag == pytest.approx(80_000 * 0.18)
    assert "plafond" in label


def test_gewone_ev_houdt_het_plafond():
    van, tot = vol_jaar(2026)
    bedrag, _ = bijtelling(80_000, co2=0, brandstof="Elektriciteit",
                           berekeningsjaar=2026, van=van, tot=tot,
                           eerste_toelating=date(2026, 1, 1))
    assert bedrag == pytest.approx(30_000 * 0.18 + 50_000 * 0.22)


# ── Youngtimer ──────────────────────────────────────────────────────────────

def test_youngtimergrens_ging_per_2026_van_vijftien_naar_zestien_jaar():
    """De grens ging per 2026 van vijftien naar zestien jaar. Een auto van juni
    2010 is op 1 januari 2026 vijftien jaar en zeven maanden oud: onder de oude
    grens een youngtimer, onder de nieuwe nog niet."""
    det = date(2010, 6, 1)
    assert is_youngtimer(det, 2025) is False     # dan pas veertien jaar en zeven maanden
    assert is_youngtimer(det, 2026) is False     # vijftien jaar en zeven maanden, grens is zestien
    assert is_youngtimer(det, 2027) is True      # zestien jaar en zeven maanden

    ouder = date(2009, 6, 1)
    assert is_youngtimer(ouder, 2025) is True     # zestien jaar en zeven maanden, grens was vijftien


def test_youngtimerleeftijd_wordt_op_een_januari_gemeten():
    """Een auto die in de loop van het jaar de grens haalt, valt er dat jaar nog
    niet onder."""
    assert is_youngtimer(date(2011, 6, 1), 2027) is False   # wordt pas in juni 2027 zestien
    assert is_youngtimer(date(2011, 6, 1), 2028) is True


def test_youngtimer_zonder_toelatingsdatum_is_geen_youngtimer():
    assert is_youngtimer(None, 2026) is False


def test_youngtimer_rekent_vijfendertig_procent_over_de_wev():
    bedrag, label = bijtelling_youngtimer(8_000, dagen=365)
    assert bedrag == pytest.approx(8_000 * 0.35)
    assert "35%" in label and "WEV" in label


def test_youngtimer_naar_rato_van_de_periode():
    bedrag, _ = bijtelling_youngtimer(10_000, dagen=182)
    assert bedrag == pytest.approx(10_000 * 0.35 * 182 / 365)


# ── Grenzen van de gecontroleerde tabel ─────────────────────────────────────

def test_waarschuwing_als_het_regimejaar_voorbij_de_tabel_ligt():
    assert waarschuwing_regimejaar(True, KORTING_GEVERIFIEERD_TOT_EN_MET) is None
    melding = waarschuwing_regimejaar(True, KORTING_GEVERIFIEERD_TOT_EN_MET + 1)
    assert melding is not None
    assert "standaardpercentage" in melding


def test_geen_waarschuwing_voor_een_auto_met_uitstoot():
    assert waarschuwing_regimejaar(False, 2030) is None


def test_standaardpercentage_kent_geen_stille_terugval():
    """Voorheen gaf een jaar buiten de tabel altijd 22%, ook voor 2010."""
    assert standaardpercentage(2010) == 25.0
    assert standaardpercentage(2016) == 25.0
    assert standaardpercentage(2017) == 22.0
    assert standaardpercentage(2035) == 22.0
