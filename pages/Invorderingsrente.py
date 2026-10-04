import streamlit as st
from datetime import date, timedelta

from _invorderingsrente import (
    ART28C_TOELICHTING,
    HERLEVING_NA_UITSTEL,
    TARIEVEN_IN_REKENING,
    TARIEVEN_TE_VERGOEDEN,
    UITSLUITING_BELASTINGRENTE,
    UITSTELGRONDEN,
    UITZONDERINGEN,
    bereken,
    buiten_bereik,
    nl_date,
    nl_euro,
    nl_euro_heel,
    nl_pct,
    oudste_ingang,
    periode_art28,
    periode_art28a,
    periode_art28b,
    periode_art28c,
    uiterste_verzoekdatum_28c,
    uitstel_uitsluiting,
    vervaldag_op,
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
    "(art. 28a), als een aanslag wordt verminderd na een afgewezen uitstelverzoek "
    "(art. 28b) of als belasting in strijd met het Unierecht is geheven (art. 28c). "
    "De dagentelling en de afronding volgen de Uitvoeringsregeling en wijken "
    "af van die bij belastingrente.",
)

GRONDSLAGEN = {
    "28": "Art. 28 — rente bij te late betaling (in rekening gebracht)",
    "28a": "Art. 28a — vergoeding als de ontvanger niet binnen 6 weken uitbetaalt",
    "28b": "Art. 28b — vergoeding bij vermindering na een afgewezen uitstelverzoek",
    "28c": "Art. 28c — vergoeding bij heffing in strijd met het Unierecht",
}

UITSLUITREDEN = {
    "28": "voor die dagen uitstel van betaling was verleend (art. 28 lid 3 IW 1990)",
    "28a": "daarover al belastingrente is vergoed (art. 28a lid 2, tweede volzin IW 1990)",
    "28b": "daarover al belastingrente is vergoed",
    "28c": "daarover belastingrente of invorderingsrente op grond van art. 28b wordt "
           "vergoed (art. 28c lid 2, tweede volzin IW 1990)",
}

