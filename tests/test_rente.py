"""Tests voor de belastingrenteberekening.

De eerste groep tests is het belangrijkst: die reproduceert de rekenvoorbeelden
die de Belastingdienst zelf op zijn site publiceert. Zolang die groen zijn, klopt
de rekenmethode aantoonbaar met de bron.
"""

from datetime import date

import pytest

from _rente import (
    bereken,
    dagen_30_360,
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
    eind, toelichting = renteperiode(
        dagtekening=date(2025, 10, 15),
        aangifte_ontvangen=date(2025, 4, 20),
        afgeweken=False,
        uiterste_aangiftedatum=UITERSTE_IB,
    )
    assert eind is None
    assert "geen" in toelichting.lower()


def test_op_tijd_maar_wel_afwijking_geeft_wel_rente():
    eind, _ = renteperiode(
        dagtekening=date(2024, 12, 11),
        aangifte_ontvangen=date(2024, 4, 28),
        afgeweken=True,
        uiterste_aangiftedatum=date(2024, 5, 1),
    )
    assert eind == date(2025, 1, 22)     # 6 weken na 11-12-2024


def test_te_laat_zonder_afwijking_wordt_gemaximeerd_op_negentien_weken():
    """Voorbeeld van de site: aangifte 3 mei 2024, aanslag 4 december 2024.
    19 weken na 3 mei is 13 september 2024 — dat is de einddatum, niet
    6 weken na de aanslag."""
    eind, toelichting = renteperiode(
        dagtekening=date(2024, 12, 4),
        aangifte_ontvangen=date(2024, 5, 3),
        afgeweken=False,
        uiterste_aangiftedatum=date(2024, 5, 1),
    )
    assert eind == date(2024, 9, 13)
    assert "gemaximeerd" in toelichting


def test_voorbeeld_1_compleet_van_aangifte_tot_bedrag():
    """De hele keten van het eerste voorbeeld: situatiebepaling én berekening."""
    eind, _ = renteperiode(
        dagtekening=date(2024, 12, 4),
        aangifte_ontvangen=date(2024, 5, 3),
        afgeweken=False,
        uiterste_aangiftedatum=date(2024, 5, 1),
    )
    totaal, _ = bereken(1000, date(2024, 7, 1), eind, TARIEVEN)
    assert totaal == 15


def test_snelle_aanslag_valt_binnen_de_maximering():
    """"Krijgt u eerder dan binnen 19 weken na ontvangst van uw aangifte een
    belastingaanslag? Dan berekenen wij belastingrente tot 6 weken na de datum
    op de belastingaanslag." """
    eind, toelichting = renteperiode(
        dagtekening=date(2025, 6, 1),
        aangifte_ontvangen=date(2025, 5, 15),
        afgeweken=False,
        uiterste_aangiftedatum=UITERSTE_IB,
    )
    assert eind == date(2025, 7, 13)        # 6 weken na 01-06-2025
    assert eind < date(2025, 5, 15) + __import__("datetime").timedelta(weeks=19)


def test_vpb_hanteert_een_maand_later_als_uiterste_datum():
    """Bij VpB is de grens 1 juni in plaats van 1 mei."""
    op_tijd_vpb, _ = renteperiode(date(2025, 10, 1), date(2025, 5, 20), False, UITERSTE_VPB)
    te_laat_ib, _ = renteperiode(date(2025, 10, 1), date(2025, 5, 20), False, UITERSTE_IB)
    assert op_tijd_vpb is None          # 20 mei is vóór 1 juni -> geen rente
    assert te_laat_ib is not None       # 20 mei is ná 1 mei    -> wel rente


def test_onbekende_aangiftedatum_valt_terug_op_de_bovengrens():
    eind, toelichting = renteperiode(date(2025, 10, 15), None, False, UITERSTE_IB)
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
