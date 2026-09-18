"""Tests voor de invorderingsrente van hoofdstuk V Invorderingswet 1990.

Anders dan bij belastingrente publiceert de Belastingdienst voor
invorderingsrente geen rekenvoorbeeld dat als toetssteen kan dienen. De tests
hieronder leggen daarom de regels vast zoals zij in de wet, het
Uitvoeringsbesluit en de Uitvoeringsregeling staan, met de vindplaats per test.
Elke test die een fiscale regel vastlegt noemt het artikel in zijn docstring,
zodat bij een wetswijziging te zien is welke test opnieuw langs de bron moet.

De drie regels die het meest afwijken van `_rente.py` staan voorop: de
dagentelling van art. 31 URIW 1990, de asymmetrische afronding van art. 32 en
het feit dat er één keer over het geheel wordt afgerond.
"""

from datetime import date

import pytest

from _invorderingsrente import (
    ART28C_SIGNALERING,
    DREMPELS,
    TARIEVEN_IN_REKENING,
    TARIEVEN_TE_VERGOEDEN,
    UITSLUITING_BELASTINGRENTE,
    UITSTELGRONDEN,
    UITZONDERINGEN,
    HERLEVING_NA_UITSTEL,
    afronden,
    bereken,
    buiten_bereik,
    dagen_invorderingsrente,
    deelperioden,
    drempel_op,
    invorderbaar_op,
    maandlengte,
    periode_art28,
    periode_art28a,
    periode_art28b,
    samenvoegen,
    splits_betaling,
    tarief_op,
    uiterste_verzoekdatum_28c,
    vervalmaand_van,
)


# ── Art. 31 URIW 1990: de dagentelling ──────────────────────────────────────

def test_volle_maand_telt_dertig_dagen():
    """Art. 31 onderdeel b URIW 1990: een volle maand is 30 dagen."""
    assert maandlengte(2025, 1, None) == 30
    assert maandlengte(2025, 4, None) == 30
    assert maandlengte(2025, 2, None) == 30


def test_vervalmaand_telt_haar_werkelijke_lengte():
    """Art. 31 onderdeel a URIW 1990: de maand waarin de enige of laatste
    betalingstermijn vervalt, telt haar werkelijke aantal dagen."""
    assert maandlengte(2025, 1, (2025, 1)) == 31
    assert maandlengte(2025, 4, (2025, 4)) == 30
    assert maandlengte(2025, 12, (2025, 12)) == 31


def test_februari_als_vervalmaand_altijd_achtentwintig_dagen():
    """Art. 31 onderdeel a, slot: februari wordt altijd op 28 dagen gesteld.

    Ook in een schrikkeljaar. 2024 en 2028 zijn schrikkeljaren.
    """
    assert maandlengte(2024, 2, (2024, 2)) == 28
    assert maandlengte(2028, 2, (2028, 2)) == 28
    assert maandlengte(2025, 2, (2025, 2)) == 28


def test_een_jaar_is_driehonderdzestig_dagen():
    """Art. 31 onderdeel b URIW 1990: een jaar wordt op 360 dagen gesteld."""
    assert dagen_invorderingsrente(date(2025, 1, 1), date(2025, 12, 31)) == 360
    assert dagen_invorderingsrente(date(2024, 1, 1), date(2024, 12, 31)) == 360


def test_telling_over_de_vervalmaand_heen():
    """Aanslag met dagtekening 15-01-2026, betaald op 10-04-2026.

    Invorderbaar op 26-02-2026, dus februari 2026 is de vervalmaand en telt
    28 dagen. Van dag 26 tot en met dag 28 is 3 dagen, maart telt 30 en april
    telt tot en met dag 9. Samen 42 dagen.
    """
    vervaldag = invorderbaar_op(date(2026, 1, 15))
    assert vervaldag == date(2026, 2, 26)
    vanaf, tot = periode_art28(vervaldag, date(2026, 4, 10))
    assert (vanaf, tot) == (date(2026, 2, 26), date(2026, 4, 9))
    assert dagen_invorderingsrente(vanaf, tot, vervalmaand_van(vervaldag)) == 42


