"""Tests voor de belastingrenteberekening.

De eerste groep tests is het belangrijkst: die reproduceert de rekenvoorbeelden
die de Belastingdienst zelf op zijn site publiceert. Zolang die groen zijn, klopt
de rekenmethode aantoonbaar met de bron.
"""

from datetime import date

import pytest

from _rente import (
    STARTMAAND_RENTE,
    bereken,
    dagen_30_360,
    eerste_dag_van_maand_na,
    nl_euro_heel,
    nl_pct,
    renteperiode,
    tarief_op,
)

# Tarieven zoals ze op belastingdienst.nl staan (algemene tabel).
TARIEVEN = [
    (date(2026, 1, 1),  5.00),
    (date(2025, 1, 1),  6.50),
    (date(2024, 1, 1),  7.50),
    (date(2023, 7, 1),  6.00),
    (date(2020, 10, 1), 4.00),
    (date(2020, 6, 1),  0.01),
    (date(2014, 4, 1),  4.00),
    (date(2013, 1, 1),  3.00),
]


# ── De gepubliceerde voorbeelden van de Belastingdienst ─────────────────────

def test_voorbeeld_belastingdienst_1():
    """"Wij rekenen belastingrente van 1 juli 2024 tot en met 13 september 2024.
    Dat is 2 maanden en 13 dagen, dus bij elkaar 73 dagen.
    U betaalt aan belastingrente: 73/360 x 7,5% x € 1.000 = € 15"
    """
    assert dagen_30_360(date(2024, 7, 1), date(2024, 9, 13)) == 73
    totaal, _ = bereken(1000, date(2024, 7, 1), date(2024, 9, 13), TARIEVEN)
    assert totaal == 15


def test_voorbeeld_belastingdienst_2():
    """Aanslag € 2.500, periode 1 juli 2024 tot en met 22 januari 2025.
    De site rekent: 180/360 x 7,5% x € 2.500 = € 93
                 +   22/360 x 6,5% x € 2.500 = €  9   -> totaal € 102
    """
    assert dagen_30_360(date(2024, 7, 1), date(2024, 12, 31)) == 180
    assert dagen_30_360(date(2025, 1, 1), date(2025, 1, 22)) == 22

    totaal, perioden = bereken(2500, date(2024, 7, 1), date(2025, 1, 22), TARIEVEN)
    assert [p["dagen"] for p in perioden] == [180, 22]
    assert [p["rente"] for p in perioden] == [93, 9]
    assert totaal == 102


def test_afronding_gebeurt_per_deelperiode_en_niet_over_het_totaal():
    """93,75 + 9,93 = 103,68. Zou over het totaal worden afgerond, dan kwam er
    103 uit; de Belastingdienst komt op 102."""
    totaal, _ = bereken(2500, date(2024, 7, 1), date(2025, 1, 22), TARIEVEN)
    assert totaal == 102
    assert totaal != 103


# ── Dagentelling 30/360 ─────────────────────────────────────────────────────

def test_een_hele_maand_is_dertig_dagen():
    assert dagen_30_360(date(2025, 3, 1), date(2025, 3, 31)) == 30
    assert dagen_30_360(date(2025, 2, 1), date(2025, 2, 28)) == 28


def test_een_heel_jaar_is_driehonderdzestig_dagen():
    assert dagen_30_360(date(2025, 1, 1), date(2025, 12, 31)) == 360


def test_schrikkeljaar_maakt_geen_verschil():
    """Bij 30/360 telt 29 februari niet extra mee."""
    assert dagen_30_360(date(2024, 1, 1), date(2024, 12, 31)) == 360


def test_een_enkele_dag():
    assert dagen_30_360(date(2025, 5, 10), date(2025, 5, 10)) == 1


def test_einddatum_telt_mee():
    assert dagen_30_360(date(2025, 5, 1), date(2025, 5, 2)) == 2


# ── Tarieven ────────────────────────────────────────────────────────────────

def test_tarief_op_datum():
    assert tarief_op(date(2026, 6, 1), TARIEVEN) == 5.00
    assert tarief_op(date(2025, 6, 1), TARIEVEN) == 6.50
    assert tarief_op(date(2026, 1, 1), TARIEVEN) == 5.00
    assert tarief_op(date(2025, 12, 31), TARIEVEN) == 6.50


def test_periode_wordt_geknipt_op_elke_tariefwijziging():
    _, perioden = bereken(10000, date(2023, 1, 1), date(2026, 6, 30), TARIEVEN)
    ingangen = [p["start"] for p in perioden]
    assert date(2023, 7, 1) in ingangen
    assert date(2024, 1, 1) in ingangen
    assert date(2025, 1, 1) in ingangen
    assert date(2026, 1, 1) in ingangen


