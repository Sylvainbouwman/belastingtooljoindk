"""Rekenlogica voor BTW-correctie privégebruik en bijtelling zakelijke auto.

Bewust vrij van Streamlit-afhankelijkheden, zodat deze functies los testbaar
zijn (zie tests/test_auto_calc.py).
"""

import calendar
from datetime import date, timedelta

# ── Bijtellingspercentages ──────────────────────────────────────────────────

# Standaardpercentage (niet-nulemissie), naar bouwjaarregime. Tot en met 2016 was
# dat 25%, vanaf 2017 22% (bron: bijtelling-privegebruik-auto-2017, "In 2017 is
# het normale percentage verlaagd van 25 naar 22").
STANDAARD_BIJTELLING_TOT_2017 = 25.0
STANDAARD_BIJTELLING_VANAF_2017 = 22.0

# Korting voor nulemissievoertuigen: {regimejaar: (percentage, plafond of None)}.
# Boven het plafond geldt het standaardpercentage van datzelfde regimejaar.
#
# Op 18-08-2026 nagelopen op belastingdienst.nl. Bij de bron bevestigd:
#   2021  12% t/m EUR 40.000   (bijtelling-privegebruik-auto-2021)
#   2022  16% t/m EUR 35.000   (bijtelling-privegebruik-auto-2022)
#   2023  16% t/m EUR 30.000   (bijtelling-privegebruik-auto-2023)
#   2024  16% t/m EUR 30.000   (bijtelling-privegebruik-auto-2024)
#   2025  17% t/m EUR 30.000   (bijtelling-privegebruik-auto-2025)
#   2026  18% t/m EUR 30.000   (bijtelling-privegebruik-auto-2026)
# De jaarpagina van 2020 bevestigt het percentage van 8%, maar noemt het plafond
# niet; 2019 (4% t/m EUR 50.000) staat in de Nieuwsbrief Loonheffingen 2019.
# NOG NIET BIJ DE BRON BEVESTIGD: het plafond van 2020 en het ontbreken van een
# plafond in 2017 en 2018. Die drie gegevens spelen alleen nog bij een
# herberekening van een oud jaar: de 60-maandstermijn van elke auto met eerste
# toelating tot en met 2020 is uiterlijk in 2025 verlopen.
KORTING_NULEMISSIE = {
    2017: (4.0, None),
    2018: (4.0, None),
    2019: (4.0, 50_000),
    2020: (8.0, 45_000),
    2021: (12.0, 40_000),
    2022: (16.0, 35_000),
    2023: (16.0, 30_000),
    2024: (16.0, 30_000),
    2025: (17.0, 30_000),
    2026: (18.0, 30_000),
}

# Laatste jaar waarvoor de korting bij de bron is nagelopen. Voor een later
# regimejaar rekent de tool met het standaardpercentage; dat kan dus te hoog
# uitpakken zodra er nieuwe wetgeving is. Zie waarschuwing_regimejaar().
KORTING_GEVERIFIEERD_TOT_EN_MET = 2026

NULEMISSIE_BRANDSTOFFEN = ("elektriciteit", "waterstof")

# Voor waterstofauto's en auto's die volledig op geintegreerde zonnecellen
# rijden geldt het verlaagde percentage over de hele catalogusprijs, zonder
# plafond. Bevestigd op de jaarpagina's 2022 t/m 2026: "Het verlaagde percentage
# van .. geldt voor auto's op waterstof en voor auto's die volledig worden
# aangedreven door geintegreerde zonnecellen."
# Zonnecelauto's zijn niet uit de RDW-gegevens te herkennen (de eisen zijn een
# vermogen van minstens 1 kilowattpiek en een accu zonder lood); daarvoor staat
# een waarschuwing op de pagina zelf.
PLAFONDVRIJE_BRANDSTOFFEN = ("waterstof",)

# Het bijtellingspercentage ligt vanaf de eerste tenaamstelling 60 maanden vast.
VASTE_TERMIJN_MAANDEN = 60