def test_zonder_vervalmaand_telt_februari_voor_dertig():
    """Zonder betalingstermijn valt onderdeel a weg en blijft alleen b over.

    Dat speelt bij art. 28a: daar vangt het tijdvak aan na de dagtekening van
    een uitbetaling en vervalt er geen betalingstermijn. Dezelfde periode als
    in de vorige test komt dan op 44 dagen uit in plaats van 42.
    """
    assert dagen_invorderingsrente(date(2026, 2, 26), date(2026, 4, 9)) == 44


def test_dag_eenendertig_wordt_op_dertig_gezet():
    """In een maand die voor 30 telt bestaat dag 31 niet; die telt als dag 30.

    Zonder die kap zou een maand van 31 dagen alsnog 31 opleveren en klopt de
    jaartelling van 360 niet meer. `dagen_30_360()` in `_rente.py` doet het
    om dezelfde reden.
    """
    assert dagen_invorderingsrente(date(2025, 1, 31), date(2025, 1, 31)) == 1
    assert dagen_invorderingsrente(date(2025, 1, 1), date(2025, 1, 31)) == 30


def test_schrikkeldag_telt_niet_mee_in_de_vervalmaand():
    """Februari 2024 als vervalmaand loopt voor de telling tot en met dag 28."""
    assert dagen_invorderingsrente(date(2024, 2, 1), date(2024, 2, 29), (2024, 2)) == 28


def test_telling_is_optelbaar():
    """Een periode knippen mag de uitkomst niet veranderen.

    Dat is de voorwaarde om op een tariefwissel te kunnen knippen zonder dat
    het totale aantal dagen verschuift.
    """
    vervalmaand = (2025, 3)
    heel = dagen_invorderingsrente(date(2025, 3, 10), date(2026, 5, 20), vervalmaand)
    deel1 = dagen_invorderingsrente(date(2025, 3, 10), date(2025, 12, 31), vervalmaand)
    deel2 = dagen_invorderingsrente(date(2026, 1, 1), date(2026, 5, 20), vervalmaand)
    assert heel == deel1 + deel2


def test_lege_periode_geeft_nul_dagen():
    assert dagen_invorderingsrente(date(2025, 5, 10), date(2025, 5, 9)) == 0


def test_dagentelling_is_niet_die_van_de_belastingrente():
    """De twee modules tellen aantoonbaar anders.

    Deze test staat er om te voorkomen dat iemand `dagen_30_360()` alsnog
    hergebruikt: over een periode die in de vervalmaand begint, wijken zij af.
    """
    from _rente import dagen_30_360
    vanaf, tot = date(2026, 1, 20), date(2026, 3, 10)
    assert dagen_30_360(vanaf, tot) == 51
    assert dagen_invorderingsrente(vanaf, tot, (2026, 1)) == 52


# ── Art. 32 URIW 1990: de afronding ─────────────────────────────────────────

def test_in_rekening_naar_beneden_en_vergoeding_naar_boven():
    """Art. 32 lid 1 en lid 2 URIW 1990."""
    assert afronden(10.9, "in_rekening") == 10
    assert afronden(10.1, "te_vergoeden") == 11
    assert afronden(10.0, "in_rekening") == 10
    assert afronden(10.0, "te_vergoeden") == 10


def test_onbekende_richting_wordt_geweigerd():
    with pytest.raises(ValueError):
        afronden(10.0, "onbekend")


def test_er_wordt_een_keer_afgerond_en_niet_per_tariefperiode():
    """Art. 30 lid 1 URIW 1990 telt de deelperioden eerst op: (A x P + A x P enz.).

    Over 01-12-2025 tot en met 31-01-2026 loopt 30 dagen tegen 4 procent en
    30 dagen tegen 4,3 procent. Samen 249, dus 10.000 x 249 / 36.000 = 69,17.
    Naar beneden is dat 69. Zou er per tariefperiode worden afgerond, zoals bij
    belastingrente, dan werd het 33 + 35 = 68. Die 68 hoort er niet uit te komen.
    """
    uit = bereken(10000, date(2025, 12, 1), date(2026, 1, 31),
                  TARIEVEN_IN_REKENING, "in_rekening")
    assert [p["dagen"] for p in uit["perioden"]] == [30, 30]
    assert [p["pct"] for p in uit["perioden"]] == [4.0, 4.3]
    assert round(uit["onafgerond"], 2) == 69.17
    assert uit["afgerond"] == 69


