import streamlit as st
import requests

from _ui import paginakop, paginastijl, veilig
from _vies import (
    LAND_NAAM,
    VIES_URL,
    adres_regels,
    duid_antwoord,
    parse_btw,
    rsin_uit_btw_nummer,
)


@st.cache_data(ttl=3600)
def vies_check(land: str, nummer: str) -> dict:
    """Raadpleegt VIES. Gooit een exceptie bij een netwerk- of HTTP-fout, zodat
    Streamlit het mislukte antwoord niet een uur lang bewaart."""
    r = requests.get(VIES_URL.format(land=land, nummer=nummer), timeout=8)
    r.raise_for_status()
    return duid_antwoord(r.json())




paginastijl()

paginakop(
    "VIES BTW-controle",
    "Controleer of een Europees BTW-nummer geldig is en haal de bijbehorende "
    "bedrijfsnaam en het adres op via de officiële EU VIES-database.",
)

# ── Invoer ───────────────────────────────────────────────────────────────────

# Geen knop: de pagina rekent direct op de invoer. Er stond een knop
# "Controleer →" die nooit werd uitgelezen en dus niets deed.
raw = st.text_input(
    "BTW-nummer",
    placeholder="bijv. NL820646660B01 of BE0123456789",
    label_visibility="collapsed",
)

if not raw:
    st.caption("Voer een BTW-nummer in met landcode (bijv. NL, DE, BE). "
               "Spaties, punten en streepjes worden automatisch verwijderd.")
    st.stop()

land, nummer = parse_btw(raw)

if land is None:
    st.error("Ongeldige invoer — begin met een geldige EU-landcode (bijv. NL, DE, BE, FR), "
             "gevolgd door alleen letters en cijfers.")
    st.stop()

# ── API-aanroep ──────────────────────────────────────────────────────────────

with st.spinner("VIES raadplegen…"):
    try:
        uitkomst = vies_check(land, nummer)
    except Exception as exc:
        st.error(
            "VIES is nu niet bereikbaar, dus het nummer is **niet gecontroleerd**. "
            "Probeer het over enkele minuten opnieuw."
        )
        st.caption(f"Technische melding: {type(exc).__name__}")
        st.stop()

# ── Resultaat ────────────────────────────────────────────────────────────────

nummer_veilig = veilig(f"{land} {nummer}")
land_naam = veilig(LAND_NAAM.get(land, land))

BADGES = {
    "geldig":   '<span class="badge-geldig">✓ Geldig</span>',
    "ongeldig": '<span class="badge-ongeldig">✗ Niet geldig</span>',
    "storing":  '<span class="badge-storing">⚠ Niet gecontroleerd</span>',
}

st.markdown(f"""
<div class="bk-tile" style="margin-bottom:12px;">
  <div class="label">Status</div>
  <div style="margin-top:6px;">{BADGES[uitkomst['status']]}</div>
  <div class="sub" style="margin-top:6px;">{nummer_veilig} &nbsp;·&nbsp; {land_naam}</div>
</div>
""", unsafe_allow_html=True)

if uitkomst["status"] == "storing":
    # VIES antwoordt met HTTP 200 en isValid=false bij een storing. Dat is iets
    # anders dan een ongeldig nummer en mag niet als zodanig worden getoond.
    st.warning(
        f"{uitkomst['melding']} Het BTW-nummer is hierdoor **niet gecontroleerd** — "
        "dit betekent níet dat het ongeldig is. Probeer het later opnieuw."
    )

elif uitkomst["status"] == "ongeldig":
    st.info("Dit BTW-nummer is niet geregistreerd of niet actief in de VIES-database. "
            "Controleer of het nummer correct is ingevoerd.")

else:
    col1, col2 = st.columns(2)

    with col1:
        naam_html = veilig(uitkomst["naam"])
        st.markdown(f"""
        <div class="bk-tile">
          <div class="label">Bedrijfsnaam</div>
          <div class="value" style="font-size:16px;">{naam_html}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        regels = [veilig(r) for r in adres_regels(uitkomst["adres"])]
        adres_html = "<br>".join(regels) if regels else "—"
        st.markdown(f"""
        <div class="bk-tile">
          <div class="label">Adres</div>
          <div class="value" style="font-size:15px;font-weight:normal;line-height:1.5;">{adres_html}</div>
        </div>""", unsafe_allow_html=True)

    rsin9 = rsin_uit_btw_nummer(land, nummer)
    if rsin9:
        rsin_fmt = f"{rsin9[:4]}.{rsin9[4:6]}.{rsin9[6:]}"
        st.markdown(f"""
        <div class="bk-tile">
          <div class="label">RSIN (afgeleid)</div>
          <div class="value" style="font-family:monospace;font-size:17px;">{rsin_fmt}</div>
          <div class="sub">Correspondeert met het RSIN in een betalingskenmerk</div>
        </div>""", unsafe_allow_html=True)

st.caption("Bron: Europese Commissie VIES · Gratis · Geen API-sleutel vereist")
