"""Regressietests voor de decodeerlogica van het betalingskenmerk.

Deze tests leggen gedrag vast dat NIET mag veranderen. Ze zijn geschreven vóór
de bugfixes van augustus 2026, zodat elke fix aantoonbaar niets anders omgooit.
"""

from datetime import date

import pytest

from _kenmerk import (
    is_mogelijk_rsin,
    mag_naar_kvk,
    nummer_label,
    rsin_uit,
    build_omschrijving,
    controlecijfer,
    controlecijfer_klopt,
    decode_boekjaar,
    decode_kenmerk,
    decode_tijdvak,
    format_rsin,
    reconstruct_year,
    rsin_check_digit,
)


def mk(posities_2_tot_16: str) -> str:
    """Bouwt een kenmerk met een kloppend controlecijfer op positie 1.

    Sinds de verificatieronde weigert decode_kenmerk een kenmerk waarvan het
    controlecijfer niet past. De synthetische kenmerken in deze tests worden
    daarom via deze helper opgebouwd, zodat ze de vorm hebben van een echt
    kenmerk en de test niet per ongeluk op de controlecijfermelding stuit.
    """
    assert len(posities_2_tot_16) == 15, posities_2_tot_16
    return f"{controlecijfer(posities_2_tot_16)}{posities_2_tot_16}"


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
    kenmerk = mk("123456781500210")
    met_spaties = " ".join(kenmerk[i:i + 4] for i in range(0, 16, 4))
    assert decode_kenmerk(met_spaties) == decode_kenmerk(kenmerk)


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
    r, fout = decode_kenmerk(mk("100000061500210"))
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
    kenmerk = mk(f"12345678{p10}500210")
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
    r, fout = decode_kenmerk(mk("123456507420240"))
    assert fout is None
    assert r["soort"] == "Vennootschapsbelasting"
    assert r["kort"] == "VpB"
    assert r["tijdvak"] == "Boekjaar 2024"
    # prefix "00" + posities 2 t/m 7
    assert r["rsin9"].startswith("00123456")


def test_inkomstenbelasting_middelcode_70():
    r, fout = decode_kenmerk(mk("123456787050000"))
    assert fout is None
    assert r["soort"] == "Inkomstenbelasting"
    assert r["kort"] == "IB"
    assert r["rsin9"] == "123456782"


def test_toeslag_middelcode_25():
    r, fout = decode_kenmerk(mk("123456782550000"))
    assert fout is None
    assert r["soort"] == "Zorgtoeslag"
    assert r["kort"] == "ZT"


def test_onbekende_middelcode_geeft_nette_fout():
    # 99 staat in geen enkele tabel en valt buiten de VpB-range
    r, fout = decode_kenmerk(mk("123456789950000"))
    assert r is None
    assert "Onbekend middelcode" in fout


@pytest.mark.parametrize("middelcode,soort", [
    ("85", "Eurovignet"),
    ("86", "Eurovignet (naheffing)"),
    ("87", "Motorrijtuigenbelasting vrachtwagens (aangifte)"),
    ("88", "Motorrijtuigenbelasting vrachtwagens (naheffing)"),
])
def test_middelcodes_85_tot_88_zijn_geen_vpb(middelcode, soort):
    """Het conflict uit de vorige ronde, nu beslecht door de specificatie.

    Paragraaf 2 leidt B-MIDDEL af uit de eerste twee posities van het RSIN: 00
    wordt 74, 80 t/m 84 blijven staan en 85 t/m 89 worden 92 t/m 96. De VpB-range
    liep hier op 80 t/m 96, waardoor 85 t/m 88 als VpB werden gelezen met een
    verzonnen RSIN erbij. Het zijn Eurovignet en MOA (paragrafen 5, 7, 10 en 11).
    """
    r, fout = decode_kenmerk(mk(f"03600001{middelcode}30001"))
    assert fout is None, middelcode
    assert r["soort"] == soort
    # het RSIN komt uit posities 2 t/m 9 en niet uit de VpB-samenstelling
    assert r["rsin9"] == "036000012"


@pytest.mark.parametrize("middelcode", ["89", "90", "91"])
def test_middelcodes_89_tot_91_bestaan_niet(middelcode):
    """Deze drie stonden in de oude VpB-range maar komen in de specificatie niet
    voor. Een nette foutmelding is beter dan een verzonnen VpB-aanslag."""
    r, fout = decode_kenmerk(mk(f"03600001{middelcode}30001"))
    assert r is None
    assert "Onbekend middelcode" in fout


