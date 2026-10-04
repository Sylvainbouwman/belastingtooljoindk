"""Voer de echte invorderingsrentepagina uit met een nagebouwde Streamlit.

De pagina bevat geen rekenlogica maar wel de blokkades, en juist die blokkades
beschermen de rekenkern: zonder antwoord op de uitstelvraag en zonder tijdig
verzoek bij art. 28c komt er geen uitkomst, en waar de wet het tijdvak open laat
(betaling na afloop van het uitstel) blijft het bij een melding. Een blokkade die
stilletjes wegvalt levert een te hoog bedrag op, dus zij hoort onder test te staan.

Er wordt geen Streamlit-server gestart en er gaat geen verkeer naar buiten. De
nep-Streamlit geeft per widget de opgegeven waarde terug, gezocht op een stukje
van het label, en anders de standaardwaarde die de pagina zelf meegeeft.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

PAGINA = Path(__file__).resolve().parents[1] / "pages" / "Invorderingsrente.py"


class Gestopt(Exception):
    """Wat `st.stop()` doet: de pagina afbreken."""


class _Blok:
    def __enter__(self):
        return self

    def __exit__(self, *rest):
        return False


class NepStreamlit:
    def __init__(self, antwoorden):
        self.antwoorden = antwoorden
        self.meldingen = []
        self.uitkomst_getoond = False
        self.session_state = {}

    # ── invoer ──
    def _waarde(self, label, standaard):
        for sleutel, waarde in self.antwoorden.items():
            if sleutel in label:
                return waarde
        return standaard

    def radio(self, label, options, **kw):
        return self._waarde(label, options[0])

    def selectbox(self, label, options, **kw):
        return self._waarde(label, options[0])

    def date_input(self, label, value=None, **kw):
        return self._waarde(label, value)

    def number_input(self, label, value=0.0, **kw):
        return self._waarde(label, value)

    def toggle(self, label, value=False, **kw):
        return self._waarde(label, value)

    def checkbox(self, label, **kw):
        return self._waarde(label, False)

    # ── opmaak ──
    def columns(self, aantal):
        return [_Blok() for _ in range(aantal)]

    def expander(self, label, expanded=False):
        return _Blok()

    def html(self, tekst):
        self.uitkomst_getoond = True
        self.meldingen.append(("html", tekst))

    def __getattr__(self, naam):
        # markdown, caption, error, warning, success, info: alles wordt vastgelegd.
        def opnemen(bericht="", *rest, **kw):
            self.meldingen.append((naam, str(bericht)))
        return opnemen

    def stop(self):
        raise Gestopt()


def pagina(**antwoorden):
    """Draai de pagina en geef de nep-Streamlit terug."""
    nep = NepStreamlit(antwoorden)
    bewaard = {naam: sys.modules.get(naam) for naam in ("streamlit", "_ui")}
    sys.modules["streamlit"] = nep
    sys.modules.pop("_ui", None)          # herimporteren tegen de nep-Streamlit
    try:
        ruimte = {"__name__": "__main__", "__file__": str(PAGINA)}
        try:
            exec(compile(PAGINA.read_text(encoding="utf-8"), str(PAGINA), "exec"), ruimte)
        except Gestopt:
            pass
    finally:
        for naam, module in bewaard.items():
            if module is None:
                sys.modules.pop(naam, None)
            else:
                sys.modules[naam] = module
    return nep


def meldingen_met(nep, soort, fragment):
    return [t for s, t in nep.meldingen if s == soort and fragment in t]


# ── Uitstel: uitvragen en blokkeren ─────────────────────────────────────────

def test_uitstel_niet_ingevuld_blokkeert_de_uitkomst():
    """Keuze van Sylvain: geen uitkomst zolang niet is ingevuld of er uitstel is."""
    nep = pagina()
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "Vul eerst in of er uitstel van betaling is verleend")


def test_uitstel_nee_geeft_wel_een_uitkomst():
    nep = pagina(**{"uitstel van betaling verleend?": "nee"})
    assert nep.uitkomst_getoond is True


def test_uitstel_ja_zonder_einddatum_schort_de_rente_op_en_geeft_een_uitkomst():
    """Art. 28 lid 3 IW 1990: geen rente over de tijd waarvoor uitstel is verleend."""
    nep = pagina(**{"uitstel van betaling verleend?": "ja",
                    "Op welke grond": "25-21"})
    assert nep.uitkomst_getoond is True
    assert meldingen_met(nep, "info", "uitstel van betaling was verleend")


def test_uitstel_ja_zonder_grond_vraagt_de_grond():
    nep = pagina(**{"uitstel van betaling verleend?": "ja"})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "Vul de grond van het uitstel in")


def test_beeindigd_uitstel_zonder_datum_van_de_gebeurtenis_vraagt_die_datum():
    nep = pagina(**{"uitstel van betaling verleend?": "ja", "Op welke grond": "25-5",
                    "door de ontvanger beëindigd": True})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "Vul de datum in van de handeling")


def test_beeindigd_uitstel_toont_de_herlevingsdatum():
    """Art. 28 lid 4 IW 1990 met art. 6 lid 1 Uitvoeringsbesluit IW 1990."""
    nep = pagina(**{"uitstel van betaling verleend?": "ja", "Op welke grond": "25-5",
                    "Dagtekening aanslagbiljet": date(2025, 1, 15),
                    "Datum van de betaling": date(2026, 6, 10),
                    "Uitstel verleend vanaf": date(2025, 2, 27),
                    "door de ontvanger beëindigd": True,
                    "Datum van de handeling of gebeurtenis": date(2025, 9, 15)})
    assert nep.uitkomst_getoond is True
    gezien = " ".join(t for _, t in nep.meldingen)
    assert "Rente herleeft op | 12-02-2026" in gezien


def test_betaling_na_de_uitsteltermijn_bij_een_grond_van_lid_4_geeft_geen_uitkomst():
    """Art. 28 lid 4: het tijdvak laat de wet aan een AMvB die het niet regelt."""
    nep = pagina(**{"uitstel van betaling verleend?": "ja", "Op welke grond": "25-5",
                    "Uitstel verleend tot en met": date.today() - timedelta(days=10)})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "algemene maatregel van bestuur")


def test_betaling_na_de_uitsteltermijn_bij_artikel_25_lid_3_geeft_wel_een_uitkomst():
    nep = pagina(**{"uitstel van betaling verleend?": "ja", "Op welke grond": "25-3",
                    "Uitstel verleend tot en met": date.today() - timedelta(days=10)})
    assert nep.uitkomst_getoond is True


def test_grond_zonder_aangewezen_herlevingstijdvak_beweert_niets():
    """Art. 25 lid 3 staat in art. 28 lid 3 maar niet in lid 4, en art. 6 van het
    Uitvoeringsbesluit wijst er geen tijdvak voor aan: geen vraag naar beëindiging."""
    nep = pagina(**{"uitstel van betaling verleend?": "ja", "Op welke grond": "25-3"})
    assert meldingen_met(nep, "caption", "geen herlevingstijdvak voor aan")


# ── Art. 28 lid 5: de aangewezen uitzonderingen ─────────────────────────────

def test_aangevinkte_uitzondering_blokkeert_de_uitkomst():
    """Art. 6bis Uitvoeringsbesluit IW 1990, aangewezen op grond van art. 28 lid 5."""
    nep = pagina(**{"uitstel van betaling verleend?": "nee",
                    "Aanhoudaanbod": True})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "er is een uitzondering aangevinkt")


# ── Art. 28: tijdige betaling ───────────────────────────────────────────────

def test_betaling_binnen_de_termijn_geeft_geen_rente():
    """Art. 28 lid 1 vraagt overschrijding van de enige of laatste betalingstermijn."""
    nep = pagina(**{"Dagtekening aanslagbiljet": date.today(),
                    "Datum van de betaling": date.today()})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "success", "Geen invorderingsrente")


def test_periode_voor_de_tariefreeks_wordt_geweigerd():
    """Het Besluit belasting- en invorderingsrente geldt pas vanaf 1 juni 2020."""
    nep = pagina(**{"uitstel van betaling verleend?": "nee",
                    "Dagtekening aanslagbiljet": date(2020, 1, 6),
                    "Datum van de betaling": date(2020, 3, 1)})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "oudste ingangsdatum die deze tool kent")


def test_voorlopige_aanslag_in_termijnen_vraagt_de_vervaldag():
    """Art. 9 lid 5 IW 1990 met 9.1 Leidraad Invordering 2008: die vervaldag wordt
    niet afgeleid maar uitgevraagd."""
    nep = pagina(**{"Soort belastingaanslag": "voorlopig-in-termijnen"})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "Vul de vervaldag van de laatste betalingstermijn in")


# ── Art. 28a ────────────────────────────────────────────────────────────────

def test_artikel_28a_weigert_de_voorlopige_aanslag_van_artikel_9_lid_5():
    """Art. 28a lid 4 IW 1990."""
    nep = pagina(**{"Welke grondslag?": "28a",
                    "voorlopige aanslag als bedoeld in art. 9 lid 5": True})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "lid 4")


def test_artikel_28a_weigert_als_de_vertraging_te_wijten_is():
    """Art. 28a lid 3 IW 1990."""
    nep = pagina(**{"Welke grondslag?": "28a",
                    "te wijten": True})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "lid 3")


def test_artikel_28a_binnen_zes_weken_geeft_geen_vergoeding():
    """Art. 28a lid 1 IW 1990."""
    nep = pagina(**{"Welke grondslag?": "28a",
                    "Dagtekening aanslag of beschikking": date.today() - timedelta(days=10),
                    "Datum waarop is uitbetaald": date.today()})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "success", "binnen zes weken na de dagtekening")


def test_artikel_28a_rekent_na_zes_weken_wel():
    nep = pagina(**{"Welke grondslag?": "28a"})
    assert nep.uitkomst_getoond is True


def test_artikel_28a_vraagt_de_periode_van_de_al_vergoede_belastingrente():
    """Art. 28a lid 2, tweede volzin IW 1990: die dagen tellen niet mee. Zonder de
    periode zou de tool te veel vergoeding berekenen."""
    nep = pagina(**{"Welke grondslag?": "28a",
                    "al belastingrente vergoed": True})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "Vul beide datums")


def test_artikel_28a_trekt_de_opgegeven_dagen_af():
    vandaag = date.today()
    nep = pagina(**{"Welke grondslag?": "28a",
                    "Dagtekening aanslag of beschikking": vandaag - timedelta(days=200),
                    "Datum waarop is uitbetaald": vandaag,
                    "al belastingrente vergoed": True,
                    "Belastingrente vergoed vanaf": vandaag - timedelta(days=199),
                    "Belastingrente vergoed tot en met": vandaag - timedelta(days=100)})
    assert nep.uitkomst_getoond is True
    assert meldingen_met(nep, "info", "tellen niet mee omdat daarover al")


# ── Art. 28b ────────────────────────────────────────────────────────────────

def test_artikel_28b_vraagt_om_het_afgewezen_uitstelverzoek():
    """Art. 28b lid 1 IW 1990 stelt dat als voorwaarde."""
    nep = pagina(**{"Welke grondslag?": "28b"})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "info", "bij beschikking heeft")


def test_artikel_28b_rekent_met_een_afgewezen_verzoek():
    nep = pagina(**{"Welke grondslag?": "28b",
                    "bij beschikking is afgewezen": True,
                    "Dagtekening aanslagbiljet": date.today() - timedelta(days=400)})
    assert nep.uitkomst_getoond is True


def test_artikel_28b_vraagt_niet_naar_uitstel():
    """De uitstelvraag hoort bij art. 28, want art. 28 lid 3 ziet op het in rekening
    brengen van rente. Bij een vergoeding speelt zij niet."""
    nep = pagina(**{"Welke grondslag?": "28b",
                    "bij beschikking is afgewezen": True,
                    "Dagtekening aanslagbiljet": date.today() - timedelta(days=400)})
    assert not meldingen_met(nep, "error", "uitstel van betaling is verleend")


# ── Art. 28c: vergoeding bij heffing in strijd met het Unierecht ────────────

def test_artikel_28c_staat_in_de_keuzelijst():
    bron = PAGINA.read_text(encoding="utf-8")
    assert '"28c":' in bron.split("GRONDSLAGEN = {", 1)[1].split("}", 1)[0]


def test_artikel_28c_zonder_antwoord_over_het_verzoek_geeft_geen_uitkomst():
    """Art. 28c lid 1 en 3: alleen op verzoek, binnen zes weken na de beschikking."""
    nep = pagina(**{"Welke grondslag?": "28c"})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "Nog geen uitkomst")


def test_artikel_28c_zonder_tijdig_verzoek_geeft_geen_vergoeding():
    nep = pagina(**{"Welke grondslag?": "28c", "tijdig ingediend?": "nee"})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "Zonder tijdig verzoek")


def test_artikel_28c_rekent_met_een_tijdig_verzoek():
    nep = pagina(**{"Welke grondslag?": "28c", "tijdig ingediend?": "ja"})
    assert nep.uitkomst_getoond is True


def test_artikel_28c_zonder_dagen_in_het_tijdvak_geeft_geen_vergoeding():
    vandaag = date.today()
    nep = pagina(**{"Welke grondslag?": "28c", "tijdig ingediend?": "ja",
                    "Datum waarop de belasting is betaald": vandaag,
                    "Datum van de terugbetaling": vandaag})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "success", "bevat hier geen dag")


def test_artikel_28c_vraagt_de_periode_van_de_al_vergoede_belastingrente():
    nep = pagina(**{"Welke grondslag?": "28c", "tijdig ingediend?": "ja",
                    "belastingrente is vergoed": True})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "Vul beide datums in")


def test_artikel_28c_trekt_de_opgegeven_dagen_af():
    vandaag = date.today()
    nep = pagina(**{"Welke grondslag?": "28c", "tijdig ingediend?": "ja",
                    "belastingrente is vergoed": True,
                    "Vergoede belastingrente: vanaf": vandaag - timedelta(days=300),
                    "Vergoede belastingrente: tot en met": vandaag - timedelta(days=200)})
    assert nep.uitkomst_getoond is True
    assert meldingen_met(nep, "info", "belastingrente of invorderingsrente op grond van art. 28b")