def test_zelfde_periode_als_vergoeding_rondt_naar_boven():
    """Dezelfde 69,17 wordt als vergoeding 70 en niet 69."""
    uit = bereken(10000, date(2025, 12, 1), date(2026, 1, 31),
                  TARIEVEN_TE_VERGOEDEN, "te_vergoeden")
    assert uit["afgerond"] == 70


# ── Art. 30 URIW 1990: de formule ───────────────────────────────────────────

def test_formule_van_artikel_30_lid_1():
    """(A x P + A x P enz.) x betaling / 36000.

    Een vol jaar tegen 4 procent over 10.000 euro is 360 x 4 x 10.000 / 36.000
    = 400 euro.
    """
    uit = bereken(10000, date(2024, 1, 1), date(2024, 12, 31),
                  TARIEVEN_IN_REKENING, "in_rekening")
    assert uit["dagen"] == 360
    assert uit["onafgerond"] == 400.0
    assert uit["bedrag"] == 400


def test_splitsing_van_een_betaling_artikel_30_lid_2():
    """hoofdsom = 36.000 x betaling / (A x P + A x P enz. + 36.000).

    Bij 360 dagen tegen 4 procent is de teller van de rente 1.440. Een betaling
    van 10.400 euro valt dan uiteen in 10.000 hoofdsom en 400 rente:
    36.000 x 10.400 / 37.440 = 10.000.
    """
    hoofdsom, rente = splits_betaling(10400, date(2024, 1, 1), date(2024, 12, 31),
                                      TARIEVEN_IN_REKENING)
    assert (hoofdsom, rente) == (10000, 400)


def test_splitsing_rondt_de_betaling_naar_beneden_af():
    """Art. 30 lid 4 URIW 1990: het bedrag van de betaling wordt naar beneden
    afgerond op hele euro's, en de twee delen tellen daarna op tot dat bedrag."""
    hoofdsom, rente = splits_betaling(10400.99, date(2024, 1, 1), date(2024, 12, 31),
                                      TARIEVEN_IN_REKENING)
    assert hoofdsom + rente == 10400


# ── Art. 33 URIW 1990: het drempelbedrag ────────────────────────────────────

def test_drempelbedrag_per_peildatum():
    """Art. 33 lid 1 URIW 1990, met de indexering van lid 2 per 01-01-2026
    (Stcrt. 2025, 42873). Daarvoor stond er 23 euro."""
    assert drempel_op(date(2025, 12, 31)) == 23
    assert drempel_op(date(2026, 1, 1)) == 49
    assert drempel_op(date(2026, 9, 18)) == 49


def test_drempel_maakt_een_klein_bedrag_nihil_bij_de_laatste_betaling():
    """Art. 33 lid 1: bij de enige of laatste betaling wordt een bedrag van
    49 euro of minder niet in rekening gebracht."""
    uit = bereken(1000, date(2026, 1, 1), date(2026, 4, 30),
                  TARIEVEN_IN_REKENING, "in_rekening", laatste_betaling=True)
    assert uit["afgerond"] == 14
    assert uit["kwijt_door_drempel"] is True
    assert uit["bedrag"] == 0


def test_drempel_geldt_niet_bij_een_tussentijdse_betaling():
    """De drempel is aan de enige of laatste betaling gekoppeld. Bij een
    tussentijdse betaling blijft het bedrag staan."""
    uit = bereken(1000, date(2026, 1, 1), date(2026, 4, 30),
                  TARIEVEN_IN_REKENING, "in_rekening", laatste_betaling=False)
    assert uit["bedrag"] == 14
    assert uit["drempel"] is None


def test_drempel_geldt_nooit_bij_een_vergoeding():
    """Art. 33 spreekt alleen van rente die in rekening wordt gebracht."""
    uit = bereken(1000, date(2026, 1, 1), date(2026, 4, 30),
                  TARIEVEN_TE_VERGOEDEN, "te_vergoeden", laatste_betaling=True)
    assert uit["drempel"] is None
    assert uit["bedrag"] == 15


# ── De tariefreeksen ────────────────────────────────────────────────────────