def test_deelperioden_sluiten_op_elkaar_aan_zonder_gaten():
    from datetime import timedelta
    _, perioden = bereken(10000, date(2023, 1, 1), date(2026, 6, 30), TARIEVEN)
    for vorige, volgende in zip(perioden, perioden[1:]):
        assert vorige["eind"] + timedelta(days=1) == volgende["start"]
    assert perioden[0]["start"] == date(2023, 1, 1)
    assert perioden[-1]["eind"] == date(2026, 6, 30)


def test_lege_periode_geeft_nul():
    totaal, perioden = bereken(10000, date(2025, 6, 1), date(2025, 5, 1), TARIEVEN)
    assert totaal == 0
    assert perioden == []


# ── Renteperiode: de drie situaties ─────────────────────────────────────────

UITERSTE_IB = date(2025, 5, 1)     # IB: vóór 1 mei volgend op het belastingjaar
UITERSTE_VPB = date(2025, 6, 1)    # VpB: vóór 1 juni


def test_op_tijd_en_geen_afwijking_geeft_geen_rente():
    """"U betaalt geen belastingrente als u voor 1 mei aangifte doet en wij uw
    gegevens ongewijzigd overnemen." Dit ontbrak volledig in de oude versie."""
    eind, _reden, toelichting = renteperiode(
        dagtekening=date(2025, 10, 15),
        aangifte_ontvangen=date(2025, 4, 20),
        aangifte_gevolgd=True,
        uiterste_aangiftedatum=UITERSTE_IB,
    )
    assert eind is None
    assert "geen" in toelichting.lower()


def test_op_tijd_maar_wel_afwijking_geeft_wel_rente():
    eind, _reden, _ = renteperiode(
        dagtekening=date(2024, 12, 11),
        aangifte_ontvangen=date(2024, 4, 28),
        aangifte_gevolgd=False,
        uiterste_aangiftedatum=date(2024, 5, 1),
    )
    assert eind == date(2025, 1, 22)     # 6 weken na 11-12-2024


def test_te_laat_zonder_afwijking_wordt_gemaximeerd_op_negentien_weken():
    """Voorbeeld van de site: aangifte 3 mei 2024, aanslag 4 december 2024.
    19 weken na 3 mei is 13 september 2024 — dat is de einddatum, niet
    6 weken na de aanslag."""
    eind, _reden, toelichting = renteperiode(
        dagtekening=date(2024, 12, 4),
        aangifte_ontvangen=date(2024, 5, 3),
        aangifte_gevolgd=True,
        uiterste_aangiftedatum=date(2024, 5, 1),
    )
    assert eind == date(2024, 9, 13)
    assert "gemaximeerd" in toelichting


def test_voorbeeld_1_compleet_van_aangifte_tot_bedrag():
    """De hele keten van het eerste voorbeeld: situatiebepaling én berekening."""
    eind, _reden, _ = renteperiode(
        dagtekening=date(2024, 12, 4),
        aangifte_ontvangen=date(2024, 5, 3),
        aangifte_gevolgd=True,
        uiterste_aangiftedatum=date(2024, 5, 1),
    )
    totaal, _ = bereken(1000, date(2024, 7, 1), eind, TARIEVEN)
    assert totaal == 15


def test_snelle_aanslag_valt_binnen_de_maximering():
    """"Krijgt u eerder dan binnen 19 weken na ontvangst van uw aangifte een
    belastingaanslag? Dan berekenen wij belastingrente tot 6 weken na de datum
    op de belastingaanslag." """
    eind, _reden, toelichting = renteperiode(
        dagtekening=date(2025, 6, 1),
        aangifte_ontvangen=date(2025, 5, 15),
        aangifte_gevolgd=True,
        uiterste_aangiftedatum=UITERSTE_IB,
    )
    assert eind == date(2025, 7, 13)        # 6 weken na 01-06-2025
    assert eind < date(2025, 5, 15) + __import__("datetime").timedelta(weeks=19)


def test_vpb_hanteert_een_maand_later_als_uiterste_datum():
    """Bij VpB is de grens 1 juni in plaats van 1 mei."""
    op_tijd_vpb, _r, _ = renteperiode(date(2025, 10, 1), date(2025, 5, 20), True, UITERSTE_VPB)
    te_laat_ib, _r2, _ = renteperiode(date(2025, 10, 1), date(2025, 5, 20), True, UITERSTE_IB)
    assert op_tijd_vpb is None          # 20 mei is vóór 1 juni -> geen rente
    assert te_laat_ib is not None       # 20 mei is ná 1 mei    -> wel rente


