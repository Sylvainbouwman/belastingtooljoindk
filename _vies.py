"""BTW-nummerlogica voor de VIES-controle van de Europese Commissie.

Bewust vrij van Streamlit-afhankelijkheden (zie tests/test_vies.py).

De VIES-API antwoordt ALTIJD met HTTP 200, ook als een lidstaat onbereikbaar is
of het verzoek geblokkeerd wordt. In die gevallen staat isValid op false en
bevat userError de reden. Wie alleen naar isValid kijkt, presenteert een storing
bij de Duitse belastingdienst als "dit nummer bestaat niet" - een verschil dat
er bij de beoordeling van het 0%-tarief bij intracommunautaire leveringen toe doet.
"""

import re

EU_LANDEN = [
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR",
    "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO",
    "SE", "SI", "SK", "XI",
]

LAND_NAAM = {
    "AT": "Oostenrijk", "BE": "België", "BG": "Bulgarije", "CY": "Cyprus",
    "CZ": "Tsjechië", "DE": "Duitsland", "DK": "Denemarken", "EE": "Estland",
    "EL": "Griekenland", "ES": "Spanje", "FI": "Finland", "FR": "Frankrijk",
    "HR": "Kroatië", "HU": "Hongarije", "IE": "Ierland", "IT": "Italië",
    "LT": "Litouwen", "LU": "Luxemburg", "LV": "Letland", "MT": "Malta",
    "NL": "Nederland", "PL": "Polen", "PT": "Portugal", "RO": "Roemenië",
    "SE": "Zweden", "SI": "Slovenië", "SK": "Slowakije", "XI": "Noord-Ierland",
}

# Landcodes die mensen intypen maar die VIES anders noemt.
LAND_ALIAS = {"GR": "EL", "UK": "XI", "GB": "XI"}

# userError-waarden die op een storing wijzen in plaats van op een ongeldig
# nummer. Bron: technische documentatie VIES REST API.
DIENSTFOUTEN = {
    "SERVICE_UNAVAILABLE": "De VIES-dienst is tijdelijk niet beschikbaar.",
    "MS_UNAVAILABLE": "De belastingdienst van het opgegeven land is tijdelijk onbereikbaar.",
    "MS_MAX_CONCURRENT_REQ": "De belastingdienst van dat land verwerkt te veel verzoeken tegelijk.",
    "GLOBAL_MAX_CONCURRENT_REQ": "VIES verwerkt te veel verzoeken tegelijk.",
    "TIMEOUT": "De belastingdienst van dat land reageerde niet op tijd.",
    "VAT_BLOCKED": "Dit verzoek is door VIES geblokkeerd.",
    "IP_BLOCKED": "Dit IP-adres is door VIES geblokkeerd.",
    "INVALID_REQUESTER_INFO": "VIES weigerde de gegevens van de aanvrager.",
    "INVALID_INPUT": "VIES accepteerde het opgegeven nummer niet als invoer.",
}

# Na de landcode laat VIES alleen letters en cijfers toe, maximaal 12 tekens.
_NUMMER = re.compile(r"^[0-9A-Z]{2,12}$")

VIES_URL = "https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{land}/vat/{nummer}"


def parse_btw(raw: str) -> tuple[str | None, str | None]:
    """Splitst een BTW-nummer in (landcode, nummer), of (None, None).

    Alleen letters en cijfers blijven over. Dat is niet alleen opschonen: zonder
    die controle belandden tekens als < > = / ongefilterd in zowel de opgevraagde
    URL als de HTML van de resultaatpagina.
    """
    opgeschoond = re.sub(r"[^0-9A-Za-z]", "", raw or "").upper()
    if len(opgeschoond) < 3:
        return None, None

    land = LAND_ALIAS.get(opgeschoond[:2], opgeschoond[:2])
    if land not in EU_LANDEN:
        return None, None

    nummer = opgeschoond[2:]
    if not _NUMMER.match(nummer):
        return None, None
    return land, nummer


def duid_antwoord(data: dict) -> dict:
    """Vertaalt een VIES-antwoord naar {status, naam, adres, melding}.

    status is 'geldig', 'ongeldig' of 'storing'.
    """
    fout = (data.get("userError") or "").upper()
    if fout in DIENSTFOUTEN:
        return {"status": "storing", "naam": None, "adres": None,
                "melding": DIENSTFOUTEN[fout]}

    if not data.get("isValid", False):
        return {"status": "ongeldig", "naam": None, "adres": None, "melding": None}

    return {
        "status": "geldig",
        "naam": _leesbaar(data.get("name")),
        "adres": _leesbaar(data.get("address")),
        "melding": None,
    }


def _leesbaar(waarde) -> str | None:
    """VIES gebruikt '---' voor 'niet verstrekt'."""
    tekst = (waarde or "").strip()
    return None if tekst in ("", "---") else tekst


def adres_regels(adres: str | None) -> list[str]:
    if not adres:
        return []
    return [regel.strip() for regel in adres.splitlines() if regel.strip()]


def rsin_uit_btw_nummer(land: str, nummer: str) -> str | None:
    """Het Nederlandse BTW-nummer bevat het RSIN: 9 cijfers gevolgd door Bxx."""
    if land != "NL":
        return None
    match = re.match(r"^(\d{9})B\d{2}$", nummer)
    return match.group(1) if match else None