def test_percentage_per_ingangsdatum_in_rekening():
    """Art. 2 Besluit belasting- en invorderingsrente, alle expressies."""
    assert tarief_op(date(2020, 6, 1), TARIEVEN_IN_REKENING) == 0.01
    assert tarief_op(date(2022, 7, 1), TARIEVEN_IN_REKENING) == 1.0
    assert tarief_op(date(2023, 1, 1), TARIEVEN_IN_REKENING) == 2.0
    assert tarief_op(date(2023, 7, 1), TARIEVEN_IN_REKENING) == 3.0
    assert tarief_op(date(2024, 1, 1), TARIEVEN_IN_REKENING) == 4.0
    assert tarief_op(date(2025, 6, 1), TARIEVEN_IN_REKENING) == 4.0
    assert tarief_op(date(2026, 1, 1), TARIEVEN_IN_REKENING) == 4.3


def test_de_twee_reeksen_lopen_uiteen_in_de_tweede_helft_van_2023():
    """Art. 2 lid 2 van het besluit koppelde de te vergoeden rente tot en met
    2023 aan de wettelijke rente, met een bodem van 4.

    De wettelijke rente ging per 01-07-2023 naar 6 procent, terwijl de in
    rekening te brengen rente op 3 procent stond. Wie hier één reeks gebruikt,
    rekent een vergoeding over de tweede helft van 2023 op de helft uit.
    """
    assert tarief_op(date(2023, 8, 1), TARIEVEN_IN_REKENING) == 3.0
    assert tarief_op(date(2023, 8, 1), TARIEVEN_TE_VERGOEDEN) == 6.0


def test_bodem_van_vier_procent_tot_en_met_2023():
    """De wettelijke rente was 2 procent tot 2023 en 4 procent in de eerste
    helft van 2023; door de bodem komt de vergoeding in beide gevallen op 4."""
    assert tarief_op(date(2020, 6, 1), TARIEVEN_TE_VERGOEDEN) == 4.0
    assert tarief_op(date(2022, 12, 31), TARIEVEN_TE_VERGOEDEN) == 4.0
    assert tarief_op(date(2023, 6, 30), TARIEVEN_TE_VERGOEDEN) == 4.0


def test_de_reeksen_vallen_vanaf_2024_samen():
    """Per 01-01-2024 is art. 2 teruggebracht tot één percentage."""
    for dag in (date(2024, 1, 1), date(2025, 7, 1), date(2026, 1, 1)):
        assert tarief_op(dag, TARIEVEN_IN_REKENING) == tarief_op(dag, TARIEVEN_TE_VERGOEDEN)


def test_onbekende_datum_geeft_geen_stille_terugval():
    """Vóór 01-06-2020 kent deze tool geen percentage. Er mag dan geen oud
    tarief worden toegepast; de aanroeper hoort een melding te geven."""
    assert tarief_op(date(2020, 5, 31), TARIEVEN_IN_REKENING) is None
    assert buiten_bereik(date(2020, 5, 31), TARIEVEN_IN_REKENING) is True
    assert buiten_bereik(date(2020, 6, 1), TARIEVEN_IN_REKENING) is False


def test_berekening_buiten_de_reeks_wordt_geweigerd():
    with pytest.raises(ValueError):
        bereken(10000, date(2019, 1, 1), date(2021, 1, 1),
                TARIEVEN_IN_REKENING, "in_rekening")


def test_reeksen_zijn_nieuw_naar_oud_gesorteerd():
    """Zoals de reeksen in de belastingrentepagina's; `tarief_op` rekent erop."""
    for reeks in (TARIEVEN_IN_REKENING, TARIEVEN_TE_VERGOEDEN, DREMPELS):
        datums = [ingang for ingang, _ in reeks]
        assert datums == sorted(datums, reverse=True)


# ── Art. 9 IW 1990: invorderbaarheid ────────────────────────────────────────

def test_invorderbaar_zes_weken_na_de_dagtekening():
    """Art. 9 lid 1 IW 1990."""
    assert invorderbaar_op(date(2026, 1, 15)) == date(2026, 2, 26)


