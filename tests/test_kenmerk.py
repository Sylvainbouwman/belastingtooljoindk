"""Regressietests voor de decodeerlogica van het betalingskenmerk.

Deze tests leggen gedrag vast dat NIET mag veranderen. Ze zijn geschreven vóór
de bugfixes van augustus 2026, zodat elke fix aantoonbaar niets anders omgooit.
"""

from datetime import date

import pytest

from _kenmerk import (
    build_omschrijving,
    decode_kenmerk,
    decode_tijdvak,
    format_rsin,
    reconstruct_year,
    rsin_check_digit,
)


# ── Invoervalidatie ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("invoer", [
    "",
    "123",
    "0" * 15,
    "0" * 17,
    "1234567890abcdef",
    "12345678901234a",
])
def test_ongeldige_invoer_geeft_foutmelding(invoer):
    resultaat, fout = decode_kenmerk(invoer)
    assert resultaat is None
    assert "16-cijferig" in fout


def test_spaties_worden_genegeerd():
    met_spaties = decode_kenmerk("0123 4567 8150 0210")
    zonder = decode_kenmerk("0123456781500210")
    assert met_spaties == zonder


# ── Elfproef ────────────────────────────────────────────────────────────────

def test_rsin_check_digit_bekende_waarden():
    # 9*1 + 8*2 + 7*3 + 6*4 + 5*5 + 4*6 + 3*7 + 2*8 = 156 ; 156 % 11 == 2
    assert rsin_check_digit("12345678") == 2
    assert rsin_check_digit("00000000") == 0


def test_format_rsin():
    assert format_rsin("123456782") == "1234.56.782"


# ── Tijdvakken ──────────────────────────────────────────────────────────────

def test_tijdvak_jaaraangifte():
    assert decode_tijdvak("00") == "Jaaraangifte"


@pytest.mark.parametrize("code,verwacht", [
    ("01", "januari"), ("06", "juni"), ("12", "december"),
])
def test_tijdvak_maanden(code, verwacht):
    assert decode_tijdvak(code) == verwacht


@pytest.mark.parametrize("code,verwacht", [
    ("21", "1e kwartaal"), ("24", "2e kwartaal"),
    ("27", "3e kwartaal"), ("30", "4e kwartaal"),
])
def test_tijdvak_kwartalen(code, verwacht):
    assert decode_tijdvak(code) == verwacht


def test_tijdvak_onbekend_valt_terug_op_ruwe_code():
    assert decode_tijdvak("50") == "tijdvak 50"


# ── Middelcodes op positie 10 (LH / OB) ─────────────────────────────────────

@pytest.mark.parametrize("p10,soort,kort,sub", [
    ("0", "Loonheffing",    "LH", "Naheffingsaanslag"),
    ("1", "Omzetbelasting", "OB", "Aangifte"),
    ("5", "Omzetbelasting", "OB", "Naheffingsaanslag"),
    ("6", "Loonheffing",    "LH", "Aangifte"),
])
def test_middelcode_positie10(p10, soort, kort, sub):
    kenmerk = f"012345678{p10}500210"
    r, fout = decode_kenmerk(kenmerk)
    assert fout is None
    assert r["soort"] == soort
    assert r["kort"] == kort
    assert r["soort_sub"] == sub
    assert r["tijdvak"] == "1e kwartaal"
    # RSIN uit posities 2 t/m 9 plus elfproefcijfer
    assert r["rsin9"] == "123456782"
    assert r["rsin"] == "1234.56.782"


# ── Middelcodes op positie 10-11 ────────────────────────────────────────────

def test_vpb_middelcode_74():
    r, fout = decode_kenmerk("0123456507420240")
    assert fout is None
    assert r["soort"] == "Vennootschapsbelasting"
    assert r["kort"] == "VpB"
    assert r["tijdvak"] == "Boekjaar 2024"
    # prefix "00" + posities 2 t/m 7
    assert r["rsin9"].startswith("00123456")


def test_inkomstenbelasting_middelcode_70():
    r, fout = decode_kenmerk("0123456787050000")
    assert fout is None
    assert r["soort"] == "Inkomstenbelasting"
    assert r["kort"] == "IB"
    assert r["rsin9"] == "123456782"


def test_toeslag_middelcode_25():
    r, fout = decode_kenmerk("0123456782550000")
    assert fout is None
    assert r["soort"] == "Zorgtoeslag"
    assert r["kort"] == "ZT"


def test_onbekende_middelcode_geeft_nette_fout():
    # 99 staat in geen enkele tabel en valt buiten de VpB-range
    r, fout = decode_kenmerk("0123456789950000")
    assert r is None
    assert "Onbekend middelcode" in fout


def test_middelcodes_85_tot_88_worden_als_vpb_gelezen():
    """Vastgelegd conflict: MIDDEL2_LABEL kent 85-88 als Eurovignet/MOA, maar de
    VpB-range 80-96 gaat voor. Dit gedrag is bewust ongewijzigd gelaten totdat
    fiscaal is uitgezocht welke van de twee klopt (zie commentaar in _kenmerk.py).
    Deze test bewaakt dat het gedrag niet per ongeluk verandert."""
    for middelcode in ("85", "86", "87", "88"):
        # pos 1-7 vrij, pos 8 jaarcijfer, pos 9 vrij, pos 10-11 middelcode, pos 12-15 boekjaar
        r, fout = decode_kenmerk(f"012345650{middelcode}20240")
        assert fout is None, middelcode
        assert r["soort"] == "Vennootschapsbelasting", middelcode


# ── Digit-strip ─────────────────────────────────────────────────────────────

def test_digit_active_heeft_altijd_zestien_posities():
    for kenmerk in ("0123456781500210", "0123456507420240", "0123456787050000"):
        r, fout = decode_kenmerk(kenmerk)
        assert fout is None
        assert len(r["digit_active"]) == 16


# ── Jaarreconstructie ───────────────────────────────────────────────────────

def test_jaar_uit_huidig_decennium():
    laatste_cijfer = date.today().year % 10
    assert reconstruct_year(laatste_cijfer) == date.today().year


def test_jaar_ligt_altijd_in_plausibel_venster():
    for cijfer in range(10):
        jaar = reconstruct_year(cijfer)
        assert date.today().year - 10 < jaar <= date.today().year + 1
        assert jaar % 10 == cijfer


# ── Omschrijving ────────────────────────────────────────────────────────────

def test_omschrijving_naheffing_krijgt_ander_voorvoegsel():
    naheffing, _ = decode_kenmerk("0123456785500210")   # OB naheffingsaanslag
    aangifte, _ = decode_kenmerk("0123456781500210")    # OB aangifte
    assert build_omschrijving(naheffing).startswith("Naheff.")
    assert not build_omschrijving(aangifte).startswith("Naheff.")


def test_omschrijving_bevat_middel_en_jaar():
    r, _ = decode_kenmerk("0123456781500210")
    tekst = build_omschrijving(r)
    assert "OB" in tekst
    assert str(r["jaar"]) in tekst
