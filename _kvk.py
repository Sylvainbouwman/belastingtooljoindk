"""Uitlezen van het KvK-basisprofiel.

Bewust vrij van Streamlit-afhankelijkheden, zodat de veldextractie los testbaar is
(zie tests/test_kvk.py).

Kosten, nagelopen op developers.kvk.nl/nl/pricing (18-08-2026):
  abonnement        EUR 6,40 per maand per API-sleutel
  Zoeken            gratis
  Basisprofiel      EUR 0,02 per bevraging
  Vestigingsprofiel EUR 0,02 per bevraging
  Naamgeving        EUR 0,02 per bevraging

Alles wat deze module uitleest komt uit het Basisprofiel, dus uit één bevraging.
Meer velden tonen kost dus niets extra; de tool haalde dat antwoord al op en
gebruikte er alleen sbiActiviteiten uit. De veldnamen hieronder zijn op
18-08-2026 gecontroleerd tegen een echt antwoord van de API.

LET OP: het RSIN zit NIET in het basisprofiel, ook niet bij een BV. Dat is op
18-08-2026 nagegaan op het profiel van een BV. Het RSIN komt alleen mee in het
antwoord van de Zoeken-API, en ook daar niet altijd. Ontbreekt het, dan betekent
dat dus niet dat het bedrijf geen RSIN heeft - alleen dat de KvK het niet
meestuurde. De pagina zegt daarom "RSIN niet meegeleverd" en niet "geen RSIN".
"""

HOOFDACTIVITEIT = "Ja"


def kvk_datum(waarde) -> str | None:
    """Zet een KvK-datum (JJJJMMDD) om naar Nederlandse notatie."""
    tekst = str(waarde or "")
    if len(tekst) != 8 or not tekst.isdigit():
        return None
    return f"{tekst[6:8]}-{tekst[4:6]}-{tekst[:4]}"


def _tak(profiel: dict | None, naam: str) -> dict:
    """Een tak onder _embedded, of een leeg dict. De KvK laat takken weg in
    plaats van ze leeg terug te geven, dus dit moet defensief."""
    embedded = (profiel or {}).get("_embedded") or {}
    return embedded.get(naam) or {}


def rechtsvorm(profiel: dict | None) -> str | None:
    """Rechtsvorm van de eigenaar; de uitgebreide vorm heeft de voorkeur omdat
    die onderscheid maakt tussen bijvoorbeeld een gewone en een flex-BV."""
    eigenaar = _tak(profiel, "eigenaar")
    return eigenaar.get("uitgebreideRechtsvorm") or eigenaar.get("rechtsvorm") or None


def handelsnamen(profiel: dict | None) -> list[str]:
    """Alle handelsnamen, in de volgorde die de KvK aangeeft."""
    namen = (profiel or {}).get("handelsnamen") or []
    gesorteerd = sorted(namen, key=lambda n: n.get("volgorde", 0))
    return [n["naam"] for n in gesorteerd if n.get("naam")]


def adres(profiel: dict | None) -> str | None:
    """Volledig bezoekadres van de hoofdvestiging.

    Bij een eenmanszaak op een woonadres schermt de KvK het adres af. Dan komt er
    geen adres terug maar de melding dat het afgeschermd is; dat hoort ook zo te
    blijven en wordt hier niet omzeild.
    """
    adressen = _tak(profiel, "hoofdvestiging").get("adressen") or []
    if not adressen:
        return None
    bezoek = next((a for a in adressen if a.get("type") == "bezoekadres"), adressen[0])
    if bezoek.get("indAfgeschermd") == "Ja":
        return "Afgeschermd op verzoek"
    volledig = bezoek.get("volledigAdres")
    if volledig:
        return volledig
    onderdelen = [bezoek.get("straatnaam"), str(bezoek.get("huisnummer") or ""),
                  bezoek.get("postcode"), bezoek.get("plaats")]
    samen = " ".join(o for o in onderdelen if o).strip()
    return samen or None


def websites(profiel: dict | None) -> list[str]:
    return list(_tak(profiel, "hoofdvestiging").get("websites") or [])


def werkzame_personen(profiel: dict | None) -> int | None:
    aantal = (profiel or {}).get("totaalWerkzamePersonen")
    if aantal is None:
        aantal = _tak(profiel, "hoofdvestiging").get("totaalWerkzamePersonen")
    try:
        return int(aantal)
    except (TypeError, ValueError):
        return None


