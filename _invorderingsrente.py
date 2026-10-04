"""Invorderingsrente volgens hoofdstuk V van de Invorderingswet 1990.

Bewust vrij van Streamlit-afhankelijkheden, net als `_rente.py`. Deze module
rekent de invorderingsrente van artikel 28 (in rekening brengen), artikel 28a en
artikel 28b en artikel 28c (vergoeden), met de opschorting tijdens uitstel van
artikel 28 lid 3 en 4; zie `uitstel_uitsluiting()` en `periode_art28c()`.

Alle bronnen hieronder zijn opgehaald uit de KOOP-repository
(repository.officiele-overheidspublicaties.nl/bwb/<BWB>/<versie>/xml/...) op
18 september 2026. Van elke versie is de SHA-512 van het opgehaalde bestand
vergeleken met de `hashcode` in het bijbehorende manifest; die kwam overeen. De
SHA-256 hieronder is het controlegetal van datzelfde bestand, zodat een volgende
sessie kan narekenen dat zij dezelfde tekst leest.

  Invorderingswet 1990                BWBR0004770  versie 2026-07-01_0
      sha256 4ea1c83fdf3c3c490ffa06e343dddad94163d55db9eabcd5d49571868f5054ee
  Uitvoeringsregeling IW 1990         BWBR0004766  versie 2026-01-01_0
      sha256 69b596a6fc43dd5a8567da2dbb6d2ed52eb58edbee64a7cb2d41cdb3a420e060
  Uitvoeringsbesluit IW 1990          BWBR0004772  versie 2025-12-12_0
      sha256 2209bcf0a5237fc412c852232dede95e6f0a8466e935352b5b5ee23c90fa550b
  Besluit belasting- en invorderingsrente  BWBR0043680  versie 2026-02-13_0
      sha256 1d7ccd565188dbc03bb578e229b5f32a164414ca8dfa87d18649127e3be7c7ba

DRIE DINGEN WAARIN DEZE MODULE AFWIJKT VAN `_rente.py`, EN WAAROM

  1. De dagentelling is niet `dagen_30_360()`. Artikel 31 van de
     Uitvoeringsregeling IW 1990 schrijft een eigen telling voor: de maand
     waarin de enige of laatste betalingstermijn vervalt telt haar werkelijke
     aantal dagen, met februari altijd op 28, en verder geldt 30 dagen per
     volle maand en 360 per jaar. Dat is dus geen zuivere 30/360-telling en
     ook geen telling in werkelijke dagen. Zie `dagen_invorderingsrente()`.
  2. De afronding is niet in beide richtingen naar beneden. Artikel 32 van
     diezelfde regeling rondt de in rekening te brengen rente naar beneden af
     op hele euro's en de te vergoeden rente naar boven.
  3. Er wordt één keer afgerond over het geheel en niet per tariefperiode. Dat
     volgt uit de formule van artikel 30 lid 1, die de deelperioden eerst
     optelt: (A x P + A x P enz.) x betaling / 36000. Bij belastingrente is het
     juist andersom; die rondt per tariefperiode af.

Alle rentesoorten zijn enkelvoudig. Dat staat met zoveel woorden in art. 28
lid 2, art. 28a lid 2 en art. 28b lid 2 IW 1990.
"""

import calendar
import math
from datetime import date, timedelta

from _format import nl_date, nl_euro, nl_euro_heel, nl_pct

# ── Tarieven ────────────────────────────────────────────────────────────────
# Opgebouwd uit alle expressies van het Besluit belasting- en invorderingsrente
# (BWBR0043680) in de KOOP-repository, elk met een eigen geverifieerde hash.
# Gesorteerd nieuw → oud, net als de reeksen in de belastingrentepagina's.
#
# LET OP — tot en met 31 december 2023 kende het besluit TWEE percentages, en
# die liepen uiteen. Artikel 2 lid 1 gaf het percentage van de in rekening te
# brengen rente als een vast getal. Artikel 2 lid 2 koppelde de te vergoeden
# rente aan de wettelijke rente van art. 6:119 BW, "met dien verstande dat het
# eerstgenoemde percentage ten minste 4 bedraagt". Pas per 1 januari 2024 is
# artikel 2 teruggebracht tot één percentage voor beide richtingen.
#
# De onderzoeksnotitie van 10 september 2026 ging uit van één reeks. Dat klopt
# alleen vanaf 2024. In de tweede helft van 2023 verschilt het meer dan een
# beetje: 3 procent in rekening tegenover 6 procent vergoed.
TARIEVEN_IN_REKENING = [
    (date(2026, 1, 1), 4.3),    # Stb. 2025, 383
    (date(2024, 1, 1), 4.0),    # Stb. 2023, 511
    (date(2023, 7, 1), 3.0),
    (date(2023, 1, 1), 2.0),
    (date(2022, 7, 1), 1.0),
    (date(2020, 6, 1), 0.01),   # coronaverlaging; eerste versie van het besluit
]