@pytest.mark.parametrize("middelcode,rsin_prefix", [
    ("92", "85"), ("93", "86"), ("94", "87"), ("95", "88"), ("96", "89"),
])
def test_vpb_middelcodes_92_tot_96_horen_bij_rsin_85_tot_89(middelcode, rsin_prefix):
    """Paragraaf 2: een RSIN dat met 85 t/m 89 begint krijgt middelcode 92 t/m 96."""
    r, fout = decode_kenmerk(mk(f"25358620{middelcode}01120"))
    assert fout is None
    assert r["soort"] == "Vennootschapsbelasting"
    assert r["rsin9"].startswith(rsin_prefix)


# ── Digit-strip ─────────────────────────────────────────────────────────────

def test_digit_active_heeft_altijd_zestien_posities():
    for kenmerk in (mk("123456781500210"), mk("123456507420240"), mk("123456787050000")):
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
    naheffing, _ = decode_kenmerk(mk("123456785500210"))   # OB naheffingsaanslag
    aangifte, _ = decode_kenmerk(mk("123456781500210"))    # OB aangifte
    assert build_omschrijving(naheffing).startswith("Naheff.")
    assert not build_omschrijving(aangifte).startswith("Naheff.")


def test_omschrijving_bevat_middel_en_jaar():
    r, _ = decode_kenmerk(mk("123456781500210"))
    tekst = build_omschrijving(r)
    assert "OB" in tekst
    assert str(r["jaar"]) in tekst


def test_omschrijving_lh_ob_blijft_ongewijzigd():
    """Bug 3 mocht de bestaande, correcte LH/OB-omschrijving niet aantasten."""
    ob_aangifte, _ = decode_kenmerk(mk("123456781500210"))
    ob_naheffing, _ = decode_kenmerk(mk("123456785500210"))
    assert build_omschrijving(ob_aangifte) == "Afdr. OB 1e kwartaal 2025"
    assert build_omschrijving(ob_naheffing) == "Naheff. OB 1e kwartaal 2025"


def test_omschrijving_aanslag_heeft_geen_tijdvak_streepje():
    """Bug 3: gaf voorheen 'Afdr. IB — 2025'.

    Positie 13 is hier een 0, dus voorlopige aanslag; het tijdvak hoort er in
    geen van beide gevallen bij.
    """
    r, _ = decode_kenmerk(mk("123456787050000"))
    tekst = build_omschrijving(r)
    assert tekst == "Voorl. aanslag IB 2025"
    assert "—" not in tekst
    assert "Afdr." not in tekst


def test_omschrijving_vpb_noemt_boekjaar_en_niet_twee_jaartallen():
    """Bug 3: gaf voorheen 'Afdr. VpB Boekjaar 2024 2025'.

    Positie 9 is het SOORT-cijfer; hier een 0, dus een voorlopige aanslag.
    """
    r, _ = decode_kenmerk(mk("123456507420240"))
    tekst = build_omschrijving(r)
    assert tekst == "Voorl. aanslag VpB boekjaar 2024"


def test_omschrijving_vpb_definitieve_aanslag():
    """Positie 9 op 6 betekent een definitieve aanslag (paragraaf 2)."""
    r, _ = decode_kenmerk(mk("123456567420240"))
    assert r["soort_sub"] == "Definitieve aanslag"
    assert build_omschrijving(r) == "Aanslag VpB boekjaar 2024"


def test_omschrijving_toeslag_gebruikt_volledige_naam():
    r, _ = decode_kenmerk(mk("123456782550000"))
    assert build_omschrijving(r) == "Zorgtoeslag 2025"


def test_omschrijving_bevat_nooit_placeholder_of_dubbel_jaartal():
    """Breed vangnet over alle middelcodes."""
    import re
    for p10 in range(10):
        for p11 in range(10):
            r, fout = decode_kenmerk(mk(f"0123456{p10}{p11}500210"))
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


# ── Controlecijfer op positie 1 ─────────────────────────────────────────────

def test_controlecijfer_klopt_op_alle_specificatievoorbeelden():
    """De specificatie noemt het algoritme wel maar beschrijft het niet. De regel
    in controlecijfer() is afgeleid uit de voorbeelden; deze test bewijst dat hij
    op alle 27 klopt, plus op het extern gevalideerde kenmerk uit de README."""
    for kenmerk, *_ in SPEC_VOORBEELDEN:
        assert controlecijfer_klopt(kenmerk), kenmerk
    assert controlecijfer_klopt("4863521721601050")


