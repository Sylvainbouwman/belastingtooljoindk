"""Leest de TARIEVEN-constante uit een rentepagina zonder die pagina te draaien.

De pagina importeren gaat niet: dan lopen de Streamlit-aanroepen en de
netwerkcall naar belastingdienst.nl mee. De tabel wordt daarom uit de broncode
gelezen. Tests toetsen zo de reeks die de app werkelijk gebruikt, en niet een
kopie in de test die uit de pas kan lopen — precies de fout die deze module
helpt voorkomen.
"""

import ast
from datetime import date
from pathlib import Path

WORTEL = Path(__file__).resolve().parent.parent


def tarieven_uit_pagina(modulenaam: str) -> list[tuple[date, float]]:
    """De TARIEVEN van een pagina als [(ingangsdatum, percentage), ...], nieuw → oud."""
    pad = WORTEL / (modulenaam.replace(".", "/") + ".py")
    boom = ast.parse(pad.read_text(encoding="utf-8"))
    for knoop in boom.body:
        if isinstance(knoop, ast.Assign) and getattr(knoop.targets[0], "id", "") == "TARIEVEN":
            rijen = []
            for element in knoop.value.elts:
                datum_call, pct = element.elts
                jaar, maand, dag = (a.value for a in datum_call.args)
                rijen.append((date(jaar, maand, dag), float(pct.value)))
            return sorted(rijen, reverse=True)
    raise AssertionError(f"TARIEVEN niet gevonden in {pad}")


TARIEVEN_IB = tarieven_uit_pagina("pages.Belastingrente_IB")
TARIEVEN_VPB = tarieven_uit_pagina("pages.Belastingrente_VpB")