def test_navordering_een_maand_en_naheffing_veertien_dagen():
    """Art. 9 lid 2 IW 1990."""
    assert invorderbaar_op(date(2026, 1, 15), "navordering") == date(2026, 2, 15)
    assert invorderbaar_op(date(2026, 1, 31), "navordering") == date(2026, 2, 28)
    assert invorderbaar_op(date(2026, 1, 15), "naheffing") == date(2026, 1, 29)


def test_onbekend_aanslagtype_wordt_geweigerd():
    with pytest.raises(ValueError):
        invorderbaar_op(date(2026, 1, 15), "voorlopig-in-termijnen")


# ── De drie tijdvakken ──────────────────────────────────────────────────────

def test_artikel_28_loopt_tot_de_dag_voor_de_betaling():
    """Art. 28 lid 2 IW 1990: het tijdvak vangt aan op de dag waarop de aanslag
    invorderbaar is en eindigt op de dag voorafgaand aan die van de betaling."""
    assert periode_art28(date(2026, 2, 26), date(2026, 2, 27)) == (
        date(2026, 2, 26), date(2026, 2, 26))


def test_artikel_28_geeft_niets_bij_tijdige_betaling():
    """Art. 28 lid 1 vraagt overschrijding van de enige of laatste
    betalingstermijn. Wie op de vervaldag betaalt, overschrijdt niet."""
    assert periode_art28(date(2026, 2, 26), date(2026, 2, 26)) is None
    assert periode_art28(date(2026, 2, 26), date(2026, 1, 5)) is None


def test_artikel_28a_pas_na_zes_weken_maar_dan_terug_tot_de_dagtekening():
    """Art. 28a lid 1 en lid 2 IW 1990 noemen verschillende momenten.

    Lid 1 bepaalt of er wordt vergoed: pas als de ontvanger niet binnen zes
    weken na de dagtekening uitbetaalt. Lid 2 bepaalt waarover wordt gerekend,
    en dat is vanaf de dag ná de dagtekening. Het tijdvak begint dus niet pas
    na die zes weken.
    """
    dagtekening = date(2026, 3, 2)
    assert periode_art28a(dagtekening, date(2026, 4, 13)) is None
    vanaf, tot = periode_art28a(dagtekening, date(2026, 4, 14))
    assert vanaf == date(2026, 3, 3)
    assert tot == date(2026, 4, 13)


def test_artikel_28b_eindigt_zes_weken_na_de_vermindering():
    """Art. 28b lid 2 IW 1990: aanvang de dag ná de invorderbaarheid, einde zes
    weken na de dagtekening van de vermindering of herziening."""
    vervaldag = invorderbaar_op(date(2025, 1, 10))
    vanaf, tot = periode_art28b(vervaldag, date(2026, 3, 5))
    assert vanaf == vervaldag + __import__("datetime").timedelta(days=1)
    assert tot == date(2026, 4, 16)


def test_artikel_28b_geeft_niets_als_het_einde_voor_het_begin_ligt():
    vervaldag = date(2026, 6, 1)
    assert periode_art28b(vervaldag, date(2026, 1, 1)) is None


# ── Samenloop met de belastingrente van hoofdstuk VA AWR ────────────────────

def test_alleen_artikel_28a_kent_de_uitsluiting():
    """Nagelezen in de wettekst zelf.

    Art. 28a lid 2, tweede volzin, sluit de dagen uit waarover al
    belastingrente is vergoed. Art. 28 lid 2 en art. 28b lid 2 kennen die
    uitsluiting niet. Art. 28c lid 2 kent haar wel, maar die grondslag wordt
    door deze tool niet gerekend.
    """
    assert UITSLUITING_BELASTINGRENTE["28"] is False
    assert UITSLUITING_BELASTINGRENTE["28a"] is True
    assert UITSLUITING_BELASTINGRENTE["28b"] is False
    assert UITSLUITING_BELASTINGRENTE["28c"] is True


def test_uitgesloten_dagen_tellen_niet_mee():
    """Over een vol jaar tegen 4 procent waarvan een half jaar al met
    belastingrente is vergoed, blijft de helft over."""
    uit = bereken(10000, date(2024, 1, 1), date(2024, 12, 31),
                  TARIEVEN_TE_VERGOEDEN, "te_vergoeden",
                  uitgesloten=[(date(2024, 1, 1), date(2024, 6, 30))])
    assert uit["dagen"] == 180
    assert uit["dagen_uitgesloten"] == 180
    assert uit["bedrag"] == 200


