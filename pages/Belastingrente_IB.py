import streamlit as st
from datetime import date

from _rente import bereken, nl_date, nl_euro, nl_euro_heel, nl_pct, renteperiode
from _ui import paginakop, paginastijl
from _tarieven_check import KOP_ALGEMEEN, controleer_nieuwe_tarieven, controleregel

# ── Tarieven ────────────────────────────────────────────────────────────────
# Enkelvoudige belastingrente IB/PH per jaar. Gesorteerd nieuw → oud.
#
# LET OP — deze reeks wijkt op één rij bewust af van de tabel op de bronpagina.
# De coronaverlaging naar 0,01% ging voor de inkomstenbelasting pas in op
# 1 juli 2020, en niet op 1 juni 2020 zoals voor de overige belastingen. Juni
# 2020 valt voor de IB dus nog onder 4,00%. Voor beide liep de verlaging tot
# 1 oktober 2020.
#
# De VpB-tabel in pages/Belastingrente_VpB.py houdt op precies deze plek wél
# 1 juni 2020 aan, en dat is daar juist: de VpB-tabel op de bronpagina heeft bij
# die rij geen voetnoot. Het verschil tussen de twee tabellen is dus bedoeld en
# mag niet worden "rechtgetrokken".
TARIEVEN = [
    (date(2026, 1, 1),  5.00),
    (date(2025, 1, 1),  6.50),
    (date(2024, 1, 1),  7.50),
    (date(2023, 7, 1),  6.00),
    (date(2020, 10, 1), 4.00),
    (date(2020, 7, 1),  0.01),   # IB: 1 juli, niet 1 juni — zie de kop hierboven
    (date(2014, 4, 1),  4.00),
    (date(2013, 1, 1),  3.00),
    (date(2012, 10, 1), 2.25),
    (date(2012, 7, 1),  2.50),
    (date(2012, 4, 1),  2.30),
    (date(2012, 1, 1),  2.85),
]

# ── Grondslag en controle ───────────────────────────────────────────────────
# Grondslag van de reeks: belastingdienst.nl, "Overzicht percentages
# belastingrente", tabel "Percentages alle belastingen (m.u.v. toeslagen en
# vennootschapsbelasting)".
#   https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/standaard_functies
#   /prive/contact/rechten_en_plichten_bij_de_belastingdienst/belastingrente
#   /overzicht_percentages_belastingrente
#
# Grondslag van de IB-uitzondering per 1 juli 2020: Verzamelspoedwet COVID-19,
# Stb. 2020, 200 — https://zoek.officielebekendmakingen.nl/stb-2020-200.html.
# Die regeling stelt het percentage voor de meeste belastingen per 1 juni 2020
# op 0,01% vast en voor de inkomstenbelasting per 1 juli 2020; voor beide gold
# de verlaging tot 1 oktober 2020. De Belastingdienst vermeldt het zelf in
# voetnoot *** onder de samenvattende tabel: "Voor de inkomstenbelasting ging de
# tijdelijke verlaging in vanaf 1-7-2020."
#
# Controle op 7 september 2026. Toen zijn nagelopen:
#   (a) alle twaalf rijen van de algemene tabel, tegen de tekst van die pagina
#       zoals die op 7 september 2026 online stond;
#   (b) de ingangsdatum van 1 juli 2020 voor de IB, tegen Stb. 2020, 200 en
#       tegen voetnoot *** op die pagina.
# Buiten de controle gebleven: de afwijkende toeslagenpercentages uit voetnoot *
# en ** op die pagina, die deze rekenpagina niet gebruikt.

# Wat de automatische controle bij elke paginaweergave niet kan zien. De
# vergelijking loopt over de tabel; de IB-uitzondering staat in een voetnoot
# ónder die tabel. Zonder deze regel zou de controle de afwijking elk jaar
# opnieuw stilzwijgend goedkeuren.
NIET_GEDEKT = (
    "De automatische controle vergelijkt deze reeks met de tabel "
    "\"Percentages alle belastingen\" op belastingdienst.nl. De IB-uitzondering "
    "per 1 juli 2020 staat daar in een voetnoot ónder die tabel en valt dus "
    "buiten die vergelijking; die ingangsdatum is met de hand gecontroleerd "
    "tegen Stb. 2020, 200 op 7 september 2026."
)

