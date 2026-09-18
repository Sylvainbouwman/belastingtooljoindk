import streamlit as st
from datetime import date, timedelta

from _invorderingsrente import (
    ART28C_SIGNALERING,
    HERLEVING_NA_UITSTEL,
    TARIEVEN_IN_REKENING,
    TARIEVEN_TE_VERGOEDEN,
    UITSLUITING_BELASTINGRENTE,
    UITSTELGRONDEN,
    UITZONDERINGEN,
    bereken,
    buiten_bereik,
    invorderbaar_op,
    nl_date,
    nl_euro,
    nl_euro_heel,
    nl_pct,
    oudste_ingang,
    periode_art28,
    periode_art28a,
    periode_art28b,
    uiterste_verzoekdatum_28c,
    vervalmaand_van,
)
from _ui import paginakop, paginastijl

# De rekenregels, de tarieven en hun vindplaats staan in _invorderingsrente.py.
# Deze pagina bevat bewust geen rekenlogica; zij vraagt uit, blokkeert waar de
# uitkomst niet gedekt is en toont het resultaat.

paginastijl()

paginakop(
    "Invorderingsrente",
    "Bereken de invorderingsrente van hoofdstuk V van de Invorderingswet 1990: de rente "
    "bij te late betaling (art. 28) en de vergoeding als de ontvanger te laat uitbetaalt "
    "(art. 28a) of als een aanslag wordt verminderd na een afgewezen uitstelverzoek "
    "(art. 28b). De dagentelling en de afronding volgen de Uitvoeringsregeling en wijken "
    "af van die bij belastingrente.",
)

GRONDSLAGEN = {
    "28": "Art. 28 — rente bij te late betaling (in rekening gebracht)",
    "28a": "Art. 28a — vergoeding als de ontvanger niet binnen 6 weken uitbetaalt",
    "28b": "Art. 28b — vergoeding bij vermindering na een afgewezen uitstelverzoek",
}

grondslag = st.radio(
    "Welke grondslag?",
    options=list(GRONDSLAGEN),
    format_func=lambda k: GRONDSLAGEN[k],
    help="Art. 28c (heffing in strijd met het Unierecht) wordt door deze tool niet "
         "berekend. Zie de signalering onder aan de pagina.",
)

vandaag = date.today()
MIN_DATUM = date(2020, 1, 1)
MAX_DATUM = date(vandaag.year + 3, 12, 31)

# ── Invoer per grondslag ────────────────────────────────────────────────────
richting = "in_rekening" if grondslag == "28" else "te_vergoeden"
tarieven = TARIEVEN_IN_REKENING if grondslag == "28" else TARIEVEN_TE_VERGOEDEN

vervaldag = None
vervalmaand = None
periode = None
grondslagbedrag = 0.0
laatste_betaling = False
uitgesloten: list[tuple[date, date]] = []
uitgangspunten: list[tuple[str, str]] = []

if grondslag in ("28", "28b"):
    col_a, col_b = st.columns(2)
    with col_a:
        aanslag_type = st.selectbox(
            "Soort belastingaanslag",
            options=["regulier", "navordering", "naheffing", "voorlopig-in-termijnen"],
            format_func=lambda k: {
                "regulier": "Definitieve of voorlopige aanslag (6 weken)",
                "navordering": "Navorderingsaanslag (1 maand)",
                "naheffing": "Naheffingsaanslag (14 dagen)",
                "voorlopig-in-termijnen": "Voorlopige aanslag in maandtermijnen",
            }[k],
            help="Bepaalt wanneer de aanslag invorderbaar is (art. 9 IW 1990). De "
                 "Algemene termijnenwet geldt hier niet, dus een vervaldag in een "
                 "weekend schuift niet op.",
        )
    with col_b:
        dagtekening = st.date_input(
            "Dagtekening aanslagbiljet",
            value=vandaag - timedelta(days=120),
            min_value=MIN_DATUM, max_value=MAX_DATUM, format="DD-MM-YYYY",
        )

    if aanslag_type == "voorlopig-in-termijnen":
        # Art. 9 lid 5 maakt de aanslag in maandtermijnen invorderbaar, en de
        # Leidraad Invordering 2008 (9.1) legt de laatste vervaldag in bepaalde
        # gevallen op 31 december. Die vervaldag wordt daarom niet afgeleid.
        vervaldag = st.date_input(
            "Vervaldag van de laatste betalingstermijn",
            value=None, min_value=MIN_DATUM, max_value=MAX_DATUM, format="DD-MM-YYYY",
            help="Bij een voorlopige aanslag in termijnen leidt deze tool de vervaldag "
                 "niet af. Neem hem over van het aanslagbiljet.",
        )
        if vervaldag is None:
            st.error(
                "Vul de vervaldag van de laatste betalingstermijn in. Bij een "
                "voorlopige aanslag in maandtermijnen hangt die af van de dagtekening "
                "en van het aantal resterende maanden, en de Leidraad Invordering legt "
                "hem in bepaalde gevallen op 31 december. Deze tool raadt die datum niet."
            )
            st.stop()
    else:
        vervaldag = invorderbaar_op(dagtekening, aanslag_type)
        st.caption(
            f"De aanslag is invorderbaar op **{nl_date(vervaldag)}** (art. 9 IW 1990). "
            f"Dat is tevens de vervaldag van de enige of laatste betalingstermijn en "
            f"bepaalt daarmee welke maand haar werkelijke aantal dagen telt."
        )

    vervalmaand = vervalmaand_van(vervaldag)
    uitgangspunten.append(("Dagtekening aanslagbiljet", nl_date(dagtekening)))
    uitgangspunten.append(("Invorderbaar / vervaldag", nl_date(vervaldag)))

