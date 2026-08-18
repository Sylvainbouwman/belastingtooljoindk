import streamlit as st
import requests
from _auto_paste import auto_paste_input as _auto_paste_input
from _kenmerk import decode_kenmerk, build_omschrijving
from _ui import is_kvk_url, kvk_sleutel_blok, paginakop, paginastijl, veilig


def render_digit_strip(raw: str, active: list) -> str:
    parts = []
    for i, (digit, on) in enumerate(zip(raw, active)):
        if i in (9, 11, 13):
            parts.append('<span style="color:#aab4cc;display:flex;align-items:center;font-size:18px;padding:0 2px">·</span>')
        bg = "#24304A" if on else "#e8ecf2"
        fg = "white" if on else "#6b7a99"
        parts.append(
            f'<div style="width:28px;height:34px;display:flex;align-items:center;'
            f'justify-content:center;border-radius:6px;font-family:monospace;'
            f'font-size:15px;font-weight:bold;background:{bg};color:{fg};">{digit}</div>'
        )
    return '<div style="display:flex;gap:3px;flex-wrap:wrap;margin-top:4px;">' + "".join(parts) + "</div>"


# ── KvK lookup ──────────────────────────────────────────────────────────────

KVK_API_URL = "https://api.kvk.nl/api/v2/zoeken"


@st.cache_data(ttl=3600)
def lookup_kvk_info(rsin9: str, api_key: str) -> dict | None:
    """Geeft {"naam": str|None, "sbi": list} terug, of None als niet gevonden."""
    resp = requests.get(
        KVK_API_URL,
        params={"rsin": rsin9, "resultatenPerPagina": 1},
        headers={"apikey": api_key},
        timeout=8,
    )
    if resp.status_code == 401:
        raise ValueError("Ongeldige of verlopen KvK API-sleutel (401). Controleer uw sleutel via developer.kvk.nl.")
    if resp.status_code == 403:
        raise ValueError("Toegang geweigerd (403). Controleer of uw API-abonnement nog actief is.")
    if resp.status_code in (404, 400):
        return None
    if not resp.ok:
        raise ValueError(f"KvK API fout {resp.status_code}: {resp.text[:200]}")
    items = resp.json().get("resultaten") or []
    if not items:
        return None
    item = items[0]
    # Fragiele veldtoegang: een link zonder rel of href liet dit omvallen.
    href = next((l.get("href") for l in item.get("links") or []
                 if l.get("rel") == "basisprofiel" and l.get("href")), None)
    sbi = []
    # K3: de href komt uit het antwoord van de KvK. Alleen een adres op de
    # KvK-API zelf mag de API-sleutel zien.
    if href and is_kvk_url(href):
        try:
            r2 = requests.get(href, headers={"apikey": api_key}, timeout=8)
            if r2.ok:
                sbi = r2.json().get("sbiActiviteiten") or []
        except Exception:
            pass
    return {"naam": item.get("naam"), "sbi": sbi}


# ── UI ──────────────────────────────────────────────────────────────────────

paginastijl()

paginakop(
    "Betalingskenmerk",
    "Plak een 16-cijferig betalingskenmerk van de Belastingdienst en zie direct om "
    "welk belastingmiddel, jaar en tijdvak het gaat.",
)

kvk_sleutel_blok(
    "Voer uw sleutel in om de bedrijfsnaam bij een RSIN op te zoeken."
)

# Input — eigen component: paste triggert direct rerun zonder klik
st.markdown('<p style="font-size:14px;font-weight:600;color:#31333F;margin-bottom:4px;">Betalingskenmerk</p>', unsafe_allow_html=True)
_comp_value = _auto_paste_input(
    value=st.session_state.get("kenmerk_digits", ""),
    key="kenmerk_comp",
    default=None,
)

if _comp_value is not None:
    st.session_state["kenmerk_digits"] = _comp_value.replace(" ", "")

vertalen = st.button("Vertalen →", use_container_width=True)
digits = st.session_state.get("kenmerk_digits", "")

if vertalen and not digits:
    st.info("Plak eerst een 16-cijferig betalingskenmerk.")
    st.stop()

if not digits:
    st.stop()

raw = digits
result, error = decode_kenmerk(raw)

if error:
    st.error(error)
    st.stop()

omschrijving = build_omschrijving(result)