def test_controlecijfer_tien_wordt_een():
    """Drie voorbeelden in de specificatie hebben een uitkomst 10; daar staat een
    1 op positie 1. Zonder die regel zou het kenmerk 17 cijfers lang worden."""
    for kenmerk in ("1036000017810909", "1036000018530001", "1036000012630001"):
        assert controlecijfer(kenmerk[1:]) == 1


def test_typefout_wordt_geweigerd_in_plaats_van_stil_verkeerd_gedecodeerd():
    """Actiepunt 10. Voorheen leverde elke verminkte invoer een geloofwaardig
    ogend maar verkeerd RSIN op."""
    goed = "4863521721601050"
    r, fout = decode_kenmerk(goed)
    assert fout is None and r["rsin9"] == "863521721"

    # één cijfer verkeerd overgenomen, ergens in het midden
    verminkt = goed[:7] + "9" + goed[8:]
    assert verminkt != goed
    r, fout = decode_kenmerk(verminkt)
    assert r is None
    assert "controlecijfer" in fout.lower()
    assert str(controlecijfer(verminkt[1:])) in fout


def test_elk_verwisseld_cijferpaar_wordt_opgemerkt():
    """Een omgewisseld cijferpaar is de klassieke typefout die een enkelvoudige
    modulus-10 niet vangt en een modulus-11 wel."""
    goed = "4863521721601050"
    gemist = 0
    for i in range(len(goed) - 1):
        if goed[i] == goed[i + 1]:
            continue
        wissel = goed[:i] + goed[i + 1] + goed[i] + goed[i + 2:]
        _, fout = decode_kenmerk(wissel)
        if fout is None:
            gemist += 1
    assert gemist == 0


def test_controlecijfer_kan_bewust_worden_overgeslagen():
    """Ontsnappingsluik voor onderzoek naar een kenmerk dat de proef niet haalt."""
    r, fout = decode_kenmerk("0123456781500210", negeer_controlecijfer=True)
    assert fout is None
    assert r["soort"] == "Omzetbelasting"


# ── De 27 voorbeelden uit de specificatie ───────────────────────────────────

