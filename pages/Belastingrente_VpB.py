import calendar
from datetime import date, timedelta

import streamlit as st

from _rente import bereken, nl_date, nl_euro, nl_euro_heel, nl_pct, renteperiode
from _tarieven_check import KOP_VPB, controleer_nieuwe_tarieven

# ── Tarieven ────────────────────────────────────────────────────────────────
# Enkelvoudige belastingrente VpB per jaar. Gesorteerd nieuw → oud.
# Bron: belastingdienst.nl — "Percentages vennootschapsbelasting"
# Laatste controle: 17 augustus 2026 (tabel 1-op-1 nagelopen tegen de bron).
# Let op: 2022 t/m 2026 zijn herziene percentages (oorspronkelijk hoger vastgesteld).
TARIEVEN = [
    (date(2026, 1, 1),  5.00),
    (date(2025, 1, 1),  6.50),
    (date(2024, 1, 1),  7.50),
    (date(2023, 7, 1),  6.00),
    (date(2022, 1, 1),  4.00),
    (date(2020, 10, 1), 4.00),
    (date(2020, 6, 1),  0.01),
    (date(2016, 9, 1),  8.00),
    (date(2015, 3, 1),  8.05),
    (date(2014, 9, 1),  8.15),
    (date(2014, 4, 1),  8.25),
    (date(2013, 1, 1),  3.00),
    (date(2012, 10, 1), 2.25),
    (date(2012, 7, 1),  2.50),
    (date(2012, 4, 1),  2.30),
    (date(2012, 1, 1),  2.85),
]

_tarief_waarschuwing = controleer_nieuwe_tarieven(TARIEVEN, KOP_VPB)


def tel_maanden_op(d: date, maanden: int) -> date:
    maand = d.month + maanden
    jaar = d.year + (maand - 1) // 12
    maand = (maand - 1) % 12 + 1
    return date(jaar, maand, min(d.day, calendar.monthrange(jaar, maand)[1]))


