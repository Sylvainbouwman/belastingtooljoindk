"""Decodeerlogica voor het 16-cijferige betalingskenmerk van de Belastingdienst.

Bewust vrij van Streamlit-afhankelijkheden, zodat deze functies los testbaar zijn
(zie tests/test_kenmerk.py).

Bron: Specificatie Betalingskenmerk_bepaling v1.5 (Belastingdienst, 20-04-2023).
Alle 27 voorbeelden uit die specificatie zijn als regressietest vastgelegd.
"""

from datetime import date

MAANDEN = [
    "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]

MIDDEL_LABEL = {
    0: {"kort": "LH",  "lang": "Loonheffing",    "sub": "Naheffingsaanslag"},
    1: {"kort": "OB",  "lang": "Omzetbelasting",  "sub": "Aangifte"},
    5: {"kort": "OB",  "lang": "Omzetbelasting",  "sub": "Naheffingsaanslag"},
    6: {"kort": "LH",  "lang": "Loonheffing",     "sub": "Aangifte"},
}

# Middelcodes die een toeslag zijn in plaats van een belastingaanslag. Bepaalt
# de formulering van de boekhoudomschrijving (zie build_omschrijving).
TOESLAG_CODES = {23, 24, 25, 26, 27, 28}

# Middelcodes op positie 10-11, conform de paragrafen 3 t/m 17 van de
# specificatie. De VpB-codes staan hier niet in; die hebben een eigen indeling
# (zie VPB_MIDDELCODES).
MIDDEL2_LABEL = {
    70: {"kort": "IB",  "lang": "Inkomstenbelasting"},                           # par. 4, A-MIDDEL H
    71: {"kort": "IH",  "lang": "Conserverende aanslag IH"},                      # par. 3, A-MIDDEL P
    73: {"kort": "IB",  "lang": "Inkomstenbelasting (gemoedsbezwaarde)"},         # par. 4, A-MIDDEL N
    75: {"kort": "ZVW", "lang": "Zorgverzekeringswet"},                           # par. 4, A-MIDDEL W
    76: {"kort": "HSB", "lang": "Motorrijtuigenbelasting (naheffing)"},           # par. 8
    78: {"kort": "HSB", "lang": "Motorrijtuigenbelasting"},                       # par. 6
    85: {"kort": "EVN", "lang": "Eurovignet"},                                    # par. 10
    86: {"kort": "EVN", "lang": "Eurovignet (naheffing)"},                        # par. 11
    87: {"kort": "MOA", "lang": "Motorrijtuigenbelasting vrachtwagens (aangifte)"},     # par. 5
    88: {"kort": "MOA", "lang": "Motorrijtuigenbelasting vrachtwagens (naheffing)"},    # par. 7
    97: {"kort": "LIR", "lang": "Landinrichtingsrente / Verontreinigingsheffing"},      # par. 9
    23: {"kort": "KOT", "lang": "Kinderopvangtoeslag"},                           # par. 12
    24: {"kort": "HT",  "lang": "Huurtoeslag"},                                   # par. 13
    25: {"kort": "ZT",  "lang": "Zorgtoeslag"},                                   # par. 14
    26: {"kort": "KGB", "lang": "Kindgebonden budget"},                           # par. 15
    27: {"kort": "VB",  "lang": "Verzuimboete Toeslagen"},                        # par. 16
    28: {"kort": "VGB", "lang": "Vergrijpboete Toeslagen"},                       # par. 17
}

# Middelcode 97 dekt twee heffingen. Welke van de twee staat op positie 16
# (A-MIDHERK): 1 = Landinrichtingsrente, 2 = Verontreinigingsheffing
# Rijkswateren. Beide voorbeelden in paragraaf 9 bevestigen dit.
MIDHERK_97 = {
    1: {"kort": "LIR", "lang": "Landinrichtingsrente"},
    2: {"kort": "VHR", "lang": "Verontreinigingsheffing Rijkswateren"},
}

# Vennootschapsbelasting, paragraaf 2. B-MIDDEL is afgeleid van de eerste twee
# posities van het RSIN: 00 wordt 74, 80 t/m 84 blijven staan, en 85 t/m 89
# worden 92 t/m 96. De codes 85 t/m 91 zijn dus GEEN VpB — 85 t/m 88 zijn
# Eurovignet en MOA (paragrafen 5, 7, 10 en 11) en 89 t/m 91 bestaan niet.
VPB_MIDDELCODES = frozenset({74}) | frozenset(range(80, 85)) | frozenset(range(92, 97))

# SOORT-cijfer uit het aanslagnummer (JAVO positie 3). De specificatie geeft geen
# codetabel; deze twee waarden komen uit de voorbeelden zelf: soort 0 staat bij
# "Voorlopige aanslag" (paragraaf 2 VpB en paragraaf 4 IB/ZVW) en soort 6 bij
# "Definitieve aanslag" (paragraaf 2). Overige waarden worden bewust niet
# gelabeld: dan is onbekend wat er staat, en een gok levert een stille fout op.
SOORT_LABEL = {0: "Voorlopige aanslag", 6: "Definitieve aanslag"}

# Middelcodes waarbij positie 13 het SOORT-cijfer is. Bij HSB, MOA en Eurovignet
# is positie 13 het begin van het volgnummer, niet het soort; bij toeslagen staat
# er wel een SOORT-cijfer, maar wat de waarden daar betekenen is niet vastgelegd.
SOORT_OP_POSITIE_13 = {70, 71, 73, 75}

# Middelcodes die per definitie een naheffingsaanslag zijn (paragrafen 8, 7 en 11).
NAHEFFING_CODES = {76, 88, 86}

# Middelcodes die per definitie over een natuurlijk persoon gaan: het nummer in
# het kenmerk is dan een BSN en geen RSIN. Inkomstenbelasting, de conserverende
# aanslag, de Zorgverzekeringswet en de toeslagen worden alleen aan personen
# opgelegd. Bij loonheffing, omzetbelasting, houderschapsbelasting, MOA,
# Eurovignet en middelcode 97 kan het beide zijn: een eenmanszaak draagt
# omzetbelasting af onder een nummer dat op het BSN is gebaseerd.
BSN_CODES = {70, 71, 73, 75} | TOESLAG_CODES

# Een RSIN begint altijd met 00 of met 80 t/m 89. Dat staat in paragraaf 2 van de
# specificatie: "NB: RSIN-s beginnen altijd met 00, of 80 t/m 89". Buiten die
# reeksen is het nummer dus geen RSIN, en heeft een opzoeking bij de KvK ook geen
# zin - die kent alleen ingeschreven organisaties.
RSIN_BEGIN = ("00",) + tuple(str(n) for n in range(80, 90))

# Weging voor het controlecijfer op positie 1, van rechts naar links toegepast
# over de posities 2 t/m 16. Zie controlecijfer() voor de verantwoording.
CONTROLE_WEGING = (2, 4, 8, 5, 10, 9, 7, 3, 6, 1)


def controlecijfer(posities_2_tot_16: str) -> int:
    """Het controlecijfer dat op positie 1 van het betalingskenmerk hoort.

    De specificatie zegt hierover alleen "berekenen m.b.v. modulus-11 algoritme,
    zie onderaan", maar onderaan staat uitsluitend de elfproef voor het BSN/RSIN
    en niet die voor het kenmerk zelf. Onderstaande regel is daarom afgeleid uit
    de voorbeelden en daarna geverifieerd: hij klopt op alle 27 voorbeelden in de
    specificatie en op het extern gevalideerde kenmerk uit de README, dus 28 van
    28. Het is de gangbare acceptgiro-elfproef.

    Weeg van rechts naar links met 2, 4, 8, 5, 10, 9, 7, 3, 6, 1 (herhalend),
    tel op en neem 11 min de rest bij deling door 11. Een uitkomst 11 wordt 0 en
    een uitkomst 10 wordt 1; dat laatste is in drie voorbeelden bevestigd.
    """
    som = sum(int(d) * CONTROLE_WEGING[i % len(CONTROLE_WEGING)]
              for i, d in enumerate(reversed(posities_2_tot_16)))
    c = 11 - som % 11
    if c == 11:
        return 0
    if c == 10:
        return 1
    return c


def controlecijfer_klopt(raw16: str) -> bool:
    """Of positie 1 past bij de overige vijftien posities."""
    return int(raw16[0]) == controlecijfer(raw16[1:])


def rsin_check_digit(d8: str) -> int:
    """Restwaarde van de elfproef over de eerste 8 cijfers.

    Let op: de uitkomst kan 10 zijn. Dat is géén controlecijfer maar het bewijs
    dat er bij deze 8 cijfers geen geldig BSN/RSIN bestaat. Gebruik rsin_uit()
    in plaats van deze functie rechtstreeks.
    """
    weights = [9, 8, 7, 6, 5, 4, 3, 2]
    return sum(int(c) * w for c, w in zip(d8, weights)) % 11


def rsin_uit(d8: str) -> str | None:
    """Vult de 8 cijfers aan tot een 9-cijferig BSN/RSIN, of None als dat niet kan.

    Bij restwaarde 10 bestaat er geen geldig negende cijfer. Dat gebeurt bij
    ongeveer één op de elf invoeren en betekent in de praktijk dat het kenmerk
    verkeerd is overgenomen.
    """
    rest = rsin_check_digit(d8)
    return None if rest == 10 else d8 + str(rest)


def reconstruct_year(digit: int, vandaag: date | None = None) -> int:
    """Reconstrueert het viercijferige jaar uit één jaarcijfer in het kenmerk.

    Het kenmerk bevat maar één cijfer, dus het decennium moet geraden worden.
    Het venster loopt van negen jaar terug tot en met vólgend jaar: voorlopige
    aanslagen worden in het najaar al voor het komende jaar verstuurd, en die
    kwamen voorheen tien jaar te vroeg uit (cijfer 7 werd in 2026 gelezen als
    2017 in plaats van 2027).
    """
    vandaag = vandaag or date.today()
    bovengrens = vandaag.year + 1
    ondergrens = bovengrens - 9          # venster van precies 10 jaar
    decennium = (vandaag.year // 10) * 10
    for basis in (decennium - 10, decennium, decennium + 10):
        jaar = basis + digit
        if ondergrens <= jaar <= bovengrens:
            return jaar
    raise AssertionError(f"geen jaar in venster voor cijfer {digit}")  # onbereikbaar


def decode_tijdvak(code: str) -> str:
    n = int(code)
    if n == 0:
        return "Jaaraangifte"
    if 1 <= n <= 12:
        return MAANDEN[n - 1]
    mapping = {21: "1e kwartaal", 24: "2e kwartaal", 27: "3e kwartaal", 30: "4e kwartaal"}
    return mapping.get(n, f"tijdvak {code}")


def decode_boekjaar(tydvak4: str) -> str:
    """Leest B-TYDVAK (positie 12 t/m 15) als beginmaand plus eindmaand.

    In het voorbeeld van paragraaf 2 staat 0112 bij een boekjaar 2022, dus 01
    t/m 12. Staat er iets anders dan twee geldige maandnummers, dan wordt de ruwe
    code getoond in plaats van een verzonnen periode.
    """
    begin, eind = tydvak4[:2], tydvak4[2:]
    if begin.isdigit() and eind.isdigit() and 1 <= int(begin) <= 12 and 1 <= int(eind) <= 12:
        return f"{MAANDEN[int(begin) - 1]} t/m {MAANDEN[int(eind) - 1]}"
    return tydvak4


def is_mogelijk_rsin(nummer9: str | None) -> bool:
    """Of dit nummer een RSIN kan zijn, op grond van de beginposities."""
    return bool(nummer9) and nummer9.startswith(RSIN_BEGIN)


def mag_naar_kvk(resultaat: dict | None) -> bool:
    """Of het nummer uit dit kenmerk bij de KvK mag worden opgezocht.

    Een BSN gaat er niet heen. Dat is een privacykeuze en tegelijk een praktische:
    de KvK kent geen particulieren, dus zo'n opzoeking levert toch niets op. Er
    zijn twee gronden om het nummer niet te versturen:

      1. het middel wordt alleen aan natuurlijke personen opgelegd (BSN_CODES);
      2. het nummer begint niet met 00 of 80 t/m 89 en is dus geen RSIN.

    Bij vennootschapsbelasting is het altijd een RSIN - de specificatie zegt in
    paragraaf 2 uitdrukkelijk dat een VpB-aanslagnummer nooit een BSN bevat.
    """
    if not resultaat or not resultaat.get("rsin9"):
        return False
    if resultaat.get("nummer_soort") == "bsn":
        return False
    if resultaat.get("nummer_soort") == "rsin":
        return True
    return is_mogelijk_rsin(resultaat["rsin9"])


def nummer_label(resultaat: dict) -> str:
    """Wat er boven het nummer komt te staan, zodat een medewerker ziet wat het is."""
    soort = resultaat.get("nummer_soort")
    if soort == "bsn":
        return "BSN (natuurlijk persoon)"
    if soort == "rsin":
        return "RSIN"
    return "RSIN" if is_mogelijk_rsin(resultaat.get("rsin9")) else "BSN (natuurlijk persoon)"


def actieve_posities(*posities: int) -> list[bool]:
    """Vlaggenlijst voor de positieweergave: True op elke gedecodeerde positie.

    De weergave onder "Positieweergave" belooft dat de donkere cijfers de
    gedecodeerde velden zijn. Deze functie houdt die belofte na, in plaats van
    per tak een handgeschreven lijst van zestien booleans.
    """
    gevraagd = set(posities)
    return [i in gevraagd for i in range(1, 17)]


def format_rsin(rsin9: str | None) -> str | None:
    if rsin9 is None:
        return None
    return f"{rsin9[:4]}.{rsin9[4:6]}.{rsin9[6:]}"


def decode_kenmerk(raw: str, negeer_controlecijfer: bool = False):
    """Returns (result_dict, error_str). One of them is None."""
    raw = raw.replace(" ", "")
    if not raw.isdigit() or len(raw) != 16:
        return None, "Voer een geldig 16-cijferig betalingskenmerk in."

    if not negeer_controlecijfer and not controlecijfer_klopt(raw):
        return None, (
            f"Het controlecijfer klopt niet. Op positie 1 hoort een "
            f"{controlecijfer(raw[1:])} te staan en niet een {raw[0]}, dus er is "
            f"minstens één cijfer verkeerd overgenomen. Controleer het kenmerk — "
            f"anders volgt een verkeerd BSN/RSIN of een verkeerd tijdvak."
        )

    p = lambda i: int(raw[i - 1])
    s = lambda f, t: raw[f - 1:t]

    middel10 = p(10)

    if middel10 in (0, 1, 5, 6):
        rsin9 = rsin_uit(s(2, 9))
        m = MIDDEL_LABEL[middel10]
        return {
            "soort": m["lang"], "soort_sub": m["sub"], "kort": m["kort"],
            "categorie": "naheffing" if m["sub"] == "Naheffingsaanslag" else "aangifte",
            "nummer_soort": "onbekend",   # een eenmanszaak draagt af onder een BSN
            "jaar": reconstruct_year(p(11)),
            "tijdvak": decode_tijdvak(s(14, 15)),
            "rsin": format_rsin(rsin9), "rsin9": rsin9,
            # 2-9 BSN/RSIN, 10 middel, 11 jaar, 14-15 tijdvak (paragraaf 1)
            "digit_active": actieve_posities(*range(2, 10), 10, 11, 14, 15),
        }, None

    middel2 = int(s(10, 11))

    if middel2 in VPB_MIDDELCODES:
        rsin6 = s(2, 7)
        if middel2 == 74:
            prefix = "00"
        elif middel2 <= 84:
            prefix = str(middel2)
        else:
            prefix = str(middel2 - 7)          # 92 t/m 96 hoort bij RSIN 85 t/m 89
        rsin9 = rsin_uit(prefix + rsin6)
        boekjaar = s(12, 15)
        return {
            "soort": "Vennootschapsbelasting",
            "soort_sub": SOORT_LABEL.get(p(9), ""),
            "kort": "VpB",
            "categorie": "vpb",
            "nummer_soort": "rsin",       # paragraaf 2: nooit een BSN
            "jaar": reconstruct_year(p(8)),
            "tijdvak": f"Boekjaar {decode_boekjaar(boekjaar)}",
            "boekjaar": boekjaar,
            "rsin": format_rsin(rsin9), "rsin9": rsin9,
            # 2-7 RSIN, 8 jaar, 9 soort, 10-11 middel, 12-15 boekjaar (paragraaf 2)
            "digit_active": actieve_posities(*range(2, 8), 8, 9, 10, 11, *range(12, 16)),
        }, None

    if middel2 in MIDDEL2_LABEL:
        rsin9 = rsin_uit(s(2, 9))
        m = MIDDEL2_LABEL[middel2]
        if middel2 == 97:
            m = MIDHERK_97.get(p(16), m)       # onderscheid LIR / VHR staat op positie 16
        leest_soort = middel2 in SOORT_OP_POSITIE_13
        soort_sub = SOORT_LABEL.get(p(13), "") if leest_soort else ""
        # 2-9 BSN/RSIN, 10-11 middel, 12 jaar; daarbij positie 13 waar dat het
        # soortcijfer is en positie 16 bij middelcode 97 (LIR of VHR).
        posities = [*range(2, 10), 10, 11, 12]
        if leest_soort:
            posities.append(13)
        if middel2 == 97:
            posities.append(16)
        return {
            "soort": m["lang"], "soort_sub": soort_sub, "kort": m["kort"],
            "categorie": "toeslag" if middel2 in TOESLAG_CODES else "aanslag",
            "naheffing": middel2 in NAHEFFING_CODES,
            "nummer_soort": "bsn" if middel2 in BSN_CODES else "onbekend",
            "jaar": reconstruct_year(p(12)),
            "tijdvak": "—",
            "rsin": format_rsin(rsin9), "rsin9": rsin9,
            "digit_active": actieve_posities(*posities),
        }, None

    return None, f"Onbekend middelcode ({middel2}). Mogelijk een bijzonder kenmerk dat niet algoritmisch te decoderen is."


def build_omschrijving(r: dict) -> str:
    """Korte omschrijving voor in de boekhouding.

    De formulering hangt af van de soort heffing. Een aangifte loonheffing is
    een afdracht, een aanslag inkomstenbelasting niet; en bij VpB is het
    boekjaar de relevante periode, niet het jaarcijfer uit het kenmerk.
    """
    categorie = r.get("categorie", "aangifte")
    voorlopig = r.get("soort_sub") == "Voorlopige aanslag"

    if categorie == "vpb":
        aanhef = "Voorl. aanslag VpB" if voorlopig else "Aanslag VpB"
        return f"{aanhef} boekjaar {r['boekjaar']}"

    if categorie == "aanslag":
        if voorlopig:
            aanhef = "Voorl. aanslag"
        elif r.get("naheffing"):
            aanhef = "Naheff."
        else:
            aanhef = "Aanslag"
        return f"{aanhef} {r['kort']} {r['jaar']}"

    if categorie == "toeslag":
        return f"{r['soort']} {r['jaar']}"

    # Aangifte of naheffingsaanslag LH/OB: hier hoort het tijdvak wél bij.
    prefix = "Naheff." if categorie == "naheffing" else "Afdr."
    return f"{prefix} {r['kort']} {r['tijdvak'].capitalize()} {r['jaar']}"
