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

Wettelijke grondslag, nagelezen op 29-09-2026 bij de gelijkwaardigheidstoets
tegen model 02-04 (zie OPENSTAAND.md punt 12 en de vrijgavenotitie van die dag):

  * Tijdvak: art. 30fc lid 2 AWR (BWBR0002320, versie 01-01-2026) laat het
    aanvangen 6 maanden na het einde van het tijdvak waarover de belasting wordt
    geheven en eindigen "op de dag voorafgaand aan de dag waarop de aanslag ...
    invorderbaar is ingevolge artikel 9 van de Invorderingswet 1990". De aanslag
    is invorderbaar de dag na de vervaldag (zie `_invorderingsrente.invorderbaar_op`),
    dus de rente loopt tot en met de vervaldag: dagtekening + 6 weken, of + 1 maand
    bij navordering. Lid 3 en lid 5 geven de maxima van 19 en 12 weken.
  * Dagentelling: art. 31 lid 1 Uitvoeringsregeling AWR 1994 (BWBR0006736). Een
    volle maand telt 30 dagen, behalve de maand op de laatste dag waarvan het
    tijdvak eindigt; zie `dagen_belastingrente()`.
  * Afronding: art. 31 lid 2 van die regeling rondt "het bedrag van de in rekening
    te brengen belastingrente" naar beneden af. Model 02-04 doet dat één keer over
    het totaal. Deze module rondt per tariefperiode af, zoals het gepubliceerde
    voorbeeld van de Belastingdienst (regel 2 hierboven). Besluit van Sylvain op
    29-09-2026: dat blijft zo. Het verschil is hooguit 1 euro per extra
    tariefperiode, en de tool komt dan lager uit.
