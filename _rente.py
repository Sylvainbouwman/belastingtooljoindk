"""Berekening van belastingrente volgens de methode van de Belastingdienst.

Bewust vrij van Streamlit-afhankelijkheden (zie tests/test_rente.py, waarin de
gepubliceerde rekenvoorbeelden van de Belastingdienst zijn nagebouwd).

Bron: belastingdienst.nl, "Belastingrente betalen bij inkomstenbelasting" en
"Belastingrente betalen bij vennootschapsbelasting", geraadpleegd 17-08-2026.

De drie regels die de uitkomst bepalen:

  1. "Voor de berekening van de belastingrente rekenen wij met 30 dagen per maand
     en 360 dagen per jaar."
  2. "Bij het betalen van belastingrente ronden we de uitkomst van de berekening
     af naar beneden op hele euro's." Dat gebeurt per tariefperiode, niet over
     het totaal — zichtbaar in hun eigen voorbeeld: 93 + 9 = 102, terwijl
     93,75 + 9,93 = 103,68 zou afronden naar 103.
  3. De renteperiode loopt tot EN MET de einddatum.
"""

import math
from datetime import date, timedelta

# Weken na de datum op de aanslag waarover nog rente loopt.
AANSLAG_WEKEN = 6

# Maximering: is de aangifte op tijd binnen en wijkt de aanslag er niet van af,
# dan loopt de rente hoogstens tot dit aantal weken na ontvangst van de aangifte.
MAXIMERING_WEKEN = 19


def dagen_30_360(vanaf: date, tot_en_met: date) -> int:
    """Aantal dagen van 'vanaf' tot en met 'tot_en_met', 30 dagen per maand.

    Een dag 31 telt als dag 30 — anders komt de laatste maand van het jaar op
    31 dagen uit en klopt het voorbeeld van de Belastingdienst niet meer
    (1 juli t/m 31 december moet 180 zijn, niet 181).
    """
    dag_vanaf = min(vanaf.day, 30)
    dag_tot = min(tot_en_met.day, 30)
    return (360 * (tot_en_met.year - vanaf.year)
            + 30 * (tot_en_met.month - vanaf.month)
            + (dag_tot - dag_vanaf + 1))


def tarief_op(dag: date, tarieven: list) -> float:
    """Percentage dat op deze dag geldt. 'tarieven' is nieuw → oud gesorteerd."""
    for ingang, percentage in tarieven:
        if dag >= ingang:
            return percentage
    return tarieven[-1][1]


def bereken(bedrag: float, vanaf: date, tot_en_met: date, tarieven: list):
    """Belastingrente over [vanaf, tot_en_met], beide inclusief.

    Geeft (totaal, deelperioden) terug. De periode wordt geknipt op elke
    tariefwijziging; per deelperiode wordt naar beneden afgerond op hele euro's.
    """
    if tot_en_met < vanaf:
        return 0, []

    knippunten = sorted({vanaf} | {d for d, _ in tarieven if vanaf < d <= tot_en_met})
    deelperioden, totaal = [], 0

    for i, start in enumerate(knippunten):
        laatste = (knippunten[i + 1] - timedelta(days=1)
                   if i + 1 < len(knippunten) else tot_en_met)
        dagen = dagen_30_360(start, laatste)
        percentage = tarief_op(start, tarieven)
        rente = math.floor(bedrag * (percentage / 100) * dagen / 360)
        totaal += rente
        deelperioden.append({
            "start": start, "eind": laatste, "dagen": dagen,
            "pct": percentage, "rente": rente,
        })

    return totaal, deelperioden


def renteperiode(dagtekening: date,
                 aangifte_ontvangen: date | None,
                 afgeweken: bool,
                 uiterste_aangiftedatum: date) -> tuple[date | None, str]:
    """Bepaalt de einddatum van de renteperiode, of None als er geen rente is.

    Geeft (einddatum_inclusief, toelichting) terug. De drie situaties van de
    Belastingdienst:

      - aangifte op tijd én geen afwijking      -> geen belastingrente
      - aangifte te laat én geen afwijking      -> tot 6 weken na de aanslag,
                                                   maar hoogstens 19 weken na
                                                   ontvangst van de aangifte
      - afwijking van de aangifte               -> tot 6 weken na de aanslag
    """
    na_aanslag = dagtekening + timedelta(weeks=AANSLAG_WEKEN)

    if afgeweken:
        return na_aanslag, (
            f"Er is afgeweken van de aangifte, dus de rente loopt tot en met "
            f"{AANSLAG_WEKEN} weken na de dagtekening."
        )

    if aangifte_ontvangen is None:
        return na_aanslag, (
            "Datum van de aangifte onbekend — gerekend tot en met "
            f"{AANSLAG_WEKEN} weken na de dagtekening. Dit is een bovengrens."
        )

    if aangifte_ontvangen < uiterste_aangiftedatum:
        return None, (
            f"De aangifte is op tijd binnengekomen (vóór "
            f"{uiterste_aangiftedatum.strftime('%d-%m-%Y')}) en er is niet van "
            f"afgeweken. In dat geval brengt de Belastingdienst geen "
            f"belastingrente in rekening."
        )

    maximering = aangifte_ontvangen + timedelta(weeks=MAXIMERING_WEKEN)
    if maximering < na_aanslag:
        return maximering, (
            f"De aangifte is na de uiterste datum binnengekomen, maar er is niet "
            f"van afgeweken. De rente is daarom gemaximeerd op "
            f"{MAXIMERING_WEKEN} weken na ontvangst van de aangifte "
            f"({maximering.strftime('%d-%m-%Y')}), in plaats van "
            f"{AANSLAG_WEKEN} weken na de dagtekening "
            f"({na_aanslag.strftime('%d-%m-%Y')})."
        )

    return na_aanslag, (
        f"De aanslag kwam binnen {MAXIMERING_WEKEN} weken na de aangifte, dus de "
        f"rente loopt tot en met {AANSLAG_WEKEN} weken na de dagtekening."
    )


# ── Opmaak ──────────────────────────────────────────────────────────────────

def nl_euro(bedrag: float) -> str:
    tekst = f"{bedrag:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {tekst}"


def nl_euro_heel(bedrag: int) -> str:
    return "€ " + f"{bedrag:,}".replace(",", ".")


def nl_date(dag: date) -> str:
    return dag.strftime("%d-%m-%Y")


def nl_pct(percentage: float) -> str:
    """Percentage in Nederlandse notatie, zonder betekenisverlies.

    "%.0f" maakte van 6,5% een "6%", van 7,5% een "8%" (bankiersafronding) en
    van 0,01% een "0%".
    """
    tekst = f"{percentage:.2f}".rstrip("0").rstrip(".")
    return tekst.replace(".", ",") + "%"