# De te vergoeden reeks tot 2024 is de uitkomst van art. 2 lid 2: het hoogste
# van de wettelijke rente en 4. De wettelijke rente zelf komt uit het Besluit
# wettelijke rente (BWBR0002744, 2 procent vanaf 01-01-2015) en het Besluit
# vaststelling wettelijke rente (BWBR0047640: 4 procent per 01-01-2023,
# 6 procent per 01-07-2023, 7 procent per 01-01-2024, 6 procent per 01-01-2025,
# 4 procent per 01-01-2026). Vanaf 01-01-2024 geldt het enkele percentage van
# art. 2 en speelt de wettelijke rente geen rol meer.
#
#   01-06-2020 t/m 31-12-2022  wettelijke rente 2, bodem 4  → 4
#   01-01-2023 t/m 30-06-2023  wettelijke rente 4, bodem 4  → 4
#   01-07-2023 t/m 31-12-2023  wettelijke rente 6, bodem 4  → 6
#   vanaf 01-01-2024           één percentage uit art. 2    → 4, en 4,3 per 2026
#
# Van de versie van het Besluit wettelijke rente die 2 procent vaststelt
# (BWBR0002744, expressie 2015-01-01_0) week de SHA-512 af van de hashcode in
# het manifest. Dat is de enige bron in deze module die niet sluitend is
# geverifieerd. Het raakt de uitkomst niet: elk percentage onder de 4 geeft na
# toepassing van de bodem dezelfde 4.
TARIEVEN_TE_VERGOEDEN = [
    (date(2026, 1, 1), 4.3),
    (date(2024, 1, 1), 4.0),
    (date(2023, 7, 1), 6.0),
    (date(2020, 6, 1), 4.0),
]

# Drempelbedrag van art. 33 Uitvoeringsregeling IW 1990. Geldt uitsluitend bij
# de enige of laatste betaling en uitsluitend voor rente die in rekening wordt
# gebracht; voor een vergoeding bestaat geen drempel. Het bedrag wordt sinds
# 1 januari 2026 elke vijf jaar geïndexeerd (art. 33 lid 2, Stcrt. 2025, 42873).
DREMPELS = [
    (date(2026, 1, 1), 49),
    (date(2002, 1, 1), 23),
]

# ── Termijnen ───────────────────────────────────────────────────────────────
INVORDERBAAR_WEKEN = 6        # art. 9 lid 1 IW 1990
NAVORDERING_MAANDEN = 1       # art. 9 lid 2 IW 1990
NAHEFFING_DAGEN = 14          # art. 9 lid 2 IW 1990
UITBETALING_WEKEN = 6         # art. 28a lid 1 IW 1990
VERMINDERING_WEKEN = 6        # art. 28b lid 2 IW 1990
VERZOEK_WEKEN_28C = 6         # art. 28c lid 3 IW 1990

# De Algemene termijnenwet is niet van toepassing op deze termijnen
# (art. 9 lid 10 IW 1990). Een vervaldag in een weekend schuift dus niet op.


# ── Uitstel ─────────────────────────────────────────────────────────────────
# Art. 28 lid 3 schort de rente op tijdens uitstel krachtens negen leden van
# art. 25. De opschorting wordt gerekend in `uitstel_uitsluiting()`; wat de wet
# niet regelt (betaling na afloop van de uitsteltermijn bij de gronden van lid 4)
# geeft geen uitkomst. Tot 04-10-2026 rekende de tool de opschorting niet door
# (OPENSTAAND.md punt 4).
UITSTELGRONDEN = [
    ("25-3", "art. 25 lid 3 — schenk- of erfbelasting, sociaal-economisch of cultureel belang"),
    ("25-5", "art. 25 lid 5 — geconserveerd inkomen uit loon- en lijfrentesfeer"),
    ("25-8", "art. 25 lid 8 — geconserveerd inkomen aanmerkelijk belang"),
    ("25-9", "art. 25 lid 9 — vervreemding aanmerkelijk belang, overdrachtsprijs schuldig gebleven"),
    ("25-11", "art. 25 lid 11 — overdracht aandelen beneden de waarde in het economische verkeer"),
    ("25-17", "art. 25 lid 17 — staking door overlijden"),
    ("25-18", "art. 25 lid 18 — staking door overdracht, overdrachtsprijs schuldig gebleven"),
    ("25-19", "art. 25 lid 19 — afbouw van het uitstel van lid 18"),
    ("25-21", "art. 25 lid 21 — onbillijkheden van overwegende aard bij een natuurlijk persoon"),
]

# Art. 28 lid 4: wordt het uitstel beëindigd, dan loopt de rente alsnog. Het
# tijdvak daarvoor staat in art. 6 Uitvoeringsbesluit IW 1990; `herlevingsdatum()`
# rekent het uit. De teksten hieronder blijven de vindplaats voor de gebruiker.
#
# Onzeker blijft bij lid 5 en 8 of de rente op de dag zelf ingaat waarop zes weken
# zijn verstreken (1 januari plus 42 dagen, 12 februari) of een dag later: art. 6
# lid 1 zegt "met ingang van de dag waarop", lid 2 zegt "de dag volgende op", en
# geen bron die is nagelezen (Leidraad, Stb. 2022, 540) beslist het. De tool kiest de
# letterlijke lezing, 12 februari; het verschil is één dag rente.
HERLEVING_NA_UITSTEL = {
    "25-5": "art. 6 lid 1 Uitvoeringsbesluit IW 1990: de rente loopt vanaf de dag "
            "waarop zes weken zijn verstreken na de eerste dag van het jaar volgend "
            "op het jaar waarin de handeling of gebeurtenis zich voordoet.",
    "25-8": "art. 6 lid 1 Uitvoeringsbesluit IW 1990: de rente loopt vanaf de dag "
            "waarop zes weken zijn verstreken na de eerste dag van het jaar volgend "
            "op het jaar waarin de handeling of gebeurtenis zich voordoet.",
}
_HERLEVING_LID2 = (
    "art. 6 lid 2 Uitvoeringsbesluit IW 1990: de rente loopt vanaf de dag volgend "
    "op de dag waarop de omstandigheid zich voordoet op grond waarvan het uitstel "
    "wordt beëindigd."
)
for _code in ("25-9", "25-11", "25-17", "25-18", "25-19", "25-21"):
    HERLEVING_NA_UITSTEL[_code] = _HERLEVING_LID2
