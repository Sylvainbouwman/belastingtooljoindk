"""Invorderingsrente volgens hoofdstuk V van de Invorderingswet 1990.

Bewust vrij van Streamlit-afhankelijkheden, net als `_rente.py`. Deze module
rekent de invorderingsrente van artikel 28 (in rekening brengen), artikel 28a en
artikel 28b (vergoeden). Artikel 28c wordt niet gerekend maar alleen
gesignaleerd; zie ART28C_SIGNALERING onderaan.

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
# art. 25. Op verzoek van Sylvain wordt die opschorting in deze versie NIET
# gerekend: de tool vraagt uit of er uitstel is verleend en op welke grond, en
# geeft geen uitkomst zolang dat niet is ingevuld. Zie het blokkeerpad in
# pages/Invorderingsrente.py.
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
# tijdvak daarvoor staat in art. 6 Uitvoeringsbesluit IW 1990. Ook dat wordt
# hier niet gerekend, maar wel getoond, zodat zichtbaar is wat er dan geldt.
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
# dagen uit waarover op grond van art. 28b invorderingsrente wordt vergoed —
# maar art. 28c wordt door deze tool niet gerekend.
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
    "28c": True,    # art. 28c lid 2, tweede volzin IW 1990 — niet gerekend
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
    maand = d.month + maanden
    jaar = d.year + (maand - 1) // 12
    maand = (maand - 1) % 12 + 1
    return date(jaar, maand, min(d.day, calendar.monthrange(jaar, maand)[1]))


def invorderbaar_op(dagtekening: date, aanslag_type: str = "regulier") -> date:
    """De dag waarop de belastingaanslag invorderbaar is, art. 9 IW 1990.

    Dit is tevens de dag waarop de enige of laatste betalingstermijn vervalt,
    en dus de dag die de vervalmaand van art. 31 URIW 1990 bepaalt.

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


def periode_art28(vervaldag: date, betaaldatum: date) -> tuple[date, date] | None:
    """Tijdvak van art. 28 lid 2: van de invorderbaarheid tot de dag vóór de betaling.

    Geeft None als er niets te rekenen valt omdat op of vóór de vervaldag is
    betaald; art. 28 lid 1 vraagt immers overschrijding van de enige of laatste
    betalingstermijn.
    """
    if betaaldatum <= vervaldag:
        return None
    return vervaldag, betaaldatum - timedelta(days=1)


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

    Vangt aan de dag ná de dag waarop de aanslag invorderbaar is en eindigt zes
    weken na de dagtekening van de vermindering of herziening. Anders dan bij
    art. 28 en 28a loopt het tijdvak dus door tot een datum die uit de
    vermindering volgt en niet tot de dag vóór een betaling.
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


# ── Artikel 28c: alleen signaleren ──────────────────────────────────────────
ART28C_SIGNALERING = (
    "Is de belasting geheven in strijd met het Unierecht en geeft de ontvanger "
    "terug op grond van een beschikking van de inspecteur, dan bestaat er op "
    "grond van art. 28c IW 1990 recht op een vergoeding van invorderingsrente "
    "over het tijdvak van de dag na de betaling tot de dag vóór de terugbetaling. "
    "Die vergoeding wordt alleen op verzoek gegeven, en de termijn voor dat "
    "verzoek eindigt zes weken na de dagtekening van die beschikking "
    "(art. 28c lid 3). Deze tool rekent die grondslag niet uit."
)

__all__ = [name for name in dir() if not name.startswith("_")] + [
    "nl_euro", "nl_euro_heel", "nl_date", "nl_pct",
]