# Auto's ouder dan deze leeftijd vallen onder de youngtimerregeling: 35% van de
# waarde in het economisch verkeer in plaats van een percentage van de
# catalogusprijs. De grens ging per 2026 van 15 naar 16 jaar (bron:
# bijtelling-privegebruik-auto-2026, "Met ingang van 2026 geldt dit voor auto's
# die ouder zijn dan 16 jaar").
YOUNGTIMER_PERCENTAGE = 35.0
YOUNGTIMER_LEEFTIJD_VANAF_2026 = 16
YOUNGTIMER_LEEFTIJD_TOT_2026 = 15

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


def is_plafondvrij(brandstof: str | None) -> bool:
    """Of het verlaagde percentage zonder plafond over de hele prijs geldt."""
    return (brandstof or "").lower() in PLAFONDVRIJE_BRANDSTOFFEN


def youngtimer_leeftijdsgrens(jaar: int) -> int:
    return YOUNGTIMER_LEEFTIJD_VANAF_2026 if jaar >= 2026 else YOUNGTIMER_LEEFTIJD_TOT_2026


def is_youngtimer(eerste_toelating: date | None, jaar: int) -> bool:
    """Of de youngtimerregeling geldt: 35% van de waarde in het economisch verkeer.

    De leeftijd wordt gemeten op 1 januari van het berekeningsjaar. De grens is
    "ouder dan" de leeftijdsgrens, dus een auto die precies zestien jaar oud is
    valt er nog niet onder.
    """
    if eerste_toelating is None:
        return False
    grens = tel_maanden_op(eerste_toelating, 12 * youngtimer_leeftijdsgrens(jaar))
    return grens < date(jaar, 1, 1)


def bijtelling_youngtimer(waarde_economisch_verkeer: float, dagen: int) -> tuple[float, str]:
    """Bijtelling volgens de youngtimerregeling, over de waarde in het
    economisch verkeer in plaats van de catalogusprijs."""
    grondslag = waarde_economisch_verkeer * (YOUNGTIMER_PERCENTAGE / 100)
    return grondslag * jaarfractie(dagen), f"{YOUNGTIMER_PERCENTAGE:.0f}% (youngtimer, over WEV)"


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


def maandfractie(van: date, tot: date) -> float:
    """Deel van een jaar in maanden, voor de BTW-correctie.

    De Belastingdienst rekent de correctie naar maanden en niet naar dagen. Het
    rekenvoorbeeld op de pagina "Btw en privegebruik auto van de zaak" gaat over
    een auto die op 1 september tot het bedrijf gaat horen en komt uit op
    "4/12 x 2,7% x EUR 45.000 = EUR 405". Een periode van 1 september tot en met
    31 december is 122 dagen; met dagen/365 zou daar EUR 406 uitkomen.

    Een volledige maand telt als 1/12. Een gedeeltelijke maand telt naar rato van
    de dagen binnen die maand, zodat een periode die midden in een maand begint
    niet ineens een hele maand oplevert. Een vol jaar geeft altijd exact 1,0, ook
    in een schrikkeljaar.
    """
    maanden = 0.0
    peil = van.replace(day=1)
    while peil <= tot:
        dagen_in_maand = calendar.monthrange(peil.year, peil.month)[1]
        eerste = max(van, peil)
        laatste = min(tot, date(peil.year, peil.month, dagen_in_maand))
        maanden += ((laatste - eerste).days + 1) / dagen_in_maand
        peil = tel_maanden_op(peil, 1)
    return min(maanden, 12.0) / 12


def btw_correctie(catalogusprijs: float, marge: bool, van: date, tot: date,
                  ingebruikname: date | None = None,
                  jaar: int | None = None) -> tuple[float, str]:
    """BTW-correctie privegebruik over de periode [van, tot], beide inclusief.

    De grondslag is de catalogusprijs inclusief BTW en BPM, conform de bron:
    "U stelt de btw die u moet betalen voor het privegebruik vast op 2,7% van de
    catalogusprijs van de auto, inclusief btw en bpm."
    """
    forfait, toelichting = btw_forfait(marge, ingebruikname, jaar or date.today().year)
    return catalogusprijs * forfait * maandfractie(van, tot), toelichting


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