if grondslag == "28":
    col_c, col_d = st.columns(2)
    with col_c:
        betaaldatum = st.date_input(
            "Datum van de betaling",
            value=vandaag, min_value=MIN_DATUM, max_value=MAX_DATUM, format="DD-MM-YYYY",
            help="De rente loopt tot en met de dag vóór de betaling (art. 28 lid 2).",
        )
    with col_d:
        grondslagbedrag = st.number_input(
            "Betaald bedrag (€)", min_value=0.0, value=10000.0, step=500.0, format="%.2f",
            help="Art. 29 van de Uitvoeringsregeling rekent de rente over iedere "
                 "betaling afzonderlijk, en art. 30 lid 1 rekent haar over het betaalde "
                 "bedrag. Bij meerdere betalingen reken je elke betaling apart door.",
        )

    laatste_betaling = st.toggle(
        "Dit is de enige of laatste betaling",
        value=True,
        help="Alleen dan geldt het drempelbedrag van art. 33 van de Uitvoeringsregeling: "
             "een bedrag aan invorderingsrente onder die grens wordt niet in rekening "
             "gebracht.",
    )

    verrekend = st.toggle(
        "Met deze aanslag is een aanslag over dezelfde belasting en hetzelfde tijdvak verrekend",
        value=False,
        help="Art. 28 lid 1, slot: voor zover dat het geval is, wordt geen "
             "invorderingsrente in rekening gebracht. Deze tool bepaalt dat deel niet.",
    )
    if verrekend:
        st.warning(
            "Art. 28 lid 1 sluit invorderingsrente uit voor zover met deze aanslag een "
            "aanslag wordt verrekend die op dezelfde belasting en hetzelfde tijdvak ziet. "
            "Deze tool kent dat verrekende deel niet. Vul hierboven alleen het bedrag in "
            "waarover wél rente loopt, of beoordeel de uitkomst met dat voorbehoud."
        )

    periode = periode_art28(vervaldag, betaaldatum)
    if periode is None:
        st.success(
            f"**Geen invorderingsrente.** Er is betaald op {nl_date(betaaldatum)} en "
            f"de enige of laatste betalingstermijn verviel op {nl_date(vervaldag)}. "
            f"Art. 28 lid 1 vraagt overschrijding van die termijn."
        )
        st.stop()
    uitgangspunten.append(("Datum betaling", nl_date(betaaldatum)))

