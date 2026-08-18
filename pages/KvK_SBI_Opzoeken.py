import streamlit as st
import requests

from _kvk import groepeer_resultaten, profiel_kort, regel_sleutel, sbi_gesplitst
from _ui import is_kvk_url, kvk_sleutel_blok, paginakop, paginastijl, veilig

KVK_ZOEKEN_URL = "https://api.kvk.nl/api/v2/zoeken"

# Zoeken is gratis, elk opgevraagd basisprofiel kost EUR 0,02
# (developers.kvk.nl/nl/pricing, nagelopen 18-08-2026).
PRIJS_PER_PROFIEL = "€ 0,02"

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
def haal_basisprofiel(href: str, api_key: str) -> dict:
    """Het volledige basisprofiel achter een zoekresultaat.

    Deze aanroep kost een bevraging. De pagina doet hem daarom alleen voor het
    resultaat dat je openklapt; eerder werd hij voor alle tien de resultaten
    gedaan, ook voor de negen die je nooit bekeek. Het antwoord wordt een uur
    gecachet, dus hetzelfde bedrijf nog eens openen is gratis.
    """
    # K3: de href komt uit het antwoord van de KvK. Wijst hij naar een andere
    # host, dan gaat de API-sleutel daar niet naartoe.
    if not is_kvk_url(href):
        return {}
    try:
        r = requests.get(href, headers={"apikey": api_key}, timeout=8)
        return r.json() if r.ok else {}
    except Exception:
        return {}


def _rij(label: str, waarde) -> str:
    """Eén regel in het gegevensblok. Lege waarden vallen weg."""
    if waarde in (None, "", []):
        return ""
    return (f'<div style="display:flex;gap:10px;margin-bottom:3px;">'
            f'<div style="min-width:150px;color:#6b7a99;">{veilig(label)}</div>'
            f'<div style="color:#24304A;font-weight:600;">{veilig(waarde)}</div></div>')


paginastijl()