def test_overlappende_uitgesloten_bereiken_tellen_maar_een_keer():
    """Zonder samenvoegen zou een dag die in twee bereiken valt, twee keer van
    het tijdvak worden afgetrokken."""
    uit = bereken(10000, date(2024, 1, 1), date(2024, 12, 31),
                  TARIEVEN_TE_VERGOEDEN, "te_vergoeden",
                  uitgesloten=[(date(2024, 1, 1), date(2024, 6, 30)),
                               (date(2024, 4, 1), date(2024, 6, 30))])
    assert uit["dagen"] == 180


def test_samenvoegen_plakt_aansluitende_bereiken():
    assert samenvoegen([(date(2024, 1, 1), date(2024, 1, 31)),
                        (date(2024, 2, 1), date(2024, 2, 20))]) == [
        (date(2024, 1, 1), date(2024, 2, 20))]
    assert samenvoegen([(date(2024, 3, 1), date(2024, 2, 1))]) == []


def test_uitsluiting_buiten_het_tijdvak_verandert_niets():
    uit = bereken(10000, date(2024, 1, 1), date(2024, 12, 31),
                  TARIEVEN_TE_VERGOEDEN, "te_vergoeden",
                  uitgesloten=[(date(2023, 1, 1), date(2023, 6, 30))])
    assert uit["dagen"] == 360
    assert uit["dagen_uitgesloten"] == 0


# ── Uitstel, uitzonderingen en artikel 28c ──────────────────────────────────

def test_negen_uitstelgronden_uit_artikel_28_lid_3():
    """Art. 28 lid 3 IW 1990 noemt het derde, vijfde, achtste, negende, elfde,
    zeventiende, achttiende, negentiende en eenentwintigste lid van art. 25."""
    codes = [code for code, _ in UITSTELGRONDEN]
    assert codes == ["25-3", "25-5", "25-8", "25-9", "25-11",
                     "25-17", "25-18", "25-19", "25-21"]


def test_herlevingstijdvak_volgt_artikel_6_uitvoeringsbesluit():
    """Art. 6 lid 1 geldt voor de gronden van art. 25 lid 5 en 8; lid 2 voor de
    overige gronden die art. 28 lid 4 noemt. Art. 25 lid 3 staat niet in
    art. 28 lid 4 en heeft dus geen aangewezen herlevingstijdvak."""
    assert "eerste dag van het jaar volgend" in HERLEVING_NA_UITSTEL["25-5"]
    assert "eerste dag van het jaar volgend" in HERLEVING_NA_UITSTEL["25-8"]
    assert "dag volgend op de dag" in HERLEVING_NA_UITSTEL["25-9"]
    assert "25-3" not in HERLEVING_NA_UITSTEL


def test_twee_aanwijzingen_op_grond_van_artikel_28_lid_5():
    """Hoofdstuk II van het Uitvoeringsbesluit IW 1990 wijst twee gevallen aan:
    art. 6bis (aanhoudaanbod box 3 over 2022) en art. 6ter (hersteloperatie
    toeslagen). De derde regel in de lijst is beleid uit de Leidraad en geen
    aanwijzing op grond van art. 28 lid 5."""
    amvb = [u for u in UITZONDERINGEN if not u["beleidsmatig"]]
    assert [u["code"] for u in amvb] == ["box3-2022", "toeslagenherstel"]
    assert all("Uitvoeringsbesluit" in u["bron"] for u in amvb)

    beleid = [u for u in UITZONDERINGEN if u["beleidsmatig"]]
    assert [u["code"] for u in beleid] == ["leidraad-25.4.6"]


def test_artikel_28c_wordt_gesignaleerd_en_niet_gerekend():
    """Art. 28c lid 1 en lid 3 IW 1990. De tool rekent deze grondslag niet."""
    assert "op verzoek" in ART28C_SIGNALERING or "alleen op verzoek" in ART28C_SIGNALERING
    assert "zes weken" in ART28C_SIGNALERING
    assert "rekent die grondslag niet uit" in ART28C_SIGNALERING