elif grondslag == "28a":
    st.caption(
        "Art. 28a kent geen betalingstermijn: het tijdvak vangt aan op de dag ná de "
        "dagtekening van de aanslag of beschikking die tot uitbetaling strekt. Daarmee "
        "is er geen maand die haar werkelijke aantal dagen telt en geldt alleen de "
        "telling van 30 dagen per maand."
    )

    voorlopige_aanslag_9_5 = st.toggle(
        "Het betreft een voorlopige aanslag als bedoeld in art. 9 lid 5 met een uit te "
        "betalen bedrag",
        value=False,
        help="Art. 28a lid 4 verklaart dit artikel op zo'n aanslag niet van toepassing.",
    )
    if voorlopige_aanslag_9_5:
        st.error(
            "**Geen vergoeding van invorderingsrente.** Art. 28a lid 4 IW 1990 verklaart "
            "art. 28a niet van toepassing op een voorlopige aanslag als bedoeld in "
            "art. 9 lid 5 die een uit te betalen bedrag behelst als bedoeld in het zesde "
            "lid van dat artikel."
        )
        st.stop()

    te_wijten = st.toggle(
        "De vertraging is aan de belastingplichtige te wijten",
        value=False,
        help="Art. 28a lid 3: voor zover dat het geval is, wordt geen invorderingsrente "
             "vergoed.",
    )
    if te_wijten:
        st.error(
            "**Geen vergoeding van invorderingsrente.** Art. 28a lid 3 IW 1990 sluit de "
            "vergoeding uit voor zover het aan de belastingplichtige is te wijten dat de "
            "uitbetaling niet tijdig is geschied. Deze tool bepaalt dat deel niet."
        )
        st.stop()

    col_c, col_d = st.columns(2)
    with col_c:
        dagtekening = st.date_input(
            "Dagtekening aanslag of beschikking tot uitbetaling",
            value=vandaag - timedelta(days=120),
            min_value=MIN_DATUM, max_value=MAX_DATUM, format="DD-MM-YYYY",
        )
    with col_d:
        betaaldatum = st.date_input(
            "Datum waarop is uitbetaald of verrekend",
            value=vandaag, min_value=MIN_DATUM, max_value=MAX_DATUM, format="DD-MM-YYYY",
        )

    grondslagbedrag = st.number_input(
        "Uit te betalen bedrag (€)", min_value=0.0, value=10000.0, step=500.0, format="%.2f",
    )

    periode = periode_art28a(dagtekening, betaaldatum)
    if periode is None:
        grens = dagtekening + timedelta(weeks=6)
        st.success(
            f"**Geen vergoeding van invorderingsrente.** De ontvanger heeft uitbetaald "
            f"op {nl_date(betaaldatum)}, binnen zes weken na de dagtekening "
            f"({nl_date(grens)}). Art. 28a lid 1 vraagt overschrijding van die termijn."
        )
        st.stop()

    uitgangspunten.append(("Dagtekening uitbetaling", nl_date(dagtekening)))
    uitgangspunten.append(("Datum uitbetaling", nl_date(betaaldatum)))

    # Art. 28a lid 2, tweede volzin: de dagen waarover al belastingrente is
    # vergoed, tellen niet mee. Dit is de enige plek waar deze module en de
    # belastingrentemodule elkaar raken, en het is een gedeelde invoer en geen
    # gedeelde rekenkern.
    st.markdown("**Samenloop met belastingrente**")
    al_vergoed = st.toggle(
        "Over een deel van deze periode is al belastingrente vergoed (hoofdstuk VA AWR)",
        value=False,
        help="Art. 28a lid 2, tweede volzin: over die dagen wordt geen invorderingsrente "
             "berekend. Art. 28 en art. 28b kennen deze uitsluiting niet.",
    )
    if al_vergoed:
        col_e, col_f = st.columns(2)
        with col_e:
            br_van = st.date_input(
                "Belastingrente vergoed vanaf", value=None,
                min_value=MIN_DATUM, max_value=MAX_DATUM, format="DD-MM-YYYY",
            )
        with col_f:
            br_tot = st.date_input(
                "Belastingrente vergoed tot en met", value=None,
                min_value=MIN_DATUM, max_value=MAX_DATUM, format="DD-MM-YYYY",
            )
        if br_van is None or br_tot is None:
            st.error(
                "Vul beide datums van de al vergoede belastingrente in, of zet de "
                "schakelaar uit. Zonder die periode zou de tool te veel vergoeding "
                "berekenen."
            )
            st.stop()
        if br_tot < br_van:
            st.error("De einddatum van de vergoede belastingrente ligt vóór de begindatum.")
            st.stop()
        uitgesloten = [(br_van, br_tot)]
        uitgangspunten.append(
            ("Al vergoede belastingrente", f"{nl_date(br_van)} t/m {nl_date(br_tot)}"))

