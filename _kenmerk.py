"""Decodeerlogica voor het 16-cijferige betalingskenmerk van de Belastingdienst.

Bewust vrij van Streamlit-afhankelijkheden, zodat deze functies los testbaar zijn
(zie tests/test_kenmerk.py).
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

# LET OP — onopgelost conflict, bewust ongewijzigd gelaten.
# De VpB-tak in decode_kenmerk() vangt middelcode 80 t/m 96 af en staat vóór de
# opzoeking in deze tabel. Daardoor zijn de entries 85, 86, 87 en 88 hieronder
# in de praktijk onbereikbaar: een kenmerk met middelcode 87 wordt nu als
# Vennootschapsbelasting getoond, niet als MOA vrachtwagens.
# Eén van beide klopt niet. Fiscaal uit te zoeken:
#   - klopt deze tabel, dan moet de VpB-range naar 80 t/m 84;
#   - klopt de VpB-range, dan moeten de vier entries hieronder weg.
# Tot die vraag beantwoord is blijft het gedrag zoals het was.
MIDDEL2_LABEL = {
    70: {"kort": "IB",  "lang": "Inkomstenbelasting"},
    71: {"kort": "IH",  "lang": "Conserverende aanslag IH"},
    73: {"kort": "IB",  "lang": "Inkomstenbelasting (gemoedsbezwaarde)"},
    74: {"kort": "VpB", "lang": "Vennootschapsbelasting"},
    75: {"kort": "ZVW", "lang": "Zorgverzekeringswet"},
    76: {"kort": "HSB", "lang": "Motorrijtuigenbelasting (naheffing)"},
    78: {"kort": "HSB", "lang": "Motorrijtuigenbelasting"},
    85: {"kort": "EVN", "lang": "Eurovignet"},                                  # onbereikbaar, zie boven
    86: {"kort": "EVN", "lang": "Eurovignet (naheffing)"},                      # onbereikbaar, zie boven
    87: {"kort": "MOA", "lang": "Motorrijtuigenbelasting vrachtwagens (aangifte)"},   # onbereikbaar, zie boven
    88: {"kort": "MOA", "lang": "Motorrijtuigenbelasting vrachtwagens (naheffing)"},  # onbereikbaar, zie boven
    97: {"kort": "LIR", "lang": "Landinrichtingsrente / Verontreinigingsheffing"},
    23: {"kort": "KOT", "lang": "Kinderopvangtoeslag"},
    24: {"kort": "HT",  "lang": "Huurtoeslag"},
    25: {"kort": "ZT",  "lang": "Zorgtoeslag"},
    26: {"kort": "KGB", "lang": "Kindgebonden budget"},
    27: {"kort": "VB",  "lang": "Verzuimboete Toeslagen"},
    28: {"kort": "VGB", "lang": "Vergrijpboete Toeslagen"},
}


def rsin_check_digit(d8: str) -> int:
    weights = [9, 8, 7, 6, 5, 4, 3, 2]
    return sum(int(c) * w for c, w in zip(d8, weights)) % 11


def reconstruct_year(digit: int) -> int:
    current_last = date.today().year % 10
    base = 2020 if digit <= current_last else 2010
    return base + digit


def decode_tijdvak(code: str) -> str:
    n = int(code)
    if n == 0:
        return "Jaaraangifte"
    if 1 <= n <= 12:
        return MAANDEN[n - 1]
    mapping = {21: "1e kwartaal", 24: "2e kwartaal", 27: "3e kwartaal", 30: "4e kwartaal"}
    return mapping.get(n, f"tijdvak {code}")


def format_rsin(rsin9: str) -> str:
    return f"{rsin9[:4]}.{rsin9[4:6]}.{rsin9[6:]}"


def decode_kenmerk(raw: str):
    """Returns (result_dict, error_str). One of them is None."""
    raw = raw.replace(" ", "")
    if not raw.isdigit() or len(raw) != 16:
        return None, "Voer een geldig 16-cijferig betalingskenmerk in."

    p = lambda i: int(raw[i - 1])
    s = lambda f, t: raw[f - 1:t]

    middel10 = p(10)

    if middel10 in (0, 1, 5, 6):
        rsin8 = s(2, 9)
        rsin9 = rsin8 + str(rsin_check_digit(rsin8))
        m = MIDDEL_LABEL[middel10]
        return {
            "soort": m["lang"], "soort_sub": m["sub"], "kort": m["kort"],
            "jaar": reconstruct_year(p(11)),
            "tijdvak": decode_tijdvak(s(14, 15)),
            "rsin": format_rsin(rsin9), "rsin9": rsin9,
            "digit_active": [False,False,False,False,False,False,False,False,False,True,True,False,False,True,True,False],
        }, None

    middel2 = int(s(10, 11))

    if middel2 == 74 or (80 <= middel2 <= 96):
        rsin6 = s(2, 7)
        if middel2 == 74:
            prefix = "00"
        elif middel2 <= 84:
            prefix = str(middel2)
        else:
            prefix = str(middel2 - 7)
        rsin8 = prefix + rsin6
        rsin9 = rsin8 + str(rsin_check_digit(rsin8))
        return {
            "soort": "Vennootschapsbelasting", "soort_sub": "", "kort": "VpB",
            "jaar": reconstruct_year(p(8)),
            "tijdvak": f"Boekjaar {s(12, 15)}",
            "rsin": format_rsin(rsin9), "rsin9": rsin9,
            "digit_active": [False,True,True,True,True,True,True,True,False,True,True,False,False,False,False,False],
        }, None

    if middel2 in MIDDEL2_LABEL:
        rsin8 = s(2, 9)
        rsin9 = rsin8 + str(rsin_check_digit(rsin8))
        m = MIDDEL2_LABEL[middel2]
        return {
            "soort": m["lang"], "soort_sub": "", "kort": m["kort"],
            "jaar": reconstruct_year(p(12)),
            "tijdvak": "—",
            "rsin": format_rsin(rsin9), "rsin9": rsin9,
            "digit_active": [False,True,True,True,True,True,True,True,True,True,True,True,False,False,False,False],
        }, None

    return None, f"Onbekend middelcode ({middel2}). Mogelijk een bijzonder kenmerk dat niet algoritmisch te decoderen is."


def build_omschrijving(r: dict) -> str:
    prefix = "Naheff." if r["soort_sub"] == "Naheffingsaanslag" else "Afdr."
    tv = r["tijdvak"].capitalize()
    return f"{prefix} {r['kort']} {tv} {r['jaar']}"
