import re

import streamlit as st
import requests
from datetime import date, timedelta
from fpdf import FPDF
from _auto_paste import auto_paste_input as _auto_paste_input
from _format import nl_date, nl_euro
from _ui import paginakop, paginastijl, veilig
from _auto_calc import bijtelling as _bijtelling
from _auto_calc import btw_correctie as _btw_correctie
from _auto_calc import (
    bijtelling_youngtimer,
    is_nulemissie,
    is_plafondvrij,
    is_youngtimer,
    maandfractie,
    vervaldatum_vaste_termijn,
    waarschuwing_regimejaar,
    youngtimer_leeftijdsgrens,
)

# Een Nederlands kenteken is zes tekens, cijfers en hoofdletters. Streepjes en
# kleine letters worden weggehaald voordat er iets naar het RDW gaat.
KENTEKEN_PATROON = re.compile(r"^[A-Z0-9]{6}$")


def normaliseer_kenteken(ruw: str) -> str | None:
    """Geeft het kenteken in RDW-vorm terug, of None als het niet geldig is."""
    opgeschoond = re.sub(r"[^A-Za-z0-9]", "", ruw or "").upper()
    return opgeschoond if KENTEKEN_PATROON.match(opgeschoond) else None


def _rdw_datum(waarde) -> date | None:
    """RDW levert datums als 'YYYYMMDD'."""
    tekst = str(waarde or "")
    if len(tekst) != 8 or not tekst.isdigit():
        return None
    try:
        return date(int(tekst[:4]), int(tekst[4:6]), int(tekst[6:8]))
    except ValueError:
        return None


@st.cache_data(show_spinner=False, ttl=600)
def _rdw_ophalen(kn: str) -> dict | None:
    # K2: nooit ongevalideerde tekens in de RDW-querystring zetten. Alleen zes
    # cijfers en hoofdletters komen hier voorbij.
    kn = normaliseer_kenteken(kn)
    if kn is None:
        return None
    try:
        r = requests.get(
            "https://opendata.rdw.nl/resource/m9d7-ebf2.json",
            params={"kenteken": kn},
            timeout=8,
        )
        if not r.ok:
            return None
        voertuigen = r.json()
        if not voertuigen:
            return None
        v = voertuigen[0]
        rb = requests.get(
            "https://opendata.rdw.nl/resource/8ys7-d773.json",
            params={"kenteken": kn},
            timeout=8,
        )
        brandstof, co2 = "Onbekend", None
        if rb.ok:
            brandstoffen = rb.json()
            if brandstoffen:
                b = brandstoffen[0]
                brandstof = b.get("brandstof_omschrijving", "Onbekend")
                try:
                    co2 = int(float(b["co2_uitstoot_gecombineerd"]))
                except (KeyError, ValueError, TypeError):
                    pass
        cat_str = v.get("catalogusprijs")
        datum_eerste_toelating = _rdw_datum(v.get("datum_eerste_toelating"))
        return {
            "voertuig": (v.get("merk", "") + " " + v.get("handelsbenaming", "")).strip(),
            "bouwjaar": str(v.get("datum_eerste_toelating", ""))[:4],
            "brandstof": brandstof,
            "co2": co2,
            "catalogusprijs": int(cat_str) if cat_str else None,
            "datum_tenaamstelling": _rdw_datum(v.get("datum_tenaamstelling")),
            "datum_eerste_toelating": datum_eerste_toelating,
        }
    except Exception:
        return None


def _pdf_bedrag(x: float) -> str:
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"EUR {s}"


def _pdf_str(s: str) -> str:
    return s.replace("—", "-").replace("–", "-").replace("≤", "<=").replace("€", "EUR")


