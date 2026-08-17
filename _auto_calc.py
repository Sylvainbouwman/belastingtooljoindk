"""Rekenlogica voor BTW-correctie privégebruik en bijtelling zakelijke auto.

Bewust vrij van Streamlit-afhankelijkheden, zodat deze functies los testbaar
zijn (zie tests/test_auto_calc.py).
"""

import calendar
from datetime import date, timedelta

# ── Bijtellingspercentages ──────────────────────────────────────────────────

# Standaardpercentage (niet-nulemissie), naar bouwjaarregime.
STANDAARD_BIJTELLING = {jaar: 25.0 for jaar in range(2012, 2017)}
STANDAARD_BIJTELLING.update({jaar: 22.0 for jaar in range(2017, 2032)})

# Korting voor nulemissievoertuigen: {regimejaar: (percentage, plafond of None)}.
# Boven het plafond geldt het standaardpercentage van datzelfde regimejaar.
#
# LET OP - NOG TE VERIFIEREN TEGEN BELASTINGDIENST.NL
# Deze reeks is op 17-08-2026 gecorrigeerd omdat de oude tabel (2017: 7%,
# 2018/2019: 16%, 2020: 12%) niet strookte met de bekende opbouw 4/8/12/16.
# De officiele overzichtspagina gaf op dat moment een 404, dus de waarden zijn
# niet bij de bron nagelopen. Controleer ze voordat je hier klanten mee bedient;
# vanaf 2026 vervalt de korting en geldt het standaardpercentage.
KORTING_NULEMISSIE = {
    2017: (4.0, None),
    2018: (4.0, None),
    2019: (4.0, 50_000),
    2020: (8.0, 45_000),
    2021: (12.0, 40_000),
    2022: (16.0, 35_000),
    2023: (16.0, 30_000),
    2024: (16.0, 30_000),
    2025: (16.0, 30_000),
}

NULEMISSIE_BRANDSTOFFEN = ("elektriciteit", "waterstof")

# Het bijtellingspercentage ligt vanaf de eerste tenaamstelling 60 maanden vast.
VASTE_TERMIJN_MAANDEN = 60

# Vanaf het vijfde jaar na ingebruikname geldt het lage BTW-forfait.
BTW_FORFAIT_HOOG = 0.027
BTW_FORFAIT_LAAG = 0.015
BTW_LAGE_FORFAIT_NA_JAREN = 4


# ── Hulpfuncties ────────────────────────────────────────────────────────────

def tel_maanden_op(d: date, maanden: int) -> date:
    maand = d.month + maanden
    jaar = d.year + (maand - 1) // 12
    maand = (maand - 1) % 12 + 1
    return date(jaar, maand, min(d.day, calendar.monthrange(jaar, maand)[1]))


def is_nulemissie(co2: int | None, brandstof: str | None) -> bool:
    if co2 == 0:
        return True
    return (brandstof or "").lower() in NULEMISSIE_BRANDSTOFFEN


def vervaldatum_vaste_termijn(eerste_toelating: date | None) -> date | None:
    """Einde van de 60-maandstermijn: de eerste dag van de maand ná de eerste
    toelating, plus 60 maanden. Vanaf die datum geldt het dan geldende regime."""
    if eerste_toelating is None:
        return None
    eerste_van_volgende_maand = tel_maanden_op(eerste_toelating.replace(day=1), 1)
    return tel_maanden_op(eerste_van_volgende_maand, VASTE_TERMIJN_MAANDEN)


# ── BTW-correctie privégebruik ──────────────────────────────────────────────

def btw_forfait(marge: bool, ingebruikname: date | None, jaar: int) -> tuple[float, str]:
    """Geeft (forfait, toelichting).

    1,5% geldt bij een marge-auto én zodra het jaar van ingebruikname plus de
    vier daaropvolgende jaren voorbij zijn. Anders 2,7%.
    """
    if marge:
        return BTW_FORFAIT_LAAG, "1,5% (marge-auto)"
    if ingebruikname is not None and jaar > ingebruikname.year + BTW_LAGE_FORFAIT_NA_JAREN:
        return BTW_FORFAIT_LAAG, f"1,5% (in gebruik sinds {ingebruikname.year}, 5e jaar of later)"
    return BTW_FORFAIT_HOOG, "2,7%"