_controle = controleer_nieuwe_tarieven(TARIEVEN, KOP_ALGEMEEN, NIET_GEDEKT)

# ── Opmaak ──────────────────────────────────────────────────────────────────
paginastijl()

paginakop(
    "Belastingrente IB",
    "Bereken de belastingrente voor een aanslag inkomstenbelasting. De rente loopt "
    "vanaf 1 juli van het jaar volgend op het belastingjaar, en eindigt 6 weken na de "
    "dagtekening — of eerder, als de aangifte op tijd binnen was.",
)

# ── Invoer ───────────────────────────────────────────────────────────────────
if _controle.status == "afwijking":
    st.warning(_controle.melding)
elif _controle.melding:
    # "onbereikbaar" of "onleesbaar": er is niets vergeleken. Dat moet zichtbaar
    # zijn, want zonder melding leest de stilte als goedkeuring.
    st.info(_controle.melding)

huidig_jaar = date.today().year

col_a, col_b = st.columns(2)
with col_a:
    belastingjaar = st.selectbox(
        "Belastingjaar",
        options=list(range(huidig_jaar - 1, huidig_jaar - 9, -1)),
        index=1,
    )
with col_b:
    dagtekening = st.date_input(
        "Dagtekening aanslag (of verwachte datum)",
        value=date.today(),
        min_value=date(2015, 1, 1),
        max_value=date(huidig_jaar + 3, 12, 31),
        format="DD-MM-YYYY",
        help="Vul de werkelijke dagtekening in, of een verwachte datum om vooraf een "
             "inschatting te maken.",
    )

# De renteperiode start altijd op 1 juli van het jaar na het belastingjaar.
r_start = date(belastingjaar + 1, 7, 1)
uiterste_aangiftedatum = date(belastingjaar + 1, 5, 1)

aanslag_type = st.radio(
    "Soort aanslag",
    options=["regulier", "navordering"],
    format_func=lambda x: "Definitieve aanslag" if x == "regulier" else "Navorderingsaanslag",
    horizontal=True,
    help="Bij een navorderingsaanslag loopt de rente tot 1 maand na de dagtekening, "
         "in plaats van 6 weken.",
)

aangifte_ontvangen = None
aangifte_gevolgd = True
verzoek_datum = None

if aanslag_type == "regulier":
    col_c, col_d = st.columns(2)
    with col_c:
        aangifte_ontvangen = st.date_input(
            "Datum ontvangst aangifte",
            value=None,
            min_value=date(belastingjaar + 1, 1, 1),
            max_value=date(huidig_jaar + 3, 12, 31),
            format="DD-MM-YYYY",
            help=f"Bepaalt twee dingen: of er überhaupt rente verschuldigd is (bij "
                 f"aangifte vóór {nl_date(uiterste_aangiftedatum)} die ongewijzigd "
                 f"wordt gevolgd is dat niet zo), en de maximering op 19 weken na "
                 f"ontvangst. Laat leeg als de datum onbekend is — dan wordt een "
                 f"bovengrens getoond.",
        )
    with col_d:
        st.write("")
        aangifte_gevolgd = st.toggle(
            "Aangifte ongewijzigd gevolgd",
            value=True,
            help="Laat aan als de Belastingdienst de aangifte zonder wijzigingen heeft "
                 "overgenomen. Zet uit als er is afgeweken — dan vervallen zowel de "
                 "vrijstelling bij tijdige aangifte als de maximering op 19 weken.",
        )
else:
    op_verzoek = st.toggle(
        "Navordering op eigen verzoek",
        value=False,
        help="Zet aan als de belastingplichtige zelf om de navordering heeft verzocht. "
             "De rente is dan wettelijk gemaximeerd op 12 weken na ontvangst van dat "
             "verzoek.",
    )
    if op_verzoek:
        verzoek_datum = st.date_input(
            "Datum ontvangst verzoek",
            value=None,
            min_value=date(belastingjaar, 1, 1),
            max_value=date(huidig_jaar + 3, 12, 31),
            format="DD-MM-YYYY",
        )

bedrag = st.number_input(
    "Aangeslagen bedrag IB (€)",
    min_value=0.0,
    value=10000.0,
    step=500.0,
    format="%.2f",
)

