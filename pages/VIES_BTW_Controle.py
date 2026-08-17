import html

import streamlit as st
import requests

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




# ── Stijl ────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: linear-gradient(180deg,#f8fbfd 0%,#eef3f7 100%); }
  .vies-header { background: linear-gradient(135deg,#24304A,#2f3d5d); color: white;
    border-radius: 16px; padding: 18px 22px; margin-bottom: 16px; }
  .vies-header h1 { margin: 0 0 6px; font-size: 26px; color: white; }
  .vies-header p  { margin: 0; font-size: 14px; color: rgba(255,255,255,0.88); line-height: 1.5; }
  .vies-tile { background: white; border-radius: 12px; padding: 14px 16px;
    box-shadow: 0 2px 10px rgba(36,48,74,.07); margin-bottom: 8px; }
  .vies-tile .label { font-size: 12px; color: #6b7a99; margin-bottom: 2px; }
  .vies-tile .value { font-size: 18px; font-weight: bold; color: #24304A; }
  .vies-tile .sub   { font-size: 13px; color: #6b7a99; margin-top: 2px; }
  .badge-geldig   { display:inline-block; background:#1a6b3a; color:white;
    border-radius:8px; padding:4px 14px; font-size:15px; font-weight:bold; }
  .badge-ongeldig { display:inline-block; background:#c0392b; color:white;
    border-radius:8px; padding:4px 14px; font-size:15px; font-weight:bold; }
  .badge-storing  { display:inline-block; background:#b8860b; color:white;
    border-radius:8px; padding:4px 14px; font-size:15px; font-weight:bold; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="vies-header">
  <h1>VIES BTW-controle</h1>
  <p>Controleer of een Europees BTW-nummer geldig is en haal de bijbehorende
     bedrijfsnaam en het adres op via de officiële EU VIES-database.</p>
</div>
""", unsafe_allow_html=True)

# ── Invoer ───────────────────────────────────────────────────────────────────

col_in, col_knop = st.columns([3, 1])
with col_in:
    raw = st.text_input(
        "BTW-nummer",
        placeholder="bijv. NL820646660B01 of BE0123456789",
        label_visibility="collapsed",
    )
with col_knop:
    st.button("Controleer →", use_container_width=True)

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

nummer_veilig = html.escape(f"{land} {nummer}")
land_naam = html.escape(LAND_NAAM.get(land, land))

BADGES = {
    "geldig":   '<span class="badge-geldig">✓ Geldig</span>',
    "ongeldig": '<span class="badge-ongeldig">✗ Niet geldig</span>',
    "storing":  '<span class="badge-storing">⚠ Niet gecontroleerd</span>',
}

st.markdown(f"""
<div class="vies-tile" style="margin-bottom:12px;">
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
        naam_html = html.escape(uitkomst["naam"]) if uitkomst["naam"] else "—"
        st.markdown(f"""
        <div class="vies-tile">
          <div class="label">Bedrijfsnaam</div>
          <div class="value" style="font-size:16px;">{naam_html}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        regels = [html.escape(r) for r in adres_regels(uitkomst["adres"])]
        adres_html = "<br>".join(regels) if regels else "—"
        st.markdown(f"""
        <div class="vies-tile">
          <div class="label">Adres</div>
          <div class="value" style="font-size:15px;font-weight:normal;line-height:1.5;">{adres_html}</div>
        </div>""", unsafe_allow_html=True)

    rsin9 = rsin_uit_btw_nummer(land, nummer)
    if rsin9:
        rsin_fmt = f"{rsin9[:4]}.{rsin9[4:6]}.{rsin9[6:]}"
        st.markdown(f"""
        <div class="vies-tile">
          <div class="label">RSIN (afgeleid)</div>
          <div class="value" style="font-family:monospace;font-size:17px;">{rsin_fmt}</div>
          <div class="sub">Correspondeert met het RSIN in een betalingskenmerk</div>
        </div>""", unsafe_allow_html=True)

st.caption("Bron: Europese Commissie VIES · Gratis · Geen API-sleutel vereist")