# Art. 25 lid 3 staat wel in art. 28 lid 3 maar niet in lid 4 en niet in art. 6
# van het Uitvoeringsbesluit. Voor die grond is dus geen herlevingstijdvak
# aangewezen; daar wordt hier niets over beweerd.


# ── Uitzonderingen: geen rente in rekening ──────────────────────────────────
# Art. 28 lid 5 IW 1990 laat bij algemene maatregel van bestuur gevallen
# aanwijzen waarin geen invorderingsrente in rekening wordt gebracht omdat dat
# door uitzonderlijke omstandigheden niet redelijk is. Die aanwijzing staat in
# hoofdstuk II van het Uitvoeringsbesluit IW 1990, dat blijkens art. 1 lid 1
# uitvoering geeft aan onder meer art. 28 van de wet. Er zijn er twee.
#
# De derde regel hieronder komt niet uit een AMvB maar uit de Leidraad
# Invordering 2008, een beleidsbesluit. Zij staat er los bij, omdat zij een
# andere status heeft: de ontvanger vermindert de rente achteraf tot nihil.
UITZONDERINGEN = [
    {
        "code": "box3-2022",
        "titel": "Aanhoudaanbod voorlopige aanslag IB 2022 met box 3",
        "uitleg": "Er wordt geen invorderingsrente in rekening gebracht gedurende de "
                  "periode waarin het aanbod van de ontvanger geldt om de invordering "
                  "van een in 2022 gedagtekende voorlopige aanslag inkomstenbelasting "
                  "over 2022 met belastbaar inkomen uit sparen en beleggen aan te "
                  "houden. Vervalt dat aanbod, dan loopt de rente alsnog volgens "
                  "art. 28, tenzij binnen zes weken na de nieuwe vaststelling wordt "
                  "betaald.",
        "bron": "art. 6bis Uitvoeringsbesluit IW 1990",
        "beleidsmatig": False,
    },
    {
        "code": "toeslagenherstel",
        "titel": "Hersteloperatie toeslagen, invordering gepauzeerd",
        "uitleg": "Komt een aanvrager van kinderopvangtoeslag met diens partner in "
                  "aanmerking voor een herstelmaatregel als bedoeld in art. 2.7 Wet "
                  "hersteloperatie toeslagen en is de invordering daardoor gepauzeerd, "
                  "dan wordt geen invorderingsrente in rekening gebracht over de "
                  "terug te vorderen bedragen die zien op de periode tot en met de "
                  "dagtekening van de brief over het einde van de pauzering.",
        "bron": "art. 6ter Uitvoeringsbesluit IW 1990",
        "beleidsmatig": False,
    },
    {
        "code": "leidraad-25.4.6",
        "titel": "Uitstel op grond van art. 25.4.6 Leidraad Invordering 2008",
        "uitleg": "De ontvanger vermindert in rekening gebrachte invorderingsrente tot "
                  "nihil voor zover die is berekend over de periode waarin uitstel van "
                  "betaling is genoten op grond van art. 25.4.6 van de Leidraad. Dit is "
                  "beleid en geen aanwijzing op grond van art. 28 lid 5; de vermindering "
                  "gebeurt achteraf.",
        "bron": "art. 28.3a Leidraad Invordering 2008",
        "beleidsmatig": True,
    },
]


# ── Samenloop met de belastingrente van hoofdstuk VA AWR ────────────────────
# Nagelezen in de wettekst zelf en niet overgenomen uit de onderzoeksnotitie.
# Alleen art. 28a lid 2, tweede volzin, sluit de dagen uit waarover al
# belastingrente is vergoed. Art. 28c lid 2 doet dat ook, en sluit daarnaast de
# dagen uit waarover op grond van art. 28b invorderingsrente wordt vergoed;
# beide uitsluitingen rekent de tool sinds 04-10-2026 bij art. 28c.
#
# Art. 28 lid 2 en art. 28b lid 2 kennen die uitsluiting NIET. Art. 28 lid 1
# kent wel een eigen, andere beperking: geen rente voor zover met de aanslag
# een aanslag wordt verrekend die op dezelfde belasting en hetzelfde tijdvak
# ziet. Dat is geen dagenuitsluiting maar een beperking van de grondslag.
#
# Dit staat als gegeven in de code omdat het precies de vraag is waarop de
# opdracht om verificatie in de wettekst vroeg; `tests/test_invorderingsrente.py`
# legt het vast zodat het niet ongemerkt wordt rechtgetrokken.
UITSLUITING_BELASTINGRENTE = {
    "28": False,    # art. 28 lid 2 IW 1990 — geen uitsluiting
    "28a": True,    # art. 28a lid 2, tweede volzin IW 1990
    "28b": False,   # art. 28b lid 2 IW 1990 — geen uitsluiting
    "28c": True,    # art. 28c lid 2, tweede volzin IW 1990
}