grondslag = st.radio(
    "Welke grondslag?",
    options=list(GRONDSLAGEN),
    format_func=lambda k: GRONDSLAGEN[k],
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
        vervaldag = vervaldag_op(dagtekening, aanslag_type)
        st.caption(
            f"De betalingstermijn vervalt op **{nl_date(vervaldag)}** (art. 9 IW 1990, "
            f"onderdeel 9.5 Leidraad Invordering 2008): dat is de uiterste betaaldatum. "
            f"Die maand telt haar werkelijke aantal dagen."
        )

    vervalmaand = vervalmaand_van(vervaldag)
    invorderbaar = vervaldag + timedelta(days=1)
    uitgangspunten.append(("Dagtekening aanslagbiljet", nl_date(dagtekening)))
    uitgangspunten.append(("Vervaldag (uiterste betaaldatum)", nl_date(vervaldag)))
    uitgangspunten.append(("Invorderbaar vanaf", nl_date(invorderbaar)))

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
            f"De rente loopt vanaf de dag daarna tot en met de dag vóór de betaling "
            f"(art. 28 lid 2), en dat tijdvak bevat hier geen dag."
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

elif grondslag == "28c":
    st.caption(ART28C_TOELICHTING)
    col_c, col_d = st.columns(2)
    with col_c:
        dagtekening_beschikking = st.date_input(
            "Dagtekening van de beschikking tot teruggaaf",
            value=vandaag, min_value=MIN_DATUM, max_value=MAX_DATUM, format="DD-MM-YYYY",
            help="De beschikking van de inspecteur op grond waarvan de ontvanger belasting "
                 "moet teruggeven omdat die in strijd met het Unierecht is geheven.",
        )
    with col_d:
        grondslagbedrag = st.number_input(
            "Terug te geven bedrag (€)", min_value=0.0, value=10000.0, step=500.0,
            format="%.2f",
            help="Art. 28c lid 2: het aan de belastingschuldige terug te geven of "
                 "teruggegeven bedrag is de grondslag.",
        )

    col_e, col_f = st.columns(2)
    with col_e:
        betaald_op = st.date_input(
            "Datum waarop de belasting is betaald, voldaan of afgedragen",
            value=vandaag - timedelta(days=400),
            min_value=MIN_DATUM, max_value=MAX_DATUM, format="DD-MM-YYYY",
        )
    with col_f:
        terugbetaald_op = st.date_input(
            "Datum van de terugbetaling",
            value=vandaag, min_value=MIN_DATUM, max_value=MAX_DATUM, format="DD-MM-YYYY",
        )

    uiterste = uiterste_verzoekdatum_28c(dagtekening_beschikking)
    verzoek = st.radio(
        "Is het verzoek om vergoeding van invorderingsrente tijdig ingediend?",
        options=["", "ja", "nee"],
        format_func=lambda k: {"": "nog niet ingevuld", "ja": "Ja", "nee": "Nee"}[k],
        horizontal=True,
        help=f"Art. 28c lid 3: de termijn eindigt zes weken na de dagtekening van de "
             f"beschikking, dus op {nl_date(uiterste)}.",
    )
    if verzoek == "":
        st.error(
            "**Nog geen uitkomst.** Art. 28c lid 1 IW 1990 vergoedt alleen op verzoek, en "
            f"dat verzoek moet uiterlijk {nl_date(uiterste)} zijn ingediend (lid 3). Vul "
            "in of dat is gebeurd."
        )
        st.stop()
    if verzoek == "nee":
        st.error(
            "**Geen vergoeding van invorderingsrente.** Zonder tijdig verzoek bestaat "
            f"geen recht op vergoeding op grond van art. 28c (termijn tot {nl_date(uiterste)})."
        )
        st.stop()

    periode = periode_art28c(betaald_op, terugbetaald_op)
    if periode is None:
        st.success(
            f"**Geen vergoeding van invorderingsrente.** Het tijdvak loopt van de dag na "
            f"de betaling ({nl_date(betaald_op)}) tot de dag vóór de terugbetaling "
            f"({nl_date(terugbetaald_op)}) en bevat hier geen dag."
        )
        st.stop()
    uitgangspunten.append(("Dagtekening beschikking", nl_date(dagtekening_beschikking)))
    uitgangspunten.append(("Verzoek uiterlijk", nl_date(uiterste)))
    uitgangspunten.append(("Belasting betaald op", nl_date(betaald_op)))
    uitgangspunten.append(("Datum terugbetaling", nl_date(terugbetaald_op)))

    # Art. 28c lid 2, tweede volzin: twee soorten dagen tellen niet mee.
    for sleutel, wat, vanaf_label, tot_label in (
        ("belastingrente", "belastingrente is vergoed (hoofdstuk VA AWR)",
         "Vergoede belastingrente: vanaf", "Vergoede belastingrente: tot en met"),
        ("28b", "invorderingsrente is vergoed op grond van art. 28b",
         "Vergoeding art. 28b: vanaf", "Vergoeding art. 28b: tot en met"),
    ):
        if st.toggle(f"Over een deel van dit tijdvak {wat}", value=False,
                     help="Art. 28c lid 2, tweede volzin: over die dagen wordt geen "
                          "invorderingsrente berekend."):
            col_g, col_h = st.columns(2)
            with col_g:
                u_van = st.date_input(vanaf_label, value=None, min_value=MIN_DATUM,
                                      max_value=MAX_DATUM, format="DD-MM-YYYY")
            with col_h:
                u_tot = st.date_input(tot_label, value=None, min_value=MIN_DATUM,
                                      max_value=MAX_DATUM, format="DD-MM-YYYY")
            if u_van is None or u_tot is None:
                st.error("Vul beide datums in, of zet de schakelaar uit. Zonder die periode "
                         "zou de tool te veel vergoeding berekenen.")
                st.stop()
            if u_tot < u_van:
                st.error("De einddatum ligt vóór de begindatum.")
                st.stop()
            uitgesloten.append((u_van, u_tot))
            uitgangspunten.append((f"Uitgesloten ({sleutel})",
                                   f"{nl_date(u_van)} t/m {nl_date(u_tot)}"))

# ── Uitstel: opschorting en herleving ───────────────────────────────────────
# Art. 28 lid 3 brengt geen rente in rekening over de tijd waarvoor uitstel is
# verleend; lid 4 en art. 6 Uitvoeringsbesluit IW 1990 laten haar herleven na een
# beëindiging. De rekenregels staan in `uitstel_uitsluiting()`. Wat de wet niet
# regelt geeft hier geen uitkomst.
if grondslag == "28":
    st.markdown("**Uitstel van betaling**")
    uitstel = st.radio(
        "Is voor deze aanslag uitstel van betaling verleend?",
        options=["", "nee", "ja"],
        format_func=lambda k: {"": "nog niet ingevuld", "nee": "Nee",
                               "ja": "Ja"}[k],
        horizontal=True,
        help="Art. 28 lid 3 IW 1990 brengt geen invorderingsrente in rekening over de "
             "tijd waarvoor uitstel is verleend krachtens art. 25 lid 3, 5, 8, 9, 11, "
             "17, 18, 19 of 21.",
    )
    if uitstel == "":
        st.error(
            "**Nog geen uitkomst.** Vul eerst in of er uitstel van betaling is verleend. "
            "Art. 28 lid 3 IW 1990 schort de rente op over de tijd waarvoor uitstel is "
            "verleend krachtens art. 25 lid 3, 5, 8, 9, 11, 17, 18, 19 of 21, dus zonder "
            "dit antwoord zou de uitkomst te hoog kunnen zijn."
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

        col_u, col_v = st.columns(2)
        with col_u:
            uitstel_van = st.date_input(
                "Uitstel verleend vanaf", value=invorderbaar,
                min_value=MIN_DATUM, max_value=MAX_DATUM, format="DD-MM-YYYY",
            )
        with col_v:
            uitstel_tot = st.date_input(
                "Uitstel verleend tot en met (leeg als er geen einddatum is)", value=None,
                min_value=MIN_DATUM, max_value=MAX_DATUM, format="DD-MM-YYYY",
            )

        beeindigd = False
        gebeurtenis = None
        if grond in HERLEVING_NA_UITSTEL:
            beeindigd = st.toggle(
                "Het uitstel is door de ontvanger beëindigd", value=False,
                help="Art. 28 lid 4 IW 1990: dan loopt de rente weer vanaf een dag die "
                     "art. 6 Uitvoeringsbesluit IW 1990 aanwijst.",
            )
            if beeindigd:
                gebeurtenis = st.date_input(
                    "Datum van de handeling of gebeurtenis waarop het uitstel is beëindigd",
                    value=None, min_value=MIN_DATUM, max_value=MAX_DATUM,
                    format="DD-MM-YYYY",
                )
        else:
            st.caption(
                "Art. 28 lid 4 IW 1990 noemt art. 25 lid 3 niet, en art. 6 van het "
                "Uitvoeringsbesluit IW 1990 wijst er geen herlevingstijdvak voor aan. "
                "Alleen de tijd waarvoor het uitstel is verleend telt dus niet mee."
            )

        opschorting = uitstel_uitsluiting(
            grond, uitstel_van, uitstel_tot, beeindigd, gebeurtenis, betaaldatum)
        if opschorting["blokkade"]:
            st.error("**Geen uitkomst.** " + opschorting["blokkade"])
            st.stop()
        uitgesloten = uitgesloten + opschorting["uitgesloten"]
        uitgangspunten.append(("Uitstel verleend", f"ja, grond {grond}"))
        for a, b in opschorting["uitgesloten"]:
            uitgangspunten.append(("Rente opgeschort", f"{nl_date(a)} t/m {nl_date(b)}"))
        if opschorting["herleving"]:
            uitgangspunten.append(("Rente herleeft op", nl_date(opschorting["herleving"])))
    else:
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
            "28b": "Terug te geven bedrag", "28c": "Terug te geven bedrag"}[grondslag]
    st.markdown(f"""
    <div class="bk-tile">
      <div class="label">{naam}</div>
      <div class="value" style="font-size:16px;">{nl_euro(grondslagbedrag)}</div>
      <div class="sub">Art. {grondslag} IW 1990</div>
    </div>""", unsafe_allow_html=True)

if uit["dagen_uitgesloten"]:
    st.info(
        f"{uit['dagen_uitgesloten']} dagen tellen niet mee omdat {UITSLUITREDEN[grondslag]}."
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

st.caption(
    "Rekenmethode volgens hoofdstuk V van de Invorderingswet 1990 en hoofdstuk III van "
    "de Uitvoeringsregeling Invorderingswet 1990: enkelvoudige rente, de maand waarin de "
    "enige of laatste betalingstermijn vervalt op haar werkelijke aantal dagen met "
    "februari altijd op 28, verder 30 dagen per maand en 360 per jaar, en één afronding "
    "over het geheel. De tarieven en hun vindplaats staan in `_invorderingsrente.py`; "
    "alle bronnen zijn op 18 september 2026 uit de KOOP-repository gehaald en tegen de "
    "hashcode in het manifest gecontroleerd."
)