def test_onbekende_aangiftedatum_valt_terug_op_de_bovengrens():
    eind, _reden, toelichting = renteperiode(date(2025, 10, 15), None, True, UITERSTE_IB)
    assert eind == date(2025, 11, 26)
    assert "bovengrens" in toelichting


# ── Opmaak ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("percentage,verwacht", [
    (5.0, "5%"), (6.5, "6,5%"), (7.5, "7,5%"),
    (0.01, "0,01%"), (8.05, "8,05%"), (2.30, "2,3%"),
])
def test_percentage_opmaak(percentage, verwacht):
    assert nl_pct(percentage) == verwacht


def test_hele_euros_in_nederlandse_notatie():
    assert nl_euro_heel(1295) == "€ 1.295"
    assert nl_euro_heel(0) == "€ 0"


# ── Startdatum bij (gebroken) boekjaar ──────────────────────────────────────

@pytest.mark.parametrize("boekjaar_eind,verwacht", [
    (date(2024, 12, 31), date(2025, 7, 1)),    # regulier boekjaar
    (date(2025, 3, 31),  date(2025, 10, 1)),   # voorbeeld uit de specificatie
    (date(2025, 6, 30),  date(2026, 1, 1)),    # zie test hieronder
    (date(2025, 2, 28),  date(2025, 9, 1)),
    (date(2025, 1, 31),  date(2025, 8, 1)),
])
def test_rente_start_in_de_zevende_maand_na_het_boekjaar(boekjaar_eind, verwacht):
    assert eerste_dag_van_maand_na(boekjaar_eind, 7) == verwacht


def test_boekjaar_dat_eindigt_op_een_korte_maand():
    """De oude opzet (einddatum + 6 maanden + 1 dag) kwam hier een dag te vroeg
    uit: 30 juni werd afgebeeld op 30 december, dus 31-12 in plaats van 01-01."""
    from _rente import _tel_maanden_op
    from datetime import timedelta
    oud = _tel_maanden_op(date(2025, 6, 30), 6) + timedelta(days=1)
    nieuw = eerste_dag_van_maand_na(date(2025, 6, 30), 7)
    assert oud == date(2025, 12, 31)      # fout
    assert nieuw == date(2026, 1, 1)      # goed


def test_vrijstellingsgrens_ligt_een_maand_voor_de_startdatum():
    """De specificatie: waar 1 juni staat, lees de 6e maand na het boekjaar."""
    assert eerste_dag_van_maand_na(date(2024, 12, 31), 6) == date(2025, 6, 1)
    assert eerste_dag_van_maand_na(date(2025, 3, 31), 6) == date(2025, 9, 1)


def test_grens_voorlopige_aanslag_ligt_in_de_vijfde_maand():
    """En waar 1 mei staat, de 5e maand."""
    assert eerste_dag_van_maand_na(date(2024, 12, 31), 5) == date(2025, 5, 1)
    assert eerste_dag_van_maand_na(date(2025, 3, 31), 5) == date(2025, 8, 1)


# ── Navorderingsaanslag ─────────────────────────────────────────────────────

def test_navordering_loopt_tot_een_maand_na_de_dagtekening():
    eind, reden, _ = renteperiode(
        dagtekening=date(2025, 9, 10), aanslag_type="navordering",
    )
    assert eind == date(2025, 10, 10)
    assert reden == "navordering"


def test_navordering_negeert_de_zes_wekenregel():
    """Één maand, niet zes weken — dat scheelt bijna twee weken rente."""
    navordering, _, _ = renteperiode(date(2025, 9, 10), aanslag_type="navordering")
    regulier, _, _ = renteperiode(date(2025, 9, 10), aangifte_gevolgd=False)
    assert navordering == date(2025, 10, 10)
    assert regulier == date(2025, 10, 22)
    assert navordering < regulier


def test_navordering_op_verzoek_wordt_gemaximeerd_op_twaalf_weken():
    eind, reden, toelichting = renteperiode(
        dagtekening=date(2025, 12, 1),
        aanslag_type="navordering",
        verzoek_datum=date(2025, 8, 1),
    )
    assert eind == date(2025, 10, 24)      # 12 weken na 01-08-2025
    assert reden == "navordering-op-verzoek"
    assert "12 weken" in toelichting


def test_navordering_op_verzoek_zonder_effect_als_de_aanslag_snel_volgt():
    """Ligt 12 weken na het verzoek ná één maand na de dagtekening, dan blijft
    de gewone navorderingsregel gelden."""
    eind, reden, _ = renteperiode(
        dagtekening=date(2025, 8, 5),
        aanslag_type="navordering",
        verzoek_datum=date(2025, 8, 1),
    )
    assert eind == date(2025, 9, 5)
    assert reden == "navordering"