def samenvoegen(intervallen: list[tuple[date, date]]) -> list[tuple[date, date]]:
    """Overlappende en aansluitende datumbereiken samenvoegen.

    Zonder dit zou een dag die in twee opgegeven bereiken valt, twee keer van
    het tijdvak worden afgetrokken.
    """
    schoon = sorted((a, b) for a, b in intervallen if b >= a)
    uit: list[tuple[date, date]] = []
    for start, eind in schoon:
        if uit and start <= uit[-1][1] + timedelta(days=1):
            uit[-1] = (uit[-1][0], max(uit[-1][1], eind))
        else:
            uit.append((start, eind))
    return uit


# ── Dagentelling ────────────────────────────────────────────────────────────

def maandlengte(jaar: int, maand: int, vervalmaand: tuple[int, int] | None) -> int:
    """Aantal dagen dat art. 31 Uitvoeringsregeling IW 1990 aan een maand toekent.

    Onderdeel a geldt uitsluitend voor de maand waarin de enige of laatste
    betalingstermijn van de aanslag vervalt: die telt haar werkelijke aantal
    dagen, waarbij februari altijd op 28 wordt gesteld (ook in een schrikkeljaar).
    Onderdeel b geldt voor alle overige maanden: 30 dagen, en daarmee 360 per jaar.

    'vervalmaand' is (jaar, maand) van die vervaldag, of None als er geen
    betalingstermijn is. Dat laatste doet zich voor bij art. 28a, waar het
    tijdvak aanvangt na de dagtekening van een uitbetaling en er dus niets
    vervalt.
    """
    if vervalmaand is not None and (jaar, maand) == vervalmaand:
        if maand == 2:
            return 28
        return calendar.monthrange(jaar, maand)[1]
    return 30


def dagen_invorderingsrente(vanaf: date, tot_en_met: date,
                            vervalmaand: tuple[int, int] | None = None) -> int:
    """Aantal dagen van 'vanaf' tot en met 'tot_en_met' volgens art. 31 URIW 1990.

    De telling loopt maand voor maand, omdat de regeling per maand een lengte
    toekent. Een dagnummer dat buiten die lengte valt — dag 31 in een maand die
    voor 30 telt — wordt op de laatste dag van die maand gezet, net zoals
    `dagen_30_360()` in `_rente.py` doet. Zonder die kap zou een maand van 31
    dagen alsnog 31 dagen opleveren en klopt de jaartelling van 360 niet meer.

    De telling is optelbaar: een periode knippen op een tariefwissel geeft
    dezelfde uitkomst als de periode in één keer tellen.
    """
    if tot_en_met < vanaf:
        return 0

    totaal = 0
    jaar, maand = vanaf.year, vanaf.month
    while (jaar, maand) <= (tot_en_met.year, tot_en_met.month):
        lengte = maandlengte(jaar, maand, vervalmaand)
        eerste = vanaf.day if (jaar, maand) == (vanaf.year, vanaf.month) else 1
        laatste = tot_en_met.day if (jaar, maand) == (tot_en_met.year, tot_en_met.month) else lengte
        totaal += max(0, min(laatste, lengte) - min(eerste, lengte) + 1)
        maand += 1
        if maand == 13:
            jaar, maand = jaar + 1, 1
    return totaal


# ── Tarieven opzoeken en de periode knippen ─────────────────────────────────

def tarief_op(dag: date, tarieven: list) -> float | None:
    """Percentage dat op deze dag geldt, of None vóór de oudste ingangsdatum.

    Wijkt bewust af van `_rente.tarief_op()`, dat terugvalt op het oudste
    percentage. Die terugval zou hier stil een percentage van 2020 op een
    periode van 2015 toepassen. Een onbekende dag hoort een melding te geven.
    """
    for ingang, percentage in tarieven:
        if dag >= ingang:
            return percentage
    return None


def oudste_ingang(tarieven: list) -> date:
    return min(ingang for ingang, _ in tarieven)


def buiten_bereik(vanaf: date, tarieven: list) -> bool:
    """True als de periode begint vóór de reeks die deze tool kent."""
    return vanaf < oudste_ingang(tarieven)


