"""Nederlandse notatie voor bedragen, datums en percentages.

Bewust vrij van Streamlit-afhankelijkheden: zowel de rekenmodules als de
pagina's gebruiken deze functies, en de tests moeten ze los kunnen aanroepen.
Stond eerder in _rente.py en nog een keer in pages/Auto_BTW_Prive.py.
"""

from datetime import date


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