# ── Opmaak ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: linear-gradient(180deg,#f8fbfd 0%,#eef3f7 100%); }
  .bk-header { background: linear-gradient(135deg,#24304A,#2f3d5d); color: white;
    border-radius: 16px; padding: 18px 22px; margin-bottom: 16px; }
  .bk-header h1 { margin: 0 0 6px; font-size: 26px; color: white; }
  .bk-header p  { margin: 0; font-size: 14px; color: rgba(255,255,255,0.88); line-height: 1.5; }
  .bk-tile { background: white; border-radius: 12px; padding: 14px 16px;
    box-shadow: 0 2px 10px rgba(36,48,74,.07); margin-bottom: 8px; }
  .bk-tile .label { font-size: 12px; color: #6b7a99; margin-bottom: 2px; }
  .bk-tile .value { font-size: 18px; font-weight: bold; color: #24304A; }
  .bk-tile .sub   { font-size: 13px; color: #6b7a99; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="bk-header">
  <h1>Belastingrente VpB</h1>
  <p>Bereken de belastingrente voor een aanslag vennootschapsbelasting.
     De rente loopt vanaf 6 maanden na het boekjaar-einde, en eindigt 6 weken na de
     dagtekening — of eerder, als de aangifte op tijd binnen was.</p>
</div>
""", unsafe_allow_html=True)

# ── Invoer ───────────────────────────────────────────────────────────────────
if _tarief_waarschuwing:
    st.warning(_tarief_waarschuwing)

huidig_jaar = date.today().year

col_a, col_b = st.columns(2)
with col_a:
    boekjaar_eind = st.date_input(
        "Einddatum boekjaar",
        value=date(huidig_jaar - 2, 12, 31),
        min_value=date(2000, 1, 1),
        max_value=date(huidig_jaar + 1, 12, 31),
        format="DD-MM-YYYY",
        help="Regulier boekjaar: 31 december. Bij een gebroken boekjaar vult u de "
             "werkelijke einddatum in.",
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

# Rente start 6 maanden na het boekjaar-einde; bij een regulier boekjaar komt dat
# uit op 1 juli, zoals belastingdienst.nl het formuleert. De vrijstellingsgrens
# ligt een maand eerder (voor VpB: vóór 1 juni).
r_start = tel_maanden_op(boekjaar_eind, 6) + timedelta(days=1)
uiterste_aangiftedatum = tel_maanden_op(boekjaar_eind, 5) + timedelta(days=1)

col_c, col_d = st.columns(2)
with col_c:
    aangifte_ontvangen = st.date_input(
        "Datum ontvangst aangifte",
        value=None,
        min_value=boekjaar_eind,
        max_value=date(huidig_jaar + 3, 12, 31),
        format="DD-MM-YYYY",
        help=f"Bepaalt twee dingen: of er überhaupt rente verschuldigd is (bij aangifte "
             f"vóór {nl_date(uiterste_aangiftedatum)} zonder afwijking is dat niet zo), "
             f"en de maximering op 19 weken na ontvangst. Laat leeg als de datum "
             f"onbekend is — dan wordt een bovengrens getoond.",
    )
with col_d:
    st.write("")
    afgeweken = st.toggle(
        "Aanslag wijkt af van de aangifte",
        value=False,
        help="Zet aan als de Belastingdienst bij het opleggen van de aanslag is "
             "afgeweken van de ingediende aangifte. Dan vervallen zowel de vrijstelling "
             "bij tijdige aangifte als de maximering op 19 weken.",
    )

bedrag = st.number_input(
    "Aangeslagen bedrag VpB (€)",
    min_value=0.0,
    value=10000.0,
    step=500.0,
    format="%.2f",
)

# ── Berekening ───────────────────────────────────────────────────────────────
r_eind, toelichting = renteperiode(
    dagtekening=dagtekening,
    aangifte_ontvangen=aangifte_ontvangen,
    afgeweken=afgeweken,
    uiterste_aangiftedatum=uiterste_aangiftedatum,
)

if r_eind is None:
    st.success(f"**Geen belastingrente verschuldigd.** {toelichting}")
    st.caption(
        "Bron: belastingdienst.nl — \"U doet aangifte vennootschapsbelasting voor "
        "1 juni volgend op het belastingjaar en wij nemen de gegevens uit uw aangifte "
        "ongewijzigd over.\""
    )
    st.stop()

if r_eind < r_start:
    st.warning(
        f"Geen belastingrente: de renteperiode zou starten op {nl_date(r_start)} maar "
        f"eindigt al op {nl_date(r_eind)}. De aanslag is gedagtekend binnen 6 maanden "
        f"na het boekjaar-einde."
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
    BELASTINGRENTE VPB
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
      <div class="sub">Boekjaar t/m {nl_date(boekjaar_eind)}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("**Berekening per periode**")
for d in deelperioden:
    st.markdown(f"""
    <div class="bk-tile" style="margin-bottom:6px">
      <div class="label">{nl_date(d['start'])} t/m {nl_date(d['eind'])}
        &nbsp;·&nbsp; {nl_pct(d['pct'])} &nbsp;·&nbsp; {d['dagen']} dagen</div>
      <div class="value">{nl_euro_heel(d['rente'])}</div>
    </div>""", unsafe_allow_html=True)

st.caption(
    "Rekenmethode volgens belastingdienst.nl: 30 dagen per maand, 360 dagen per jaar, "
    "per tariefperiode naar beneden afgerond op hele euro's. Tarieventabel nagelopen op "
    "17 augustus 2026; deze pagina controleert automatisch of de bron inmiddels afwijkt. "
    "Bij een gebroken boekjaar wordt de vrijstellingsgrens afgeleid als 5 maanden na het "
    "boekjaar-einde — controleer dat als u daarmee werkt."
)