def test_navordering_maandtelling_over_een_jaargrens():
    eind, _, _ = renteperiode(date(2025, 12, 20), aanslag_type="navordering")
    assert eind == date(2026, 1, 20)


def test_navordering_op_het_einde_van_een_lange_maand():
    """31 januari + 1 maand bestaat niet; dat wordt 28 februari."""
    eind, _, _ = renteperiode(date(2025, 1, 31), aanslag_type="navordering")
    assert eind == date(2025, 2, 28)


# ── VpB: voorlopige aanslag conform verzoek ─────────────────────────────────

def test_tijdig_verzochte_voorlopige_aanslag_geeft_geen_rente():
    eind, reden, _ = renteperiode(
        dagtekening=date(2025, 10, 1),
        aangifte_ontvangen=date(2025, 8, 1),
        aangifte_gevolgd=False,
        uiterste_aangiftedatum=UITERSTE_VPB,
        voorlopige_aanslag_conform=True,
    )
    assert eind is None
    assert reden == "vrijstelling-voorlopig"


# ── Reden van de einddatum (par. 13 van de specificatie) ────────────────────

def test_elke_situatie_geeft_een_herkenbare_reden():
    gevallen = {
        "vrijstelling": dict(dagtekening=date(2025, 10, 1),
                             aangifte_ontvangen=date(2025, 4, 20),
                             aangifte_gevolgd=True, uiterste_aangiftedatum=UITERSTE_IB),
        "19-wekenregel": dict(dagtekening=date(2024, 12, 4),
                              aangifte_ontvangen=date(2024, 5, 3),
                              aangifte_gevolgd=True,
                              uiterste_aangiftedatum=date(2024, 5, 1)),
        "6-wekenregel": dict(dagtekening=date(2025, 10, 1),
                             aangifte_ontvangen=date(2025, 6, 1),
                             aangifte_gevolgd=False, uiterste_aangiftedatum=UITERSTE_IB),
        "bovengrens": dict(dagtekening=date(2025, 10, 1), aangifte_ontvangen=None,
                           aangifte_gevolgd=True, uiterste_aangiftedatum=UITERSTE_IB),
        "navordering": dict(dagtekening=date(2025, 10, 1), aanslag_type="navordering"),
    }
    for verwachte_reden, argumenten in gevallen.items():
        _, reden, _ = renteperiode(**argumenten)
        assert reden == verwachte_reden, argumenten


# ── Navordering bij een gebroken boekjaar ───────────────────────────────────

def test_navordering_bij_een_gebroken_boekjaar():
    """De README noemde deze combinatie als niet apart getoetst. De startdatum
    volgt uit het boekjaar en de einddatum uit het aanslagtype; die twee staan los
    van elkaar, dus de combinatie hoort te werken. Hier vastgelegd.

    Boekjaar t/m 30-06-2024, navorderingsaanslag met dagtekening 10-09-2025.
    Start: de 7e maand na het boekjaar, dus 01-01-2025. Eind: 1 maand na de
    dagtekening, dus 10-10-2025.
    """
    boekjaar_eind = date(2024, 6, 30)
    start = eerste_dag_van_maand_na(boekjaar_eind, STARTMAAND_RENTE)
    assert start == date(2025, 1, 1)

    eind, reden, _ = renteperiode(date(2025, 9, 10), aanslag_type="navordering")
    assert eind == date(2025, 10, 10)
    assert reden == "navordering"

    bedrag, regels = bereken(100_000, start, eind, TARIEVEN)
    assert bedrag > 0
    assert regels[0]["start"] == start
    assert regels[-1]["eind"] == eind


@pytest.mark.parametrize("boekjaar_eind,verwachte_start", [
    (date(2024, 12, 31), date(2025, 7, 1)),
    (date(2024, 6, 30), date(2025, 1, 1)),
    (date(2024, 2, 29), date(2024, 9, 1)),
    (date(2024, 9, 15), date(2025, 4, 1)),
])
def test_navordering_startdatum_volgt_het_boekjaar(boekjaar_eind, verwachte_start):
    """Bij navordering blijft de startdatum die van het boekjaar; alleen de
    einddatum wijkt af. Ook voor een boekjaar dat midden in een maand eindigt."""
    assert eerste_dag_van_maand_na(boekjaar_eind, STARTMAAND_RENTE) == verwachte_start
    eind, reden, _ = renteperiode(date(2026, 1, 20), aanslag_type="navordering")
    assert reden == "navordering" and eind == date(2026, 2, 20)