elif grondslag == "28b":
    afgewezen = st.toggle(
        "Er is eerder een verzoek om uitstel van betaling gedaan dat bij beschikking is "
        "afgewezen",
        value=False,
        help="Art. 28b lid 1 stelt dit als voorwaarde voor de vergoeding.",
    )
    if not afgewezen:
        st.info(
            "**Nog geen uitkomst.** Art. 28b lid 1 IW 1990 vergoedt alleen als de "
            "belastingschuldige eerder een verzoek om uitstel van betaling heeft gedaan "
            "voor het bestreden bedrag en de ontvanger dat bij beschikking heeft "
            "afgewezen. Zet de schakelaar aan als dat zo is."
        )
        st.stop()

    col_c, col_d = st.columns(2)
    with col_c:
        dagtekening_vermindering = st.date_input(
            "Dagtekening van de vermindering of herziening",
            value=vandaag, min_value=MIN_DATUM, max_value=MAX_DATUM, format="DD-MM-YYYY",
        )
    with col_d:
        grondslagbedrag = st.number_input(
            "Terug te geven bedrag (€)", min_value=0.0, value=10000.0, step=500.0,
            format="%.2f",
            help="Art. 28b lid 2, slot: het terug te geven bedrag is de grondslag.",
        )

    periode = periode_art28b(vervaldag, dagtekening_vermindering)
    if periode is None:
        st.warning(
            "Geen vergoeding: het tijdvak zou eindigen vóór het begint. Controleer de "
            "dagtekening van de vermindering."
        )
        st.stop()
    uitgangspunten.append(("Dagtekening vermindering", nl_date(dagtekening_vermindering)))

# ── Uitstel: uitvragen en blokkeren ─────────────────────────────────────────
# Besluit van Sylvain: de opschorting tijdens uitstel (art. 28 lid 3 en 4) wordt
# in deze versie niet doorgerekend. De tool vraagt uit of er uitstel is verleend
# en geeft geen uitkomst zolang dat niet is ingevuld. Dat is dezelfde lijn die
# de rentepagina's al volgen bij een onvolledige verklaring.
if grondslag == "28":
    st.markdown("**Uitstel van betaling**")
    uitstel = st.radio(
        "Is voor deze aanslag uitstel van betaling verleend?",
        options=["", "nee", "ja"],
        format_func=lambda k: {"": "nog niet ingevuld", "nee": "Nee",
                               "ja": "Ja"}[k],
        horizontal=True,
        help="Art. 28 lid 3 IW 1990 brengt geen invorderingsrente in rekening over de "
             "tijd waarvoor uitstel is verleend krachtens negen genoemde leden van "
             "art. 25. Deze tool rekent die opschorting niet uit.",
    )
    if uitstel == "":
        st.error(
            "**Nog geen uitkomst.** Vul eerst in of er uitstel van betaling is verleend. "
            "Art. 28 lid 3 IW 1990 schort de rente op over de tijd waarvoor uitstel is "
            "verleend krachtens art. 25 lid 3, 5, 8, 9, 11, 17, 18, 19 of 21. Deze "
            "versie rekent die opschorting niet door, dus zonder dit antwoord zou de "
            "uitkomst te hoog kunnen zijn."
        )
        st.stop()

    if uitstel == "ja":
        grond = st.selectbox(
            "Op welke grond is het uitstel verleend?",
            options=[""] + [code for code, _ in UITSTELGRONDEN],
            format_func=lambda k: "nog niet ingevuld" if k == "" else dict(UITSTELGRONDEN)[k],
        )
        if grond == "":
            st.error("Vul de grond van het uitstel in.")
            st.stop()

        st.error(
            "**Geen uitkomst: deze tool rekent de opschorting tijdens uitstel niet door.** "
            f"Het uitstel is verleend op grond van {dict(UITSTELGRONDEN)[grond]}. "
            "Art. 28 lid 3 IW 1990 brengt over die tijd geen invorderingsrente in "
            "rekening. Een uitkomst zonder die opschorting zou te hoog zijn."
        )
        herleving = HERLEVING_NA_UITSTEL.get(grond)
        if herleving:
            st.info(
                "Wordt het uitstel beëindigd of wordt er niet binnen de uitsteltermijn "
                f"betaald, dan loopt de rente alsnog (art. 28 lid 4 IW 1990). {herleving}"
            )
        else:
            st.info(
                "Art. 28 lid 4 IW 1990 noemt deze grond niet, en art. 6 van het "
                "Uitvoeringsbesluit IW 1990 wijst er geen herlevingstijdvak voor aan. "
                "Over het tijdvak na een beëindiging van dit uitstel doet deze tool dus "
                "geen uitspraak."
            )
        st.stop()

    uitgangspunten.append(("Uitstel van betaling verleend", "nee"))

    # Art. 28 lid 5: de aangewezen gevallen waarin geen rente in rekening wordt
    # gebracht, plus de beleidsmatige vermindering uit de Leidraad.
    with st.expander("Uitzonderingen: gevallen waarin geen rente in rekening wordt gebracht"):
        st.caption(
            "Art. 28 lid 5 IW 1990 laat bij algemene maatregel van bestuur gevallen "
            "aanwijzen waarin het in rekening brengen van invorderingsrente door "
            "uitzonderlijke omstandigheden niet redelijk is. Hoofdstuk II van het "
            "Uitvoeringsbesluit IW 1990 wijst er twee aan. De derde regel hieronder is "
            "beleid uit de Leidraad Invordering 2008 en heeft een andere status: de "
            "ontvanger vermindert de rente dan achteraf tot nihil."
        )
        gekozen = []
        for uitzondering in UITZONDERINGEN:
            label = uitzondering["titel"]
            if uitzondering["beleidsmatig"]:
                label += "  (beleid, geen AMvB)"
            if st.checkbox(label, key="uitz_" + uitzondering["code"]):
                gekozen.append(uitzondering)
            st.caption(f"{uitzondering['uitleg']}  \n*{uitzondering['bron']}*")

    if gekozen:
        regels = "\n".join(f"- {u['titel']} ({u['bron']})" for u in gekozen)
        st.error(
            "**Geen uitkomst: er is een uitzondering aangevinkt.** Over (een deel van) "
            "deze periode wordt geen invorderingsrente in rekening gebracht, of wordt de "
            "rente achteraf tot nihil verminderd:\n\n" + regels + "\n\n"
            "Deze tool bepaalt niet over welke dagen de uitzondering precies loopt en "
            "geeft daarom geen bedrag."
        )
        st.stop()