def sbi_gesplitst(profiel: dict | None) -> tuple[list, list]:
    """(hoofdactiviteiten, nevenactiviteiten)."""
    codes = (profiel or {}).get("sbiActiviteiten") or []
    hoofd = [c for c in codes if c.get("indHoofdactiviteit") == HOOFDACTIVITEIT]
    neven = [c for c in codes if c.get("indHoofdactiviteit") != HOOFDACTIVITEIT]
    return hoofd, neven


def groepeer_resultaten(resultaten: list | None) -> list[dict]:
    """Eén regel per bedrijf in de zoekresultaten.

    De Zoeken-API geeft per bedrijf meerdere records: een `rechtspersoon` zonder
    adres, een `hoofdvestiging` met adres, en bij meer locaties ook
    `nevenvestiging`-records. Voor Onesti B.V. leverde dat twee ogenschijnlijk
    identieke regels op, waarvan één zonder plaatsnaam.

    Meer dan één regel per KvK-nummer voegt niets toe, want het basisprofiel hangt
    aan het KvK-nummer en niet aan de vestiging. Van elk nummer blijft daarom het
    record met de meeste bruikbare gegevens over - de hoofdvestiging, want die
    heeft een adres en een vestigingsnummer. De volgorde van de KvK blijft
    behouden, en het aantal vestigingsrecords komt als extra veld mee zodat de
    pagina kan melden dat een bedrijf meerdere locaties heeft.

    Een record zonder KvK-nummer wordt niet weggegooid maar apart gehouden; beter
    een regel te veel dan een treffer die stil verdwijnt.
    """
    groepen: dict = {}
    for index, record in enumerate(resultaten or []):
        sleutel = record.get("kvkNummer") or f"__zonder_nummer_{index}"
        groepen.setdefault(sleutel, []).append(record)

    gegroepeerd = []
    for records in groepen.values():
        beste = max(records, key=_bruikbaarheid)
        vestigingen = sum(1 for r in records if r.get("type") in
                          ("hoofdvestiging", "nevenvestiging"))
        gegroepeerd.append({**beste, "vestigingen_in_resultaat": vestigingen})
    return gegroepeerd


def _bruikbaarheid(record: dict) -> tuple:
    """Hoe geschikt een record is om als regel te tonen. Hoger is beter."""
    return (
        2 if record.get("type") == "hoofdvestiging" else 0,
        1 if record.get("adres") else 0,
        1 if record.get("vestigingsnummer") else 0,
    )


def regel_sleutel(record: dict, index: int) -> str:
    """Unieke sleutel voor de widgets bij een zoekresultaat.

    Streamlit weigert twee widgets met dezelfde sleutel en laat dan de hele pagina
    omvallen met StreamlitDuplicateElementKey. Dat gebeurde bij een zoekopdracht
    waarvan twee resultaten hetzelfde KvK-nummer hadden - de Zoeken-API geeft per
    bedrijf immers een rechtspersoon en een hoofdvestiging terug. Het KvK-nummer
    alleen is dus geen veilige sleutel, ook niet na het groeperen: een record
    zonder nummer zou opnieuw botsen. De index erbij maakt hem altijd uniek.
    """
    return f"{index}-{record.get('kvkNummer') or 'zonder-nummer'}"


def profiel_kort(profiel: dict | None) -> dict:
    """De velden die de pagina toont, allemaal uit dezelfde ene bevraging.

    Velden die de KvK niet meestuurt komen er als None of lege lijst uit, zodat de
    pagina ze kan overslaan in plaats van "None" te tonen.
    """
    namen = handelsnamen(profiel)
    return {
        "naam": (profiel or {}).get("naam"),
        "statutaire_naam": (profiel or {}).get("statutaireNaam"),
        "handelsnamen": namen,
        "rechtsvorm": rechtsvorm(profiel),
        "geregistreerd": kvk_datum((profiel or {}).get("formeleRegistratiedatum")),
        "werkzame_personen": werkzame_personen(profiel),
        "adres": adres(profiel),
        "websites": websites(profiel),
        "vestigingsnummer": _tak(profiel, "hoofdvestiging").get("vestigingsnummer"),
        "non_mailing": (profiel or {}).get("indNonMailing") == "Ja",
    }
