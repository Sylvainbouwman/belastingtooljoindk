"""Signaleert of belastingdienst.nl nieuwere belastingrentepercentages toont
dan de tabellen die in deze app hardgecodeerd staan.

De pagina bevat twee tabellen (algemeen en vennootschapsbelasting) met rijen als:

    <tr><th>Vanaf 1-1-2026</th>                    <td>5</td></tr>
    <tr><th>1-1-2025 tot en met 31-12-2025*</th>   <td>6,5</td></tr>

Er wordt bewust per rij geparsed in plaats van alle datums op de pagina te
verzamelen: de einddatums (31-12-2025) en losse datums elders op de pagina
leveren anders vals alarm op.
"""

import re
from datetime import date

import requests
import streamlit as st

BELASTINGDIENST_URL = (
    "https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/"
    "standaard_functies/prive/contact/rechten_en_plichten_bij_de_belastingdienst/"
    "belastingrente/overzicht_percentages_belastingrente"
)

KOP_ALGEMEEN = "Percentages alle belastingen"
KOP_VPB = "Percentages vennootschapsbelasting"

_RIJ = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_TH = re.compile(r"<th[^>]*>(.*?)</th>", re.S | re.I)
_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
_DATUM = re.compile(r"\b(\d{1,2})-(\d{1,2})-(\d{4})\b")
_PERCENTAGE = re.compile(r"(\d+(?:,\d+)?)")


def _tekst(html_fragment: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", html_fragment).split())


@st.cache_data(show_spinner=False)
def _haal_pagina_op(maand: str) -> str:
    """Haalt de tarievenpagina op, gecached per maand (maand = 'YYYY-MM').

    Gooit een exceptie bij een fout in plaats van None terug te geven, zodat
    Streamlit het mislukte antwoord níet cachet en de volgende paginaweergave
    het opnieuw probeert.
    """
    resp = requests.get(
        BELASTINGDIENST_URL,
        timeout=8,
        headers={"User-Agent": "Mozilla/5.0 (compatible; BouwmanTools)"},
    )
    resp.raise_for_status()
    return resp.text


def parse_tarieventabel(html: str, kop: str) -> list[tuple[date, float]]:
    """Leest één tabel van de pagina uit als [(ingangsdatum, percentage), ...].

    Geeft een lege lijst terug als de tabel niet herkend wordt; de aanroeper
    zwijgt dan liever dan dat hij onterecht waarschuwt.
    """
    start = html.find(kop)
    if start == -1:
        return []
    einde = html.find("</table>", start)
    if einde == -1:
        return []

    rijen = []
    for rij_html in _RIJ.findall(html[start:einde]):
        th = _TH.search(rij_html)
        td = _TD.search(rij_html)
        if not th or not td:
            continue  # kopregel van de tabel
        datum_match = _DATUM.search(_tekst(th.group(1)))
        pct_match = _PERCENTAGE.search(_tekst(td.group(1)))
        if not datum_match or not pct_match:
            continue
        dag, maand, jaar = (int(g) for g in datum_match.groups())
        try:
            ingang = date(jaar, maand, dag)
        except ValueError:
            continue
        rijen.append((ingang, float(pct_match.group(1).replace(",", "."))))
    return sorted(rijen, reverse=True)


def vergelijk(tarieven: list, online: list[tuple[date, float]]) -> str | None:
    """Vergelijkt de eigen tarieventabel met de online tabel."""
    if not online or not tarieven:
        return None

    eigen_datum, eigen_pct = tarieven[0]
    online_datum, _ = online[0]

    if online_datum > eigen_datum:
        return (
            f"Er staat een nieuwere periode op belastingdienst.nl "
            f"(ingang **{online_datum.strftime('%d-%m-%Y')}**) dan de nieuwste regel in "
            f"deze app (**{eigen_datum.strftime('%d-%m-%Y')}**). "
            f"[Controleer de percentages]({BELASTINGDIENST_URL}) en werk de "
            f"tarieventabel in de code bij."
        )

    for datum, pct in online:
        if datum == eigen_datum and abs(pct - eigen_pct) > 0.001:
            return (
                f"Het percentage vanaf **{eigen_datum.strftime('%d-%m-%Y')}** is op "
                f"belastingdienst.nl **{pct:g}%**, maar in deze app staat "
                f"**{eigen_pct:g}%**. Belastingrentepercentages worden met terugwerkende "
                f"kracht herzien. [Controleer de percentages]({BELASTINGDIENST_URL})."
            )
    return None


def controleer_nieuwe_tarieven(tarieven: list, kop: str = KOP_ALGEMEEN) -> str | None:
    """Waarschuwing als de online tabel afwijkt, of None als alles klopt of de
    pagina niet bereikbaar is."""
    try:
        html = _haal_pagina_op(date.today().strftime("%Y-%m"))
    except Exception:
        return None  # Niet bereikbaar - stilzwijgend doorgaan
    return vergelijk(tarieven, parse_tarieventabel(html, kop))