# Hier stond een zelfgemaakte kopieerknop met een onclick-attribuut. Streamlit
# haalt gebeurtenisattributen uit meegegeven HTML, dus die knop deed bij een klik
# helemaal niets: geen kopie, geen terugkoppeling. Een codeblok heeft een eigen
# kopieerknop die het wel doet — daar was het CSS-regeltje voor stCodeBlock in
# het stijlblok ook al voor bedoeld.
st.markdown(
    '<div class="bk-omschrijving" style="padding-bottom:6px;margin-bottom:0;">'
    '<div class="label">Omschrijving voor in uw boekhouding</div></div>',
    unsafe_allow_html=True,
)
st.code(omschrijving, language=None)

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Soort</div>
      <div class="value">{result['soort']}</div>
      <div class="sub">{result['soort_sub']}</div>
    </div>""", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Tijdvak</div>
      <div class="value">{result['tijdvak'].capitalize()}</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Jaartal</div>
      <div class="value">{result['jaar']}</div>
    </div>""", unsafe_allow_html=True)
    if result["rsin"]:
        st.markdown(f"""
        <div class="bk-tile">
          <div class="label">BSN / RSIN</div>
          <div class="value" style="font-family:monospace;font-size:17px;">{result['rsin']}</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="bk-tile">
          <div class="label">BSN / RSIN</div>
          <div class="value" style="font-size:15px;color:#c0392b;">Niet af te leiden</div>
          <div class="sub">De elfproef gaat niet op — het kenmerk is waarschijnlijk
          verkeerd overgenomen. Controleer de cijfers.</div>
        </div>""", unsafe_allow_html=True)

kvk_key = st.session_state.get("kvk_api_key", "")
rsin9 = result["rsin9"]

def _naam_tile(waarde: str) -> str:
    return f"""
    <div class="bk-tile" style="margin-top:0">
      <div class="label">Naam bij RSIN</div>
      <div class="value">{waarde}</div>
    </div>"""

if not rsin9:
    pass  # Geen geldig RSIN afgeleid: KvK-opzoeking heeft geen zin.
elif kvk_key:
    # Eerder deed deze pagina eerst een volledige herberekening om een laadtekst
    # te kunnen tonen en haalde de gegevens pas in de tweede ronde op. Een
    # spinner doet hetzelfde zonder die extra ronde.
    with st.spinner("Naam bij RSIN ophalen…"):
        sbi_codes = []
        try:
            info = lookup_kvk_info(rsin9, kvk_key)
            if info:
                naam_value = info["naam"] or "Niet gevonden in KvK-register (mogelijk BSN van particulier)"
                sbi_codes = info["sbi"]
            else:
                naam_value = "Niet gevonden in KvK-register (mogelijk BSN van particulier)"
        except ValueError as e:
            naam_value = f"⚠ {e}"
        except Exception as e:
            naam_value = f"KvK niet bereikbaar ({type(e).__name__}: {e})"
        st.markdown(_naam_tile(veilig(naam_value)), unsafe_allow_html=True)
        if sbi_codes:
            hoofd = [s for s in sbi_codes if s.get("indHoofdactiviteit") == "Ja"]
            neven = [s for s in sbi_codes if s.get("indHoofdactiviteit") != "Ja"]
            hoofd_str = " · ".join(
                f"{veilig(a.get('sbiCode'))} {veilig(a.get('sbiOmschrijving'))}" for a in hoofd
            ) or "—"
            neven_str = " · ".join(
                f"{veilig(a.get('sbiCode'))} {veilig(a.get('sbiOmschrijving'))}" for a in neven
            )
            st.markdown(f"""
            <div class="bk-tile">
              <div class="label">SBI-code</div>
              <div class="value" style="font-size:16px;">{hoofd_str}</div>
              {f'<div class="sub">Nevenactiviteit: {neven_str}</div>' if neven_str else ''}
            </div>""", unsafe_allow_html=True)
else:
    st.info("Stel uw KvK API-sleutel in de zijbalk in om de bedrijfsnaam en SBI-code automatisch op te zoeken.")

with st.expander("Positieweergave", expanded=False):
    st.markdown(render_digit_strip(raw, result["digit_active"]), unsafe_allow_html=True)
    st.caption("Donkere posities zijn de gedecodeerde velden.")