# Elke rij komt letterlijk uit Specificatie Betalingskenmerk_bepaling v1.5. Het
# BSN/RSIN is het nummer uit het bijbehorende aanslagnummer, dus een echte
# controle op de terugrekening en niet op wat de code nu toevallig doet. De
# omschrijving uit het document staat als commentaar achter elke rij.
#
# LET OP: drie voorbeelden zijn in het document zelf inconsistent — het
# aanslagnummer en het kenmerk verschillen daar één cijfer in het jaartal
# (F0314240, A0414121 en N2100030). Hieronder staat wat het gedrukte kenmerk
# zegt; zie het wijzigingsrapport voor de terugkoppeling daarover.
SPEC_VOORBEELDEN = [
    ('2036000016301110', '036000012', 'Loonheffing', 'Aangifte',
     2023, 'november', 'Afdr. LH November 2023'),   # Aangifte LB, November 2023
    ('0036000011302270', '036000012', 'Omzetbelasting', 'Aangifte',
     2023, '3e kwartaal', 'Afdr. OB 3e kwartaal 2023'),   # Aangifte OB, Derde kwartaal 2023
    ('1036000015303240', '036000012', 'Omzetbelasting', 'Naheffingsaanslag',
     2023, '2e kwartaal', 'Naheff. OB 2e kwartaal 2023'),   # Naheffingsaanslag OB, Tweede kwartaal ‘23
    ('1036000010304121', '036000012', 'Loonheffing', 'Naheffingsaanslag',
     2023, 'december', 'Naheff. LH December 2023'),   # Naheffingsaanslag LB, December 2023
    ('9253586208001120', '802535860', 'Vennootschapsbelasting', 'Voorlopige aanslag',
     2022, 'Boekjaar januari t/m december', 'Voorl. aanslag VpB boekjaar 0112'),   # Voorlopige aanslag VpB 2022
    ('6253586368001230', '802535860', 'Vennootschapsbelasting', 'Definitieve aanslag',
     2023, 'Boekjaar 0123', 'Aanslag VpB boekjaar 0123'),   # Definitieve aanslag VpB 2023
    ('4036000017000001', '036000012', 'Inkomstenbelasting', 'Voorlopige aanslag',
     2020, '—', 'Voorl. aanslag IB 2020'),   # Voorlopige aanslag IB, 2020
    ('6036000017300003', '036000012', 'Inkomstenbelasting (gemoedsbezwaarde)', 'Voorlopige aanslag',
     2020, '—', 'Voorl. aanslag IB 2020'),   # Voorlopige aanslag IB gem.bezw., 2021
    ('9036000017520034', '036000012', 'Zorgverzekeringswet', 'Voorlopige aanslag',
     2022, '—', 'Voorl. aanslag ZVW 2022'),   # Voorlopige aanslag ZVW gem.bezw., 2022
    ('3036000018730001', '036000012', 'Motorrijtuigenbelasting vrachtwagens (aangifte)', '',
     2023, '—', 'Aanslag MOA 2023'),   # Aangifte MOA, 2013
    ('1036000018710909', '036000012', 'Motorrijtuigenbelasting vrachtwagens (aangifte)', '',
     2021, '—', 'Aanslag MOA 2021'),   # Aangifte MOA, 2021
    ('1036000017830001', '036000012', 'Motorrijtuigenbelasting', '',
     2023, '—', 'Aanslag HSB 2023'),   # Aangifte HSB, 2023
    ('1036000017810909', '036000012', 'Motorrijtuigenbelasting', '',
     2021, '—', 'Aanslag HSB 2021'),   # Aangifte HSB, 2021
    ('5036000018830001', '036000012', 'Motorrijtuigenbelasting vrachtwagens (naheffing)', '',
     2023, '—', 'Naheff. MOA 2023'),   # Naheffingsaanslag MOA, 2023
    ('3036000018810909', '036000012', 'Motorrijtuigenbelasting vrachtwagens (naheffing)', '',
     2021, '—', 'Naheff. MOA 2021'),   # Naheffingsaanslag MOA, 2021
    ('8036000017630001', '036000012', 'Motorrijtuigenbelasting (naheffing)', '',
     2023, '—', 'Naheff. HSB 2023'),   # Naheffingsaanslag HSB, 2023
    ('6036000017610909', '036000012', 'Motorrijtuigenbelasting (naheffing)', '',
     2021, '—', 'Naheff. HSB 2021'),   # Naheffingsaanslag HSB, 2021
    ('7036000019730001', '036000012', 'Landinrichtingsrente', '',
     2023, '—', 'Aanslag LIR 2023'),   # Aanslag LIR, 2023
    ('3036000019710002', '036000012', 'Verontreinigingsheffing Rijkswateren', '',
     2021, '—', 'Aanslag VHR 2021'),   # Aanslag VHR, 2021
    ('1036000018530001', '036000012', 'Eurovignet', '',
     2023, '—', 'Aanslag EVN 2023'),   # Aangifte Eurovignet, 2023
    ('1036000018630001', '036000012', 'Eurovignet (naheffing)', '',
     2023, '—', 'Naheff. EVN 2023'),   # Naheffingsaanslag Eurovignet, 2023
    ('4036000012330001', '036000012', 'Kinderopvangtoeslag', '',
     2023, '—', 'Kinderopvangtoeslag 2023'),   # Kinderopvang Toeslag, 2023
    ('6036000012430001', '036000012', 'Huurtoeslag', '',
     2023, '—', 'Huurtoeslag 2023'),   # Huurtoeslag, 2023
    ('8036000012530001', '036000012', 'Zorgtoeslag', '',
     2023, '—', 'Zorgtoeslag 2023'),   # Zorgtoeslag, 20213
    ('1036000012630001', '036000012', 'Kindgebonden budget', '',
     2023, '—', 'Kindgebonden budget 2023'),   # Kindgeonden budget, 2023
    ('1036000012730001', '036000012', 'Verzuimboete Toeslagen', '',
     2023, '—', 'Verzuimboete Toeslagen 2023'),   # Verzuimboetebeschikking, 2023
    ('3036000012830001', '036000012', 'Vergrijpboete Toeslagen', '',
     2023, '—', 'Vergrijpboete Toeslagen 2023'),   # Vergrijpboetebeschikking, 2023
]


@pytest.mark.parametrize("kenmerk,bsn,soort,soort_sub,jaar,tijdvak,omschrijving", SPEC_VOORBEELDEN)
def test_specificatievoorbeeld(kenmerk, bsn, soort, soort_sub, jaar, tijdvak, omschrijving):
    r, fout = decode_kenmerk(kenmerk)
    assert fout is None, fout
    assert r["rsin9"] == bsn
    assert r["soort"] == soort
    assert r["soort_sub"] == soort_sub
    assert r["jaar"] == jaar
    assert r["tijdvak"] == tijdvak
    assert build_omschrijving(r) == omschrijving