# ── Grenzen van de tariefreeks ──────────────────────────────────────────────
vanaf, tot_en_met = periode

if buiten_bereik(vanaf, tarieven):
    st.error(
        f"De renteperiode begint op {nl_date(vanaf)} en daarmee vóór "
        f"{nl_date(oudste_ingang(tarieven))}, de oudste ingangsdatum die deze tool kent. "
        f"Het Besluit belasting- en invorderingsrente geldt pas vanaf 1 juni 2020. Voor "
        f"deze periode kan hier geen betrouwbare uitkomst worden gegeven."
    )
    st.stop()

if tot_en_met > vandaag:
    laatste_ingang, laatste_percentage = max(tarieven, key=lambda rij: rij[0])
    st.warning(
        "Deze berekening loopt door tot een toekomstige datum en is een raming. Vanaf "
        f"{nl_date(laatste_ingang)} gebruikt de tool het laatst opgenomen percentage van "
        f"{nl_pct(laatste_percentage)}. Het percentage van de invorderingsrente wordt bij "
        "losse wijziging van het besluit vastgesteld en niet op een vast jaarmoment, dus "
        "een latere wijziging is niet te voorspellen."
    )

uit = bereken(
    grondslagbedrag, vanaf, tot_en_met, tarieven, richting,
    vervalmaand=vervalmaand,
    laatste_betaling=laatste_betaling,
    uitgesloten=uitgesloten,
)

# ── Uitvoer ─────────────────────────────────────────────────────────────────
kop = "INVORDERINGSRENTE IN REKENING" if richting == "in_rekening" else "INVORDERINGSRENTE VERGOED"
kleur = "#1a4d2e,#1e5c36" if richting == "in_rekening" else "#24304A,#2f3d5d"

st.html(f"""
<div style="background:linear-gradient(135deg,{kleur});color:white;
  border-radius:14px;padding:20px 22px;margin-bottom:12px;text-align:center;
  box-shadow:0 4px 16px rgba(26,77,46,.25);">
  <div style="font-size:12px;color:rgba(255,255,255,0.8);margin-bottom:6px;letter-spacing:.05em;">
    {kop}
  </div>
  <div style="font-size:36px;font-weight:bold;font-family:monospace;">
    {nl_euro_heel(uit["bedrag"])}
  </div>
</div>
""")

if uit["kwijt_door_drempel"]:
    st.success(
        f"De berekende rente van {nl_euro_heel(uit['afgerond'])} blijft onder het "
        f"drempelbedrag van {nl_euro_heel(uit['drempel'])} dat op {nl_date(tot_en_met)} "
        f"gold. Art. 33 van de Uitvoeringsregeling IW 1990 brengt dat bij de enige of "
        f"laatste betaling niet in rekening."
    )

col1, col2, col3 = st.columns(3)