def _maak_pdf(auto_results: list, klant_naam: str, klant_nr: str, jaar: int) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(25, 20, 25)
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_fill_color(36, 48, 74)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 11, "BTW-correctie en bijtelling zakelijke auto", fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    def _rij(label, waarde):
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(50, 6, label)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, waarde, new_x="LMARGIN", new_y="NEXT")

    def _sectie(titel):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(36, 48, 74)
        pdf.cell(0, 7, titel, new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(200, 210, 225)
        pdf.line(25, pdf.get_y(), 185, pdf.get_y())
        pdf.ln(2)

    if klant_naam or klant_nr:
        _sectie("Klantgegevens")
        if klant_naam:
            _rij("Naam:", klant_naam)
        if klant_nr:
            _rij("Klantnummer:", klant_nr)

    _sectie(f"Berekening {jaar}")

    for i, r in enumerate(auto_results):
        label = f"Auto {i + 1}" if len(auto_results) > 1 else "Voertuig"
        _sectie(label)
        _rij("Kenteken:", r["kenteken"])
        _rij("Voertuig:", f"{r['auto']['voertuig']} ({r['auto']['bouwjaar']})")
        _rij("Brandstof:", r["auto"]["brandstof"])
        co2_txt = f"{r['auto']['co2']} g/km" if r["auto"]["co2"] is not None else "Onbekend"
        _rij("CO2-uitstoot:", co2_txt)
        det = r["auto"].get("datum_eerste_toelating")
        _rij("Eerste toelating:", nl_date(det) if det else "Onbekend")
        ts = r["auto"].get("datum_tenaamstelling")
        _rij("In gebruik vanaf:", nl_date(ts) if ts else "Onbekend")
        _rij("Catalogusprijs:", _pdf_bedrag(r["catalogusprijs"]))
        _rij("Marge-auto:", "Ja" if r["marge"] else "Nee")
        _rij("Periode:", f"{r['periode_label']} ({r['dagen']} dagen / "
                         f"{r['maanden']:.2f} van 12 maanden)")
        if r["youngtimer"]:
            wev_txt = _pdf_bedrag(r["wev"]) if r["wev"] else "niet ingevuld"
            _rij("Youngtimer:", f"Ja - bijtelling 35% over WEV ({wev_txt})")

        pdf.ln(2)
        pdf.set_fill_color(230, 238, 255)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, _pdf_str(f"BTW-correctie privegebruik ({r['btw_label']})"),
                 fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(26, 58, 110)
        pdf.cell(0, 8, _pdf_bedrag(r["btw"]), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        pdf.set_fill_color(225, 245, 232)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, _pdf_str(f"Bijtelling ({r['bij_label']})"), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(26, 77, 46)
        pdf.cell(0, 8, _pdf_bedrag(r["bij"]) if r["bij"] is not None else "-",
                 new_x="LMARGIN", new_y="NEXT")

    if len(auto_results) > 1:
        _sectie("Totaal")
        total_btw = sum(r["btw"] for r in auto_results)
        total_bij = sum(r["bij"] for r in auto_results if r["bij"] is not None)
        pdf.ln(1)
        pdf.set_fill_color(220, 232, 255)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, "Totaal BTW-correctie", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(26, 58, 110)
        pdf.cell(0, 8, _pdf_bedrag(total_btw), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        pdf.set_fill_color(210, 240, 220)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, "Totaal bijtelling", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(26, 77, 46)
        pdf.cell(0, 8, _pdf_bedrag(total_bij), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, f"Gegenereerd op {date.today().strftime('%d-%m-%Y')} via belastingtooljoindk.streamlit.app",
             new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 5,
        "Berekening op basis van forfaitmethode (art. 4 lid 2 Wet OB). De "
        "BTW-correctie is naar maanden berekend, conform het rekenvoorbeeld van de "
        "Belastingdienst; de bijtelling naar dagen. Bij een IB-ondernemer is de "
        "bijtelling nooit hoger dan de totale autokosten van het jaar - die kosten "
        "zijn hier niet bekend en dus niet toegepast. "
        "Voertuiggegevens via RDW Open Data. Indicatief - geen fiscaal advies.")

    return bytes(pdf.output())


paginastijl()

paginakop(
    "🚗 Auto BTW privé",
    "BTW-correctie en bijtelling voor privégebruik zakelijke auto — forfaitmethode, "
    "RDW-koppeling.",
)

# ── Globale instellingen ──────────────────────────────────────────────────────
huidig_jaar = date.today().year
col_a, col_n, col_nr = st.columns([1, 2, 1])
with col_a:
    berekeningsjaar = st.selectbox(
        "Berekeningsjaar",
        options=list(range(huidig_jaar, huidig_jaar - 8, -1)),
        index=0,
    )
with col_n:
    klant_naam = st.text_input("Klantnaam", key="klant_naam", placeholder="Optioneel — voor de PDF")
with col_nr:
    klant_nr = st.text_input("Klantnummer", key="klant_nr", placeholder="bijv. 12345")


# ── Session state: lijst van auto's ─────────────────────────────────────────
if "autos" not in st.session_state:
    st.session_state["autos"] = [{"id": 0, "kenteken": ""}]
if "_next_id" not in st.session_state:
    st.session_state["_next_id"] = 1

n_autos = len(st.session_state["autos"])

# ── Per-auto secties ──────────────────────────────────────────────────────────
auto_results = []

for idx, auto_entry in enumerate(list(st.session_state["autos"])):
    car_id = auto_entry["id"]

    with st.container(border=True):

        # Label + verwijderknop
        hcol1, hcol2 = st.columns([20, 1])
        with hcol1:
            if n_autos > 1:
                st.markdown(f'<div class="auto-nr">Auto {idx + 1}</div>', unsafe_allow_html=True)
        with hcol2:
            if idx > 0:
                if st.button("✕", key=f"del_{car_id}", help="Verwijder deze auto"):
                    st.session_state["autos"] = [a for a in st.session_state["autos"] if a["id"] != car_id]
                    st.rerun()

        # Kenteken
        st.markdown('<p style="font-size:13px;font-weight:600;color:#31333F;margin-bottom:3px;">Kenteken</p>',
                    unsafe_allow_html=True)
        _should_focus = st.session_state.get("_focus_car_id") == car_id
        if _should_focus:
            del st.session_state["_focus_car_id"]
        _kent_val = _auto_paste_input(
            value=auto_entry["kenteken"],
            pattern=r"^[A-Z0-9]{6}$",
            placeholder="bijv. TH-992-G",
            key=f"kenteken_comp_{car_id}",
            default=None,
            focus=_should_focus,
        )
        if _kent_val is not None and _kent_val != auto_entry["kenteken"]:
            auto_entry["kenteken"] = _kent_val
            st.rerun()

        kenteken_i = auto_entry["kenteken"]

        if len(kenteken_i) < 6:
            if len(kenteken_i) > 0:
                st.caption(f"{len(kenteken_i)}/6 tekens — voer een geldig kenteken in.")
            auto_results.append(None)
            continue

        with st.spinner("RDW ophalen…"):
            auto_data_i = _rdw_ophalen(kenteken_i)

        if auto_data_i is None:
            st.error(f"Kenteken **{kenteken_i}** niet gevonden in het RDW, of geen geldig kenteken.")
            auto_results.append(None)
            continue

        # Auto-info strip
        ts_i = auto_data_i["datum_tenaamstelling"]
        co2_txt = f"{auto_data_i['co2']} g/km" if auto_data_i["co2"] is not None else "CO₂ onbekend"
        cat_txt = nl_euro(auto_data_i["catalogusprijs"]) if auto_data_i["catalogusprijs"] else "—"
        ts_html = (f' &nbsp;·&nbsp; <span style="color:#1a4d2e;font-weight:600;">In gebruik vanaf {nl_date(ts_i)}</span>'
                   if ts_i else "")
        det_i = auto_data_i["datum_eerste_toelating"]
        verval_i = vervaldatum_vaste_termijn(det_i)
        verval_html = (
            f' &nbsp;·&nbsp; <span style="color:#6b7a99;">Bijtellingsregime {det_i.year} '
            f'vast t/m {nl_date(verval_i - timedelta(days=1))}</span>'
            if verval_i else ""
        )
        st.markdown(
            f'<div class="auto-info">'
            f'<b>{veilig(kenteken_i)}</b> &nbsp;·&nbsp; {veilig(auto_data_i["voertuig"])} &nbsp;·&nbsp; '
            f'Bouwjaar {veilig(auto_data_i["bouwjaar"])} &nbsp;·&nbsp; '
            f'{veilig(auto_data_i["brandstof"])} &nbsp;·&nbsp; '
            f'{co2_txt} &nbsp;·&nbsp; Catalogusprijs {cat_txt}{ts_html}{verval_html}</div>',
            unsafe_allow_html=True,
        )

        # Catalogusprijs
        catalogusprijs_i = float(auto_data_i["catalogusprijs"]) if auto_data_i["catalogusprijs"] else None
        if catalogusprijs_i is None:
            st.warning("Catalogusprijs niet gevonden — vul handmatig in.")
            cat_h = st.number_input("Catalogusprijs (€, incl. BTW en BPM)",
                                    min_value=0, value=0, step=500, key=f"cat_{car_id}")
            if cat_h == 0:
                auto_results.append(None)
                continue
            catalogusprijs_i = float(cat_h)

        # Slimme default periode
        van_key = f"datum_van_{car_id}_{berekeningsjaar}"
        tot_key = f"datum_tot_{car_id}_{berekeningsjaar}"
        flip_pending_key = f"_flip_pending_{car_id}"

        # Wis datumkeys als het kenteken van deze auto-slot is veranderd
        prev_kv_key = f"_prev_kent_{car_id}"
        if st.session_state.get(prev_kv_key) != kenteken_i:
            st.session_state.pop(van_key, None)
            st.session_state.pop(tot_key, None)
            st.session_state.pop(flip_pending_key, None)
            st.session_state[prev_kv_key] = kenteken_i

        # Verwerk flip vóór widget-instantiatie (Streamlit staat geen schrijven toe ná render)
        if st.session_state.pop(flip_pending_key, False):
            _fv = st.session_state.get(van_key, date(berekeningsjaar, 1, 1))
            _ft = st.session_state.get(tot_key, date(berekeningsjaar, 12, 31))
            _jan1 = date(berekeningsjaar, 1, 1)
            _dec31 = date(berekeningsjaar, 12, 31)
            if _fv > _jan1:
                st.session_state[van_key] = _jan1
                st.session_state[tot_key] = _fv - timedelta(days=1)
            elif _ft < _dec31:
                st.session_state[van_key] = _ft + timedelta(days=1)
                st.session_state[tot_key] = _dec31

        if van_key not in st.session_state:
            if idx == 0:
                if ts_i and ts_i.year == berekeningsjaar:
                    st.session_state[van_key] = ts_i
                else:
                    st.session_state[van_key] = date(berekeningsjaar, 1, 1)
            else:
                prev_id = st.session_state["autos"][idx - 1]["id"]
                prev_tot = st.session_state.get(f"datum_tot_{prev_id}_{berekeningsjaar}",
                                                 date(berekeningsjaar, 6, 30))
                chained = prev_tot + timedelta(days=1)
                if chained <= date(berekeningsjaar, 12, 31):
                    st.session_state[van_key] = chained
                elif ts_i and ts_i.year == berekeningsjaar:
                    # Vorige auto loopt t/m 31-12: gebruik tenaamstelling als deze in het jaar valt
                    st.session_state[van_key] = ts_i
                else:
                    st.session_state[van_key] = date(berekeningsjaar, 1, 1)

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            datum_van_i = st.date_input(
                "Van",
                min_value=date(berekeningsjaar, 1, 1),
                max_value=date(berekeningsjaar, 12, 31),
                format="DD-MM-YYYY",
                key=van_key,
            )
        with col_d2:
            datum_tot_i = st.date_input(
                "Tot en met",
                value=date(berekeningsjaar, 12, 31),
                min_value=date(berekeningsjaar, 1, 1),
                max_value=date(berekeningsjaar, 12, 31),
                format="DD-MM-YYYY",
                key=tot_key,
            )

        if datum_tot_i < datum_van_i:
            st.error("Einddatum moet na de begindatum liggen.")
            auto_results.append(None)
            continue

        dagen_i = (datum_tot_i - datum_van_i).days + 1
        periode_label_i = f"{nl_date(datum_van_i)} t/m {nl_date(datum_tot_i)}"
        maanden_i = maandfractie(datum_van_i, datum_tot_i) * 12

        # Marge per auto: bij meerdere auto's in één berekening kan de ene een
        # marge-auto zijn en de andere niet. Dit stond eerder als één schakelaar
        # voor de hele pagina.
        marge_i = st.toggle(
            "Marge-auto (1,5%)",
            value=False,
            key=f"marge_{car_id}",
            help="Vink aan als deze auto als marge-auto is gekocht (zonder BTW-factuur). "
                 "Het lage forfait van 1,5% wordt daarnaast automatisch toegepast zodra "
                 "het jaar van ingebruikname en de vier jaren daarna voorbij zijn.",
        )

        # Bepaal of omdraaien mogelijk is (periode beslaat niet het hele jaar)
        jan1_y = date(berekeningsjaar, 1, 1)
        dec31_y = date(berekeningsjaar, 12, 31)
        _can_flip = datum_van_i > jan1_y or datum_tot_i < dec31_y

        cap_col, btn_col = st.columns([4, 1])
        with cap_col:
            st.caption(f"Periode: {periode_label_i} — **{dagen_i} dagen**")
        with btn_col:
            if _can_flip:
                if st.button("⇄ Omdraaien", key=f"flip_{car_id}",
                             help="Zet de periode om naar het complement in hetzelfde jaar "
                                  "(bijv. 1-3 t/m 31-12 ↔ 1-1 t/m 28-2)"):
                    st.session_state[flip_pending_key] = True
                    st.rerun()

        btw_i, btw_label_i = _btw_correctie(
            catalogusprijs_i, marge_i, datum_van_i, datum_tot_i,
            ingebruikname=auto_data_i["datum_tenaamstelling"],
            jaar=berekeningsjaar,
        )

        # Youngtimer: 35% van de waarde in het economisch verkeer in plaats van
        # een percentage van de catalogusprijs. De WEV staat niet in de
        # RDW-gegevens, dus die moet erbij worden gezet.
        youngtimer_i = is_youngtimer(det_i, berekeningsjaar)
        wev_i = None
        if youngtimer_i:
            st.warning(
                f"Deze auto is op 1 januari {berekeningsjaar} ouder dan "
                f"{youngtimer_leeftijdsgrens(berekeningsjaar)} jaar en valt onder de "
                f"youngtimerregeling: de bijtelling is 35% van de waarde in het "
                f"economisch verkeer, niet een percentage van de catalogusprijs. "
                f"Vul die waarde hieronder in. De BTW-correctie blijft over de "
                f"catalogusprijs lopen."
            )
            wev_h = st.number_input(
                "Waarde in het economisch verkeer (€)",
                min_value=0, value=0, step=500, key=f"wev_{car_id}",
            )
            wev_i = float(wev_h) if wev_h else None

        if youngtimer_i:
            if wev_i is None:
                bij_i, bij_label_i = None, "youngtimer — WEV nog invullen"
            else:
                bij_i, bij_label_i = bijtelling_youngtimer(wev_i, dagen_i)
        else:
            bij_i, bij_label_i = _bijtelling(
                catalogusprijs_i, auto_data_i["co2"], auto_data_i["brandstof"],
                berekeningsjaar, datum_van_i, datum_tot_i,
                eerste_toelating=auto_data_i["datum_eerste_toelating"],
            )

            melding_i = waarschuwing_regimejaar(
                is_nulemissie(auto_data_i["co2"], auto_data_i["brandstof"]),
                berekeningsjaar,
            )
            if melding_i:
                st.warning(melding_i)

            if (is_nulemissie(auto_data_i["co2"], auto_data_i["brandstof"])
                    and not is_plafondvrij(auto_data_i["brandstof"])):
                st.caption(
                    "Rijdt deze auto volledig op geïntegreerde zonnecellen (minstens "
                    "1 kilowattpiek, accu zonder lood)? Dan geldt het verlaagde "
                    "percentage over de hele catalogusprijs, zonder plafond. Dat is "
                    "niet uit de RDW-gegevens af te leiden en zit dus niet in de "
                    "berekening hieronder."
                )

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.html(f"""
            <div style="background:linear-gradient(135deg,#1a3a6e,#1e4680);color:white;
              border-radius:12px;padding:16px 20px;text-align:center;
              box-shadow:0 4px 14px rgba(26,58,110,.2);">
              <div style="font-size:11px;color:rgba(255,255,255,0.8);margin-bottom:4px;letter-spacing:.06em;">
                BTW-CORRECTIE PRIVÉGEBRUIK
              </div>
              <div style="font-size:30px;font-weight:bold;font-family:monospace;">{nl_euro(btw_i)}</div>
              <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-top:4px;">
                {btw_label_i} forfait &nbsp;·&nbsp; {maanden_i:.2f}/12 maanden
              </div>
            </div>""")
        with col_r2:
            bij_waarde = nl_euro(bij_i) if bij_i is not None else "—"
            st.html(f"""
            <div style="background:linear-gradient(135deg,#1a4d2e,#1e5c36);color:white;
              border-radius:12px;padding:16px 20px;text-align:center;
              box-shadow:0 4px 14px rgba(26,77,46,.2);">
              <div style="font-size:11px;color:rgba(255,255,255,0.8);margin-bottom:4px;letter-spacing:.06em;">
                BIJTELLING (FISCALE WAARDE)
              </div>
              <div style="font-size:30px;font-weight:bold;font-family:monospace;">{bij_waarde}</div>
              <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-top:4px;">
                {bij_label_i} &nbsp;·&nbsp; {dagen_i} dagen
              </div>
            </div>""")

        auto_results.append({
            "kenteken": kenteken_i,
            "auto": auto_data_i,
            "catalogusprijs": catalogusprijs_i,
            "periode_label": periode_label_i,
            "dagen": dagen_i,
            "maanden": maanden_i,
            "marge": marge_i,
            "youngtimer": youngtimer_i,
            "wev": wev_i,
            "btw": btw_i,
            "btw_label": btw_label_i,
            "bij": bij_i,
            "bij_label": bij_label_i,
        })

# ── Auto toevoegen ────────────────────────────────────────────────────────────
if n_autos < 5:
    if st.button("＋ Auto toevoegen", use_container_width=False):
        new_id = st.session_state["_next_id"]
        st.session_state["_next_id"] += 1
        last_id = st.session_state["autos"][-1]["id"]
        last_tot = st.session_state.get(
            f"datum_tot_{last_id}_{berekeningsjaar}",
            date(berekeningsjaar, 6, 30),
        )
        chained_van = last_tot + timedelta(days=1)
        if chained_van.year == berekeningsjaar:
            st.session_state[f"datum_van_{new_id}_{berekeningsjaar}"] = chained_van
        st.session_state["autos"].append({"id": new_id, "kenteken": ""})
        st.session_state["_focus_car_id"] = new_id
        st.rerun()

# ── Totalen (bij meerdere auto's) ─────────────────────────────────────────────
valid_results = [r for r in auto_results if r is not None]

if len(valid_results) > 1:
    total_btw = sum(r["btw"] for r in valid_results)
    # Een youngtimer zonder ingevulde WEV levert geen bedrag; die telt niet mee
    # en dat wordt eronder gemeld, zodat het totaal niet stil te laag uitkomt.
    bij_bedragen = [r["bij"] for r in valid_results if r["bij"] is not None]
    total_bij = sum(bij_bedragen)
    ontbrekend = len(valid_results) - len(bij_bedragen)
    st.markdown("---")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.html(f"""
        <div style="background:linear-gradient(135deg,#0f2a5e,#153470);color:white;
          border-radius:12px;padding:14px 20px;text-align:center;
          box-shadow:0 4px 14px rgba(15,42,94,.25);">
          <div style="font-size:11px;color:rgba(255,255,255,0.75);margin-bottom:4px;letter-spacing:.06em;">
            TOTAAL BTW-CORRECTIE
          </div>
          <div style="font-size:26px;font-weight:bold;font-family:monospace;">{nl_euro(total_btw)}</div>
          <div style="font-size:11px;color:rgba(255,255,255,0.6);margin-top:3px;">
            {len(valid_results)} auto's · {sum(r['dagen'] for r in valid_results)} dagen totaal
          </div>
        </div>""")
    with col_t2:
        st.html(f"""
        <div style="background:linear-gradient(135deg,#0f3d22,#134a28);color:white;
          border-radius:12px;padding:14px 20px;text-align:center;
          box-shadow:0 4px 14px rgba(15,61,34,.25);">
          <div style="font-size:11px;color:rgba(255,255,255,0.75);margin-bottom:4px;letter-spacing:.06em;">
            TOTAAL BIJTELLING
          </div>
          <div style="font-size:26px;font-weight:bold;font-family:monospace;">{nl_euro(total_bij)}</div>
          <div style="font-size:11px;color:rgba(255,255,255,0.6);margin-top:3px;">
            {len(bij_bedragen)} van {len(valid_results)} auto's · {berekeningsjaar}
          </div>
        </div>""")
    if ontbrekend:
        st.warning(
            f"{ontbrekend} auto('s) tellen niet mee in de totale bijtelling omdat de "
            f"waarde in het economisch verkeer nog niet is ingevuld."
        )

# ── PDF ───────────────────────────────────────────────────────────────────────
if valid_results:
    kenteken_label = "_".join(r["kenteken"] for r in valid_results)
    bestandsnaam = f"BTW_auto_{kenteken_label}_{berekeningsjaar}.pdf"

    if st.button("📄 Genereer PDF", use_container_width=True):
        try:
            pdf_bytes = _maak_pdf(valid_results, klant_naam, klant_nr, berekeningsjaar)
            st.session_state["pdf_bytes"] = pdf_bytes
            st.session_state["pdf_naam"] = bestandsnaam
        except Exception as e:
            st.error(f"PDF genereren mislukt: {e}")

    if "pdf_bytes" in st.session_state and st.session_state.get("pdf_naam") == bestandsnaam:
        st.download_button(
            label="📥 Download PDF",
            data=st.session_state["pdf_bytes"],
            file_name=bestandsnaam,
            mime="application/pdf",
            use_container_width=True,
        )

if valid_results:
    st.info(
        "**Bij een IB-ondernemer is de bijtelling nooit hoger dan de totale "
        "autokosten van het jaar** (afschrijving, brandstof, onderhoud, verzekering, "
        "motorrijtuigenbelasting). Die kosten zijn hier niet bekend, dus dat maximum "
        "is niet toegepast. Bij een lage catalogusprijs en weinig kosten kan de "
        "uitkomst hierboven dus te hoog zijn."
    )

st.caption(
    "Forfaitmethode art. 4 lid 2 Wet OB · BTW-correctie naar maanden, bijtelling naar "
    "dagen · Voertuiggegevens via RDW Open Data · Toekomstig: opslaan in AFAS-dossier."
)