def test_alle_specificatievoorbeelden_leveren_het_juiste_nummer_op():
    """Vangnet los van de parametrisatie: geen enkel voorbeeld mag een RSIN
    opleveren dat niet in het aanslagnummer staat."""
    for kenmerk, bsn, *_ in SPEC_VOORBEELDEN:
        r, fout = decode_kenmerk(kenmerk)
        assert fout is None
        assert r["rsin9"] == bsn, kenmerk


# ── Middelcode 97: twee heffingen onder één code ────────────────────────────

def test_middelcode_97_onderscheidt_lir_en_vhr_op_positie_16():
    """Paragraaf 9: positie 16 draagt de middelherkenning. 1 is
    landinrichtingsrente, 2 is verontreinigingsheffing rijkswateren. Voorheen
    stonden beide namen met een schuine streep in één label."""
    lir, fout = decode_kenmerk(mk("036000019730001"))
    assert fout is None
    assert lir["soort"] == "Landinrichtingsrente"
    assert lir["kort"] == "LIR"

    vhr, fout = decode_kenmerk(mk("036000019710002"))
    assert fout is None
    assert vhr["soort"] == "Verontreinigingsheffing Rijkswateren"
    assert vhr["kort"] == "VHR"


def test_middelcode_97_met_onbekende_herkenning_valt_terug_op_het_dubbele_label():
    r, fout = decode_kenmerk(mk("036000019730005"))
    assert fout is None
    assert "/" in r["soort"]


# ── SOORT-cijfer: voorlopige of definitieve aanslag ─────────────────────────

def test_soort_alleen_gelabeld_bij_bekende_codes():
    """Alleen 0 en 6 komen in de specificatievoorbeelden voor. Bij een andere
    waarde wordt niets beweerd, want dan is onbekend wat er staat."""
    voorlopig, _ = decode_kenmerk(mk("036000017000001"))
    assert voorlopig["soort_sub"] == "Voorlopige aanslag"

    onbekend, _ = decode_kenmerk(mk("036000017034001"))
    assert onbekend["soort_sub"] == ""
    assert "Aanslag IB" in build_omschrijving(onbekend)


def test_soort_wordt_niet_gelezen_waar_het_veld_niet_bestaat():
    """Bij HSB, MOA en Eurovignet is positie 13 het volgnummer. Daar mag geen
    aanslagsoort uit worden gelezen."""
    for body in ("036000018730001", "036000017830001", "036000018530001"):
        r, fout = decode_kenmerk(mk(body))
        assert fout is None
        assert r["soort_sub"] == ""


# ── Boekjaar van een VpB-aanslag ────────────────────────────────────────────

def test_boekjaar_wordt_als_maandbereik_gelezen():
    """Paragraaf 2 laat 0112 zien bij boekjaar 2022, dus beginmaand en eindmaand."""
    assert decode_boekjaar("0112") == "januari t/m december"
    assert decode_boekjaar("0403") == "april t/m maart"


def test_boekjaar_valt_terug_op_de_ruwe_code_bij_onmogelijke_maanden():
    """Beter de ruwe code tonen dan een verzonnen periode."""
    assert decode_boekjaar("0123") == "0123"
    assert decode_boekjaar("2024") == "2024"
    assert decode_boekjaar("0000") == "0000"


def test_positieweergave_markeert_de_rsin_cijfers_bij_lh_en_ob():
    """De legenda belooft dat donkere cijfers de gedecodeerde velden zijn. Bij
    LH en OB stonden de acht RSIN-posities toch als niet-gedecodeerd."""
    r, fout = decode_kenmerk(mk("123456781500210"))
    assert fout is None
    actief = r["digit_active"]
    assert all(actief[i] for i in range(1, 9)), "posities 2 t/m 9 dragen het RSIN"
    assert actief[9] and actief[10]                      # middel en jaar
    assert actief[13] and actief[14]                     # tijdvak
    assert not actief[0] and not actief[15]              # controlecijfer en volgnummer


def test_positieweergave_markeert_het_boekjaar_bij_vpb():
    r, fout = decode_kenmerk(mk("123456507420240"))
    assert fout is None
    assert all(r["digit_active"][11:15]), "posities 12 t/m 15 dragen het boekjaar"