def test_uiterste_verzoekdatum_28c():
    """Art. 28c lid 3: zes weken na dagtekening van de beschikking."""
    assert uiterste_verzoekdatum_28c(date(2026, 3, 2)) == date(2026, 4, 13)


# ── Een doorgerekend geval van begin tot eind ───────────────────────────────

def test_volledig_geval_artikel_28():
    """Aanslag van 25.000 euro, dagtekening 15-01-2026, betaald op 10-04-2026.

    Invorderbaar 26-02-2026, dus de vervalmaand is februari 2026 en telt 28
    dagen. Het tijdvak is 26-02-2026 tot en met 09-04-2026, samen 42 dagen, en
    het percentage is 4,3. De rente is 42 x 4,3 x 25.000 / 36.000 = 125,42, naar
    beneden afgerond 125. Dat ligt boven de drempel van 49 euro.
    """
    vervaldag = invorderbaar_op(date(2026, 1, 15))
    vanaf, tot = periode_art28(vervaldag, date(2026, 4, 10))
    uit = bereken(25000, vanaf, tot, TARIEVEN_IN_REKENING, "in_rekening",
                  vervalmaand=vervalmaand_van(vervaldag), laatste_betaling=True)
    assert uit["dagen"] == 42
    assert round(uit["onafgerond"], 2) == 125.42
    assert uit["bedrag"] == 125
    assert uit["kwijt_door_drempel"] is False


def test_volledig_geval_artikel_28a():
    """Teruggaaf van 8.000 euro, dagtekening 02-03-2026, uitbetaald 01-07-2026.

    Later dan zes weken, dus er wordt vergoed. Het tijdvak loopt van 03-03-2026
    tot en met 30-06-2026: maart 28 dagen vanaf dag 3, april, mei en juni elk
    30. Er is geen betalingstermijn, dus alle maanden tellen voor 30 en het
    tijdvak is 28 + 90 = 118 dagen. 118 x 4,3 x 8.000 / 36.000 = 112,76, naar
    boven afgerond 113.
    """
    vanaf, tot = periode_art28a(date(2026, 3, 2), date(2026, 7, 1))
    assert (vanaf, tot) == (date(2026, 3, 3), date(2026, 6, 30))
    uit = bereken(8000, vanaf, tot, TARIEVEN_TE_VERGOEDEN, "te_vergoeden")
    assert uit["dagen"] == 118
    assert round(uit["onafgerond"], 2) == 112.76
    assert uit["bedrag"] == 113


def test_volledig_geval_artikel_28b():
    """Aanslag met dagtekening 10-01-2025, uitstelverzoek afgewezen, vermindering
    met dagtekening 05-03-2026 en een terug te geven bedrag van 12.000 euro.

    Invorderbaar 21-02-2025, dus het tijdvak vangt aan op 22-02-2025 en eindigt
    zes weken na 05-03-2026, dat is 16-04-2026. De vervalmaand is februari 2025
    en telt 28 dagen.
    """
    vervaldag = invorderbaar_op(date(2025, 1, 10))
    assert vervaldag == date(2025, 2, 21)
    vanaf, tot = periode_art28b(vervaldag, date(2026, 3, 5))
    assert (vanaf, tot) == (date(2025, 2, 22), date(2026, 4, 16))
    uit = bereken(12000, vanaf, tot, TARIEVEN_TE_VERGOEDEN, "te_vergoeden",
                  vervalmaand=vervalmaand_van(vervaldag))
    # 22-02 t/m 28-02 is 7 dagen, maart t/m december 2025 is 300, januari t/m
    # maart 2026 is 90 en april tot en met dag 16 is 16: samen 413 dagen.
    assert uit["dagen"] == 413
    assert uit["perioden"][0]["pct"] == 4.0
    assert uit["perioden"][1]["pct"] == 4.3


def test_deelperioden_knippen_op_de_tariefwissel():
    perioden = deelperioden(date(2025, 11, 1), date(2026, 2, 28),
                            TARIEVEN_IN_REKENING)
    assert [p["start"] for p in perioden] == [date(2025, 11, 1), date(2026, 1, 1)]
    assert [p["eind"] for p in perioden] == [date(2025, 12, 31), date(2026, 2, 28)]