paginakop(
    "KvK / SBI opzoeken",
    "Zoek op bedrijfsnaam, KvK-nummer of RSIN en zie de bedrijfsgegevens en de "
    "SBI-activiteitencode(s).",
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

# De KvK geeft per bedrijf meerdere records terug - een rechtspersoon zonder adres
# en een hoofdvestiging met adres - wat twee bijna identieke regels opleverde.
# Eén regel per KvK-nummer; het basisprofiel hangt toch aan dat nummer.
gevonden = len(resultaten)
resultaten = groepeer_resultaten(resultaten)
if gevonden > len(resultaten):
    st.caption(f"{gevonden} records samengevoegd tot "
               f"{len(resultaten)} {'bedrijf' if len(resultaten) == 1 else 'bedrijven'}")

# "resultaat" + "en" gaf "resultaaten"; het meervoud verliest een a.
st.caption(f"{len(resultaten)} " + ("resultaat" if len(resultaten) == 1 else "resultaten") + " gevonden")

# Bij één treffer meteen ophalen — dat is het geval bij een KvK-nummer of RSIN, en
# dan is de bevraging toch wat je wilde. Bij meer treffers wacht de pagina op een
# klik, zodat een zoekopdracht op naam niet tien bevragingen kost.
if len(resultaten) > 1:
    st.caption(f"Klik op een naam voor de gegevens. Zoeken is gratis; per opgevraagd profiel rekent de KvK {PRIJS_PER_PROFIEL}.")
    geopend = st.session_state.get("kvk_geopend")
else:
    geopend = regel_sleutel(resultaten[0], 0)

for index, res in enumerate(resultaten):
    naam   = res.get("naam") or "—"
    kvk_nr = res.get("kvkNummer", "")
    rsin   = res.get("rsin", "")
    plaats = ((res.get("adres") or {}).get("binnenlandsAdres") or {}).get("plaats", "")
    # Fragiele veldtoegang: een link zonder rel of href liet de pagina omvallen.
    href   = next((l.get("href") for l in res.get("links") or []
                   if l.get("rel") == "basisprofiel" and l.get("href")), None)

    sleutel = regel_sleutel(res, index)

    # Regels onder de naam: plaats en, als het bedrijf meerdere vestigingen in de
    # resultaten had, dat aantal.
    onder = " · ".join(deel for deel in (
        f"KvK {kvk_nr}",
        plaats,
        f"{res['vestigingen_in_resultaat']} vestigingen"
        if res.get("vestigingen_in_resultaat", 0) > 1 else "",
    ) if deel)

    with st.container(border=True):
        if sleutel != geopend and href:
            # De naam is zelf de knop, zodat je erop kunt klikken in plaats van op
            # een knop ernaast. Een tertiaire knop heeft geen kader en leest als
            # een link; de regel eronder blijft gewone tekst.
            if st.button(f"**{naam}**", key=f"open_{sleutel}", type="tertiary"):
                st.session_state["kvk_geopend"] = sleutel
                st.rerun()
            st.markdown(
                f'<div style="font-size:13px;color:#6b7a99;margin-top:-8px;">{veilig(onder)}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="font-size:17px;font-weight:700;color:#24304A;">{veilig(naam)}</div>'
                f'<div style="font-size:13px;color:#6b7a99;">{veilig(onder)}</div>',
                unsafe_allow_html=True,
            )

        if sleutel != geopend:
            continue

        if not href:
            st.caption("Geen basisprofiel beschikbaar bij dit resultaat.")
            continue

        with st.spinner("Basisprofiel ophalen…"):
            profiel = haal_basisprofiel(href, kvk_key)

        if not profiel:
            st.warning("Het basisprofiel kon niet worden opgehaald.")
            continue

        p = profiel_kort(profiel)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="bk-tile">
              <div class="label">Statutaire naam</div>
              <div class="value" style="font-size:16px;">{veilig(p["statutaire_naam"] or p["naam"] or naam)}</div>
              {f'<div class="sub">Handelsnamen: {veilig(" · ".join(p["handelsnamen"]))}</div>' if p["handelsnamen"] else ''}
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="bk-tile">
              <div class="label">KvK-nummer · RSIN</div>
              <div class="value" style="font-size:16px;font-family:monospace;">{veilig(kvk_nr)}</div>
              <div class="sub">{veilig(rsin, leeg="RSIN niet meegeleverd")}</div>
            </div>""", unsafe_allow_html=True)

        gegevens = (
            _rij("Rechtsvorm", p["rechtsvorm"])
            + _rij("Geregistreerd sinds", p["geregistreerd"])
            + _rij("Werkzame personen", p["werkzame_personen"])
            + _rij("Adres hoofdvestiging", p["adres"])
            + _rij("Website", " · ".join(p["websites"]) if p["websites"] else None)
            + _rij("Vestigingsnummer", p["vestigingsnummer"])
        )
        if gegevens:
            st.markdown(
                f'<div class="bk-tile"><div class="label">Bedrijfsgegevens</div>'
                f'<div style="margin-top:8px;font-size:14px;">{gegevens}</div></div>',
                unsafe_allow_html=True,
            )

        hoofd, neven = sbi_gesplitst(profiel)
        if hoofd or neven:
            badges_hoofd = "".join(
                f'<span class="sbi-badge">{veilig(a.get("sbiCode"))}</span> '
                f'{veilig(a.get("sbiOmschrijving"))}<br>'
                for a in hoofd
            )
            badges_neven = "".join(
                f'<span class="sbi-badge sbi-badge-neven">{veilig(a.get("sbiCode"))}</span> '
                f'{veilig(a.get("sbiOmschrijving"))}<br>'
                for a in neven
            )
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

        if p["non_mailing"]:
            st.caption("Dit bedrijf staat als **non-mailing** geregistreerd: niet gebruiken "
                       "voor ongevraagde reclame per post of telefoon.")

st.caption(
    f"Bron: KvK Handelsregister API · zoeken gratis, basisprofiel {PRIJS_PER_PROFIEL} "
    "per bevraging · antwoorden worden een uur gecachet"
)
