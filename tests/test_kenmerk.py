"""Regressietests voor de decodeerlogica van het betalingskenmerk.

Deze tests leggen gedrag vast dat NIET mag veranderen. Ze zijn geschreven vóór
de bugfixes van augustus 2026, zodat elke fix aantoonbaar niets anders omgooit.
"""

from datetime import date

import pytest

from _kenmerk import (
    rsin_uit,
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


def test_format_rsin_laat_none_door():
    assert format_rsin(None) is None


def test_rsin_uit_geeft_negen_cijfers():
    assert rsin_uit("12345678") == "123456782"
    assert len(rsin_uit("12345678")) == 9


def test_rsin_uit_geeft_none_bij_restwaarde_tien():
    # Bug 1: 10 is geen controlecijfer maar het bewijs dat er geen geldig
    # BSN/RSIN bestaat. Vroeger werd "10" aangeplakt -> nummer van 10 cijfers.
    assert rsin_check_digit("10000006") == 10
    assert rsin_uit("10000006") is None


def test_rsin_is_nooit_langer_dan_negen_cijfers():
    """Bug 1, regressiebewaking over de volle invoerruimte."""
    for n in range(10_000_000, 10_050_000):
        uitkomst = rsin_uit(str(n).zfill(8))
        assert uitkomst is None or len(uitkomst) == 9


def test_kenmerk_met_onmogelijke_elfproef_decodeert_zonder_rsin():
    """Bug 1: de rest van het kenmerk blijft bruikbaar, alleen het RSIN vervalt."""
    r, fout = decode_kenmerk("0100000061500210")
    assert fout is None
    assert r["rsin9"] is None
    assert r["rsin"] is None
    # soort, jaar en tijdvak zijn wél gewoon afgeleid
    assert r["soort"] == "Omzetbelasting"
    assert r["tijdvak"] == "1e kwartaal"


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


def test_jaar_kan_een_jaar_vooruit_kijken():
    """Bug 10: een voorlopige aanslag voor volgend jaar kwam tien jaar te vroeg uit."""
    assert reconstruct_year(7, date(2026, 8, 17)) == 2027
    assert reconstruct_year(6, date(2026, 8, 17)) == 2026
    assert reconstruct_year(8, date(2026, 8, 17)) == 2018


def test_jaar_over_de_decenniumgrens():
    """Bug 10: in 2029 hoort cijfer 0 bij 2030, niet bij 2020."""
    assert reconstruct_year(0, date(2029, 11, 1)) == 2030
    assert reconstruct_year(9, date(2029, 11, 1)) == 2029
    assert reconstruct_year(1, date(2029, 11, 1)) == 2021


@pytest.mark.parametrize("peiljaar", range(2015, 2046))
def test_jaarvenster_is_sluitend_op_elke_peildatum(peiljaar):
    """Elk cijfer levert precies één jaar op, alle tien vallen in het venster
    [peiljaar-8, peiljaar+1] en er zijn geen dubbelingen."""
    peildatum = date(peiljaar, 7, 1)
    jaren = [reconstruct_year(c, peildatum) for c in range(10)]
    assert len(set(jaren)) == 10
    for cijfer, jaar in enumerate(jaren):
        assert jaar % 10 == cijfer
        assert peiljaar - 8 <= jaar <= peiljaar + 1


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


def test_omschrijving_lh_ob_blijft_ongewijzigd():
    """Bug 3 mocht de bestaande, correcte LH/OB-omschrijving niet aantasten."""
    ob_aangifte, _ = decode_kenmerk("0123456781500210")
    ob_naheffing, _ = decode_kenmerk("0123456785500210")
    assert build_omschrijving(ob_aangifte) == "Afdr. OB 1e kwartaal 2025"
    assert build_omschrijving(ob_naheffing) == "Naheff. OB 1e kwartaal 2025"


def test_omschrijving_aanslag_heeft_geen_tijdvak_streepje():
    """Bug 3: gaf voorheen 'Afdr. IB — 2025'."""
    r, _ = decode_kenmerk("0123456787050000")
    tekst = build_omschrijving(r)
    assert tekst == "Aanslag IB 2025"
    assert "—" not in tekst
    assert "Afdr." not in tekst


def test_omschrijving_vpb_noemt_boekjaar_en_niet_twee_jaartallen():
    """Bug 3: gaf voorheen 'Afdr. VpB Boekjaar 2024 2025'."""
    r, _ = decode_kenmerk("0123456507420240")
    tekst = build_omschrijving(r)
    assert tekst == "Aanslag VpB boekjaar 2024"


def test_omschrijving_toeslag_gebruikt_volledige_naam():
    r, _ = decode_kenmerk("0123456782550000")
    assert build_omschrijving(r) == "Zorgtoeslag 2025"


def test_omschrijving_bevat_nooit_placeholder_of_dubbel_jaartal():
    """Breed vangnet over alle middelcodes."""
    import re
    for p10 in range(10):
        for p11 in range(10):
            r, fout = decode_kenmerk(f"0123456{p10}{p11}500210")
            if fout:
                continue
            tekst = build_omschrijving(r)
            assert "—" not in tekst, tekst
            assert not re.search(r"\b(19|20)\d{2}\s+(19|20)\d{2}\b", tekst), tekst


def test_gevalideerd_kenmerk_uit_de_readme():
    """Het enige kenmerk waarvan de juiste uitkomst extern is bevestigd.
    Als deze test omvalt, is er iets fundamenteels mis met de decodering."""
    r, fout = decode_kenmerk("4863521721601050")
    assert fout is None
    assert r["soort"] == "Omzetbelasting"
    assert r["soort_sub"] == "Aangifte"
    assert r["jaar"] == 2026
    assert r["tijdvak"] == "mei"
    assert r["rsin9"] == "863521721"
    assert build_omschrijving(r) == "Afdr. OB Mei 2026"