def deelperioden(vanaf: date, tot_en_met: date, tarieven: list,
                 vervalmaand: tuple[int, int] | None = None,
                 uitgesloten: list[tuple[date, date]] | None = None) -> list[dict]:
    """De periode geknipt op elke tariefwijziging, met dagen en percentage.

    'uitgesloten' bevat de bereiken waarover al belastingrente is vergoed op
    grond van hoofdstuk VA AWR. Die dagen tellen niet mee; zie
    UITSLUITING_BELASTINGRENTE voor de vraag bij welke grondslag dat speelt.
    Per deelperiode blijft zichtbaar hoeveel dagen er zijn afgetrokken, zodat
    de uitkomst navolgbaar blijft.
    """
    if tot_en_met < vanaf:
        return []

    weg = samenvoegen(uitgesloten or [])
    knippunten = sorted({vanaf} | {d for d, _ in tarieven if vanaf < d <= tot_en_met})
    uit = []
    for i, start in enumerate(knippunten):
        laatste = (knippunten[i + 1] - timedelta(days=1)
                   if i + 1 < len(knippunten) else tot_en_met)
        bruto = dagen_invorderingsrente(start, laatste, vervalmaand)
        af = 0
        for a, b in weg:
            overlap_start, overlap_eind = max(a, start), min(b, laatste)
            if overlap_eind >= overlap_start:
                af += dagen_invorderingsrente(overlap_start, overlap_eind, vervalmaand)
        uit.append({
            "start": start,
            "eind": laatste,
            "dagen": max(0, bruto - af),
            "dagen_bruto": bruto,
            "dagen_uitgesloten": min(af, bruto),
            "pct": tarief_op(start, tarieven),
        })
    return uit


# ── De berekening zelf ──────────────────────────────────────────────────────

def _som_dagen_maal_percentage(perioden: list[dict]) -> float:
    """De teller 'A x P + A x P enz.' uit art. 30 lid 1 URIW 1990."""
    return sum(p["dagen"] * p["pct"] for p in perioden)


def rente_onafgerond(grondslag: float, perioden: list[dict]) -> float:
    """Invorderingsrente vóór afronding, volgens de formule van art. 30 lid 1.

        (A x P + A x P enz.) x betaling / 36000

    36000 is 360 dagen maal 100 procent. De formule staat in de regeling als
    afbeelding en niet als tekst; zij is overgenomen uit illustratie 123954.png
    bij art. 30 lid 1 in de KOOP-versie 2026-01-01_0 van BWBR0004766.

    Voor rente die wordt vergoed kent de regeling geen eigen formule. Art. 30
    is naar zijn tekst geschreven voor de in rekening te brengen rente over een
    betaling. Voor art. 28a en 28b wordt dezelfde enkelvoudige formule gebruikt
    met het uit te betalen respectievelijk het terug te geven bedrag als
    grondslag; de wet noemt die grondslag zelf (art. 28b lid 2, slot).
    """
    return grondslag * _som_dagen_maal_percentage(perioden) / 36000


def afronden(bedrag: float, richting: str) -> int:
    """Afronding op hele euro's volgens art. 32 URIW 1990.

    Lid 1: in rekening te brengen rente naar beneden. Lid 2: te vergoeden rente
    naar boven. Eén keer over het geheel, niet per tariefperiode — dat volgt uit
    de formule van art. 30 lid 1, die de deelperioden eerst optelt.
    """
    if richting == "in_rekening":
        return math.floor(bedrag)
    if richting == "te_vergoeden":
        return math.ceil(bedrag)
    raise ValueError(f"onbekende richting: {richting}")


def drempel_op(dag: date) -> int:
    """Het drempelbedrag van art. 33 URIW 1990 dat op deze dag geldt."""
    for ingang, bedrag in DREMPELS:
        if dag >= ingang:
            return bedrag
    return DREMPELS[-1][1]


def bereken(grondslag: float, vanaf: date, tot_en_met: date, tarieven: list,
            richting: str, vervalmaand: tuple[int, int] | None = None,
            laatste_betaling: bool = False,
            uitgesloten: list[tuple[date, date]] | None = None) -> dict:
    """Invorderingsrente over [vanaf, tot_en_met], beide inclusief.

    Geeft een woordenboek terug met de deelperioden, het onafgeronde bedrag,
    het afgeronde bedrag, het toegepaste drempelbedrag en het eindbedrag.

    'laatste_betaling' zet de drempel van art. 33 aan. Die geldt alleen bij de
    enige of laatste betaling en alleen voor rente die in rekening wordt
    gebracht; bij een vergoeding wordt hij nooit toegepast.

    'uitgesloten' zijn de bereiken waarover al belastingrente is vergoed. De
    aanroeper bepaalt of die uitsluiting bij zijn grondslag hoort; zie
    UITSLUITING_BELASTINGRENTE.
    """
    perioden = deelperioden(vanaf, tot_en_met, tarieven, vervalmaand, uitgesloten)
    if any(p["pct"] is None for p in perioden):
        raise ValueError("de periode begint vóór de tariefreeks van deze tool")

    onafgerond = rente_onafgerond(grondslag, perioden)
    afgerond = afronden(onafgerond, richting)

    drempel = None
    kwijt_door_drempel = False
    if richting == "in_rekening" and laatste_betaling:
        drempel = drempel_op(tot_en_met)
        if afgerond <= drempel:
            kwijt_door_drempel = True

    return {
        "perioden": perioden,
        "dagen": sum(p["dagen"] for p in perioden),
        "dagen_uitgesloten": sum(p["dagen_uitgesloten"] for p in perioden),
        "onafgerond": onafgerond,
        "afgerond": afgerond,
        "drempel": drempel,
        "kwijt_door_drempel": kwijt_door_drempel,
        "bedrag": 0 if kwijt_door_drempel else afgerond,
    }