# ── Berekening ───────────────────────────────────────────────────────────────
r_eind, reden, toelichting = renteperiode(
    dagtekening=dagtekening,
    aangifte_ontvangen=aangifte_ontvangen,
    aangifte_gevolgd=aangifte_gevolgd,
    uiterste_aangiftedatum=uiterste_aangiftedatum,
    aanslag_type=aanslag_type,
    verzoek_datum=verzoek_datum,
)

if r_eind is None:
    st.success(f"**Geen belastingrente verschuldigd.** {toelichting}")
    st.caption(
        "Bron: belastingdienst.nl — \"U betaalt geen belastingrente als u op tijd "
        "aangifte inkomstenbelasting doet en wij uw gegevens uit de aangifte "
        "ongewijzigd overnemen.\""
    )
    st.stop()

if r_eind < r_start:
    st.warning(
        f"Geen belastingrente: de renteperiode zou starten op {nl_date(r_start)} maar "
        f"eindigt al op {nl_date(r_eind)}."
    )
    st.stop()

totaal_rente, deelperioden = bereken(bedrag, r_start, r_eind, TARIEVEN)
totaal_dagen = sum(d["dagen"] for d in deelperioden)

# ── Uitvoer ──────────────────────────────────────────────────────────────────
st.html(f"""
<div style="background:linear-gradient(135deg,#1a4d2e,#1e5c36);color:white;
  border-radius:14px;padding:20px 22px;margin-bottom:12px;text-align:center;
  box-shadow:0 4px 16px rgba(26,77,46,.25);">
  <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-bottom:6px;letter-spacing:.05em;">
    BELASTINGRENTE IB
  </div>
  <div style="font-size:36px;font-weight:bold;font-family:monospace;">
    {nl_euro_heel(totaal_rente)}
  </div>
</div>
""")

st.info(toelichting)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Renteperiode</div>
      <div class="value" style="font-size:14px;">{nl_date(r_start)} t/m {nl_date(r_eind)}</div>
      <div class="sub">{totaal_dagen} dagen (30 per maand)</div>
    </div>""", unsafe_allow_html=True)

with col2:
    uniq_tarieven = sorted({d["pct"] for d in deelperioden})
    tarief_txt = " / ".join(nl_pct(p) for p in uniq_tarieven)
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Rentetarief (per jaar)</div>
      <div class="value">{tarief_txt}</div>
      <div class="sub">Enkelvoudig, 360 dagen</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Aangeslagen bedrag</div>
      <div class="value" style="font-size:16px;">{nl_euro(bedrag)}</div>
      <div class="sub">Belastingjaar {belastingjaar}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("**Berekening per periode**")
for d in deelperioden:
    st.markdown(f"""
    <div class="bk-tile" style="margin-bottom:6px">
      <div class="label">{nl_date(d['start'])} t/m {nl_date(d['eind'])}
        &nbsp;·&nbsp; {nl_pct(d['pct'])} &nbsp;·&nbsp; {d['dagen']} dagen</div>
      <div class="value">{nl_euro_heel(d['rente'])}</div>
    </div>""", unsafe_allow_html=True)

with st.expander("Uitgangspunten van deze berekening", expanded=False):
    st.markdown(f"""
| | |
|---|---|
| Soort aanslag | {"Definitieve aanslag" if aanslag_type == "regulier" else "Navorderingsaanslag"} |
| Aangifte ontvangen | {nl_date(aangifte_ontvangen) if aangifte_ontvangen else "onbekend"} |
| Dagtekening aanslag | {nl_date(dagtekening)} |
| Aangifte ongewijzigd gevolgd | {"ja" if aangifte_gevolgd else "nee"} |
| Reden einddatum rente | `{reden}` |
| Renteperiode | {nl_date(r_start)} t/m {nl_date(r_eind)} |
| Bedrag waarover rente loopt | {nl_euro(bedrag)} |
""")

st.caption(
    "Rekenmethode volgens belastingdienst.nl: 30 dagen per maand, 360 dagen per jaar, "
    "per tariefperiode naar beneden afgerond op hele euro's. Tarieventabel met de hand "
    "nagelopen op 7 september 2026. " + controleregel(_controle)
)