def btw_correctie(catalogusprijs: float, marge: bool, dagen: int,
                  ingebruikname: date | None = None,
                  jaar: int | None = None) -> tuple[float, str]:
    forfait, toelichting = btw_forfait(marge, ingebruikname, jaar or date.today().year)
    return catalogusprijs * forfait * jaarfractie(dagen), toelichting


# ── Bijtelling ──────────────────────────────────────────────────────────────

def jaarfractie(dagen: int) -> float:
    """Deel van een jaar. Nooit meer dan 1: in een schrikkeljaar levert een vol
    jaar 366 dagen op, en 366/365 zou 100,27% van het forfait opleveren."""
    return min(dagen, 365) / 365


def regime_jaar(eerste_toelating: date | None, berekeningsjaar: int, op: date | None = None) -> int:
    """Welk bouwjaarregime geldt op een gegeven moment.

    Binnen de 60-maandstermijn is dat het jaar van eerste toelating; daarna het
    lopende berekeningsjaar.
    """
    if eerste_toelating is None:
        return berekeningsjaar
    vervaldatum = vervaldatum_vaste_termijn(eerste_toelating)
    peil = op or date(berekeningsjaar, 1, 1)
    return eerste_toelating.year if peil < vervaldatum else berekeningsjaar


def bijtelling_regime(catalogusprijs: float, nulemissie: bool, jaar: int) -> tuple[float, str]:
    """Bijtellingsgrondslag per vol jaar plus een leesbaar label."""
    standaard = STANDAARD_BIJTELLING.get(jaar, 22.0)
    if not nulemissie or jaar not in KORTING_NULEMISSIE:
        return catalogusprijs * (standaard / 100), f"{standaard:.0f}%"

    pct, plafond = KORTING_NULEMISSIE[jaar]
    if plafond is None:
        return catalogusprijs * (pct / 100), f"{pct:.0f}% (0-emissie)"
    if catalogusprijs <= plafond:
        return catalogusprijs * (pct / 100), f"{pct:.0f}% (0-emissie, ≤ € {plafond:,})"
    grondslag = plafond * (pct / 100) + (catalogusprijs - plafond) * (standaard / 100)
    return grondslag, f"{pct:.0f}% t/m € {plafond:,} + {standaard:.0f}% daarboven"


def bijtelling(catalogusprijs: float, co2: int | None, brandstof: str | None,
               berekeningsjaar: int, van: date, tot: date,
               eerste_toelating: date | None = None) -> tuple[float, str]:
    """Bijtelling over de periode [van, tot] (beide inclusief).

    Het percentage ligt 60 maanden vast vanaf de eerste toelating. Valt die
    vervaldatum midden in de periode, dan wordt de periode gesplitst en krijgt
    elk deel zijn eigen regime.
    """
    nulemissie = is_nulemissie(co2, brandstof)
    vervaldatum = vervaldatum_vaste_termijn(eerste_toelating)

    if vervaldatum is None or not (van < vervaldatum <= tot):
        jaar = regime_jaar(eerste_toelating, berekeningsjaar, van)
        grondslag, label = bijtelling_regime(catalogusprijs, nulemissie, jaar)
        return grondslag * jaarfractie((tot - van).days + 1), label

    delen = [(van, vervaldatum - timedelta(days=1), eerste_toelating.year),
             (vervaldatum, tot, berekeningsjaar)]
    totaal_dagen = sum((eind - start).days + 1 for start, eind, _ in delen)
    # Voorkom dat een schrikkeljaar door de splitsing alsnog boven 1,0 uitkomt.
    schaal = min(1.0, 365 / totaal_dagen) if totaal_dagen else 1.0

    bedrag, labels = 0.0, []
    for start, eind, jaar in delen:
        grondslag, label = bijtelling_regime(catalogusprijs, nulemissie, jaar)
        dagen = (eind - start).days + 1
        bedrag += grondslag * (dagen / 365) * schaal
        labels.append(label)

    if labels[0] == labels[1]:
        # Regimewissel zonder gevolg voor het percentage: niet tonen.
        return bedrag, labels[0]
    laatste_dag = (vervaldatum - timedelta(days=1)).strftime("%d-%m-%Y")
    return bedrag, f"{labels[0]} t/m {laatste_dag} → daarna {labels[1]}"