def splits_betaling(betaling: float, vanaf: date, tot_en_met: date, tarieven: list,
                    vervalmaand: tuple[int, int] | None = None) -> tuple[int, int]:
    """Een betaling splitsen in hoofdsom en invorderingsrente, art. 30 lid 2.

        hoofdsom = 36 000 x betaling / (A x P + A x P enz. + 36 000)
        invorderingsrente = betaling - hoofdsom

    Uit illustratie 123955.png bij art. 30 lid 2. Art. 30 lid 4 schrijft voor
    dat het bedrag van de betaling eerst naar beneden wordt afgerond op hele
    euro's; dat gebeurt hier. De rente is het restant, zodat de twee delen
    samen precies de afgeronde betaling zijn.

    Dit is de situatie waarin een ontvangen bedrag moet worden toegerekend. Wie
    wil weten hoeveel rente er over een betaald bedrag loopt, gebruikt
    `bereken()` met de formule van lid 1.
    """
    betaling = math.floor(betaling)
    perioden = deelperioden(vanaf, tot_en_met, tarieven, vervalmaand)
    som = _som_dagen_maal_percentage(perioden)
    hoofdsom = math.floor(36000 * betaling / (som + 36000))
    return hoofdsom, betaling - hoofdsom


# ── Invorderbaarheid en de drie tijdvakken ──────────────────────────────────

def _tel_maanden_op(d: date, maanden: int) -> date:
    """Onderdeel 9.5 Leidraad Invordering 2008: valt de dagtekening op de laatste
    dag van een maand, dan vervalt een termijn van een maand op de laatste dag
    van de volgende maand (28 februari → 31 maart); anders op de dag met
    hetzelfde nummer, gekapt op de lengte van die maand. Zelfde regel als in
    `_rente._tel_maanden_op`; tot 29-09-2026 werd alleen gekapt."""
    maand = d.month + maanden
    jaar = d.year + (maand - 1) // 12
    maand = (maand - 1) % 12 + 1
    lengte = calendar.monthrange(jaar, maand)[1]
    if d.day == calendar.monthrange(d.year, d.month)[1]:
        return date(jaar, maand, lengte)
    return date(jaar, maand, min(d.day, lengte))


def vervaldag_op(dagtekening: date, aanslag_type: str = "regulier") -> date:
    """De vervaldag: de laatste dag van de enige of laatste betalingstermijn.

    Art. 9 IW 1990 geeft de termijn (zes weken, een maand of veertien dagen na
    de dagtekening); de Leidraad Invordering 2008, onderdeel 9.5, zegt op welke
    dag hij vervalt: bij dagtekening 15 maart vervalt de termijn van zes weken op
    26 april, dus dagtekening plus 42 dagen. Wie op die dag betaalt, betaalt op
    tijd. Deze dag bepaalt de vervalmaand van art. 31 URIW 1990.

    Art. 28 lid 2 sluit art. 10 uitdrukkelijk uit, dus versnelde invordering
    vervroegt dit tijdstip voor de renteberekening niet.

    Een voorlopige aanslag die in termijnen invorderbaar is (art. 9 lid 5) valt
    hier bewust buiten: de laatste termijn hangt af van de dagtekening en van
    het aantal resterende maanden, en de Leidraad Invordering 2008 legt die
    vervaldag in bepaalde gevallen op 31 december. Die vervaldag wordt daarom
    uitgevraagd en niet afgeleid.
    """
    if aanslag_type in ("navordering", "conserverende-navordering"):
        return _tel_maanden_op(dagtekening, NAVORDERING_MAANDEN)
    if aanslag_type == "naheffing":
        return dagtekening + timedelta(days=NAHEFFING_DAGEN)
    if aanslag_type == "regulier":
        return dagtekening + timedelta(weeks=INVORDERBAAR_WEKEN)
    raise ValueError(f"onbekend aanslagtype: {aanslag_type}")


def invorderbaar_op(dagtekening: date, aanslag_type: str = "regulier") -> date:
    """De dag waarop de belastingaanslag invorderbaar is: de dag na de vervaldag.

    "Invorderbaar zes weken na de dagtekening" (art. 9 lid 1 IW 1990) lezen we
    als: invorderbaar zodra de betalingstermijn is verstreken. Tot 29-09-2026
    rekende deze module de vervaldag zelf als eerste rentedag. Dat gaf een dag meer
    dan model 02-04 en dan de Belastingdienst, die invorderingsrente rekent "vanaf
    de dag na de uiterste betaaldatum" (belastingdienst.nl, Invorderingsrente,
    geraadpleegd 29-09-2026, rekenvoorbeeld: uiterste betaaldatum 31 maart, rente
    vanaf 1 april). Het sluit ook aan op de belastingrente, die volgens art. 30fc
    lid 2 AWR eindigt "op de dag voorafgaand aan de dag waarop de aanslag
    invorderbaar is" en in `_rente.py` tot en met de vervaldag loopt; zonder deze
    lezing telde die ene dag in beide renten mee. Besluit van Sylvain op
    29-09-2026; zie OPENSTAAND.md punt 12.
    """
    return vervaldag_op(dagtekening, aanslag_type) + timedelta(days=1)


def periode_art28(vervaldag: date, betaaldatum: date) -> tuple[date, date] | None:
    """Tijdvak van art. 28 lid 2: van de invorderbaarheid tot de dag vóór de betaling.

    De invorderbaarheid is de dag na de vervaldag; zie `invorderbaar_op()`.
    Geeft None als er niets te rekenen valt: wie op de vervaldag betaalt,
    overschrijdt de termijn niet (art. 28 lid 1), en wie de dag erna betaalt heeft
    een tijdvak zonder dagen, want dat eindigt op de dag vóór de betaling.
    """
    vanaf = vervaldag + timedelta(days=1)
    tot = betaaldatum - timedelta(days=1)
    if tot < vanaf:
        return None
    return vanaf, tot


