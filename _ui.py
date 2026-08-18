"""Gedeelde bouwstenen voor de pagina's: opmaak, veilige HTML en de KvK-sleutel.

Het stijlblok en het KvK-sleutelblok stonden in elke pagina opnieuw. Belangrijker
nog: elke pagina zette gegevens van buiten (KvK-namen, SBI-omschrijvingen,
RDW-velden, VIES-antwoorden) rechtstreeks in HTML. Dat gaat nu via veilig().
"""

import html
from urllib.parse import urlparse

import streamlit as st

# Alle pagina's gebruiken dezelfde koptekst en tegels. De klassenamen beginnen
# met bk- omdat de Betalingskenmerk-pagina die als eerste had.
PAGINA_CSS = """
<style>
  [data-testid="stAppViewContainer"] { background: linear-gradient(180deg,#f8fbfd 0%,#eef3f7 100%); }
  .bk-header { background: linear-gradient(135deg,#24304A,#2f3d5d); color: white;
    border-radius: 16px; padding: 18px 22px; margin-bottom: 16px; }
  .bk-header h1 { margin: 0 0 6px; font-size: 26px; color: white; }
  .bk-header p  { margin: 0; font-size: 14px; color: rgba(255,255,255,0.88); line-height: 1.5; }
  .bk-omschrijving { background: white; border-radius: 14px; padding: 16px 20px;
    box-shadow: 0 4px 16px rgba(36,48,74,.08); margin-bottom: 12px; }
  .bk-omschrijving .label { font-size: 12px; color: #6b7a99; font-weight: 600;
    letter-spacing:.03em; margin-bottom: 6px; }
  .bk-omschrijving .value { font-size: 20px; font-weight: bold; color: #24304A;
    font-family: monospace; }
  .bk-tile { background: white; border-radius: 12px; padding: 14px 16px;
    box-shadow: 0 2px 10px rgba(36,48,74,.07); margin-bottom: 8px; }
  .bk-tile .label { font-size: 12px; color: #6b7a99; margin-bottom: 2px; }
  .bk-tile .value { font-size: 18px; font-weight: bold; color: #24304A; }
  .bk-tile .sub   { font-size: 13px; color: #6b7a99; margin-top: 2px; }
  .auto-info { background: #f0f4f8; border-radius: 8px; padding: 8px 14px;
    font-size: 13px; color: #24304A; margin: 6px 0 10px 0; }
  .auto-info b { color: #1a3a6e; }
  .auto-nr { font-size: 13px; font-weight: 700; color: #6b7a99;
    text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
  .badge-geldig   { display:inline-block; background:#1a6b3a; color:white;
    border-radius:8px; padding:4px 14px; font-size:15px; font-weight:bold; }
  .badge-ongeldig { display:inline-block; background:#c0392b; color:white;
    border-radius:8px; padding:4px 14px; font-size:15px; font-weight:bold; }
  .badge-storing  { display:inline-block; background:#b8860b; color:white;
    border-radius:8px; padding:4px 14px; font-size:15px; font-weight:bold; }
  .sbi-badge { display:inline-block; background:#24304A; color:white;
    border-radius:6px; padding:3px 10px; font-size:13px; font-weight:bold;
    font-family:monospace; margin-right:6px; }
  .sbi-badge-neven { background:#6b7a99; }
  div[data-testid="stCodeBlock"] button { display: inline-flex !important; }
</style>
"""


def veilig(waarde, leeg: str = "—") -> str:
    """Maakt een waarde van buiten geschikt om in HTML te zetten.

    Alles wat via een API binnenkomt gaat hier langs voordat het in een
    f-string met unsafe_allow_html belandt. Zonder deze stap kan een naam met
    een < of & de opmaak breken of markup injecteren.
    """
    if waarde is None or waarde == "":
        return leeg
    return html.escape(str(waarde))


def paginastijl() -> None:
    st.markdown(PAGINA_CSS, unsafe_allow_html=True)


def paginakop(titel: str, tekst: str) -> None:
    """Koptekst boven een pagina. Titel en tekst zijn vaste teksten uit de code,
    maar gaan voor de zekerheid ook langs veilig()."""
    st.markdown(
        f'<div class="bk-header"><h1>{veilig(titel)}</h1><p>{veilig(tekst)}</p></div>',
        unsafe_allow_html=True,
    )


# ── KvK ─────────────────────────────────────────────────────────────────────

KVK_HOST = "api.kvk.nl"


def is_kvk_url(url: str) -> bool:
    """Of een URL naar de KvK-API zelf wijst.

    De zoekresultaten van de KvK bevatten een href naar het basisprofiel. Die
    URL werd zonder controle opgevraagd, met de API-sleutel in de header. Wijst
    zo'n href ooit naar een andere host, dan lekt de sleutel daarheen.
    """
    try:
        ontleed = urlparse(url or "")
    except ValueError:
        return False
    return ontleed.scheme == "https" and ontleed.hostname == KVK_HOST


def kvk_sleutel_blok(toelichting: str | None = None) -> str:
    """Zet de KvK-sleutel klaar en geeft hem terug.

    Op Streamlit Cloud komt de sleutel uit de secrets; lokaal wordt hij in de
    zijbalk gevraagd en alleen in de sessie bewaard.
    """
    try:
        uit_secrets = st.secrets.get("kvk_api_key", "")
    except Exception:
        uit_secrets = ""

    if uit_secrets:
        st.session_state["kvk_api_key"] = uit_secrets
        return uit_secrets

    with st.sidebar:
        st.markdown("### KvK API-sleutel")
        if toelichting:
            st.markdown(toelichting)
        ingevoerd = st.text_input(
            "API-sleutel", value=st.session_state.get("kvk_api_key", ""),
            type="password", label_visibility="collapsed",
        )
        if ingevoerd:
            st.session_state["kvk_api_key"] = ingevoerd
        elif "kvk_api_key" in st.session_state:
            del st.session_state["kvk_api_key"]

    return st.session_state.get("kvk_api_key", "")