"""

import math
from datetime import date, timedelta

from _format import nl_date, nl_euro, nl_euro_heel, nl_pct

# Weken na de datum op de aanslag waarover nog rente loopt.
AANSLAG_WEKEN = 6

# Maximering: is de aangifte op tijd binnen en wijkt de aanslag er niet van af,
# dan loopt de rente hoogstens tot dit aantal weken na ontvangst van de aangifte.
MAXIMERING_WEKEN = 19

# Bij een navorderingsaanslag loopt de rente tot één maand na de dagtekening.
NAVORDERING_MAANDEN = 1

# Is de navordering op verzoek van de belastingplichtige, dan geldt daarnaast een
# wettelijk maximum van 12 weken na ontvangst van dat verzoek.
NAVORDERING_VERZOEK_WEKEN = 12

# De maand (geteld vanaf de maand ná het boekjaar) waarin de rente begint.
# Voor een boekjaar t/m 31 december is dat juli, oftewel de 7e maand.
STARTMAAND_RENTE = 7

# De maand waarin de vrijstellingsgrens ligt: 1 juni bij VpB, dus de 6e maand.
GRENSMAAND_VRIJSTELLING = 6

# Voor het VpB-verzoek om een voorlopige aanslag: 1 mei, dus de 5e maand.
GRENSMAAND_VOORLOPIGE_AANSLAG = 5


def eerste_dag_van_maand_na(boekjaar_eind: date, maanden: int) -> date:
    """Eerste dag van de n-de maand ná de maand waarin het boekjaar eindigt.

    De Belastingdienst formuleert de VpB-termijnen in hele maanden ("vanaf de
    7e maand na het boekjaar"), niet in dagen. Dat is hier bewust letterlijk
    overgenomen. Rekenen met 'einddatum + 6 maanden + 1 dag' gaat namelijk mis
    zodra het boekjaar op de laatste dag van een korte maand eindigt: bij een
    boekjaar t/m 30-06-2025 levert dat 31-12-2025 op in plaats van 01-01-2026,
    omdat 30 juni naar 30 december wordt afgebeeld. Het lost bovendien het
    randgeval op van een boekjaar dat midden in een maand eindigt.
    """
    maand = boekjaar_eind.month + maanden
    jaar = boekjaar_eind.year + (maand - 1) // 12
    maand = (maand - 1) % 12 + 1
    return date(jaar, maand, 1)


def _tel_maanden_op(d: date, maanden: int) -> date:
    """Zelfde dag, zoveel maanden later, volgens onderdeel 9.5 Leidraad Invordering 2008.

    Valt 'd' op de laatste dag van een maand, dan is de uitkomst de laatste dag
    van de doelmaand: dagtekening 28 februari geeft een termijn van een maand die
    op 31 maart vervalt (28 maart in een schrikkeljaar, want dan is 28 februari
    niet de laatste dag), en 31 oktober geeft 30 november. Anders dezelfde
    dag, gekapt op de lengte van de doelmaand. Tot 29-09-2026 werd alleen
    gekapt, waardoor 28-02-2025 op 28-03-2025 uitkwam; gevonden door de
    bron-controleur bij de gelijkwaardigheidstoets tegen model 02-04.
    """
    import calendar
    maand = d.month + maanden
    jaar = d.year + (maand - 1) // 12
    maand = (maand - 1) % 12 + 1
    lengte = calendar.monthrange(jaar, maand)[1]
    if d.day == calendar.monthrange(d.year, d.month)[1]:
        return date(jaar, maand, lengte)
    return date(jaar, maand, min(d.day, lengte))


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


def dagen_belastingrente(vanaf: date, tot_en_met: date, einde_tijdvak: bool) -> int:
    """Aantal dagen volgens art. 31 lid 1 Uitvoeringsregeling AWR 1994.

    "Bij de bepaling van het aantal dagen waarover ingevolge hoofdstuk VA van de
    wet belastingrente wordt berekend, wordt een volle kalendermaand gesteld op
    30 dagen, met uitzondering van de maand op de laatste dag waarvan het
    tijdvak waarover de rente wordt berekend eindigt, in welk geval het
    werkelijke aantal dagen in aanmerking wordt genomen." (BWBR0006736, versie
    01-01-2026, geraadpleegd 29-09-2026.)

    Dat wijkt op twee plekken af van `dagen_30_360()`, die deze module tot
    29-09-2026 gebruikte en die model 02-04 ook zo telt:

      * Een deelperiode die bij een tariefwissel stopt, is niet het einde van het
        tijdvak. Eindigt zij op de laatste dag van een maand, dan is dat een
        volle maand van 30 dagen, ook in februari. `dagen_30_360()` telde
        februari daar als 28; bij de VpB-wissel van 1 maart 2015 kostte dat
        twee dagen.
      * Eindigt het tijdvak zelf op de laatste dag van een maand, dan telt die
        maand haar werkelijke aantal dagen: 31 in januari, 28 of 29 in februari.
        `dagen_30_360()` kapte dag 31 op 30.

    'einde_tijdvak' zegt of 'tot_en_met' het einde van het hele rentetijdvak is,
    en niet alleen van een deelperiode. Een onvolledige laatste maand telt de
    dagen die erin vallen; dat volgt uit de dagnummers.
    """
    import calendar
    if einde_tijdvak and (vanaf.year, vanaf.month) == (tot_en_met.year, tot_en_met.month):
        # Begin en einde in de laatste maand: die telt haar werkelijke dagen.
        return tot_en_met.day - vanaf.day + 1
    dag_vanaf = min(vanaf.day, 30)
    lengte = calendar.monthrange(tot_en_met.year, tot_en_met.month)[1]
    if tot_en_met.day == lengte:
        dag_tot = lengte if einde_tijdvak else 30
    else:
        dag_tot = tot_en_met.day
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
        dagen = dagen_belastingrente(start, laatste, einde_tijdvak=(laatste == tot_en_met))
        percentage = tarief_op(start, tarieven)
        rente = math.floor(bedrag * (percentage / 100) * dagen / 360)
        totaal += rente
        deelperioden.append({
            "start": start, "eind": laatste, "dagen": dagen,
            "pct": percentage, "rente": rente,
        })

    return totaal, deelperioden


def renteperiode(dagtekening: date,
                 aangifte_ontvangen: date | None = None,
                 aangifte_gevolgd: bool = True,
                 uiterste_aangiftedatum: date | None = None,
                 aanslag_type: str = "regulier",
                 verzoek_datum: date | None = None,
                 voorlopige_aanslag_conform: bool = False) -> tuple[date | None, str, str]:
    """Bepaalt de einddatum van de renteperiode.

    Geeft (einddatum_inclusief, reden, toelichting) terug. einddatum is None als
    er geen belastingrente verschuldigd is. 'reden' is een korte code die op de
    pagina wordt getoond, zodat een fiscalist kan zien welke regel is toegepast.

    De situaties:

      vrijstelling            aangifte op tijd én ongewijzigd gevolgd
      vrijstelling-voorlopig  VpB: tijdig om een voorlopige aanslag verzocht en
                              die is conform opgelegd
      19-wekenregel           te laat maar ongewijzigd gevolgd, en 19 weken na
                              de aangifte ligt vóór 6 weken na de aanslag
      6-wekenregel            afgeweken van de aangifte, of de aanslag kwam
                              binnen de 19 weken
      navordering             tot 1 maand na de dagtekening
      navordering-op-verzoek  idem, maar gemaximeerd op 12 weken na het verzoek
      bovengrens              aangiftedatum onbekend; uitkomst is een maximum

    Bij een navorderingsaanslag zijn de aangiftevragen niet van toepassing: die
    aanslag volgt per definitie niet de oorspronkelijke aangifte. De volgorde
    wijkt daarmee bewust af van de pseudocode in de specificatie, die de
    vrijstelling vóór de navorderingscheck plaatst.
    """
    if aanslag_type == "navordering":
        normaal = _tel_maanden_op(dagtekening, NAVORDERING_MAANDEN)
        if verzoek_datum is not None:
            maximum = verzoek_datum + timedelta(weeks=NAVORDERING_VERZOEK_WEKEN)
            if maximum < normaal:
                return maximum, "navordering-op-verzoek", (
                    f"Navordering op uw eigen verzoek. De rente is wettelijk "
                    f"gemaximeerd op {NAVORDERING_VERZOEK_WEKEN} weken na ontvangst "
                    f"van het verzoek ({nl_date(maximum)}), in plaats van "
                    f"{NAVORDERING_MAANDEN} maand na de dagtekening ({nl_date(normaal)})."
                )
        return normaal, "navordering", (
            f"Navorderingsaanslag: de rente loopt tot en met "
            f"{NAVORDERING_MAANDEN} maand na de dagtekening ({nl_date(normaal)})."
        )

    if voorlopige_aanslag_conform:
        return None, "vrijstelling-voorlopig", (
            "Er is tijdig om een voorlopige aanslag verzocht en die is "
            "overeenkomstig het verzoek opgelegd. In dat geval brengt de "
            "Belastingdienst geen belastingrente in rekening."
        )

    na_aanslag = dagtekening + timedelta(weeks=AANSLAG_WEKEN)

    if not aangifte_gevolgd:
        return na_aanslag, "6-wekenregel", (
            f"Er is afgeweken van de aangifte, dus de maximering van "
            f"{MAXIMERING_WEKEN} weken geldt niet. De rente loopt tot en met "
            f"{AANSLAG_WEKEN} weken na de dagtekening ({nl_date(na_aanslag)})."
        )

    if aangifte_ontvangen is None:
        return na_aanslag, "bovengrens", (
            f"Datum van de aangifte onbekend — gerekend tot en met "
            f"{AANSLAG_WEKEN} weken na de dagtekening ({nl_date(na_aanslag)}). "
            f"Dit is een bovengrens: met een aangiftedatum kan de uitkomst lager "
            f"uitvallen of zelfs nihil zijn."
        )

    if uiterste_aangiftedatum is not None and aangifte_ontvangen < uiterste_aangiftedatum:
        return None, "vrijstelling", (
            f"De aangifte is op tijd binnengekomen (vóór "
            f"{nl_date(uiterste_aangiftedatum)}) en is ongewijzigd gevolgd. "
            f"In dat geval brengt de Belastingdienst geen belastingrente in rekening."
        )

    maximering = aangifte_ontvangen + timedelta(weeks=MAXIMERING_WEKEN)
    if maximering < na_aanslag:
        return maximering, "19-wekenregel", (
            f"De aangifte is na de uiterste datum binnengekomen, maar is wel "
            f"ongewijzigd gevolgd. De rente is daarom gemaximeerd op "
            f"{MAXIMERING_WEKEN} weken na ontvangst van de aangifte "
            f"({nl_date(maximering)}), in plaats van {AANSLAG_WEKEN} weken na de "
            f"dagtekening ({nl_date(na_aanslag)})."
        )

    return na_aanslag, "6-wekenregel", (
        f"De aanslag kwam binnen {MAXIMERING_WEKEN} weken na de aangifte, dus de "
        f"rente loopt tot en met {AANSLAG_WEKEN} weken na de dagtekening "
        f"({nl_date(na_aanslag)})."
    )


# ── Opmaak ──────────────────────────────────────────────────────────────────

# De notatiefuncties staan in _format.py, omdat ook de autopagina ze gebruikt.
# Hier blijven ze beschikbaar zodat "from _rente import nl_euro" blijft werken.
__all__ = [name for name in dir() if not name.startswith("_")] + [
    "nl_euro", "nl_euro_heel", "nl_date", "nl_pct",
]