def periode_art28a(dagtekening: date, betaaldatum: date) -> tuple[date, date] | None:
    """Tijdvak van art. 28a lid 2: van de dag na de dagtekening tot de dag vóór de betaling.

    Geeft None als de ontvanger binnen zes weken na de dagtekening heeft
    uitbetaald of verrekend; dan ontstaat er op grond van lid 1 geen recht op
    een vergoeding. Let op dat lid 1 en lid 2 verschillende momenten noemen:
    lid 1 bepaalt óf er wordt vergoed, lid 2 vanaf wanneer wordt gerekend. Is
    de zeswekentermijn overschreden, dan loopt het tijdvak dus terug tot de dag
    na de dagtekening en niet pas vanaf het einde van die zes weken.
    """
    if betaaldatum <= dagtekening + timedelta(weeks=UITBETALING_WEKEN):
        return None
    return dagtekening + timedelta(days=1), betaaldatum - timedelta(days=1)


def periode_art28b(vervaldag: date, dagtekening_vermindering: date) -> tuple[date, date] | None:
    """Tijdvak van art. 28b lid 2.

    Eindigt zes weken na de dagtekening van de vermindering of herziening. Anders
    dan bij art. 28 en 28a loopt het tijdvak dus door tot een datum die uit de
    vermindering volgt en niet tot de dag vóór een betaling.

    'vervaldag' is de laatste dag van de betalingstermijn. Het tijdvak vangt aan
    op de dag erna (`invorderbaar_op()`). De letterlijke tekst van lid 2 ("de dag
    na die waarop de aanslag invorderbaar is") zou een dag later geven, maar de
    Belastingdienst laat de vergoeding de dag na de vervaldag ingaan: KG:207:2022:2
    (Kennisgroep Belastingdienst, 28-03-2023) en belastingdienst.nl, Invorderingsrente
    (geraadpleegd 04-10-2026: termijn eindigt 1 mei, vergoeding vanaf 2 mei).
    Besluit van Sylvain op 04-10-2026 om de uitvoering te volgen; tot dan begon
    het tijdvak twee dagen na de vervaldag.
    """
    eind = dagtekening_vermindering + timedelta(weeks=VERMINDERING_WEKEN)
    start = vervaldag + timedelta(days=1)
    if eind < start:
        return None
    return start, eind


def vervalmaand_van(vervaldag: date) -> tuple[int, int]:
    return (vervaldag.year, vervaldag.month)


def uiterste_verzoekdatum_28c(dagtekening_beschikking: date) -> date:
    """Art. 28c lid 3: zes weken na dagtekening van de beschikking."""
    return dagtekening_beschikking + timedelta(weeks=VERZOEK_WEKEN_28C)


# ── Artikel 28c: vergoeding bij heffing in strijd met het Unierecht ─────────
# Tekst nagelezen in BWBR0004770 versie 2026-07-01_0 (KOOP, 04-10-2026). Lid 1:
# op verzoek wordt invorderingsrente vergoed voor zover de ontvanger op grond van
# een beschikking van de inspecteur belasting moet teruggeven omdat die in strijd
# met het Unierecht is geheven. Lid 2: enkelvoudig, over het tijdvak vanaf de dag
# na die van de betaling tot de dag vóór de terugbetaling, met als grondslag het
# terug te geven bedrag; niet over dagen waarover belastingrente (hoofdstuk VA
# AWR) of invorderingsrente op grond van art. 28b wordt vergoed. Lid 3: het
# verzoek moet binnen zes weken na de dagtekening van de beschikking zijn gedaan.
ART28C_TOELICHTING = (
    "Is de belasting geheven in strijd met het Unierecht en geeft de ontvanger "
    "terug op grond van een beschikking van de inspecteur, dan wordt op verzoek "
    "invorderingsrente vergoed (art. 28c lid 1 IW 1990). Het tijdvak loopt van de "
    "dag na de betaling tot de dag vóór de terugbetaling, met het terug te geven "
    "bedrag als grondslag (lid 2). Het verzoek moet binnen zes weken na de "
    "dagtekening van de beschikking zijn gedaan (lid 3)."
)


def periode_art28c(betaald_op: date, terugbetaald_op: date) -> tuple[date, date] | None:
    """Tijdvak van art. 28c lid 2: de dag na de betaling tot de dag vóór de terugbetaling.

    Geeft None als dat tijdvak geen dag bevat. Anders dan bij art. 28 is er geen
    betalingstermijn van een aanslag, dus ook geen vervalmaand in de zin van art. 31
    onderdeel a URIW: alle maanden vallen onder onderdeel b en tellen 30 dagen. Dat
    is dezelfde redenering als bij art. 28a (OPENSTAAND.md punt 7).
    """
    start = betaald_op + timedelta(days=1)
    eind = terugbetaald_op - timedelta(days=1)
    if eind < start:
        return None
    return start, eind


# ── Uitstel: opschorting en herleving (art. 28 lid 3 en 4) ──────────────────