with col1:
    telling = ("30 dagen per maand, behalve de vervaldagmaand"
               if vervalmaand else "30 dagen per maand")
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Renteperiode</div>
      <div class="value" style="font-size:14px;">{nl_date(vanaf)} t/m {nl_date(tot_en_met)}</div>
      <div class="sub">{uit["dagen"]} dagen ({telling})</div>
    </div>""", unsafe_allow_html=True)

with col2:
    uniek = sorted({p["pct"] for p in uit["perioden"]})
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">Rentetarief (per jaar)</div>
      <div class="value">{" / ".join(nl_pct(p) for p in uniek)}</div>
      <div class="sub">Enkelvoudig, 360 dagen</div>
    </div>""", unsafe_allow_html=True)

with col3:
    naam = {"28": "Betaald bedrag", "28a": "Uit te betalen bedrag",
            "28b": "Terug te geven bedrag"}[grondslag]
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">{naam}</div>
      <div class="value" style="font-size:16px;">{nl_euro(grondslagbedrag)}</div>
      <div class="sub">Art. {grondslag} IW 1990</div>
    </div>""", unsafe_allow_html=True)

if uit["dagen_uitgesloten"]:
    st.info(
        f"{uit['dagen_uitgesloten']} dagen tellen niet mee omdat daarover al "
        f"belastingrente is vergoed (art. 28a lid 2, tweede volzin IW 1990)."
    )

st.markdown("**Berekening per periode**")
for p in uit["perioden"]:
    afgetrokken = (f" &nbsp;·&nbsp; {p['dagen_uitgesloten']} dagen afgetrokken"
                   if p["dagen_uitgesloten"] else "")
    st.markdown(f"""
    <div class="bk-tile" style="margin-bottom:6px">
      <div class="label">{nl_date(p['start'])} t/m {nl_date(p['eind'])}
        &nbsp;·&nbsp; {nl_pct(p['pct'])} &nbsp;·&nbsp; {p['dagen']} dagen{afgetrokken}</div>
      <div class="value">{p['dagen']} × {nl_pct(p['pct'])}</div>
    </div>""", unsafe_allow_html=True)

st.caption(
    f"De deelperioden worden eerst opgeteld en pas daarna wordt er afgerond: "
    f"{uit['dagen']} dagen leveren {nl_euro(uit['onafgerond'])} op, en dat wordt "
    f"{'naar beneden' if richting == 'in_rekening' else 'naar boven'} afgerond op "
    f"{nl_euro_heel(uit['afgerond'])} (art. 30 lid 1 en art. 32 Uitvoeringsregeling "
    f"IW 1990)."
)

with st.expander("Uitgangspunten van deze berekening", expanded=False):
    regels = "\n".join(f"| {label} | {waarde} |" for label, waarde in uitgangspunten)
    st.markdown(f"""
| | |
|---|---|
| Grondslag | {GRONDSLAGEN[grondslag]} |
{regels}
| Renteperiode | {nl_date(vanaf)} t/m {nl_date(tot_en_met)} |
| Aantal dagen | {uit["dagen"]} |
| Uitsluiting belastingrente van toepassing | {"ja" if UITSLUITING_BELASTINGRENTE[grondslag] else "nee"} |
| Bedrag vóór afronding | {nl_euro(uit["onafgerond"])} |
| Drempelbedrag art. 33 | {nl_euro_heel(uit["drempel"]) if uit["drempel"] is not None else "niet van toepassing"} |
""")

with st.expander("Art. 28c — heffing in strijd met het Unierecht (alleen signalering)"):
    st.markdown(ART28C_SIGNALERING)
    st.caption(
        "Wie die vergoeding wil, moet het verzoek tijdig indienen. Voor een beschikking "
        f"met dagtekening vandaag ({nl_date(vandaag)}) eindigt die termijn op "
        f"{nl_date(uiterste_verzoekdatum_28c(vandaag))}."
    )

st.caption(
    "Rekenmethode volgens hoofdstuk V van de Invorderingswet 1990 en hoofdstuk III van "
    "de Uitvoeringsregeling Invorderingswet 1990: enkelvoudige rente, de maand waarin de "
    "enige of laatste betalingstermijn vervalt op haar werkelijke aantal dagen met "
    "februari altijd op 28, verder 30 dagen per maand en 360 per jaar, en één afronding "
    "over het geheel. De tarieven en hun vindplaats staan in `_invorderingsrente.py`; "
    "alle bronnen zijn op 18 september 2026 uit de KOOP-repository gehaald en tegen de "
    "hashcode in het manifest gecontroleerd."
)