def test_positieweergave_markeert_positie_16_alleen_bij_middelcode_97():
    lir, _ = decode_kenmerk(mk("036000019730001"))
    assert lir["digit_active"][15] is True
    hsb, _ = decode_kenmerk(mk("036000017830001"))
    assert hsb["digit_active"][15] is False


# ── K5: welk nummer mag naar de KvK ─────────────────────────────────────────

@pytest.mark.parametrize("nummer,verwacht", [
    ("001234567", True),     # RSIN begint met 00
    ("801234567", True),     # 80 t/m 89
    ("891234567", True),
    ("863521721", True),     # het gevalideerde kenmerk uit de README
    ("123456782", False),    # gewoon een BSN-reeks
    ("036000012", False),
    ("791234567", False),    # net onder de reeks
    ("901234567", False),    # net erboven
    (None, False),
])
def test_mogelijk_rsin_volgt_de_beginposities_uit_de_specificatie(nummer, verwacht):
    """Paragraaf 2: "RSIN-s beginnen altijd met 00, of 80 t/m 89"."""
    assert is_mogelijk_rsin(nummer) is verwacht


def test_inkomstenbelasting_levert_een_bsn_en_gaat_niet_naar_de_kvk():
    """Actiepunt 3: inkomstenbelasting wordt alleen aan natuurlijke personen
    opgelegd, dus het nummer is een BSN. Dat gaat niet naar een externe partij."""
    r, fout = decode_kenmerk(mk("036000017000001"))
    assert fout is None
    assert r["nummer_soort"] == "bsn"
    assert mag_naar_kvk(r) is False
    assert "BSN" in nummer_label(r)


@pytest.mark.parametrize("body", [
    "036000017000001",   # 70 inkomstenbelasting
    "036000017100001",   # 71 conserverende aanslag
    "036000017300001",   # 73 IB gemoedsbezwaarde
    "036000017500001",   # 75 zorgverzekeringswet
    "036000012300001",   # 23 kinderopvangtoeslag
    "036000012400001",   # 24 huurtoeslag
    "036000012500001",   # 25 zorgtoeslag
    "036000012600001",   # 26 kindgebonden budget
    "036000012700001",   # 27 verzuimboete
    "036000012800001",   # 28 vergrijpboete
])
def test_persoonsgebonden_middelen_gaan_nooit_naar_de_kvk(body):
    r, fout = decode_kenmerk(mk(body))
    assert fout is None
    assert r["nummer_soort"] == "bsn"
    assert mag_naar_kvk(r) is False


def test_vennootschapsbelasting_is_altijd_een_rsin():
    """Paragraaf 2: een VpB-aanslagnummer bevat altijd een RSIN en nooit een BSN."""
    r, fout = decode_kenmerk(mk("253586208001120"))
    assert fout is None
    assert r["nummer_soort"] == "rsin"
    assert mag_naar_kvk(r) is True
    assert nummer_label(r) == "RSIN"


def test_omzetbelasting_hangt_af_van_het_nummer_zelf():
    """Een BV en een eenmanszaak dragen beide omzetbelasting af. Bij een nummer
    dat geen RSIN kan zijn, blijft de opzoeking uit."""
    bedrijf, _ = decode_kenmerk("4863521721601050")     # het gevalideerde kenmerk
    assert bedrijf["nummer_soort"] == "onbekend"
    assert bedrijf["rsin9"] == "863521721"
    assert mag_naar_kvk(bedrijf) is True

    persoon, _ = decode_kenmerk(mk("123456781500210"))
    assert persoon["nummer_soort"] == "onbekend"
    assert persoon["rsin9"] == "123456782"
    assert mag_naar_kvk(persoon) is False


def test_zonder_nummer_geen_opzoeking():
    r, fout = decode_kenmerk(mk("100000061500210"))
    assert fout is None and r["rsin9"] is None
    assert mag_naar_kvk(r) is False
    assert mag_naar_kvk(None) is False


def test_geen_enkel_specificatievoorbeeld_stuurt_een_bsn_naar_de_kvk():
    """Breed vangnet over de 27 officiële voorbeelden: alles wat doorgelaten wordt
    moet een nummer zijn dat een RSIN kán zijn."""
    for kenmerk, bsn, *_ in SPEC_VOORBEELDEN:
        r, fout = decode_kenmerk(kenmerk)
        assert fout is None
        if mag_naar_kvk(r):
            assert is_mogelijk_rsin(r["rsin9"]), (kenmerk, r["rsin9"])
