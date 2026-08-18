import streamlit as st
import requests

from _ui import is_kvk_url, kvk_sleutel_blok, paginakop, paginastijl, veilig

KVK_ZOEKEN_URL = "https://api.kvk.nl/api/v2/zoeken"

# ── Lookup functies ───────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def zoek_bedrijf(zoekterm: str, api_key: str) -> list:
    """Zoek op naam, KvK-nummer of RSIN. Geeft lijst van resultaten."""
    zoekterm = zoekterm.strip()
    if zoekterm.isdigit() and len(zoekterm) == 9:
        param = {"rsin": zoekterm}
    elif zoekterm.isdigit():
        param = {"kvkNummer": zoekterm}
    else:
        param = {"naam": zoekterm}
    param["resultatenPerPagina"] = 10
    resp = requests.get(KVK_ZOEKEN_URL, params=param, headers={"apikey": api_key}, timeout=8)
    if resp.status_code == 401:
        raise ValueError("Ongeldige of verlopen KvK API-sleutel (401).")
    if not resp.ok:
        raise ValueError(f"KvK fout {resp.status_code}: {resp.text[:200]}")
    return resp.json().get("resultaten", [])


@st.cache_data(ttl=3600)
def haal_sbi(href: str, api_key: str) -> list:
    # K3: de href komt uit het antwoord van de KvK. Wijst hij naar een andere
    # host, dan gaat de API-sleutel daar niet naartoe.
    if not is_kvk_url(href):
        return []
    try:
        r = requests.get(href, headers={"apikey": api_key}, timeout=8)
        return r.json().get("sbiActiviteiten", []) if r.ok else []
    except Exception:
        return []

paginastijl()

paginakop(
    "KvK / SBI opzoeken",
    "Zoek op bedrijfsnaam, KvK-nummer of RSIN en zie direct de SBI-activiteitencode(s).",
)

# ── Invoer ────────────────────────────────────────────────────────────────────

kvk_key = kvk_sleutel_blok()

if not kvk_key:
    st.info("Stel uw KvK API-sleutel in via de zijbalk om bedrijven op te zoeken.")
    st.stop()

# Geen knop: de pagina zoekt direct op de invoer. Er stond een knop
# "Zoeken →" waarvan de uitkomst nooit werd uitgelezen.
zoekterm = st.text_input(
    "Zoeken",
    placeholder="Bedrijfsnaam, KvK-nummer (8 cijfers) of RSIN (9 cijfers)",
    label_visibility="collapsed",
)

if not zoekterm:
    st.caption("Typ een naam om op te zoeken, of plak een KvK-nummer of RSIN.")
    st.stop()

# ── Resultaten ────────────────────────────────────────────────────────────────

try:
    resultaten = zoek_bedrijf(zoekterm, kvk_key)
except ValueError as e:
    st.error(str(e))
    st.stop()

if not resultaten:
    st.warning("Geen resultaten gevonden. Controleer de spelling of probeer een KvK-nummer.")
    st.stop()

st.caption(f"{len(resultaten)} resultaat{'en' if len(resultaten) != 1 else ''} gevonden")

for res in resultaten:
    naam     = res.get("naam") or "—"
    kvk_nr   = res.get("kvkNummer", "")
    rsin     = res.get("rsin", "")
    adres    = (res.get("adres") or {}).get("binnenlandsAdres") or {}
    plaats   = adres.get("plaats", "")
    # Fragiele veldtoegang: een link zonder rel of href liet de pagina omvallen.
    href     = next((l.get("href") for l in res.get("links") or []
                     if l.get("rel") == "basisprofiel" and l.get("href")), None)

    with st.expander(f"**{naam}** — KvK {kvk_nr}  ·  {plaats}", expanded=len(resultaten) == 1):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="bk-tile">
              <div class="label">Bedrijfsnaam</div>
              <div class="value" style="font-size:16px;">{veilig(naam)}</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="bk-tile">
              <div class="label">KvK-nummer · RSIN</div>
              <div class="value" style="font-size:16px;font-family:monospace;">{veilig(kvk_nr)}</div>
              <div class="sub">{veilig(rsin)}</div>
            </div>""", unsafe_allow_html=True)

        if href:
            sbi_codes = haal_sbi(href, kvk_key)
            if sbi_codes:
                hoofd = [s for s in sbi_codes if s.get("indHoofdactiviteit") == "Ja"]
                neven = [s for s in sbi_codes if s.get("indHoofdactiviteit") != "Ja"]

                badges_hoofd = "".join(
                    f'<span class="sbi-badge">{veilig(a.get("sbiCode"))}</span> '
                    f'{veilig(a.get("sbiOmschrijving"))}<br>'
                    for a in hoofd
                )
                badges_neven = "".join(
                    f'<span class="sbi-badge sbi-badge-neven">{veilig(a.get("sbiCode"))}</span> '
                    f'{veilig(a.get("sbiOmschrijving"))}<br>'
                    for a in neven
                ) if neven else ""

                st.markdown(f"""
                <div class="bk-tile">
                  <div class="label">Hoofdactiviteit</div>
                  <div style="margin-top:6px;font-size:15px;line-height:2;">{badges_hoofd or "—"}</div>
                  {f'<div class="label" style="margin-top:10px;">Nevenactiviteit</div><div style="margin-top:6px;font-size:15px;line-height:2;">{badges_neven}</div>' if badges_neven else ''}
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="bk-tile">
                  <div class="label">SBI-code</div>
                  <div class="sub" style="margin-top:4px;">Tijdelijk niet beschikbaar (KvK verwerkt de gegevens)</div>
                </div>""", unsafe_allow_html=True)

st.caption("Bron: KvK Handelsregister API")