def waarschuwing_regimejaar(nulemissie: bool, jaar: int) -> str | None:
    """Melding als er voor een nulemissieauto geen gecontroleerde korting is.

    Zodra het regimejaar voorbij het laatst nagelopen jaar ligt, rekent de tool
    met het standaardpercentage. Dat is niet per definitie juist — het is wat er
    bekend is. Beter een melding dan een stille aanname.
    """
    if nulemissie and jaar > KORTING_GEVERIFIEERD_TOT_EN_MET:
        return (f"Voor regimejaar {jaar} is geen kortingspercentage voor "
                f"nulemissieauto's in de tool opgenomen; er is gerekend met het "
                f"standaardpercentage van {standaardpercentage(jaar):.0f}%. De tabel is "
                f"nagelopen tot en met {KORTING_GEVERIFIEERD_TOT_EN_MET}. Controleer of er "
                f"nieuwe wetgeving is.")
    return None


def standaardpercentage(jaar: int) -> float:
    """Het percentage voor een auto met CO2-uitstoot, naar regimejaar."""
    return STANDAARD_BIJTELLING_TOT_2017 if jaar < 2017 else STANDAARD_BIJTELLING_VANAF_2017


def bijtelling_regime(catalogusprijs: float, nulemissie: bool, jaar: int,
                      plafondvrij: bool = False) -> tuple[float, str]:
    """Bijtellingsgrondslag per vol jaar plus een leesbaar label.

    plafondvrij: waterstof- en zonnecelauto's krijgen het verlaagde percentage
    over de hele catalogusprijs; voor de overige nulemissieauto's geldt het
    plafond van het regimejaar.
    """
    standaard = standaardpercentage(jaar)
    if not nulemissie or jaar not in KORTING_NULEMISSIE:
        return catalogusprijs * (standaard / 100), f"{standaard:.0f}%"

    pct, plafond = KORTING_NULEMISSIE[jaar]
    if plafond is None or plafondvrij:
        achtergrond = "0-emissie" if plafond is None else "waterstof, geen plafond"
        return catalogusprijs * (pct / 100), f"{pct:.0f}% ({achtergrond})"
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
    plafondvrij = is_plafondvrij(brandstof)
    vervaldatum = vervaldatum_vaste_termijn(eerste_toelating)

    if vervaldatum is None or not (van < vervaldatum <= tot):
        jaar = regime_jaar(eerste_toelating, berekeningsjaar, van)
        grondslag, label = bijtelling_regime(catalogusprijs, nulemissie, jaar, plafondvrij)
        return grondslag * jaarfractie((tot - van).days + 1), label

    delen = [(van, vervaldatum - timedelta(days=1), eerste_toelating.year),
             (vervaldatum, tot, berekeningsjaar)]
    totaal_dagen = sum((eind - start).days + 1 for start, eind, _ in delen)
    # Voorkom dat een schrikkeljaar door de splitsing alsnog boven 1,0 uitkomt.
    schaal = min(1.0, 365 / totaal_dagen) if totaal_dagen else 1.0

    bedrag, labels = 0.0, []
    for start, eind, jaar in delen:
        grondslag, label = bijtelling_regime(catalogusprijs, nulemissie, jaar, plafondvrij)
        dagen = (eind - start).days + 1
        bedrag += grondslag * (dagen / 365) * schaal
        labels.append(label)

    if labels[0] == labels[1]:
        # Regimewissel zonder gevolg voor het percentage: niet tonen.
        return bedrag, labels[0]
    laatste_dag = (vervaldatum - timedelta(days=1)).strftime("%d-%m-%Y")
    return bedrag, f"{labels[0]} t/m {laatste_dag} → daarna {labels[1]}"
