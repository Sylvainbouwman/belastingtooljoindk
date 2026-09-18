"""Voer de echte invorderingsrentepagina uit met een nagebouwde Streamlit.

De pagina bevat geen rekenlogica maar wel de blokkades, en juist die blokkades
zijn het antwoord op twee keuzes van Sylvain: de opschorting tijdens uitstel
wordt niet doorgerekend maar uitgevraagd, en art. 28c wordt alleen gesignaleerd.
Een blokkade die stilletjes wegvalt levert een te hoog bedrag op, dus zij hoort
onder test te staan.

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


def test_uitstel_ja_blokkeert_en_noemt_de_grond():
    """Art. 28 lid 3 IW 1990 schort de rente op; deze versie rekent dat niet door."""
    nep = pagina(**{"uitstel van betaling verleend?": "ja",
                    "Op welke grond": "25-21"})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "rekent de opschorting tijdens uitstel niet door")
    assert meldingen_met(nep, "error", "art. 25 lid 21")


def test_uitstel_ja_zonder_grond_vraagt_de_grond():
    nep = pagina(**{"uitstel van betaling verleend?": "ja"})
    assert nep.uitkomst_getoond is False
    assert meldingen_met(nep, "error", "Vul de grond van het uitstel in")


def test_herlevingstijdvak_wordt_getoond_bij_een_grond_uit_artikel_6_lid_1():
    """Art. 28 lid 4 IW 1990 met art. 6 lid 1 Uitvoeringsbesluit IW 1990."""
    nep = pagina(**{"uitstel van betaling verleend?": "ja", "Op welke grond": "25-5"})
    assert meldingen_met(nep, "info", "eerste dag van het jaar volgend")


def test_grond_zonder_aangewezen_herlevingstijdvak_beweert_niets():
    """Art. 25 lid 3 staat in art. 28 lid 3 maar niet in lid 4, en art. 6 van het
    Uitvoeringsbesluit wijst er geen tijdvak voor aan."""
    nep = pagina(**{"uitstel van betaling verleend?": "ja", "Op welke grond": "25-3"})
    assert meldingen_met(nep, "info", "geen herlevingstijdvak voor aan")


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


# ── Art. 28c: alleen signalering ────────────────────────────────────────────

def test_artikel_28c_wordt_gesignaleerd_en_niet_gerekend():
    nep = pagina(**{"uitstel van betaling verleend?": "nee"})
    getoond = " ".join(t for _, t in nep.meldingen)
    assert "art. 28c IW 1990" in getoond
    assert "rekent die grondslag niet uit" in getoond


def test_de_pagina_kent_geen_grondslag_28c():
    """Art. 28c mag niet als rekenoptie in de keuzelijst staan."""
    nep = pagina(**{"uitstel van betaling verleend?": "nee"})
    assert nep.antwoorden.get("Welke grondslag?") is None
    bron = PAGINA.read_text(encoding="utf-8")
    assert '"28c":' not in bron.split("GRONDSLAGEN = {", 1)[1].split("}", 1)[0]
