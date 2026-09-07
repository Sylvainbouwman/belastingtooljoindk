"""Signaleert of belastingdienst.nl nieuwere belastingrentepercentages toont
dan de tabellen die in deze app hardgecodeerd staan.

De pagina bevat twee tabellen (algemeen en vennootschapsbelasting) met rijen als:

    <tr><th>Vanaf 1-1-2026</th>                    <td>5</td></tr>
    <tr><th>1-1-2025 tot en met 31-12-2025*</th>   <td>6,5</td></tr>

Er wordt bewust per rij geparsed in plaats van alle datums op de pagina te
verzamelen: de einddatums (31-12-2025) en losse datums elders op de pagina
leveren anders vals alarm op.

Wat deze controle wél en niet ziet:

  * `vergelijk()` toetst de nieuwste rij: een nieuwere periode op de bron, en
    een met terugwerkende kracht herzien percentage bij diezelfde ingangsdatum.
    Dat dekt de twee manieren waarop de tabel in de praktijk verandert.
  * De volledige rij-voor-rij vergelijking staat in de netwerktest in
    `tests/test_tarieven_check.py`, niet hier; die hoort bij het onderhoud en
    niet bij elke paginaweergave.
  * Alles wat op de bronpagina buiten de tabellen staat, blijft buiten bereik.
    De pagina zet uitzonderingen namelijk in voetnoten ónder een tabel — zoals
    "Voor de inkomstenbelasting ging de tijdelijke verlaging in vanaf 1-7-2020"
    onder de algemene tabel. Zo'n voetnoot wordt hier niet gelezen. Een pagina
    die op een voetnoot leunt, geeft dat door via `niet_gedekt`, zodat de
    controle zelf meldt welk deel zij niet dekt in plaats van te zwijgen.
"""

import re
from datetime import date
from typing import NamedTuple

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


class Controle(NamedTuple):
    """Uitkomst van de tarievencontrole.

    `status` is een van:

      "gelijk"        de vergeleken rijen komen overeen met de bron
      "afwijking"     de bron wijkt af; `melding` bevat de waarschuwing
      "onbereikbaar"  belastingdienst.nl was niet op te halen; er is niets
                      vergeleken
      "onleesbaar"    de pagina kwam binnen maar de tabel werd niet herkend;
                      er is evenmin iets vergeleken

    De laatste twee bestaan omdat "geen waarschuwing" anders twee dingen
    betekent: dat de reeks klopt, of dat er niets is gecontroleerd. Die tweede
    toestand las als de eerste.

    `niet_gedekt` beschrijft wat deze vergelijking structureel niet kan zien,
    ook wanneer zij slaagt. Zie de IB-pagina: de uitzondering per 1 juli 2020
    staat op de bronpagina in een voetnoot ónder de tabel en valt dus buiten
    het bereik van een tabelvergelijking.
    """

    status: str
    melding: str | None = None
    niet_gedekt: str | None = None


def controleer_nieuwe_tarieven(tarieven: list,
                               kop: str = KOP_ALGEMEEN,
                               niet_gedekt: str | None = None) -> Controle:
    """Vergelijkt de eigen tarieventabel met de tabel onder `kop` op de bron.

    Geeft altijd een Controle terug, nooit None, zodat de aanroeper kan zien of
    er werkelijk is gecontroleerd. Een netwerkfout laat de app bewust niet
    stuklopen; hij levert de status "onbereikbaar" op, die de pagina als melding
    toont.

    Het gooien in `_haal_pagina_op` blijft staan zoals het is: die functie is
    gecached, en juist door te gooien houdt Streamlit het mislukte antwoord niet
    vast, zodat de volgende paginaweergave het opnieuw probeert. De uitzondering
    verlaat de gecachete functie vóórdat zij hier wordt gevangen.
    """
    try:
        html = _haal_pagina_op(date.today().strftime("%Y-%m"))
    except Exception as fout:
        return Controle("onbereikbaar", (
            f"De tarieventabel is deze keer **niet** tegen belastingdienst.nl "
            f"gecontroleerd: de pagina was niet op te halen "
            f"({type(fout).__name__}). De berekening hieronder gebruikt de tabel "
            f"in de code. [Controleer de percentages]({BELASTINGDIENST_URL}) als "
            f"de uitkomst ergens op wordt gebaseerd."
        ), niet_gedekt)

    online = parse_tarieventabel(html, kop)
    if not online:
        return Controle("onleesbaar", (
            f"De tabel \"{kop}\" is op belastingdienst.nl niet herkend — "
            f"waarschijnlijk is de opmaak van de pagina gewijzigd. Er is deze "
            f"keer **niets** gecontroleerd. "
            f"[Controleer de percentages]({BELASTINGDIENST_URL})."
        ), niet_gedekt)

    melding = vergelijk(tarieven, online)
    if melding:
        return Controle("afwijking", melding, niet_gedekt)
    return Controle("gelijk", None, niet_gedekt)


# ── Voettekst ───────────────────────────────────────────────────────────────

_CONTROLEREGEL = {
    "gelijk": ("De tarieventabel is bij deze paginaweergave vergeleken met "
               "belastingdienst.nl en komt daarmee overeen."),
    "afwijking": ("De tarieventabel wijkt af van belastingdienst.nl; zie de "
                  "waarschuwing boven de invoer."),
    "onbereikbaar": ("De tarieventabel is bij deze paginaweergave **niet** "
                     "vergeleken met belastingdienst.nl: die pagina was niet op "
                     "te halen."),
    "onleesbaar": ("De tarieventabel is bij deze paginaweergave **niet** "
                   "vergeleken met belastingdienst.nl: de tabel op die pagina "
                   "werd niet herkend."),
}


def controleregel(controle: Controle) -> str:
    """Eén zin voor de voettekst die zegt wát er deze keer is gecontroleerd.

    Bewust ook een zin bij "gelijk": stond er alleen iets bij een afwijking,
    dan bleef het verschil tussen "gecontroleerd en in orde" en "niet
    gecontroleerd" onzichtbaar.
    """
    regel = _CONTROLEREGEL[controle.status]
    if controle.niet_gedekt:
        regel += " " + controle.niet_gedekt
    return regel