def herlevingsdatum(grond: str, gebeurtenis: date) -> date | None:
    """De dag waarop de rente herleeft nadat de ontvanger het uitstel beëindigt.

    Art. 6 lid 1 Uitvoeringsbesluit IW 1990 (uitstel krachtens art. 25 lid 5 of 8):
    de dag waarop zes weken zijn verstreken na de eerste dag van het jaar volgend
    op het jaar van de handeling of gebeurtenis. Art. 6 lid 2 (lid 9, 11, 17 tot
    en met 19 en 21): de dag volgend op de dag van de omstandigheid. Voor art. 25
    lid 3 wijst het besluit niets aan: dan None.

    Zes weken na 1 januari is 1 januari plus 42 dagen, dezelfde telling die onderdeel
    9.5 Leidraad Invordering 2008 voor een termijn van zes weken hanteert.
    """
    if grond in ("25-5", "25-8"):
        return date(gebeurtenis.year + 1, 1, 1) + timedelta(weeks=6)
    if grond in HERLEVING_NA_UITSTEL:
        return gebeurtenis + timedelta(days=1)
    return None


def uitstel_uitsluiting(grond: str, van: date, tot: date | None, beeindigd: bool,
                        gebeurtenis: date | None, betaaldatum: date) -> dict:
    """De dagen die art. 28 lid 3 en 4 van het rentetijdvak aftrekken.

    Geeft {'uitgesloten': [(van, tot)], 'herleving': date | None, 'blokkade': str | None}.
    Bij een 'blokkade' geeft de aanroeper geen bedrag.

    - Uitstel niet beëindigd: lid 3, geen rente over de tijd waarvoor uitstel is
      verleend. Zonder einddatum loopt het uitstel tot de betaling door.
    - Uitstel beëindigd door de ontvanger (alleen de gronden van lid 4): de rente
      loopt weer vanaf de herlevingsdatum van art. 6 Uitvoeringsbesluit; de dagen
      van het begin van het uitstel tot die dag blijven buiten de berekening.
    - Betaling na het verstrijken van de uitsteltermijn: lid 4 laat het tijdvak aan
      een AMvB, en art. 6 Uitvoeringsbesluit regelt alleen de beëindiging. Voor de
      gronden van lid 4 is daarom geen uitkomst te geven. Voor art. 25 lid 3 staat
      lid 4 niet, dus tellen de dagen ná de termijn gewoon mee.
      Er is wel beleid: onderdeel 74.5 en 74.5a Leidraad Invordering 2008 (lid 9 en
      11, rente vanaf het verschijnen van een niet tijdig betaalde termijn) en 74.10
      en 74.11 (lid 17 tot en met 19, rente vanaf de dag na het einde van het
      uitstel). Die rekent deze tool niet, omdat de Leidraad "vervallen" uitstel
      noemt en niet zeker is dat daar het gewoon aflopen van de termijn onder valt.
    """
    if beeindigd:
        if grond not in HERLEVING_NA_UITSTEL:
            return {"uitgesloten": [], "herleving": None, "blokkade": (
                "Art. 28 lid 4 IW 1990 noemt art. 25 lid 3 niet en art. 6 van het "
                "Uitvoeringsbesluit IW 1990 wijst er geen herlevingstijdvak voor aan. "
                "Voor een beëindigd uitstel op die grond is geen bedrag te geven.")}
        if gebeurtenis is None:
            return {"uitgesloten": [], "herleving": None, "blokkade": (
                "Vul de datum in van de handeling of gebeurtenis waarop het uitstel is "
                "beëindigd.")}
        herleving = herlevingsdatum(grond, gebeurtenis)
        if herleving <= van:
            return {"uitgesloten": [], "herleving": herleving, "blokkade": (
                f"De rente herleeft op {nl_date(herleving)}, niet na het begin van het "
                f"uitstel ({nl_date(van)}). Controleer de datums.")}
        return {"uitgesloten": [(van, herleving - timedelta(days=1))],
                "herleving": herleving, "blokkade": None}

    if tot is None or betaaldatum <= tot:
        eind = betaaldatum if tot is None else tot
        return {"uitgesloten": [(van, eind)], "herleving": None, "blokkade": None}

    if grond in HERLEVING_NA_UITSTEL:
        return {"uitgesloten": [], "herleving": None, "blokkade": (
            "De betaling is gedaan na het einde van de termijn waarvoor uitstel is "
            "verleend. Art. 28 lid 4 IW 1990 laat het tijdvak waarover dan rente wordt "
            "berekend aan een algemene maatregel van bestuur, en art. 6 van het "
            "Uitvoeringsbesluit IW 1990 regelt alleen de beëindiging van het uitstel. "
            "De Leidraad Invordering 2008 kent beleid voor art. 25 lid 9, 11 en 17 "
            "tot en met 19 (onderdeel 74.5, 74.5a, 74.10 en 74.11: rente vanaf het "
            "verschijnen van de termijn of de dag na het einde van het uitstel), maar "
            "dat rekent deze tool niet. Voor dit geval is dus geen bedrag te geven.")}
    return {"uitgesloten": [(van, tot)], "herleving": None, "blokkade": None}

__all__ = [name for name in dir() if not name.startswith("_")] + [
    "nl_euro", "nl_euro_heel", "nl_date", "nl_pct",
]
