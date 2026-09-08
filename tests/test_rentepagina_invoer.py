"""Voer de echte berekeningssectie uit; geen Streamlit-start of bronverkeer."""
import ast
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
import _rente


class Gestopt(Exception):
    pass


class VasteDatum(date):
    @classmethod
    def today(cls):
        return cls(2026, 9, 8)


def pagina(naam, **invoer):
    pad = Path(__file__).resolve().parents[1] / 'pages' / naam
    tekst = pad.read_text(encoding='utf-8')
    boom = ast.parse(tekst)
    tariefnode = next(n for n in boom.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'TARIEVEN' for t in n.targets))
    ns = {'date': VasteDatum}
    exec(compile(ast.Module(body=[tariefnode], type_ignores=[]), str(pad), 'exec'), ns)
    meldingen, berekeningen = [], []

    def stop():
        raise Gestopt()

    def bereken(*args):
        berekeningen.append(args)
        return _rente.bereken(*args)

    ns.update(vars(_rente))
    ns.update(date=VasteDatum, TARIEVEN=ns['TARIEVEN'], bereken=bereken,
              st=SimpleNamespace(stop=stop, **{
                  k: (lambda bericht, soort=k: meldingen.append((soort, bericht)))
                  for k in ['error', 'warning', 'success', 'caption']}),
              op_verzoek=False, verzoek_datum=None, aanslag_type='navordering',
              aangifte_ontvangen=None, aangifte_gevolgd=True,
              voorlopige_aanslag_conform=False, uiterste_aangiftedatum=date(2026, 5, 1),
              dagtekening=date(2026, 7, 1), r_start=date(2026, 1, 1), bedrag=10000)
    ns.update(invoer)
    sectie = tekst.split('# ── Berekening', 1)[1].split('\n', 1)[1]
    sectie = sectie.split('totaal_dagen =', 1)[0]
    try:
        exec(compile(sectie, str(pad), 'exec'), ns)
    except Gestopt:
        pass
    return meldingen, berekeningen, ns


@pytest.mark.parametrize('naam', ['Belastingrente_IB.py', 'Belastingrente_VpB.py'])
def test_verzoek_zonder_datum_blokkeert_voor_berekening(naam):
    m, b, _ = pagina(naam, op_verzoek=True)
    assert not b
    assert any(s == 'error' and 'datum' in t for s, t in m)


@pytest.mark.parametrize('naam', ['Belastingrente_IB.py', 'Belastingrente_VpB.py'])
def test_verzoek_met_datum_behoudt_verzoekroute(naam):
    _, b, ns = pagina(naam, op_verzoek=True, verzoek_datum=date(2026, 3, 1))
    assert b
    assert ns['reden'] == 'navordering-op-verzoek'


def test_vpb_voor_tariefreeks_rekent_niet_met_oudste_tarief():
    m, b, _ = pagina('Belastingrente_VpB.py', r_start=date(2001, 7, 1))
    assert not b
    assert any(s == 'error' and 'tariefreeks' in t for s, t in m)


def test_eerste_gedekte_dag_mag_wel():
    _, b, _ = pagina('Belastingrente_VpB.py', r_start=date(2012, 1, 1))
    assert b


@pytest.mark.parametrize('naam', ['Belastingrente_IB.py', 'Belastingrente_VpB.py'])
def test_toekomst_is_raming_ook_binnen_zelfde_jaar(naam):
    m, b, _ = pagina(naam, dagtekening=date(2026, 10, 1))
    assert b
    assert any(s == 'warning' and 'raming' in t for s, t in m)


@pytest.mark.parametrize('naam', ['Belastingrente_IB.py', 'Belastingrente_VpB.py'])
def test_historische_periode_geen_toekomstwaarschuwing(naam):
    m, b, _ = pagina(naam)
    assert b
    assert not any('raming' in t for _, t in m)


def test_vpb_vrijstelling_is_een_gebruikersverklaring():
    m, b, _ = pagina('Belastingrente_VpB.py', aanslag_type='regulier',
                     voorlopige_aanslag_conform=True)
    assert not b
    assert any(s == 'caption' and 'uw verklaring' in t for s, t in m)
